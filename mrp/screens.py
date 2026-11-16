"""畫面用的服務方法：具名查詢、下拉選單、主檔清單，以及料件、BOM、途程、MPS、單據轉換等寫入動作。

電腦版直接呼叫；手機版透過連線服務呼叫同一組方法（伺服器端每次都檢查權限）。
"""
import datetime as dt
import math
from decimal import Decimal

from .core import BizError, date
from .views import LOOKUPS, VIEWS

ONE = Decimal(1)


class Screens:
    # ---------------------------------------------------------------- 讀取
    def v(self, name, *args):
        if name not in VIEWS:
            raise BizError("未登記的查詢：%s" % name)
        func, kind, sql = VIEWS[name]
        if not self.user:
            raise BizError("請先登入")
        if func:
            self.need(func, 1)
        if kind == "rows":
            return self.db.rows(sql, args or None)
        if kind == "row":
            return self.db.row(sql, args or None)
        return self.db.value(sql, args or None)

    def lookup(self, name):
        if name not in LOOKUPS or not self.user:
            raise BizError("未登記的選單：%s" % name)
        return [(r["k"], r["t"]) for r in self.db.rows(LOOKUPS[name])]

    def master_rows(self, key):
        from .ui.masters import MASTERS
        m = MASTERS[key]
        self.need(m["func"], 1)
        return self.db.rows("SELECT * FROM %s %s ORDER BY %s" % (
            m["table"], ("WHERE " + m["where"]) if m.get("where") else "", m["order"]))

    def dashboard_data(self):
        v = self.db.value
        return dict(
            items=v("SELECT COUNT(*) FROM itm_item WHERE is_active=1"),
            so=v("SELECT COUNT(*) FROM sal_order_h WHERE status IN ('A','P')"),
            po=v("SELECT COALESCE(SUM((d.qty-d.received_qty)*d.unit_price*h.exchange_rate),0) FROM pur_order_d d JOIN "
                 "pur_order_h h ON h.id=d.po_id WHERE d.status='O' AND h.status IN ('A','P')"),
            wo=v("SELECT COUNT(*) FROM sfc_work_order WHERE status IN ('R','S')"),
            value=v("SELECT COALESCE(SUM(remaining_qty*unit_cost),0) FROM inv_layer WHERE is_closed=0"),
            run=self.db.row("SELECT * FROM mrp_run WHERE status='D' ORDER BY id DESC LIMIT 1"),
            load=self.db.rows("SELECT w.wc_code, w.wc_name, MAX(l.load_pct) mx FROM crp_load l JOIN rou_work_center w ON "
                              "w.id=l.wc_id WHERE l.run_id=(SELECT MAX(id) FROM crp_run) GROUP BY w.id ORDER BY mx DESC"),
            company=self.company().get("company_name") or "", has_data=self.has_business_data())

    def wo_list(self, flt="open"):
        self.need("SFC", 1)
        if flt == "open":
            where, args = "WHERE w.status IN ('P','R','S')", ()
        elif flt:
            where, args = "WHERE w.status=%s", (flt,)
        else:
            where, args = "", ()
        return self.db.rows("SELECT w.*, i.item_code, i.item_name FROM sfc_work_order w JOIN itm_item i ON i.id=w.item_id "
                            "%s ORDER BY w.id DESC LIMIT 500" % where, args or None)

    # ---------------------------------------------------------------- 料件
    def create_item(self, data):
        self.need("ITM")
        with self.db.transaction():
            rid = self.save_row("itm_item", data)
            wh = self.db.value("SELECT id FROM bas_warehouse WHERE wh_code=%s", ("FG" if data.get("item_type") == "F" else "RM",))
            self.db.exec("INSERT IGNORE INTO itm_plan (item_id, default_wh_id) VALUES (%s,%s)", (rid, wh))
            rev = self.db.exec("INSERT INTO itm_revision (item_id, rev_code, status) VALUES (%s,'A','A')", (rid,))
            self.db.exec("UPDATE itm_item SET current_rev_id=%s WHERE id=%s", (rev, rid))
        return rid

    def delete_item(self, item_id):
        self.need("ITM")
        with self.db.transaction():      # 任一步驟被擋（已被使用）就整筆還原
            self.db.exec("UPDATE itm_item SET current_rev_id=NULL WHERE id=%s", (item_id,))
            self.delete_row("itm_revision", item_id, key="item_id")
            self.delete_row("itm_item", item_id)

    def item_plan(self, item_id):
        self.need("ITM", 1)
        self.db.exec("INSERT IGNORE INTO itm_plan (item_id) VALUES (%s)", (item_id,))
        return self.db.row("SELECT * FROM itm_plan WHERE item_id=%s", (item_id,))

    def calc_eoq(self, item_id):
        self.need("ITM")
        p = self.db.row("SELECT p.*, (SELECT s.unit_price*c.exchange_rate FROM pur_item_source s JOIN bas_currency c ON "
                        "c.currency_code=s.currency_code WHERE s.item_id=p.item_id ORDER BY s.priority LIMIT 1) price "
                        "FROM itm_plan p WHERE p.item_id=%s", (item_id,))
        if not (p and p["annual_demand"] and p["order_cost"] and p["price"] and p["holding_rate"]):
            raise BizError("請先輸入年需求量、每次訂購成本、持有成本率，並在供應來源設定單價")
        eoq = math.sqrt(2 * float(p["annual_demand"]) * float(p["order_cost"]) / (float(p["price"]) * float(p["holding_rate"])))
        self.db.exec("UPDATE itm_plan SET eoq_qty=%s WHERE item_id=%s", (round(eoq, 4), item_id))
        return eoq

    def set_current_rev(self, item_id, rev_id):
        self.need("ITM")
        self.db.exec("UPDATE itm_item SET current_rev_id=%s WHERE id=%s AND EXISTS (SELECT 1 FROM itm_revision r WHERE "
                     "r.id=%s AND r.item_id=%s)", (rev_id, item_id, rev_id, item_id))

    # ---------------------------------------------------------------- BOM
    BOM_COLS = ("child_item_id", "child_rev_id", "required_country", "qty_per", "scrap_rate", "op_seq", "issue_type",
                "is_phantom", "effective_date", "obsolete_date", "note")

    def save_bom(self, item_id, bom_id, head, lines):
        self.need("BOM")
        if bom_id and self.db.value("SELECT status FROM bom_header WHERE id=%s", (bom_id,)) != "D":
            raise BizError("已核准的 BOM 要先取消核准才能修改")
        lines = [l for l in lines if l.get("child_item_id")]
        if not lines:
            raise BizError("請至少輸入一個元件")
        for l in lines:
            if int(l["child_item_id"]) == int(item_id):
                raise BizError("元件不能是母件自己")
            if not l.get("qty_per") or Decimal(str(l["qty_per"])) <= 0:
                raise BizError("用量要大於 0")
        with self.db.transaction():
            hv = {k: head.get(k) for k in ("bom_ver", "base_qty", "parent_rev_id", "is_default", "note")}
            hv.update(parent_item_id=item_id, base_qty=hv.get("base_qty") or 1, bom_ver=hv.get("bom_ver") or "01",
                      is_default=int(bool(hv.get("is_default"))))
            bid = self.save_row("bom_header", hv, bom_id)
            if hv["is_default"]:
                self.db.exec("UPDATE bom_header SET is_default=0 WHERE parent_item_id=%s AND id<>%s", (item_id, bid))
            self.db.exec("DELETE FROM bom_detail WHERE bom_id=%s", (bid,))
            for i, l in enumerate(lines, 1):
                r = {k: l.get(k) for k in self.BOM_COLS}
                r.update(bom_id=bid, line_no=i, scrap_rate=r.get("scrap_rate") or 0, issue_type=r.get("issue_type") or "P",
                         effective_date=r.get("effective_date") or "2000-01-01", is_phantom=int(bool(r.get("is_phantom"))))
                self.db.exec("INSERT INTO bom_detail (%s) VALUES (%s)" % (", ".join(r), ", ".join(["%s"] * len(r))),
                             list(r.values()))
            self.compute_low_level_codes()
        return bid

    def set_bom_status(self, bom_id, st):
        self.need("BOM")
        if st == "A":
            self.compute_low_level_codes()       # 檢查循環
        self.db.exec("UPDATE bom_header SET status=%s, approved_by=%s, approved_at=IF(%s='A',NOW(),NULL) WHERE id=%s",
                     (st, self.user_id if st == "A" else None, st, bom_id))
        self.log("STATUS", "bom_header", bom_id, st, "BOM")

    def copy_bom_version(self, bom_id):
        self.need("BOM")
        h = self.db.row("SELECT * FROM bom_header WHERE id=%s", (bom_id,))
        vers = {r["bom_ver"] for r in self.db.rows("SELECT bom_ver FROM bom_header WHERE parent_item_id=%s",
                                                  (h["parent_item_id"],))}
        n = 1
        while "%02d" % n in vers:
            n += 1
        with self.db.transaction():
            nid = self.db.exec("INSERT INTO bom_header (parent_item_id, parent_rev_id, bom_ver, base_qty, is_default, status, "
                               "note, created_by) SELECT parent_item_id, parent_rev_id, %s, base_qty, 0, 'D', note, %s FROM "
                               "bom_header WHERE id=%s", ("%02d" % n, self.user_id, bom_id))
            self.db.exec("INSERT INTO bom_detail (bom_id, line_no, %s) SELECT %%s, line_no, %s FROM bom_detail WHERE bom_id=%%s"
                         % (", ".join(self.BOM_COLS), ", ".join(self.BOM_COLS)), (nid, bom_id))
        return "%02d" % n

    # ---------------------------------------------------------------- 途程
    ROU_COLS = ("op_seq", "op_name", "wc_id", "setup_hours", "run_hours", "is_outsource", "supplier_id", "is_report_point")

    def save_routing(self, item_id, routing_id, head, lines):
        self.need("ROU")
        lines = [l for l in lines if l.get("wc_id")]
        if not lines:
            raise BizError("請至少輸入一道工序")
        seqs = [l.get("op_seq") for l in lines]
        if None in seqs or len(set(seqs)) != len(seqs):
            raise BizError("工序號碼不能空白或重複（建議 10、20、30…）")
        with self.db.transaction():
            hv = {k: head.get(k) for k in ("routing_ver", "rev_id", "is_default", "note")}
            hv.update(item_id=item_id, routing_ver=hv.get("routing_ver") or "01", status="A",
                      is_default=int(bool(hv.get("is_default"))))
            rid = self.save_row("rou_routing_h", hv, routing_id)
            if hv["is_default"]:
                self.db.exec("UPDATE rou_routing_h SET is_default=0 WHERE item_id=%s AND id<>%s", (item_id, rid))
            self.db.exec("DELETE FROM rou_routing_d WHERE routing_id=%s", (rid,))
            for l in lines:
                r = {k: l.get(k) for k in self.ROU_COLS}
                r.update(routing_id=rid, op_name=r.get("op_name") or "工序 %s" % r["op_seq"],
                         setup_hours=r.get("setup_hours") or 0, run_hours=r.get("run_hours") or 0,
                         is_outsource=int(bool(r.get("is_outsource"))), is_report_point=int(bool(r.get("is_report_point"))))
                self.db.exec("INSERT INTO rou_routing_d (%s) VALUES (%s)" % (", ".join(r), ", ".join(["%s"] * len(r))),
                             list(r.values()))
        return rid

    # ---------------------------------------------------------------- MPS
    def update_mps_line(self, line_id, qty, day):
        self.need("MPS")
        self.db.exec("UPDATE mps_plan_d SET mps_qty=%s, period_start=%s, is_firm=1 WHERE id=%s",
                     (Decimal(str(qty)), date(day), line_id))
        self.log("EDIT", "mps_plan_d", line_id, {"mps_qty": qty}, "MPS")

    def void_mps(self, mps_id):
        self.need("MPS")
        self.db.exec("UPDATE mps_plan_h SET status='X' WHERE id=%s", (mps_id,))
        self.log("STATUS", "mps_plan_h", mps_id, "X", "MPS")

    # ---------------------------------------------------------------- 單據轉換
    def pr_to_po(self, pr_id):
        self.need("PUR")
        h, lines = self.doc("PR", pr_id)
        by = {}
        for l in lines:
            if not l["suggest_supplier_id"]:
                raise BizError("每一項都要有建議供應商才能轉採購單")
            by.setdefault(l["suggest_supplier_id"], []).append(dict(item_id=l["item_id"], rev_id=l["rev_id"], qty=l["qty"],
                                                                     due_date=l["need_date"], id=l["id"]))
        out = []
        with self.db.transaction():
            for sup, ls in by.items():
                out.append(self.create_po_from_planned(sup, ls))
                for l in ls:
                    self.db.exec("UPDATE pur_req_d SET ordered_qty=qty WHERE id=%s", (l["id"],))
            self.db.exec("UPDATE pur_req_h SET status='C' WHERE id=%s", (pr_id,))
        return out

    def so_to_wo(self, so_id):
        self.need("SFC")
        h, lines = self.doc("SO", so_id)
        mfg = [l for l in lines if self.db.value("SELECT source_type FROM itm_item WHERE id=%s", (l["item_id"],)) != "P"
               and l["qty"] > l["shipped_qty"]]
        if not mfg:
            raise BizError("此訂單沒有需要生產的自製料件")
        self._calendar()
        out = []
        for l in mfg:
            lt = self.db.value("SELECT lead_time_days FROM itm_plan WHERE item_id=%s", (l["item_id"],)) or 0
            out.append(self.create_work_order(l["item_id"], l["qty"] - l["shipped_qty"], self.workday_back(l["due_date"], lt),
                                              l["due_date"], so_line_id=l["id"], rev_id=l["rev_id"]))
        return out

    # ---------------------------------------------------------------- 行事曆
    def extend_calendar_years(self):
        self.need("BAS")
        from .seed import extend_calendar
        y = dt.date.today().year
        extend_calendar(self.db, dt.date(y, 1, 1), dt.date(y + 2, 12, 31))
        return y + 2
