"""會計拋轉：把 MRP II 的存貨與交易依「會計科目對應」產生傳票，送到「資料助秘之一般公司會計」。

格式與「資料助秘之一般公司進銷存」「人事薪資差勤」相同（zms-gl）：
1. 拋轉檔（.zmsgl，JSON）：在會計系統「傳票作業 → 拋轉匯入」匯入。
2. 直接傳送：會計系統開著「手機連線服務」（埠 8765）時，用會計系統的帳號密碼直接送過去。
會計端匯入後產生「未審核」傳票；同一批次（batch_uid）不會被重複匯入；缺少的明細科目、客戶、廠商會自動建立。
拋轉過的來源單據會標上批次；要重新拋轉須先「取消拋轉」（已直接傳送的批次，會先請會計系統刪除未審核傳票）。

分錄（永續盤存，金額一律為本位幣；存貨科目依料件類型：原料／包材→原料、半成品→在製品、成品→製成品）：
* 進貨驗收 PUR：借 存貨、進項稅額／貸 應付帳款（往來：廠商）
* 工單領料 ISS（含完工倒扣）：借 在製品／貸 存貨（先進先出成本）
* 報工 RPT（每日彙總）：借 在製品／貸 已分攤直接人工、已分攤製造費用（工時 × 工作中心費率）
* 完工入庫 CMP：借 存貨／貸 在製品
* 出貨 SHP：借 應收帳款（往來：客戶）／貸 銷貨收入、銷項稅額；借 銷貨成本／貸 存貨
* 庫存調整 ADJ：借貸 存貨與存貨盤盈虧（報廢原因記存貨報廢損失）
期初開帳（BEG）與調撥（TRF）不拋轉：期初請在會計系統用開帳傳票，調撥不改變存貨科目。
"""
import datetime as dt
import json
import time
import urllib.error
import urllib.request
import uuid
from collections import defaultdict
from decimal import Decimal

from . import APP_NAME, APP_VERSION, rocdate
from .core import D0, BizError, date, money

FORMAT = "zms-gl"
SCOPES = {"PUR": "進貨驗收", "ISS": "工單領料", "RPT": "報工（人工與製費）", "CMP": "完工入庫", "SHP": "出貨",
          "ADJ": "庫存調整"}
INV_KEY = {"R": "INV_RAW", "P": "INV_RAW", "X": "INV_RAW", "S": "INV_WIP", "F": "INV_FG"}


class GL:
    # ================================================================ 科目
    def _acct(self):
        rows = {r["map_code"]: (r["account_no"], r["account_name"]) for r in self.db.rows("SELECT * FROM acc_account_map")}
        need = ("INV_RAW", "INV_WIP", "INV_FG", "VAT_IN", "AP", "AR", "SALES", "VAT_OUT", "COGS", "LABOR_APPLIED",
                "OH_APPLIED", "SCRAP", "INV_ADJ")
        miss = [k for k in need if k not in rows or not rows[k][0]]
        if miss:
            raise BizError("會計科目對應缺少：%s，請到「成本會計 → 會計科目對應」設定" % "、".join(miss))
        for k, (a, n) in rows.items():
            if k in need and not (a.isdigit() and len(a) == 4):
                raise BizError("會計科目對應 %s 的科目代號 %s 要是四碼明細科目" % (k, a))
        return rows

    # ================================================================ 待拋轉
    def gl_pending(self, date_from, date_to):
        """各類別尚未拋轉的筆數。"""
        self.need("ACC", 1)
        f, t = date(date_from), date(date_to)
        out = dict.fromkeys(SCOPES, 0)
        out["PUR"] = self.db.value("SELECT COUNT(*) FROM pur_receipt_h WHERE status='A' AND gl_batch_id IS NULL AND "
                                   "rcv_date BETWEEN %s AND %s", (f, t))
        out["SHP"] = self.db.value("SELECT COUNT(*) FROM sal_ship_h WHERE status='A' AND gl_batch_id IS NULL AND "
                                   "ship_date BETWEEN %s AND %s", (f, t))
        for r in self.db.rows("SELECT doc_type, COUNT(DISTINCT doc_no) c FROM inv_txn WHERE gl_batch_id IS NULL AND "
                              "doc_type IN ('ISS','CMP','ADJ') AND txn_time>=%s AND txn_time<%s GROUP BY doc_type",
                              (f, t + dt.timedelta(days=1))):
            out[r["doc_type"]] = r["c"]
        out["RPT"] = self.db.value("SELECT COUNT(*) FROM sfc_report WHERE gl_batch_id IS NULL AND (setup_hours+run_hours)>0 "
                                   "AND start_time>=%s AND start_time<%s", (f, t + dt.timedelta(days=1)))
        return out

    # ================================================================ 預覽
    def gl_preview(self, date_from, date_to, scopes=None, with_quiet=False):
        """回傳 (傳票清單, 來源清單)；with_quiet＝True 時另回傳「借貸相抵、不需傳票」的來源（仍要標記為已處理）。不寫入資料庫。傳票：dict(ref, date, src, memo, lines[account, summary, debit,
        credit, partner_kind, partner, dept], total)。"""
        self.need("ACC", 1)
        f, t = date(date_from), date(date_to)
        if f > t:
            raise BizError("起始日不能晚於結束日")
        t1 = t + dt.timedelta(days=1)
        scopes = [s for s in SCOPES if s in set(scopes or SCOPES)]
        A = self._acct()
        itype = {r["id"]: r["item_type"] for r in self.db.rows("SELECT id, item_type FROM itm_item")}
        vouchers, sources, quiet = [], [], []

        def acct(key):
            return A[key][0]

        def inv_acct(item_id):
            return acct(INV_KEY.get(itype.get(item_id), "INV_RAW"))

        def V(ref, d, src, memo, nets, summary, partner=None, src_keys=()):
            """nets：{(科目, 往來種類, 往來代號): 金額（正借負貸）}"""
            lines = []
            for (a, pk, p), amt in sorted(nets.items(), key=lambda kv: (kv[1] < 0, kv[0][0])):
                amt = money(amt)
                if amt == 0:
                    continue
                lines.append(dict(account=a, summary=summary[:100], debit=amt if amt > 0 else D0,
                                  credit=-amt if amt < 0 else D0, partner_kind=pk or "", partner=p or "", dept=""))
            dr = sum((x["debit"] for x in lines), D0)
            cr = sum((x["credit"] for x in lines), D0)
            if not lines:
                quiet.extend(src_keys)       # 例：半成品完工入庫，借貸都是在製品
                return
            if dr != cr:      # 四捨五入差額（極少發生）：調整到最大一行
                big = max(lines, key=lambda x: x["debit"] + x["credit"])
                if big["debit"]:
                    big["debit"] += cr - dr
                else:
                    big["credit"] += dr - cr
                dr = cr = max(dr, cr)
            vouchers.append(dict(ref=ref, date=d, src=src, memo=memo[:100], lines=lines, total=dr))
            sources.append(list(src_keys))

        def txn_by_doc(doc_type):
            g = defaultdict(list)
            for r in self.db.rows("SELECT x.*, DATE(x.txn_time) d FROM inv_txn x WHERE x.gl_batch_id IS NULL AND "
                                  "x.doc_type=%s AND x.txn_time>=%s AND x.txn_time<%s ORDER BY x.id", (doc_type, f, t1)):
                g[(r["doc_no"], r["d"])].append(r)
            return g

        def tax_split(amount, tax_type, rate):
            """依稅別回傳 (未稅, 稅額)：1 外加、2 內含、3 零稅、4 免稅。"""
            amount, rate = Decimal(amount), Decimal(str(rate or 0))
            if str(tax_type) == "1":
                return amount, money(amount * rate)
            if str(tax_type) == "2":
                tax = money(amount - amount / (1 + rate))
                return amount - tax, tax
            return amount, D0

        # ---------------------------------------------------------- 進貨驗收
        if "PUR" in scopes:
            for h in self.db.rows("SELECT r.*, s.sup_code, s.sup_name, o.tax_type, o.tax_rate FROM pur_receipt_h r "
                                  "JOIN pur_supplier s ON s.id=r.supplier_id LEFT JOIN pur_order_h o ON o.id=(SELECT p.po_id "
                                  "FROM pur_receipt_d d JOIN pur_order_d p ON p.id=d.po_line_id WHERE d.rcv_id=r.id LIMIT 1) "
                                  "WHERE r.status='A' AND r.gl_batch_id IS NULL AND r.rcv_date BETWEEN %s AND %s "
                                  "ORDER BY r.rcv_date, r.id", (f, t)):
                txns = self.db.rows("SELECT * FROM inv_txn WHERE doc_type='RCV' AND doc_no=%s", (h["rcv_no"],))
                gross = sum((Decimal(x["amount"]) for x in txns), D0)
                if not gross:
                    continue
                net, tax = tax_split(gross, h["tax_type"] or "1", h["tax_rate"] or 0)
                nets = defaultdict(lambda: D0)
                for x in txns:                                   # 內含稅時存貨依比例扣掉稅額
                    nets[(inv_acct(x["item_id"]), "", "")] += Decimal(x["amount"]) * net / gross
                nets[(acct("VAT_IN"), "", "")] += tax
                nets[(acct("AP"), "V", h["sup_code"])] -= net + tax
                V(h["rcv_no"], h["rcv_date"], "PUR", "進貨 %s %s" % (h["rcv_no"], h["sup_name"]), nets,
                  "進貨 %s %s" % (h["rcv_no"], h["sup_name"]),
                  src_keys=[("rcv", h["id"])] + [("txn", x["id"]) for x in txns])

        # ---------------------------------------------------------- 出貨
        if "SHP" in scopes:
            for h in self.db.rows("SELECT s.*, c.cust_code, c.cust_name, o.tax_type, o.tax_rate FROM sal_ship_h s "
                                  "JOIN sal_customer c ON c.id=s.customer_id LEFT JOIN sal_order_h o ON o.id=(SELECT od.so_id "
                                  "FROM sal_ship_d d JOIN sal_order_d od ON od.id=d.so_line_id WHERE d.ship_id=s.id LIMIT 1) "
                                  "WHERE s.status='A' AND s.gl_batch_id IS NULL AND s.ship_date BETWEEN %s AND %s "
                                  "ORDER BY s.ship_date, s.id", (f, t)):
                txns = self.db.rows("SELECT * FROM inv_txn WHERE doc_type='SHP' AND doc_no=%s", (h["ship_no"],))
                net, tax = tax_split(Decimal(h["base_untaxed_amount"] or 0), h["tax_type"] or "1", h["tax_rate"] or 0)
                nets = defaultdict(lambda: D0)
                nets[(acct("AR"), "C", h["cust_code"])] += net + tax
                nets[(acct("SALES"), "", "")] -= net
                nets[(acct("VAT_OUT"), "", "")] -= tax
                for x in txns:                                   # 出貨成本（先進先出）
                    nets[(acct("COGS"), "", "")] -= Decimal(x["amount"])
                    nets[(inv_acct(x["item_id"]), "", "")] += Decimal(x["amount"])
                V(h["ship_no"], h["ship_date"], "SHP", "出貨 %s %s" % (h["ship_no"], h["cust_name"]), nets,
                  "出貨 %s %s" % (h["ship_no"], h["cust_name"]),
                  src_keys=[("ship", h["id"])] + [("txn", x["id"]) for x in txns])

        # ---------------------------------------------------------- 領料、完工、調整（依存貨異動帳）
        names = {"ISS": "工單領料", "CMP": "完工入庫", "ADJ": "庫存調整"}
        for code in ("ISS", "CMP", "ADJ"):
            if code not in scopes:
                continue
            reasons = {}
            if code == "ADJ":
                reasons = {r["adj_no"]: r["reason"] for r in self.db.rows("SELECT adj_no, reason FROM inv_adjust_h")}
            for (no, d), txns in txn_by_doc(code).items():
                nets = defaultdict(lambda: D0)
                wo = {x["wo_id"] for x in txns if x["wo_id"]}
                wo_no = self.db.value("SELECT wo_no FROM sfc_work_order WHERE id=%s", (min(wo),)) if wo else ""
                for x in txns:
                    amt = Decimal(x["amount"])
                    nets[(inv_acct(x["item_id"]), "", "")] += amt
                    if code in ("ISS", "CMP"):
                        nets[(acct("INV_WIP"), "", "")] -= amt
                    else:
                        key = "SCRAP" if reasons.get(no) == "S" and amt < 0 else "INV_ADJ"
                        nets[(acct(key), "", "")] -= amt
                memo = "%s %s%s" % (names[code], no, "（工單 %s）" % wo_no if wo_no else "")
                V(no, d, code, memo, nets, memo, src_keys=[("txn", x["id"]) for x in txns])

        # ---------------------------------------------------------- 報工（每日彙總）
        if "RPT" in scopes:
            by_day = defaultdict(list)
            for r in self.db.rows(
                    "SELECT r.*, DATE(r.start_time) d, w.wo_no, (SELECT c.labor_rate FROM acc_wc_rate c WHERE c.wc_id=r.wc_id "
                    "AND c.period<=DATE_FORMAT(r.start_time,'%%Y%%m') ORDER BY c.period DESC LIMIT 1) lr, (SELECT c.overhead_rate "
                    "FROM acc_wc_rate c WHERE c.wc_id=r.wc_id AND c.period<=DATE_FORMAT(r.start_time,'%%Y%%m') ORDER BY "
                    "c.period DESC LIMIT 1) ohr FROM sfc_report r JOIN sfc_wo_operation o ON o.id=r.wo_op_id JOIN "
                    "sfc_work_order w ON w.id=o.wo_id WHERE r.gl_batch_id IS NULL AND (r.setup_hours+r.run_hours)>0 AND "
                    "r.start_time>=%s AND r.start_time<%s ORDER BY r.start_time", (f, t1)):
                by_day[r["d"]].append(r)
            for d, reps in sorted(by_day.items()):
                nets = defaultdict(lambda: D0)
                for r in reps:
                    h = Decimal(r["setup_hours"]) + Decimal(r["run_hours"])
                    lab, oh = money(h * Decimal(r["lr"] or 0)), money(h * Decimal(r["ohr"] or 0))
                    nets[(acct("INV_WIP"), "", "")] += lab + oh
                    nets[(acct("LABOR_APPLIED"), "", "")] -= lab
                    nets[(acct("OH_APPLIED"), "", "")] -= oh
                memo = "報工 %s 共 %d 筆（人工與製費轉入在製品）" % (rocdate.show(d), len(reps))
                V("RPT-%s" % d.strftime("%Y%m%d"), d, "RPT", memo, nets, memo, src_keys=[("rpt", r["id"]) for r in reps])
        vouchers_sorted = sorted(zip(vouchers, sources), key=lambda vs: (vs[0]["date"], list(SCOPES).index(vs[0]["src"]),
                                                                          vs[0]["ref"]))
        out = [v for v, s in vouchers_sorted], [s for v, s in vouchers_sorted]
        return out + (quiet,) if with_quiet else out

    # ================================================================ 批次
    def next_gl_batch_no(self):
        prefix = "GL" + dt.date.today().strftime("%Y%m%d")
        last = self.db.value("SELECT MAX(batch_no) FROM acc_gl_batch WHERE batch_no LIKE %s", (prefix + "%",))
        return "%s%03d" % (prefix, int(last[len(prefix):]) + 1 if last else 1)

    def create_gl_batch(self, date_from, date_to, scopes=None):
        self.need("ACC")
        vouchers, sources, quiet = self.gl_preview(date_from, date_to, scopes, with_quiet=True)
        if not vouchers:
            raise BizError("這段期間沒有尚未拋轉的交易")
        A = self._acct()
        comp = self.company()
        no = self.next_gl_batch_no()
        uid = "%s-%s" % (comp.get("tax_id") or "ZMSMRP2", uuid.uuid4().hex)
        names = {a: n for a, n in A.values()}
        used = sorted({x["account"] for v in vouchers for x in v["lines"]})
        partners = []
        for kind, code in sorted({(x["partner_kind"], x["partner"]) for v in vouchers for x in v["lines"] if x["partner"]}):
            if kind == "C":
                p = self.db.row("SELECT cust_name name, short_name, tax_id, contact, phone, address FROM sal_customer "
                                "WHERE cust_code=%s", (code,)) or {}
            else:
                p = self.db.row("SELECT sup_name name, short_name, tax_id, contact, phone, address FROM pur_supplier "
                                "WHERE sup_code=%s", (code,)) or {}
            partners.append({k: str(p.get(k) or "") for k in ("name", "short_name", "tax_id", "contact", "phone", "address")}
                            | dict(kind=kind, code=code))
        payload = dict(
            format=FORMAT, version=1, batch_uid=uid, batch_no=no, source=APP_NAME, source_version=APP_VERSION,
            company=dict(name=comp.get("company_name", ""), tax_id=comp.get("tax_id") or ""),
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S"), created_by=self.user["user_name"] if self.user else "",
            date_from=date(date_from).isoformat(), date_to=date(date_to).isoformat(),
            accounts=[dict(code=a, name=names.get(a, "")) for a in used], partners=partners, departments=[],
            vouchers=[dict(ref=v["ref"], date=v["date"].isoformat(), type="轉", memo=v["memo"],
                           lines=[dict(account=x["account"], summary=x["summary"], debit=str(x["debit"]),
                                       credit=str(x["credit"]), partner_kind=x["partner_kind"], partner=x["partner"],
                                       dept=x["dept"]) for x in v["lines"]]) for v in vouchers])
        total = sum((v["total"] for v in vouchers), D0)
        scope = ",".join(s for s in SCOPES if s in set(scopes or SCOPES))
        with self.db.transaction():
            bid = self.db.exec("INSERT INTO acc_gl_batch (batch_no, batch_uid, date_from, date_to, scope, voucher_count, "
                               "total, payload, status, created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'N',%s)",
                               (no, uid, date(date_from), date(date_to), scope, len(vouchers), total,
                                json.dumps(payload, ensure_ascii=False), self.user_id))
            for v, src in zip(vouchers, sources):
                period = v["date"].strftime("%Y%m")
                self.db.exec("INSERT IGNORE INTO acc_period (period, start_date, end_date) VALUES (%s,%s,LAST_DAY(%s))",
                             (period, v["date"].replace(day=1), v["date"]))
                vid = self.db.exec("INSERT INTO acc_voucher_h (voucher_no, batch_id, voucher_date, period, source_type, "
                                   "status, summary, created_by) VALUES (%s,%s,%s,%s,%s,'N',%s,%s)",
                                   (v["ref"], bid, v["date"], period, v["src"], v["memo"], self.user_id))
                self.db.exec_many("INSERT INTO acc_voucher_d (voucher_id, line_no, account_no, dr_amount, cr_amount, summary, "
                                  "ref_doc_no) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                                  [(vid, i, x["account"], x["debit"], x["credit"], x["summary"], v["ref"])
                                   for i, x in enumerate(v["lines"], 1)])
                self._mark(src, bid)
            if quiet:
                self._mark(quiet, bid)
        self.log("GLBATCH", "acc_gl_batch", no, {"vouchers": len(vouchers), "total": total}, "ACC")
        return bid

    def _mark(self, src, bid):
        table = {"rcv": "pur_receipt_h", "ship": "sal_ship_h", "txn": "inv_txn", "rpt": "sfc_report"}
        by = defaultdict(list)
        for kind, key in src:
            by[table[kind]].append(int(key))
        for t, ids in by.items():
            self.db.exec("UPDATE %s SET gl_batch_id=%%s WHERE id IN (%s)" % (t, ",".join(map(str, ids))), (bid,))

    def gl_batches(self, limit=200):
        self.need("ACC", 1)
        return self.db.rows("SELECT b.id, b.batch_no, b.batch_uid, b.date_from, b.date_to, b.scope, b.voucher_count, b.total, "
                            "b.method, b.status, b.result, b.created_at, u.user_name FROM acc_gl_batch b LEFT JOIN sys_user u "
                            "ON u.id=b.created_by ORDER BY b.id DESC LIMIT %s", (limit,))

    def gl_batch(self, bid):
        self.need("ACC", 1)
        b = self.db.row("SELECT * FROM acc_gl_batch WHERE id=%s", (bid,))
        if not b:
            raise BizError("拋轉批次不存在")
        b["data"] = json.loads(b["payload"] or "{}")
        return b

    def gl_batch_vouchers(self, bid):
        self.need("ACC", 1)
        return self.db.rows("SELECT h.voucher_no, h.voucher_date, h.source_type, h.summary voucher_memo, d.line_no, "
                            "d.account_no, m.account_name, d.dr_amount, d.cr_amount, d.summary FROM acc_voucher_h h JOIN "
                            "acc_voucher_d d ON d.voucher_id=h.id LEFT JOIN (SELECT account_no, MIN(account_name) account_name "
                            "FROM acc_account_map GROUP BY account_no) m ON m.account_no=d.account_no WHERE h.batch_id=%s "
                            "ORDER BY h.voucher_date, h.id, d.line_no", (bid,))

    def export_gl_batch(self, bid, path):
        self.need("ACC")
        b = self.gl_batch(bid)
        if b["status"] == "X":
            raise BizError("此批次已取消")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(b["data"], f, ensure_ascii=False, indent=1)
        self.db.exec("UPDATE acc_gl_batch SET method='F', status=IF(status='S','S','E'), result=%s WHERE id=%s",
                     ("已匯出拋轉檔 %s" % time.strftime("%Y-%m-%d %H:%M"), bid))
        self.db.exec("UPDATE acc_voucher_h SET status=IF(status='S','S','E'), exported_at=NOW() WHERE batch_id=%s", (bid,))
        self.log("GLEXPORT", "acc_gl_batch", b["batch_no"], path, "ACC")

    def send_gl_batch(self, bid, remote):
        """直接傳送到會計系統（remote＝AcctClient）。"""
        self.need("ACC")
        b = self.gl_batch(bid)
        if b["status"] == "X":
            raise BizError("此批次已取消")
        res = remote.call("import_gl_batch", b["data"])
        nos = res.get("voucher_nos") or []
        text = "已送達會計系統：%d 張傳票 %s" % (len(nos), ("%s～%s" % (nos[0], nos[-1])) if nos else "")
        self.db.exec("UPDATE acc_gl_batch SET status='S', method='A', result=%s WHERE id=%s", (text[:500], bid))
        self.db.exec("UPDATE acc_voucher_h SET status='S', exported_at=NOW() WHERE batch_id=%s", (bid,))
        self.log("GLSEND", "acc_gl_batch", b["batch_no"], text, "ACC")
        return res

    def cancel_gl_batch(self, bid, remote=None):
        """取消拋轉：解除來源單據標記、刪除批次傳票。已直接傳送的批次會先請會計系統刪除（傳票須仍未審核）。"""
        self.need("ACC")
        b = self.gl_batch(bid)
        if b["status"] == "X":
            return
        if b["status"] == "S":
            if not remote:
                raise BizError("此批次已直接傳送到會計系統，取消時要連線到會計系統一併刪除傳票")
            remote.call("cancel_gl_import", b["batch_uid"])
        with self.db.transaction():
            for t in ("pur_receipt_h", "sal_ship_h", "inv_txn", "sfc_report"):
                self.db.exec("UPDATE %s SET gl_batch_id=NULL WHERE gl_batch_id=%%s" % t, (bid,))
            self.db.exec("DELETE d FROM acc_voucher_d d JOIN acc_voucher_h h ON h.id=d.voucher_id WHERE h.batch_id=%s", (bid,))
            self.db.exec("DELETE FROM acc_voucher_h WHERE batch_id=%s", (bid,))
            self.db.exec("UPDATE acc_gl_batch SET status='X', result=CONCAT(COALESCE(result,''), ' ／已取消') WHERE id=%s", (bid,))
        self.log("GLCANCEL", "acc_gl_batch", b["batch_no"], None, "ACC")


# ================================================================ 會計系統連線（直接傳送）
class AcctClient:
    """連到「資料助秘之一般公司會計」的手機連線服務（http://電腦:8765）。"""

    def __init__(self, url, uid, pw, timeout=20):
        self.url = (url or "").strip().rstrip("/")
        if self.url and not self.url.startswith("http"):
            self.url = "http://" + self.url
        if self.url.count(":") == 1:
            self.url += ":8765"
        self.uid, self.pw, self.timeout = uid, pw, timeout
        self.token = None

    def _post(self, path, body, token=None):
        data = json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")
        req = urllib.request.Request(self.url + path, data=data, method="POST",
                                     headers={"Content-Type": "application/json; charset=utf-8"})
        if token:
            req.add_header("Authorization", "Bearer " + token)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read().decode("utf-8")).get("error")
            except Exception:
                msg = str(e)
            raise BizError("會計系統回應錯誤：%s" % msg)
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise BizError("連不到會計系統（%s）：請確認會計系統已開啟，並在「系統管理 → 手機連線」打開連線服務。%s"
                           % (self.url, getattr(e, "reason", e)))

    def ping(self):
        try:
            with urllib.request.urlopen(urllib.request.Request(self.url + "/api/ping"), timeout=6) as r:
                info = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            raise BizError("連不到會計系統（%s）：%s" % (self.url, e))
        if "會計" not in str(info.get("app", "")):
            raise BizError("這個網址不是會計系統（%s）" % info.get("app", ""))
        return info

    def login(self):
        r = self._post("/api/login", dict(uid=self.uid, pw=self.pw))
        if "token" not in r:
            raise BizError("會計系統登入失敗：%s" % r.get("error", ""))
        self.token = r["token"]
        return r

    def call(self, method, *args, **kwargs):
        if not self.token:
            self.login()
        r = self._post("/api/call", dict(obj="books", method=method, args=list(args), kwargs=kwargs), self.token)
        if "biz" in r:
            raise BizError("會計系統：%s" % r["biz"])
        if "error" in r:
            raise BizError("會計系統：%s" % r["error"])
        return _plain(r.get("result"))


def _plain(o):
    if isinstance(o, dict):
        if len(o) == 1 and next(iter(o)) in ("$d", "$date", "$dt"):
            k, v = next(iter(o.items()))
            return Decimal(v) if k == "$d" else v
        return {k: _plain(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_plain(x) for x in o]
    return o
