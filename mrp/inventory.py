"""存貨過帳：入庫建立先進先出成本層、出庫依先進先出（或先到期先出）扣層，並維護批號、版本、產地、餘額與異動帳。

* inv_txn：所有入出庫的流水帳（單一真相）
* inv_balance：料件 × 倉庫 × 儲位 × 批號 × 版本 的現有量與保留量
* inv_layer / inv_layer_consume：先進先出成本層與耗用明細
"""
import datetime as dt
from decimal import Decimal

from .core import D0, BizError, money, price, qty


class Inventory:
    # ---------------------------------------------------------------- 批號
    def lot_id(self, item_id, lot_no, rev_id=None, mfr_part_id=None, origin=None, date_code=None, when=None,
               supplier_id=None, source_doc=None, exp_date=None):
        if not lot_no:
            return None
        r = self.db.row("SELECT id FROM inv_lot WHERE item_id=%s AND lot_no=%s", (item_id, lot_no))
        if r:
            return r["id"]
        return self.db.exec("INSERT INTO inv_lot (item_id, rev_id, mfr_part_id, origin_country, date_code, lot_no, "
                            "received_at, supplier_id, source_doc_no, exp_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                            (item_id, rev_id, mfr_part_id, origin, date_code, lot_no, when or dt.datetime.now(),
                             supplier_id, source_doc, exp_date))

    def _bal(self, item_id, wh_id, lot_id, rev_id, delta, loc_id=None, when=None):
        self.db.exec("INSERT INTO inv_balance (item_id, warehouse_id, location_id, lot_id, rev_id, on_hand_qty, last_txn_at) "
                     "VALUES (%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE on_hand_qty=on_hand_qty+VALUES(on_hand_qty), "
                     "last_txn_at=VALUES(last_txn_at)", (item_id, wh_id, loc_id, lot_id, rev_id, delta,
                                                         when or dt.datetime.now()))

    def _txn(self, doc_type, doc_no, line_no, item_id, wh_id, q, unit_cost, lot_id=None, rev_id=None, loc_id=None,
             wo_id=None, when=None):
        return self.db.exec("INSERT INTO inv_txn (txn_time, doc_type, doc_no, doc_line_no, item_id, rev_id, warehouse_id, "
                            "location_id, lot_id, qty, unit_cost, amount, wo_id, created_by) "
                            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                            (when or dt.datetime.now(), doc_type, doc_no, line_no, item_id, rev_id, wh_id, loc_id, lot_id,
                             q, price(unit_cost), money(Decimal(q) * Decimal(unit_cost)), wo_id, self.user_id))

    # ---------------------------------------------------------------- 入庫
    def post_in(self, doc_type, doc_no, line_no, item_id, wh_id, q, unit_cost, lot_id=None, rev_id=None, loc_id=None,
                wo_id=None, when=None):
        q, unit_cost = qty(q), price(unit_cost)
        if q <= 0:
            raise BizError("入庫數量要大於 0")
        when = when or dt.datetime.now()
        if isinstance(when, dt.date) and not isinstance(when, dt.datetime):
            when = dt.datetime.combine(when, dt.datetime.now().time())
        tid = self._txn(doc_type, doc_no, line_no, item_id, wh_id, q, unit_cost, lot_id, rev_id, loc_id, wo_id, when)
        self._bal(item_id, wh_id, lot_id, rev_id, q, loc_id, when)
        self.db.exec("INSERT INTO inv_layer (item_id, warehouse_id, lot_id, rev_id, in_txn_id, received_at, in_qty, "
                     "remaining_qty, unit_cost) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                     (item_id, wh_id, lot_id, rev_id, tid, when, q, q, unit_cost))
        return tid

    # ---------------------------------------------------------------- 出庫（先進先出）
    def fifo_candidates(self, item_id, wh_id, lot_id=None, rev_id=None, country=None, own_alloc=False):
        """可發的成本層（依入庫時間由舊到新；料件設定先到期先出時依有效日）。
        own_alloc=False：每層可發量要扣掉該批已保留給其他工單的量。"""
        rule = self.db.value("SELECT issue_rule FROM itm_plan WHERE item_id=%s", (item_id,)) or "F"
        order = "COALESCE(t.exp_date,'9999-12-31'), l.received_at, l.id" if rule == "E" else "l.received_at, l.id"
        where, args = ["l.item_id=%s", "l.warehouse_id=%s", "l.is_closed=0"], [item_id, wh_id]
        if lot_id:
            where.append("l.lot_id=%s")
            args.append(lot_id)
        if rev_id:
            where.append("l.rev_id=%s")
            args.append(rev_id)
        if country:
            where.append("t.origin_country=%s")
            args.append(country)
        alloc = "0" if own_alloc else "COALESCE(b.allocated_qty,0)"
        return self.db.rows(
            "SELECT l.*, t.lot_no, t.origin_country, l.remaining_qty - %s AS avail FROM inv_layer l "
            "LEFT JOIN inv_lot t ON t.id=l.lot_id "
            "LEFT JOIN inv_balance b ON b.item_id=l.item_id AND b.warehouse_id=l.warehouse_id "
            " AND b.lot_key=IFNULL(l.lot_id,0) AND b.rev_key=IFNULL(l.rev_id,0) AND b.loc_key=0 "
            "WHERE %s HAVING avail > 0 ORDER BY %s FOR UPDATE" % (alloc, " AND ".join(where), order), args)

    def post_out(self, doc_type, doc_no, line_no, item_id, wh_id, q, lot_id=None, rev_id=None, country=None, wo_id=None,
                 when=None, own_alloc=False):
        """依先進先出扣減，回傳 (總成本, [(批號, 產地, 數量, 單位成本)])。庫存不足時整筆擋下。"""
        q = qty(q)
        if q <= 0:
            raise BizError("出庫數量要大於 0")
        when = when or dt.datetime.now()
        if isinstance(when, dt.date) and not isinstance(when, dt.datetime):
            when = dt.datetime.combine(when, dt.datetime.now().time())
        layers = self.fifo_candidates(item_id, wh_id, lot_id, rev_id, country, own_alloc)
        have = sum((Decimal(l["avail"]) for l in layers), D0)
        if have < q:
            code = self.db.value("SELECT item_code FROM itm_item WHERE id=%s", (item_id,))
            wh = self.db.value("SELECT wh_name FROM bas_warehouse WHERE id=%s", (wh_id,))
            cond = "（限%s）" % country if country else ""
            raise BizError("%s 在 %s 的可用庫存%s只有 %s，不足 %s" % (code, wh, cond, have.normalize(), q.normalize()))
        left, total, used = q, D0, []
        for l in layers:
            if left <= 0:
                break
            take = min(left, Decimal(l["avail"]))
            if take <= 0:
                continue
            tid = self._txn(doc_type, doc_no, line_no, item_id, wh_id, -take, l["unit_cost"], l["lot_id"], l["rev_id"],
                            None, wo_id, when)
            self.db.exec("UPDATE inv_layer SET remaining_qty=remaining_qty-%s WHERE id=%s", (take, l["id"]))
            amt = money(take * Decimal(l["unit_cost"]))
            self.db.exec("INSERT INTO inv_layer_consume (out_txn_id, layer_id, qty, unit_cost, amount) "
                         "VALUES (%s,%s,%s,%s,%s)", (tid, l["id"], take, l["unit_cost"], amt))
            self._bal(item_id, wh_id, l["lot_id"], l["rev_id"], -take, None, when)
            if own_alloc:   # 用掉自己保留的量
                self.db.exec("UPDATE inv_balance SET allocated_qty=GREATEST(0, allocated_qty-%s) WHERE item_id=%s AND "
                             "warehouse_id=%s AND lot_key=IFNULL(%s,0) AND rev_key=IFNULL(%s,0) AND loc_key=0",
                             (take, item_id, wh_id, l["lot_id"], l["rev_id"]))
            total += amt
            used.append((l["lot_no"], l["origin_country"], take, Decimal(l["unit_cost"])))
            left -= take
        return total, used

    def reserve(self, item_id, wh_id, q, country=None):
        """保留庫存（例：指定日製的工單用料）：依先進先出把保留量記在批號餘額上。回傳實際保留量。"""
        left = qty(q)
        done = D0
        for l in self.fifo_candidates(item_id, wh_id, country=country):
            if left <= 0:
                break
            take = min(left, Decimal(l["avail"]))
            self.db.exec("UPDATE inv_balance SET allocated_qty=allocated_qty+%s WHERE item_id=%s AND warehouse_id=%s AND "
                         "lot_key=IFNULL(%s,0) AND rev_key=IFNULL(%s,0) AND loc_key=0",
                         (take, item_id, wh_id, l["lot_id"], l["rev_id"]))
            left -= take
            done += take
        return done

    # ---------------------------------------------------------------- 查詢
    def stock(self, keyword="", wh_id=None, only_short=False):
        self.need("INV", 1)
        where, args = ["i.is_active=1"], []
        if keyword:
            where.append("(i.item_code LIKE %s OR i.item_name LIKE %s OR i.spec LIKE %s)")
            args += ["%%%s%%" % keyword] * 3
        if wh_id:
            where.append("b.warehouse_id=%s")
            args.append(wh_id)
        rows = self.db.rows(
            "SELECT i.id item_id, i.item_code, i.item_name, i.spec, i.item_type, u.unit_name, "
            "COALESCE(SUM(b.on_hand_qty),0) on_hand, COALESCE(SUM(b.allocated_qty),0) allocated, "
            "COALESCE(SUM(CASE WHEN w.is_nettable=1 AND (r.id IS NULL OR r.status<>'O') THEN b.on_hand_qty END),0) usable, "
            "p.safety_stock, (SELECT SUM(l.remaining_qty*l.unit_cost) FROM inv_layer l WHERE l.item_id=i.id%s) value "
            "FROM itm_item i JOIN bas_unit u ON u.id=i.unit_id LEFT JOIN itm_plan p ON p.item_id=i.id "
            "LEFT JOIN inv_balance b ON b.item_id=i.id LEFT JOIN bas_warehouse w ON w.id=b.warehouse_id "
            "LEFT JOIN itm_revision r ON r.id=b.rev_id WHERE %s GROUP BY i.id ORDER BY i.item_code"
            % (" AND l.warehouse_id=%d" % int(wh_id) if wh_id else "", " AND ".join(where)), args)
        if only_short:
            rows = [r for r in rows if Decimal(r["usable"]) < Decimal(r["safety_stock"] or 0)]
        return rows

    def stock_detail(self, item_id):
        """料件的批號 × 倉庫 × 版本 × 產地明細。"""
        self.need("INV", 1)
        return self.db.rows(
            "SELECT w.wh_name, t.lot_no, rv.rev_code, rv.status rev_status, c.origin_label, t.date_code, t.received_at, "
            "b.on_hand_qty, b.allocated_qty, w.is_nettable FROM inv_balance b JOIN bas_warehouse w ON w.id=b.warehouse_id "
            "LEFT JOIN inv_lot t ON t.id=b.lot_id LEFT JOIN itm_revision rv ON rv.id=b.rev_id "
            "LEFT JOIN bas_country c ON c.country_code=t.origin_country WHERE b.item_id=%s AND b.on_hand_qty<>0 "
            "ORDER BY w.wh_code, t.received_at", (item_id,))

    def layers(self, item_id, open_only=True):
        self.need("INV", 1)
        return self.db.rows(
            "SELECT l.id, l.received_at, w.wh_name, t.lot_no, c.origin_label, rv.rev_code, l.in_qty, l.remaining_qty, "
            "l.unit_cost, l.remaining_qty*l.unit_cost value, x.doc_type, x.doc_no FROM inv_layer l "
            "JOIN bas_warehouse w ON w.id=l.warehouse_id JOIN inv_txn x ON x.id=l.in_txn_id "
            "LEFT JOIN inv_lot t ON t.id=l.lot_id LEFT JOIN bas_country c ON c.country_code=t.origin_country "
            "LEFT JOIN itm_revision rv ON rv.id=l.rev_id WHERE l.item_id=%s%s ORDER BY l.received_at, l.id"
            % ("%s", " AND l.is_closed=0" if open_only else ""), (item_id,))

    def ledger(self, item_id, start=None, end=None):
        self.need("INV", 1)
        where, args = ["x.item_id=%s"], [item_id]
        if start:
            where.append("x.txn_time>=%s")
            args.append(start)
        if end:
            where.append("x.txn_time<%s")
            args.append(end + dt.timedelta(days=1))
        rows = self.db.rows(
            "SELECT x.id, x.txn_time, x.doc_type, d.doc_name, x.doc_no, w.wh_name, t.lot_no, c.origin_label, rv.rev_code, "
            "x.qty, x.unit_cost, x.amount FROM inv_txn x JOIN bas_warehouse w ON w.id=x.warehouse_id "
            "JOIN sys_doc_type d ON d.doc_type=x.doc_type LEFT JOIN inv_lot t ON t.id=x.lot_id "
            "LEFT JOIN bas_country c ON c.country_code=t.origin_country LEFT JOIN itm_revision rv ON rv.id=x.rev_id "
            "WHERE %s ORDER BY x.txn_time, x.id" % " AND ".join(where), args)
        bal = D0
        if start:
            bal = Decimal(self.db.value("SELECT COALESCE(SUM(qty),0) FROM inv_txn WHERE item_id=%s AND txn_time<%s",
                                        (item_id, start)) or 0)
        for r in rows:
            bal += Decimal(r["qty"])
            r["balance"] = bal
            r["qty_in"] = r["qty"] if r["qty"] > 0 else None
            r["qty_out"] = -r["qty"] if r["qty"] < 0 else None
        return rows
