"""單據作業：一般單據（單頭＋單身）存檔、核准，以及會影響存貨的過帳作業。"""
import datetime as dt
from collections import defaultdict
from decimal import Decimal

from .core import D0, BizError, date, money, price, qty

ONE = Decimal(1)

# 一般單據定義：單頭表、單身表、外鍵、單號欄、日期欄、單別、權限、單頭欄位、單身欄位、是否外幣
DOCS = {
    "SO": dict(title="客戶訂單", head="sal_order_h", line="sal_order_d", fk="so_id", no="so_no", date="order_date",
               doc_type="SO", func="SAL", fx=True,
               head_cols=["customer_id", "cust_po_no", "currency_code", "exchange_rate", "tax_type", "tax_rate",
                          "sales_id", "note"],
               line_cols=["item_id", "rev_id", "qty", "unit_price", "due_date"]),
    "PO": dict(title="採購單", head="pur_order_h", line="pur_order_d", fk="po_id", no="po_no", date="po_date",
               doc_type="PO", func="PUR", fx=True,
               head_cols=["supplier_id", "po_type", "currency_code", "exchange_rate", "tax_type", "tax_rate", "buyer_id",
                          "note"],
               line_cols=["item_id", "rev_id", "mfr_part_id", "origin_country", "qty", "unit_price", "due_date"]),
    "PR": dict(title="請購單", head="pur_req_h", line="pur_req_d", fk="pr_id", no="pr_no", date="pr_date",
               doc_type="PR", func="PUR", fx=False, head_cols=["dept_id", "requester_id", "note"],
               line_cols=["item_id", "rev_id", "qty", "need_date", "suggest_supplier_id"]),
    "FC": dict(title="需求預測", head="fct_forecast_h", line="fct_forecast_d", fk="forecast_id", no="fc_no",
               date="fc_date", doc_type="FC", func="FCT", fx=False, head_cols=["method", "bucket_type", "note"],
               line_cols=["item_id", "customer_id", "period_start", "forecast_qty"]),
}


class Ops:
    # ================================================================ 一般單據
    def doc(self, kind, doc_id):
        d = DOCS[kind]
        h = self.db.row("SELECT * FROM %s WHERE id=%%s" % d["head"], (doc_id,))
        if not h:
            raise BizError("找不到單據")
        lines = self.db.rows("SELECT * FROM %s WHERE %s=%%s ORDER BY %s" % (
            d["line"], d["fk"], "line_no" if kind != "FC" else "id"), (doc_id,))
        return h, lines

    def save_doc(self, kind, doc_id, head, lines):
        """存檔（草稿）。head、lines 為畫面欄位 dict；回傳 (id, 單號)。"""
        d = DOCS[kind]
        self.need(d["func"])
        when = date(head.get(d["date"]))
        if doc_id:
            st = self.db.value("SELECT status FROM %s WHERE id=%%s" % d["head"], (doc_id,))
            if st not in ("D",):
                raise BizError("已核准或已結案的單據不能修改")
        lines = [l for l in lines if l.get("item_id")]
        if not lines:
            raise BizError("請至少輸入一個料件")
        hv = {c: (head.get(c) if head.get(c) != "" else None) for c in d["head_cols"]}
        if d["fx"]:
            cur = hv.get("currency_code") or self.base_currency()
            hv["currency_code"] = cur
            hv["exchange_rate"] = price(hv.get("exchange_rate") or self.rate_on(cur, when))
            hv["tax_rate"] = Decimal(str(hv.get("tax_rate") or self.param("default_tax_rate", "0.05")))
        rows, untaxed = [], D0
        for i, l in enumerate(lines, 1):
            r = {c: (l.get(c) if l.get(c) != "" else None) for c in d["line_cols"]}
            for c in ("qty", "forecast_qty"):
                if c in r:
                    r[c] = qty(r[c])
                    if r[c] <= 0:
                        raise BizError("第 %d 項數量要大於 0" % i)
            for c in ("due_date", "need_date", "period_start"):
                if c in r:
                    r[c] = date(r[c] or when)
            if d["fx"]:
                r["unit_price"] = price(r.get("unit_price") or 0)
                r["amount"] = money(r["qty"] * r["unit_price"])
                r["base_amount"] = money(r["amount"] * hv["exchange_rate"])
                untaxed += r["amount"]
            if kind != "FC":
                r["line_no"] = i
            rows.append(r)
        if d["fx"]:
            tax_type = str(hv.get("tax_type") or "1")
            tax = money(untaxed * hv["tax_rate"]) if tax_type == "1" else D0
            if tax_type == "2":              # 內含：金額已含稅
                tax = money(untaxed - untaxed / (ONE + hv["tax_rate"]))
                untaxed -= tax
            hv.update(untaxed_amount=untaxed, tax_amount=tax, base_untaxed_amount=money(untaxed * hv["exchange_rate"]),
                      base_tax_amount=money(tax * hv["exchange_rate"]))
        hv[d["date"]] = when
        with self.db.transaction():
            if doc_id:
                no = self.db.value("SELECT %s FROM %s WHERE id=%%s" % (d["no"], d["head"]), (doc_id,))
                self.db.exec("UPDATE %s SET %s, updated_by=%%s WHERE id=%%s" % (
                    d["head"], ", ".join("%s=%%s" % c for c in hv)), list(hv.values()) + [self.user_id, doc_id])
                self.db.exec("DELETE FROM %s WHERE %s=%%s" % (d["line"], d["fk"]), (doc_id,))
            else:
                no = self.next_no(d["doc_type"], when)
                hv[d["no"]] = no
                hv["created_by"] = self.user_id
                doc_id = self.db.exec("INSERT INTO %s (%s) VALUES (%s)" % (
                    d["head"], ", ".join(hv), ", ".join(["%s"] * len(hv))), list(hv.values()))
            for r in rows:
                r[d["fk"]] = doc_id
                self.db.exec("INSERT INTO %s (%s) VALUES (%s)" % (d["line"], ", ".join(r), ", ".join(["%s"] * len(r))),
                             list(r.values()))
        self.log("SAVE", d["head"], no, None, d["func"])
        return doc_id, no

    def set_doc_status(self, kind, doc_id, status):
        d = DOCS[kind]
        self.need(d["func"])
        cur = self.db.value("SELECT status FROM %s WHERE id=%%s" % d["head"], (doc_id,))
        allowed = {"A": ("D",), "D": ("A",), "X": ("D", "A"), "C": ("A", "P")}
        if cur not in allowed.get(status, ()):
            names = {"A": "核准", "D": "取消核准", "X": "作廢", "C": "結案"}
            raise BizError("目前狀態不能%s" % names.get(status, status))
        if status == "D" and kind in ("PO", "SO"):
            done = self.db.value("SELECT COALESCE(SUM(%s),0) FROM %s WHERE %s=%%s" % (
                "received_qty" if kind == "PO" else "shipped_qty", d["line"], d["fk"]), (doc_id,))
            if done:
                raise BizError("已有進貨／出貨，不能取消核准")
        self.db.exec("UPDATE %s SET status=%%s WHERE id=%%s" % d["head"], (status, doc_id))
        if status == "C" and kind in ("PO", "SO"):
            self.db.exec("UPDATE %s SET status='C' WHERE %s=%%s AND status='O'" % (d["line"], d["fk"]), (doc_id,))
        self.log("STATUS", d["head"], doc_id, status, d["func"])

    def doc_list(self, kind, keyword="", status=None, limit=300):
        d = DOCS[kind]
        party = {"SO": ("sal_customer", "customer_id", "cust_name"), "PO": ("pur_supplier", "supplier_id", "sup_name")}
        join, pcol = "", "''"
        if kind in party:
            t, c, n = party[kind]
            join = " LEFT JOIN %s p ON p.id=h.%s" % (t, c)
            pcol = "p.%s" % n
        where, args = [], []
        if keyword:
            where.append("(h.%s LIKE %%s OR %s LIKE %%s)" % (d["no"], pcol))
            args += ["%%%s%%" % keyword] * 2
        if status:
            where.append("h.status=%s")
            args.append(status)
        amt = ", h.currency_code, h.untaxed_amount, h.base_untaxed_amount" if d["fx"] else ""
        return self.db.rows("SELECT h.id, h.%s doc_no, h.%s doc_date, h.status, %s party%s FROM %s h%s %s "
                            "ORDER BY h.%s DESC, h.id DESC LIMIT %d" % (
                                d["no"], d["date"], pcol, amt, d["head"], join,
                                ("WHERE " + " AND ".join(where)) if where else "", d["date"], limit), args)

    # ================================================================ 採購
    def source_for(self, item_id, supplier_id, country=None):
        return self.db.row("SELECT * FROM pur_item_source WHERE item_id=%s AND supplier_id=%s AND (%s IS NULL OR "
                           "origin_country=%s) ORDER BY priority LIMIT 1", (item_id, supplier_id, country, country)) \
            or self.db.row("SELECT * FROM pur_item_source WHERE item_id=%s AND supplier_id=%s ORDER BY priority LIMIT 1",
                           (item_id, supplier_id))

    def create_po_from_planned(self, supplier_id, planned):
        sup = self.db.row("SELECT * FROM pur_supplier WHERE id=%s", (supplier_id,))
        today = dt.date.today()
        lines = []
        for p in planned:
            src = self.source_for(p["item_id"], supplier_id) or {}
            lines.append(dict(item_id=p["item_id"], rev_id=p["rev_id"], mfr_part_id=src.get("mfr_part_id"),
                              origin_country=src.get("origin_country"), qty=p["qty"],
                              unit_price=src.get("unit_price") or 0, due_date=p["due_date"]))
        cur = (planned and self.source_for(planned[0]["item_id"], supplier_id) or {}).get("currency_code") \
            or sup["currency_code"]
        pid, no = self.save_doc("PO", None, dict(po_date=today, supplier_id=supplier_id, po_type="N",
                                                 currency_code=cur, tax_type="1",
                                                 note="由 MRP 計畫訂單轉入"), lines)
        return no

    def receive_po(self, po_id, lines, rcv_date=None, warehouse_id=None, invoice_no=None):
        """進貨驗收：lines=[dict(po_line_id, accept_qty, reject_qty, lot_no, date_code, mfr_part_id, origin_country,
        coo_cert_no)]。合格量依「單價 × 匯率」換算成本位幣成本入庫，建立先進先出成本層。"""
        self.need("PUR")
        po = self.db.row("SELECT * FROM pur_order_h WHERE id=%s", (po_id,))
        if not po or po["status"] not in ("A", "P"):
            raise BizError("採購單要先核准才能進貨")
        when = date(rcv_date or dt.date.today())
        rate = self.rate_on(po["currency_code"], when)     # 進貨日匯率（與採購日不同 → 匯差）
        wh = warehouse_id or self.db.value("SELECT id FROM bas_warehouse WHERE wh_code='RM'")
        lines = [l for l in lines if qty(l.get("accept_qty")) + qty(l.get("reject_qty")) > 0]
        if not lines:
            raise BizError("請輸入進貨數量")
        no = self.next_no("RCV", when)
        with self.db.transaction():
            rid = self.db.exec("INSERT INTO pur_receipt_h (rcv_no, rcv_date, supplier_id, warehouse_id, currency_code, "
                               "exchange_rate, invoice_no, status, created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,'A',%s)",
                               (no, when, po["supplier_id"], wh, po["currency_code"], rate, invoice_no, self.user_id))
            total = base_total = D0
            for i, l in enumerate(lines, 1):
                pl = self.db.row("SELECT * FROM pur_order_d WHERE id=%s AND po_id=%s", (l["po_line_id"], po_id))
                if not pl:
                    raise BizError("採購明細不存在")
                acc, rej = qty(l.get("accept_qty")), qty(l.get("reject_qty"))
                if pl["received_qty"] + acc > pl["qty"] * Decimal("1.1"):
                    raise BizError("第 %d 項進貨量超過採購量 10%%" % i)
                amount = money(acc * pl["unit_price"])
                base_cost = price(Decimal(pl["unit_price"]) * rate)
                origin = l.get("origin_country") or pl["origin_country"]
                mfr = l.get("mfr_part_id") or pl["mfr_part_id"]
                self.db.exec("INSERT INTO pur_receipt_d (rcv_id, line_no, po_line_id, item_id, rev_id, mfr_part_id, "
                             "origin_country, date_code, coo_cert_no, lot_no, receive_qty, accept_qty, reject_qty, "
                             "unit_price, amount, base_amount) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                             (rid, i, pl["id"], pl["item_id"], pl["rev_id"], mfr, origin, l.get("date_code"),
                              l.get("coo_cert_no"), l.get("lot_no"), acc + rej, acc, rej, pl["unit_price"], amount,
                              money(amount * rate)))
                if acc > 0:
                    lot = self.lot_id(pl["item_id"], l.get("lot_no"), pl["rev_id"], mfr, origin, l.get("date_code"),
                                      None, po["supplier_id"], no)
                    self.post_in("RCV", no, i, pl["item_id"], wh, acc, base_cost, lot, pl["rev_id"], when=when)
                    std = self.db.value("SELECT material_cost FROM acc_item_cost WHERE item_id=%s AND cost_type='S' "
                                        "ORDER BY period DESC LIMIT 1", (pl["item_id"],))
                    if std:
                        var = money((base_cost - Decimal(std)) * acc)
                        if var:
                            self.db.exec("INSERT INTO acc_variance (period, variance_type, item_id, ref_doc_no, amount, "
                                         "note) VALUES (%s,'PPV',%s,%s,%s,'採購價差（實際 − 標準）')",
                                         (when.strftime("%Y%m"), pl["item_id"], no, var))
                    if po["exchange_rate"] and Decimal(po["exchange_rate"]) != rate:
                        fx = money(amount * (rate - Decimal(po["exchange_rate"])))
                        self.db.exec("INSERT INTO acc_variance (period, variance_type, item_id, ref_doc_no, amount, note) "
                                     "VALUES (%s,'FXV',%s,%s,%s,%s)", (when.strftime("%Y%m"), pl["item_id"], no, fx,
                                                                     "採購匯率 %s → 進貨匯率 %s" % (po["exchange_rate"], rate)))
                self.db.exec("UPDATE pur_order_d SET received_qty=received_qty+%s, status=IF(received_qty+%s>=qty,'C',"
                             "status) WHERE id=%s", (acc, acc, pl["id"]))
                total += amount
                base_total += money(amount * rate)
            self.db.exec("UPDATE pur_receipt_h SET untaxed_amount=%s, base_untaxed_amount=%s WHERE id=%s",
                         (total, base_total, rid))
            open_ = self.db.value("SELECT COUNT(*) FROM pur_order_d WHERE po_id=%s AND status='O'", (po_id,))
            self.db.exec("UPDATE pur_order_h SET status=%s WHERE id=%s", ("P" if open_ else "C", po_id))
        self.log("POST", "pur_receipt_h", no, None, "PUR")
        return no

    # ================================================================ 銷售
    def ship_so(self, so_id, lines, ship_date=None, warehouse_id=None, invoice_no=None):
        """出貨：lines=[dict(so_line_id, qty)]，依先進先出扣成品庫存。"""
        self.need("SAL")
        so = self.db.row("SELECT * FROM sal_order_h WHERE id=%s", (so_id,))
        if not so or so["status"] not in ("A", "P"):
            raise BizError("訂單要先核准才能出貨")
        when = date(ship_date or dt.date.today())
        wh = warehouse_id or self.db.value("SELECT id FROM bas_warehouse WHERE wh_code='FG'")
        rate = self.rate_on(so["currency_code"], when)
        lines = [l for l in lines if qty(l.get("qty")) > 0]
        if not lines:
            raise BizError("請輸入出貨數量")
        no = self.next_no("SHP", when)
        with self.db.transaction():
            sid = self.db.exec("INSERT INTO sal_ship_h (ship_no, ship_date, customer_id, warehouse_id, currency_code, "
                               "exchange_rate, invoice_no, status, created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,'A',%s)",
                               (no, when, so["customer_id"], wh, so["currency_code"], rate, invoice_no, self.user_id))
            total = D0
            for i, l in enumerate(lines, 1):
                sl = self.db.row("SELECT * FROM sal_order_d WHERE id=%s AND so_id=%s", (l["so_line_id"], so_id))
                q = qty(l["qty"])
                if sl["shipped_qty"] + q > sl["qty"]:
                    raise BizError("第 %d 項出貨量超過訂單未出貨量" % i)
                cost, used = self.post_out("SHP", no, i, sl["item_id"], wh, q, rev_id=sl["rev_id"], when=when)
                amount = money(q * sl["unit_price"])
                self.db.exec("INSERT INTO sal_ship_d (ship_id, line_no, so_line_id, item_id, rev_id, qty, unit_price, "
                             "amount, base_amount, lot_no) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                             (sid, i, sl["id"], sl["item_id"], sl["rev_id"], q, sl["unit_price"], amount,
                              money(amount * rate), ",".join(sorted({u[0] for u in used if u[0]}))[:30] or None))
                self.db.exec("UPDATE sal_order_d SET shipped_qty=shipped_qty+%s, status=IF(shipped_qty+%s>=qty,'C',status) "
                             "WHERE id=%s", (q, q, sl["id"]))
                total += amount
            self.db.exec("UPDATE sal_ship_h SET untaxed_amount=%s, base_untaxed_amount=%s WHERE id=%s",
                         (total, money(total * rate), sid))
            open_ = self.db.value("SELECT COUNT(*) FROM sal_order_d WHERE so_id=%s AND status='O'", (so_id,))
            self.db.exec("UPDATE sal_order_h SET status=%s WHERE id=%s", ("P" if open_ else "C", so_id))
        self.log("POST", "sal_ship_h", no, None, "SAL")
        return no

    # ================================================================ 工單
    def create_work_order(self, item_id, plan_qty, start, finish, planned_order_id=None, rev_id=None, so_line_id=None,
                          warehouse_id=None, note=None):
        self.need("SFC")
        start, finish = date(start), date(finish)
        if finish < start:
            finish = start
        it = self.db.row("SELECT i.*, p.default_wh_id FROM itm_item i LEFT JOIN itm_plan p ON p.item_id=i.id WHERE i.id=%s",
                         (item_id,))
        if it["source_type"] == "P":
            raise BizError("%s 是採購件，不能開工單" % it["item_code"])
        bom = self.db.value("SELECT id FROM bom_header WHERE parent_item_id=%s AND status='A' ORDER BY is_default DESC, "
                            "id DESC LIMIT 1", (item_id,))
        rou = self.db.value("SELECT id FROM rou_routing_h WHERE item_id=%s AND status='A' ORDER BY is_default DESC, id DESC "
                            "LIMIT 1", (item_id,))
        no = self.next_no("WO", start)
        wh = warehouse_id or it["default_wh_id"] or self.db.value(
            "SELECT id FROM bas_warehouse WHERE wh_code=%s", ("FG" if it["item_type"] == "F" else "RM",))
        self.db.exec("INSERT INTO sfc_work_order (wo_no, wo_type, item_id, rev_id, bom_id, routing_id, plan_qty, plan_start, "
                     "plan_finish, so_line_id, planned_order_id, warehouse_id, status, note, created_by) "
                     "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'P',%s,%s)",
                     (no, "O" if it["source_type"] == "O" else "S", item_id, rev_id or it["current_rev_id"], bom, rou,
                      qty(plan_qty), start, finish, so_line_id, planned_order_id, wh, note, self.user_id))
        self.log("ADD", "sfc_work_order", no, None, "SFC")
        return no

    def explode_bom(self, item_id, q, on_date=None, phantom=True):
        """單階展開（虛設件穿透）：回傳 [dict(item_id, qty, op_seq, issue_type, required_country, child_rev_id)]。"""
        on_date = on_date or dt.date.today()
        out = []
        for b in self.db.rows("SELECT d.*, h.base_qty, i.item_type FROM bom_header h JOIN bom_detail d ON d.bom_id=h.id "
                              "JOIN itm_item i ON i.id=d.child_item_id WHERE h.parent_item_id=%s AND h.status='A' AND "
                              "h.is_default=1 AND d.effective_date<=%s AND (d.obsolete_date IS NULL OR d.obsolete_date>%s) "
                              "ORDER BY d.line_no", (item_id, on_date, on_date)):
            need = (Decimal(q) / Decimal(b["base_qty"] or 1) * Decimal(b["qty_per"]) /
                    (ONE - Decimal(b["scrap_rate"] or 0))).quantize(Decimal("0.0001"))
            if phantom and (b["is_phantom"] or b["item_type"] == "X"):
                out += self.explode_bom(b["child_item_id"], need, on_date)
                continue
            out.append(dict(item_id=b["child_item_id"], qty=need, op_seq=b["op_seq"], issue_type=b["issue_type"],
                            required_country=b["required_country"], rev_id=b["child_rev_id"]))
        return out

    def release_wo(self, wo_id):
        """發放工單：展開 BOM 成工單用料、複製途程成工單工序；指定產地的用料先保留該產地批號。"""
        self.need("SFC")
        w = self.db.row("SELECT * FROM sfc_work_order WHERE id=%s", (wo_id,))
        if w["status"] != "P":
            raise BizError("只有「計畫」狀態的工單可以發放")
        mats = self.explode_bom(w["item_id"], w["plan_qty"], w["plan_start"])
        if not mats:
            raise BizError("此料件沒有已核准的 BOM，無法發放工單")
        rm = self.db.value("SELECT id FROM bas_warehouse WHERE wh_code='RM'")
        notes = []
        with self.db.transaction():
            self.db.exec("DELETE FROM sfc_wo_material WHERE wo_id=%s", (wo_id,))
            self.db.exec("DELETE FROM sfc_wo_operation WHERE wo_id=%s", (wo_id,))
            for i, m in enumerate(mats, 1):
                wh = self.db.value("SELECT default_wh_id FROM itm_plan WHERE item_id=%s", (m["item_id"],)) or rm
                self.db.exec("INSERT INTO sfc_wo_material (wo_id, line_no, item_id, rev_id, required_country, required_qty, "
                             "op_seq, issue_type, warehouse_id, required_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                             (wo_id, i, m["item_id"], m["rev_id"], m["required_country"], m["qty"], m["op_seq"],
                              m["issue_type"], wh, w["plan_start"]))
                if m["required_country"] and m["issue_type"] != "N":
                    got = self.reserve(m["item_id"], wh, m["qty"], m["required_country"])
                    code = self.db.value("SELECT item_code FROM itm_item WHERE id=%s", (m["item_id"],))
                    notes.append("%s 指定 %s：已保留 %s" % (code, m["required_country"], got.normalize()))
            if w["routing_id"]:
                for o in self.db.rows("SELECT * FROM rou_routing_d WHERE routing_id=%s ORDER BY op_seq", (w["routing_id"],)):
                    self.db.exec("INSERT INTO sfc_wo_operation (wo_id, op_seq, op_name, wc_id, plan_setup_hours, "
                                 "plan_run_hours) VALUES (%s,%s,%s,%s,%s,%s)",
                                 (wo_id, o["op_seq"], o["op_name"], o["wc_id"], o["setup_hours"],
                                  Decimal(o["run_hours"]) * Decimal(w["plan_qty"])))
            self.db.exec("UPDATE sfc_work_order SET status='R' WHERE id=%s", (wo_id,))
        self.log("RELEASE", "sfc_work_order", w["wo_no"], notes, "SFC")
        return notes

    def issue_wo(self, wo_id, lines=None, issue_date=None):
        """工單領料：lines=[dict(wo_material_id, qty)]；省略＝把所有「領料」方式的未領量一次領完。依先進先出扣庫存。"""
        self.need("SFC")
        w = self.db.row("SELECT * FROM sfc_work_order WHERE id=%s", (wo_id,))
        if w["status"] not in ("R", "S"):
            raise BizError("工單要先發放才能領料")
        mats = {m["id"]: m for m in self.db.rows("SELECT * FROM sfc_wo_material WHERE wo_id=%s", (wo_id,))}
        if lines is None:
            lines = [dict(wo_material_id=m["id"], qty=m["required_qty"] - m["issued_qty"]) for m in mats.values()
                     if m["issue_type"] == "P" and m["required_qty"] > m["issued_qty"]]
        lines = [l for l in lines if qty(l.get("qty")) > 0]
        if not lines:
            raise BizError("沒有需要領的料")
        when = date(issue_date or dt.date.today())
        no = self.next_no("ISS", when)
        used_all = []
        with self.db.transaction():
            wh0 = mats[int(lines[0]["wo_material_id"])]["warehouse_id"]
            iid = self.db.exec("INSERT INTO sfc_issue_h (issue_no, issue_date, issue_type, wo_id, warehouse_id, status, "
                               "created_by) VALUES (%s,%s,'I',%s,%s,'A',%s)",
                               (no, dt.datetime.combine(when, dt.datetime.now().time()), wo_id, wh0, self.user_id))
            n = 0
            for l in lines:
                m = mats[int(l["wo_material_id"])]
                q = qty(l["qty"])
                own = bool(m["required_country"])
                cost, used = self.post_out("ISS", no, None, m["item_id"], m["warehouse_id"], q, rev_id=m["rev_id"],
                                           country=m["required_country"], wo_id=wo_id, when=when, own_alloc=own)
                for lot_no, origin, take, uc in used:
                    n += 1
                    self.db.exec("INSERT INTO sfc_issue_d (issue_id, line_no, wo_material_id, item_id, rev_id, lot_no, qty) "
                                 "VALUES (%s,%s,%s,%s,%s,%s,%s)", (iid, n, m["id"], m["item_id"], m["rev_id"], lot_no, take))
                    used_all.append((m["item_id"], lot_no, origin, take, uc))
                self.db.exec("UPDATE sfc_wo_material SET issued_qty=issued_qty+%s WHERE id=%s", (q, m["id"]))
            self.db.exec("UPDATE sfc_work_order SET status='S', actual_start=COALESCE(actual_start,NOW()) WHERE id=%s",
                         (wo_id,))
        self.log("POST", "sfc_issue_h", no, None, "SFC")
        return no, used_all

    def report_op(self, wo_op_id, good, scrap=0, setup_hours=0, run_hours=0, employee_id=None, machine_id=None,
                  report_type="L", scrap_reason=None, start=None):
        """報工（計工單）：記錄工時、良品、不良。"""
        self.need("SFC")
        op = self.db.row("SELECT o.*, w.wo_no, w.status wst FROM sfc_wo_operation o JOIN sfc_work_order w ON w.id=o.wo_id "
                         "WHERE o.id=%s", (wo_op_id,))
        if op["wst"] not in ("R", "S"):
            raise BizError("工單不在生產中")
        good, scrap = qty(good), qty(scrap)
        start = start or dt.datetime.now()
        no = self.next_no("RPT")
        hours = Decimal(setup_hours or 0) + Decimal(run_hours or 0)
        self.db.exec("INSERT INTO sfc_report (report_no, report_type, wo_op_id, employee_id, machine_id, wc_id, start_time, "
                     "end_time, setup_hours, run_hours, good_qty, scrap_qty, scrap_reason) "
                     "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                     (no, report_type, wo_op_id, employee_id or None, machine_id or None, op["wc_id"], start,
                      start + dt.timedelta(hours=float(hours)), setup_hours or 0, run_hours or 0, good, scrap,
                      scrap_reason))
        plan = self.db.value("SELECT plan_qty FROM sfc_work_order WHERE id=%s", (op["wo_id"],))
        self.db.exec("UPDATE sfc_wo_operation SET good_qty=good_qty+%s, scrap_qty=scrap_qty+%s, actual_hours=actual_hours+%s, "
                     "status=IF(good_qty+scrap_qty+%s+%s>=%s,'F','S') WHERE id=%s",
                     (good, scrap, hours, good, scrap, plan, wo_op_id))
        self.db.exec("UPDATE sfc_work_order SET status='S', scrap_qty=scrap_qty+%s, actual_start=COALESCE(actual_start,NOW()) "
                     "WHERE id=%s", (scrap if self._is_last_op(op) else 0, op["wo_id"]))
        self.log("POST", "sfc_report", no, None, "SFC")
        return no

    def _is_last_op(self, op):
        return op["op_seq"] == self.db.value("SELECT MAX(op_seq) FROM sfc_wo_operation WHERE wo_id=%s", (op["wo_id"],))

    def complete_wo(self, wo_id, q, complete_date=None, warehouse_id=None, lot_no=None):
        """完工入庫：先倒扣（倒扣料）依比例扣料，再以「已投入材料 ＋ 報工工時 × 費率」計算單位成本入庫。"""
        self.need("SFC")
        w = self.db.row("SELECT * FROM sfc_work_order WHERE id=%s", (wo_id,))
        if w["status"] not in ("R", "S", "F"):
            raise BizError("工單要先發放才能完工入庫")
        q = qty(q)
        if q <= 0:
            raise BizError("入庫數量要大於 0")
        if w["completed_qty"] + q > w["plan_qty"] * Decimal("1.1"):
            raise BizError("完工量超過工單數量 10%")
        when = date(complete_date or dt.date.today())
        wh = warehouse_id or w["warehouse_id"]
        no = self.next_no("CMP", when)
        with self.db.transaction():
            for m in self.db.rows("SELECT * FROM sfc_wo_material WHERE wo_id=%s AND issue_type='B'", (wo_id,)):
                need = (Decimal(m["required_qty"]) * q / Decimal(w["plan_qty"])).quantize(Decimal("0.0001"))
                need = min(need, Decimal(m["required_qty"]) - Decimal(m["issued_qty"]))
                if need > 0:
                    self.post_out("ISS", no, None, m["item_id"], m["warehouse_id"], need, rev_id=m["rev_id"],
                                  country=m["required_country"], wo_id=wo_id, when=when, own_alloc=bool(m["required_country"]))
                    self.db.exec("UPDATE sfc_wo_material SET issued_qty=issued_qty+%s WHERE id=%s", (need, m["id"]))
            mat = -Decimal(self.db.value("SELECT COALESCE(SUM(amount),0) FROM inv_txn WHERE wo_id=%s AND doc_type='ISS'",
                                         (wo_id,)) or 0)
            conv = Decimal(self.db.value(
                "SELECT COALESCE(SUM((r.setup_hours+r.run_hours)*(COALESCE(c.labor_rate,0)+COALESCE(c.overhead_rate,0))),0) "
                "FROM sfc_report r JOIN sfc_wo_operation o ON o.id=r.wo_op_id LEFT JOIN acc_wc_rate c ON c.wc_id=r.wc_id "
                "AND c.period=(SELECT MAX(period) FROM acc_wc_rate x WHERE x.wc_id=r.wc_id AND x.period<=%s) "
                "WHERE o.wo_id=%s", (when.strftime("%Y%m"), wo_id)) or 0)
            done_amt = Decimal(self.db.value("SELECT COALESCE(SUM(amount),0) FROM inv_txn WHERE wo_id=%s AND doc_type='CMP'",
                                             (wo_id,)) or 0)
            remaining = max(D0, Decimal(w["plan_qty"]) - Decimal(w["completed_qty"]))
            unit = price((mat + conv - done_amt) / remaining) if remaining > 0 else D0
            unit = max(unit, D0)
            lot = self.lot_id(w["item_id"], lot_no or w["wo_no"], w["rev_id"], when=when, source_doc=no)
            self.post_in("CMP", no, 1, w["item_id"], wh, q, unit, lot, w["rev_id"], wo_id=wo_id, when=when)
            self.db.exec("INSERT INTO sfc_complete (complete_no, complete_date, wo_id, rev_id, warehouse_id, lot_no, qty, "
                         "qc_result, status, created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,'P','A',%s)",
                         (no, dt.datetime.combine(when, dt.datetime.now().time()), wo_id, w["rev_id"], wh,
                          lot_no or w["wo_no"], q, self.user_id))
            fin = w["completed_qty"] + q >= w["plan_qty"]
            self.db.exec("UPDATE sfc_work_order SET completed_qty=completed_qty+%s, status=%s, actual_finish=%s WHERE id=%s",
                         (q, "F" if fin else "S", dt.datetime.now() if fin else None, wo_id))
        self.log("POST", "sfc_complete", no, None, "SFC")
        return no, unit

    def set_wo_status(self, wo_id, status):
        self.need("SFC")
        w = self.db.row("SELECT * FROM sfc_work_order WHERE id=%s", (wo_id,))
        ok = {"X": ("P",), "C": ("F", "S", "R"), "P": ("R",)}
        if w["status"] not in ok.get(status, ()):
            raise BizError("目前狀態不能變更為此狀態")
        if status == "P" and self.db.value("SELECT COALESCE(SUM(issued_qty),0) FROM sfc_wo_material WHERE wo_id=%s", (wo_id,)):
            raise BizError("已經領料，不能取消發放")
        with self.db.transaction():
            if status in ("P", "C", "X"):   # 釋放保留
                for m in self.db.rows("SELECT * FROM sfc_wo_material WHERE wo_id=%s AND required_country IS NOT NULL AND "
                                      "required_qty>issued_qty", (wo_id,)):
                    left = Decimal(m["required_qty"]) - Decimal(m["issued_qty"])
                    for b in self.db.rows("SELECT b.id, b.allocated_qty FROM inv_balance b JOIN inv_lot t ON t.id=b.lot_id "
                                          "WHERE b.item_id=%s AND b.warehouse_id=%s AND t.origin_country=%s AND "
                                          "b.allocated_qty>0", (m["item_id"], m["warehouse_id"], m["required_country"])):
                        take = min(left, Decimal(b["allocated_qty"]))
                        self.db.exec("UPDATE inv_balance SET allocated_qty=allocated_qty-%s WHERE id=%s", (take, b["id"]))
                        left -= take
                        if left <= 0:
                            break
            if status == "P":
                self.db.exec("DELETE FROM sfc_wo_material WHERE wo_id=%s", (wo_id,))
                self.db.exec("DELETE FROM sfc_wo_operation WHERE wo_id=%s", (wo_id,))
            self.db.exec("UPDATE sfc_work_order SET status=%s WHERE id=%s", (status, wo_id))
        self.log("STATUS", "sfc_work_order", w["wo_no"], status, "SFC")

    # ================================================================ 庫存作業
    def opening_stock(self, item_id, wh_id, q, unit_cost, lot_no=None, origin=None, date_code=None, rev_id=None,
                      mfr_part_id=None, when=None):
        self.need("INV")
        when = date(when or dt.date.today())
        no = self.next_no("BEG", when)
        with self.db.transaction():
            lot = self.lot_id(item_id, lot_no, rev_id, mfr_part_id, origin, date_code, when, source_doc=no)
            self.post_in("BEG", no, 1, item_id, wh_id, q, unit_cost, lot, rev_id, when=when)
        return no

    def adjust_stock(self, item_id, wh_id, q, reason="O", unit_cost=None, note=None, when=None):
        """庫存調整：正數＝增加（以指定或最近成本入庫）、負數＝減少（依先進先出扣減）。"""
        self.need("INV")
        q = qty(q)
        if q == 0:
            raise BizError("調整數量不能為 0")
        when = date(when or dt.date.today())
        no = self.next_no("ADJ", when)
        with self.db.transaction():
            aid = self.db.exec("INSERT INTO inv_adjust_h (adj_no, adj_date, warehouse_id, reason, status, note, created_by) "
                               "VALUES (%s,%s,%s,%s,'A',%s,%s)", (no, when, wh_id, reason, note, self.user_id))
            if q > 0:
                uc = unit_cost if unit_cost not in (None, "") else (self.db.value(
                    "SELECT unit_cost FROM inv_layer WHERE item_id=%s ORDER BY received_at DESC LIMIT 1", (item_id,)) or 0)
                self.post_in("ADJ", no, 1, item_id, wh_id, q, uc, when=when)
            else:
                cost, _ = self.post_out("ADJ", no, 1, item_id, wh_id, -q, when=when)
                uc = cost / -q
            self.db.exec("INSERT INTO inv_adjust_d (adj_id, line_no, item_id, qty, unit_cost) VALUES (%s,1,%s,%s,%s)",
                         (aid, item_id, q, price(uc)))
        return no

    def transfer_stock(self, item_id, from_wh, to_wh, q, when=None):
        """調撥：依先進先出從撥出倉扣減，再以相同成本、相同批號入撥入倉（保留原入庫時間，先進先出順序不變）。"""
        self.need("INV")
        if int(from_wh) == int(to_wh):
            raise BizError("撥出倉與撥入倉不能相同")
        when = date(when or dt.date.today())
        no = self.next_no("TRF", when)
        with self.db.transaction():
            tid = self.db.exec("INSERT INTO inv_transfer_h (trf_no, trf_date, from_wh_id, to_wh_id, status, created_by) "
                               "VALUES (%s,%s,%s,%s,'A',%s)", (no, when, from_wh, to_wh, self.user_id))
            layers = self.fifo_candidates(item_id, from_wh)
            left = qty(q)
            plan = []
            for l in layers:
                if left <= 0:
                    break
                take = min(left, Decimal(l["avail"]))
                plan.append((l, take))
                left -= take
            if left > 0:
                raise BizError("撥出倉庫存不足")
            for l, take in plan:
                self.post_out("TRF", no, 1, item_id, from_wh, take, lot_id=l["lot_id"], rev_id=l["rev_id"], when=when)
                t = self.post_in("TRF", no, 1, item_id, to_wh, take, l["unit_cost"], l["lot_id"], l["rev_id"], when=when)
                self.db.exec("UPDATE inv_layer SET received_at=%s WHERE in_txn_id=%s", (l["received_at"], t))
            self.db.exec("INSERT INTO inv_transfer_d (trf_id, line_no, item_id, qty) VALUES (%s,1,%s,%s)", (tid, item_id, q))
        return no

    # ================================================================ 成本
    def roll_up_cost(self, period=None):
        """標準成本累算（由最低階往上）：採購件＝主要供應來源單價 × 匯率；自製件＝Σ(元件成本 × 用量 ÷ (1 − 損耗)) ＋
        途程工時 × (人工費率 ＋ 製費率)。寫入 acc_item_cost（S 標準）。"""
        self.need("ACC")
        period = period or dt.date.today().strftime("%Y%m")
        self.db.exec("INSERT IGNORE INTO acc_period (period, start_date, end_date) VALUES (%s,%s,LAST_DAY(%s))",
                     (period, dt.date(int(period[:4]), int(period[4:]), 1), dt.date(int(period[:4]), int(period[4:]), 1)))
        self.compute_low_level_codes()
        items = self.db.rows("SELECT id, item_code, source_type, low_level_code FROM itm_item ORDER BY low_level_code DESC")
        cost = {}
        rates = {r["wc_id"]: r for r in self.db.rows(
            "SELECT c.* FROM acc_wc_rate c WHERE c.period=(SELECT MAX(period) FROM acc_wc_rate x WHERE x.wc_id=c.wc_id "
            "AND x.period<=%s)", (period,))}
        for it in items:
            mat = lab = oh = D0
            if it["source_type"] == "P":
                s = self.db.row("SELECT s.unit_price, c.exchange_rate FROM pur_item_source s JOIN bas_currency c ON "
                                "c.currency_code=s.currency_code WHERE s.item_id=%s ORDER BY s.priority LIMIT 1", (it["id"],))
                if s:
                    mat = Decimal(s["unit_price"]) * Decimal(s["exchange_rate"])
                else:
                    mat = Decimal(self.db.value("SELECT unit_cost FROM inv_layer WHERE item_id=%s ORDER BY received_at DESC "
                                                "LIMIT 1", (it["id"],)) or 0)
            else:
                for b in self.db.rows("SELECT d.child_item_id, d.qty_per, d.scrap_rate, h.base_qty FROM bom_header h JOIN "
                                      "bom_detail d ON d.bom_id=h.id WHERE h.parent_item_id=%s AND h.status='A' AND "
                                      "h.is_default=1", (it["id"],)):
                    c = cost.get(b["child_item_id"], D0)
                    mat += c * Decimal(b["qty_per"]) / Decimal(b["base_qty"] or 1) / (ONE - Decimal(b["scrap_rate"] or 0))
                for o in self.db.rows("SELECT d.* FROM rou_routing_h h JOIN rou_routing_d d ON d.routing_id=h.id WHERE "
                                      "h.item_id=%s AND h.status='A' AND h.is_default=1", (it["id"],)):
                    r = rates.get(o["wc_id"]) or {}
                    hrs = Decimal(o["run_hours"]) + Decimal(o["setup_hours"]) / Decimal(100)   # 整備工時以 100 件分攤
                    lab += hrs * Decimal(r.get("labor_rate") or 0)
                    oh += hrs * Decimal(r.get("overhead_rate") or 0)
            cost[it["id"]] = mat + lab + oh
            self.db.exec("INSERT INTO acc_item_cost (item_id, cost_type, period, material_cost, labor_cost, overhead_cost, "
                         "rolled_at) VALUES (%s,'S',%s,%s,%s,%s,NOW()) ON DUPLICATE KEY UPDATE material_cost=VALUES("
                         "material_cost), labor_cost=VALUES(labor_cost), overhead_cost=VALUES(overhead_cost), rolled_at=NOW()",
                         (it["id"], period, price(mat), price(lab), price(oh)))
        self.log("RUN", "acc_item_cost", period, None, "ACC")
        return len(items)
