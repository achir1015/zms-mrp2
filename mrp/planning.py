"""規劃引擎：主生產排程（MPS）、物料需求規劃（MRP）、產能需求規劃（RCCP／CRP）、計畫訂單轉單。

MRP 三步驟：
  1. 展開 Exploding：依低階碼由上而下，自製件的計畫訂單 → 下階毛需求（÷ 基準量 × 用量 ÷ (1 − 損耗率)）
  2. 淨需求 Netting：毛需求 − (可用庫存 − 工單已分配 − 安全存量) − 預定接收
  3. 位移 Offsetting：依工廠行事曆往前推前置工作天
"""
import datetime as dt
import math
from collections import defaultdict
from decimal import Decimal

from .core import D0, BizError, date, qty

ONE = Decimal(1)


class Planning:
    # ================================================================ 工作天
    def _calendar(self):
        rows = self.db.rows("SELECT cal_date, workday_seq FROM bas_calendar WHERE is_workday=1 ORDER BY cal_date")
        if not rows:
            raise BizError("工廠行事曆是空的，請到「基本資料 → 工廠行事曆」產生行事曆")
        self._cal_by_seq = {r["workday_seq"]: r["cal_date"] for r in rows}
        self._cal_dates = [r["cal_date"] for r in rows]
        self._cal_seq = {r["cal_date"]: r["workday_seq"] for r in rows}

    def workday_back(self, d, days):
        """d 往前推 days 個工作天（d 若是假日先退到前一個工作天）。"""
        import bisect
        i = bisect.bisect_right(self._cal_dates, d) - 1
        if i < 0:
            return d - dt.timedelta(days=int(days * 1.4))
        seq = self._cal_seq[self._cal_dates[i]] - int(days)
        if seq in self._cal_by_seq:
            return self._cal_by_seq[seq]
        return self._cal_dates[0] - dt.timedelta(days=int((1 - seq) * 1.4))   # 超出行事曆：用日曆天估計

    # ================================================================ 低階碼
    def compute_low_level_codes(self):
        self.db.exec("UPDATE itm_item SET low_level_code=0")
        edges = defaultdict(set)
        for r in self.db.rows("SELECT h.parent_item_id p, d.child_item_id c FROM bom_header h JOIN bom_detail d ON "
                              "d.bom_id=h.id WHERE h.status='A' AND h.is_default=1"):
            edges[r["p"]].add(r["c"])
        llc = {}

        def walk(item, lvl, path):
            if item in path:
                code = self.db.value("SELECT item_code FROM itm_item WHERE id=%s", (item,))
                raise BizError("BOM 有循環：%s 直接或間接用到自己，請修正物料清單" % code)
            if llc.get(item, -1) >= lvl:
                return
            llc[item] = lvl
            for c in edges.get(item, ()):
                walk(c, lvl + 1, path | {item})
        for p in list(edges):
            walk(p, 0, frozenset())
        for item, lvl in llc.items():
            if lvl:
                self.db.exec("UPDATE itm_item SET low_level_code=%s WHERE id=%s", (lvl, item))
        return max(llc.values() or [0])

    # ================================================================ MPS
    def generate_mps(self, start=None, days=None, include_forecast=True):
        """由未出貨的客戶訂單與預測產生主生產排程（MPS 料件）：每期需求 = MAX(預測未沖銷, 訂單)。"""
        self.need("MPS")
        start = date(start or dt.date.today())
        days = int(days or self.param("mrp_horizon_days", 120))
        end = start + dt.timedelta(days=days)
        demand = defaultdict(lambda: {"order": D0, "fc": D0, "so": [], "fcl": []})
        for r in self.db.rows(
                "SELECT d.id, d.item_id, GREATEST(d.due_date, %s) due, d.qty-d.shipped_qty open_qty FROM sal_order_d d "
                "JOIN sal_order_h h ON h.id=d.so_id JOIN itm_plan p ON p.item_id=d.item_id "
                "WHERE h.status IN ('A','P') AND d.status='O' AND d.qty>d.shipped_qty AND d.due_date<=%s "
                "AND p.is_mps_item=1", (start, end)):
            k = (r["item_id"], r["due"])
            demand[k]["order"] += Decimal(r["open_qty"])
            demand[k]["so"].append((r["id"], Decimal(r["open_qty"])))
        if include_forecast:
            for r in self.db.rows(
                    "SELECT d.id, d.item_id, d.period_start, d.forecast_qty-d.consumed_qty q FROM fct_forecast_d d "
                    "JOIN fct_forecast_h h ON h.id=d.forecast_id JOIN itm_plan p ON p.item_id=d.item_id "
                    "WHERE h.status='A' AND d.period_start BETWEEN %s AND %s AND d.forecast_qty>d.consumed_qty "
                    "AND p.is_mps_item=1", (start, end)):
                k = (r["item_id"], r["period_start"])
                demand[k]["fc"] += Decimal(r["q"])
                demand[k]["fcl"].append((r["id"], Decimal(r["q"])))
        if not demand:
            raise BizError("計畫期間內沒有 MPS 料件的未出貨訂單或預測。請確認料件的計畫參數已勾選「列入主生產排程」")
        no = self.next_no("MPS", start)
        with self.db.transaction():
            mid = self.db.exec("INSERT INTO mps_plan_h (mps_no, plan_date, bucket_type, horizon_start, horizon_end, status, "
                               "created_by) VALUES (%s,%s,'D',%s,%s,'C',%s)", (no, start, start, end, self.user_id))
            for (item, d), v in sorted(demand.items(), key=lambda kv: (kv[0][0], kv[0][1])):
                q = max(v["order"], v["fc"])
                lid = self.db.exec("INSERT INTO mps_plan_d (mps_id, item_id, period_start, forecast_qty, order_qty, mps_qty) "
                                   "VALUES (%s,%s,%s,%s,%s,%s)", (mid, item, d, v["fc"], v["order"], q))
                for so_line, oq in v["so"]:
                    self.db.exec("INSERT INTO mps_demand_link (mps_line_id, demand_type, so_line_id, linked_qty) "
                                 "VALUES (%s,'S',%s,%s)", (lid, so_line, oq))
                for fc_line, fq in v["fcl"]:
                    self.db.exec("INSERT INTO mps_demand_link (mps_line_id, demand_type, fc_line_id, linked_qty) "
                                 "VALUES (%s,'F',%s,%s)", (lid, fc_line, fq))
        self.log("ADD", "mps_plan_h", no, None, "MPS")
        return mid

    # ================================================================ MRP
    def run_mrp(self, mps_id, plan_start=None, use_safety=None, use_scrap=None, progress=None):
        """執行一次 MRP（再生法），回傳 mrp_run.id。"""
        self.need("MRP")
        plan_start = date(plan_start or dt.date.today())
        use_safety = bool(int(self.param("mrp_use_safety", 1))) if use_safety is None else use_safety
        use_scrap = bool(int(self.param("mrp_use_scrap", 1))) if use_scrap is None else use_scrap
        mps = self.db.row("SELECT * FROM mps_plan_h WHERE id=%s", (mps_id,))
        if not mps:
            raise BizError("找不到主生產排程")
        if mps["status"] == "X":
            raise BizError("此主生產排程已作廢")
        self._calendar()
        max_llc = self.compute_low_level_codes()
        run_no = self.next_no("MRP", plan_start)
        run_id = self.db.exec("INSERT INTO mrp_run (run_no, mps_id, plan_start, horizon_days, use_safety_stock, use_scrap, "
                              "run_by) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                              (run_no, mps_id, plan_start, (mps["horizon_end"] - plan_start).days, int(use_safety),
                               int(use_scrap), self.user_id))
        try:
            stats = self._mrp(run_id, mps_id, plan_start, max_llc, use_safety, use_scrap, progress)
        except Exception as e:
            self.db.exec("UPDATE mrp_run SET status='E', finished_at=NOW(), message=%s WHERE id=%s", (str(e)[:500], run_id))
            raise
        self.db.exec("UPDATE mrp_run SET status='D', finished_at=NOW(), item_count=%s, planned_count=%s, message=%s "
                     "WHERE id=%s", (stats["items"], stats["orders"], "例外訊息 %d 筆" % stats["exceptions"], run_id))
        self.db.exec("UPDATE mps_plan_h SET status='R' WHERE id=%s", (mps_id,))
        self.log("RUN", "mrp_run", run_no, stats, "MRP")
        return run_id

    def _supply_data(self):
        """各料件的期初可用量、已分配量、預定接收（未結採購、未完工工單）。"""
        avail = defaultdict(lambda: D0)
        for r in self.db.rows(
                "SELECT b.item_id, SUM(b.on_hand_qty) q FROM inv_balance b JOIN bas_warehouse w ON w.id=b.warehouse_id "
                "AND w.is_nettable=1 LEFT JOIN itm_revision r ON r.id=b.rev_id "
                "WHERE r.id IS NULL OR r.status<>'O' GROUP BY b.item_id"):
            avail[r["item_id"]] += Decimal(r["q"])
        for r in self.db.rows(   # 已發放工單尚未領的料 = 已分配需求
                "SELECT m.item_id, SUM(GREATEST(m.required_qty-m.issued_qty,0)) q FROM sfc_wo_material m "
                "JOIN sfc_work_order w ON w.id=m.wo_id WHERE w.status IN ('R','S') AND m.issue_type<>'N' "
                "GROUP BY m.item_id"):
            avail[r["item_id"]] -= Decimal(r["q"])
        receipts = defaultdict(list)
        for r in self.db.rows(
                "SELECT d.item_id, d.due_date dd, d.qty-d.received_qty q, h.po_no doc FROM pur_order_d d "
                "JOIN pur_order_h h ON h.id=d.po_id WHERE d.status='O' AND h.status IN ('A','P') AND d.qty>d.received_qty"):
            receipts[r["item_id"]].append({"date": r["dd"], "qty": Decimal(r["q"]), "doc": r["doc"], "used": False})
        for r in self.db.rows(
                "SELECT item_id, plan_finish dd, plan_qty-completed_qty-scrap_qty q, wo_no doc FROM sfc_work_order "
                "WHERE status IN ('P','R','S') AND plan_qty>completed_qty+scrap_qty"):
            receipts[r["item_id"]].append({"date": r["dd"], "qty": Decimal(r["q"]), "doc": r["doc"], "used": False})
        for v in receipts.values():
            v.sort(key=lambda x: x["date"])
        return avail, receipts

    def _lot(self, p, net, future):
        """批量法則。future＝之後各需求日的毛需求（POQ 用）。"""
        if net <= 0:
            return D0
        rule = p["lot_rule"]
        lot = net
        if rule == "FOQ" and Decimal(p["fixed_lot_qty"]) > 0:
            f = Decimal(p["fixed_lot_qty"])
            lot = f * math.ceil(net / f)
        elif rule == "EOQ":
            eoq = Decimal(p["eoq_qty"] or 0)
            if eoq <= 0 and p["annual_demand"] and p["order_cost"] and p["unit_cost"]:
                h = Decimal(p["unit_cost"]) * Decimal(p["holding_rate"] or "0.2")
                if h > 0:
                    eoq = Decimal(math.sqrt(2 * float(p["annual_demand"]) * float(p["order_cost"]) / float(h)))
            if eoq > 0:
                lot = eoq * math.ceil(net / eoq)
        elif rule == "POQ" and int(p["poq_periods"] or 1) > 1:
            lot = net + sum(future[: int(p["poq_periods"]) - 1], D0)
        mult = Decimal(p["order_multiple"] or 0)
        if mult > 0:
            lot = mult * math.ceil(lot / mult)
        return max(lot, Decimal(p["min_order_qty"] or 0)).quantize(Decimal("0.0001"))

    def _mrp(self, run_id, mps_id, plan_start, max_llc, use_safety, use_scrap, progress):
        items = {r["id"]: r for r in self.db.rows(
            "SELECT i.id, i.item_code, i.source_type, i.low_level_code, i.current_rev_id, p.*, "
            "(SELECT s.unit_price * c.exchange_rate FROM pur_item_source s JOIN bas_currency c ON c.currency_code="
            "s.currency_code WHERE s.item_id=i.id ORDER BY s.priority LIMIT 1) unit_cost "
            "FROM itm_item i LEFT JOIN itm_plan p ON p.item_id=i.id")}
        for it in items.values():
            if it.get("item_id") is None:     # 沒有計畫參數 → 用預設
                it.update(lead_time_days=0, safety_stock=0, lot_rule="LFL", fixed_lot_qty=0, order_multiple=0,
                          min_order_qty=0, poq_periods=1, eoq_qty=0, annual_demand=0, order_cost=0, holding_rate=0.2)
        boms = defaultdict(list)
        for r in self.db.rows(
                "SELECT h.parent_item_id, h.base_qty, d.child_item_id, d.qty_per, d.scrap_rate, d.required_country, "
                "d.effective_date, d.obsolete_date FROM bom_header h JOIN bom_detail d ON d.bom_id=h.id "
                "WHERE h.status='A' AND h.is_default=1"):
            boms[r["parent_item_id"]].append(r)
        avail, receipts = self._supply_data()
        # 需求：item → list of dict(date, qty, src, mps_line, parent_po, country)
        req = defaultdict(list)
        for r in self.db.rows("SELECT id, item_id, period_start, mps_qty FROM mps_plan_d WHERE mps_id=%s AND mps_qty>0",
                              (mps_id,)):
            req[r["item_id"]].append(dict(date=max(r["period_start"], plan_start), qty=Decimal(r["mps_qty"]), src="M",
                                          mps_line=r["id"], parent_po=None, country=None))
        n_orders = n_exc = 0
        records, done_items = [], set()
        for lvl in range(max_llc + 1):
            level_items = [i for i in req if items.get(i, {}).get("low_level_code", 0) == lvl]
            for k, item_id in enumerate(sorted(level_items, key=lambda i: items[i]["item_code"])):
                if progress:
                    progress("第 %d 階：%s" % (lvl, items[item_id]["item_code"]))
                p = items[item_id]
                done_items.add(item_id)
                ss = Decimal(p["safety_stock"] or 0) if use_safety else D0
                poh = avail[item_id] - ss
                by_date = defaultdict(list)
                for d in req[item_id]:
                    by_date[d["date"]].append(d)
                dates = sorted(by_date)
                gross_list = [sum((x["qty"] for x in by_date[d]), D0) for d in dates]
                rcv = receipts.get(item_id, [])
                for di, d in enumerate(dates):
                    gross = gross_list[di]
                    sr = D0
                    for rc in rcv:                       # 需求日前到的預定接收
                        if not rc["used"] and rc["date"] <= d:
                            rc["used"] = True
                            sr += rc["qty"]
                    net = max(D0, gross - (poh + sr))
                    if net > 0:                          # 之後才到的在途量 → 建議提前，而不是另開新單
                        for rc in rcv:
                            if net <= 0:
                                break
                            if not rc["used"] and rc["date"] > d:
                                rc["used"] = True
                                sr += rc["qty"]
                                net = max(D0, gross - (poh + sr))
                                self._exc(run_id, item_id, "EXP", rc["doc"], rc["date"], d, rc["qty"],
                                          "%s 預定 %s 到貨，請提前到 %s" % (rc["doc"], rc["date"], d))
                                n_exc += 1
                    lot = self._lot(p, net, gross_list[di + 1:])
                    lt = int(p["lead_time_days"] or 0) + int(p.get("safety_lead_days") or 0)
                    rel = self.workday_back(d, lt) if lot > 0 else None
                    poh = poh + sr + lot - gross
                    records.append((run_id, item_id, d, gross, sr, poh + ss, net, lot, lot))
                    countries = {x["country"] for x in by_date[d]}
                    country = countries.pop() if len(countries) == 1 else None
                    po_id = None
                    if lot > 0:
                        otype = {"M": "M", "O": "O"}.get(p["source_type"], "P")
                        sup = None
                        if otype != "M":
                            sup = self.db.value(
                                "SELECT supplier_id FROM pur_item_source WHERE item_id=%s AND (%s IS NULL OR "
                                "origin_country=%s) ORDER BY priority LIMIT 1", (item_id, country, country)) \
                                or self.db.value("SELECT supplier_id FROM pur_item_source WHERE item_id=%s "
                                                 "ORDER BY priority LIMIT 1", (item_id,))
                        po_id = self.db.exec(
                            "INSERT INTO mrp_planned_order (run_id, item_id, rev_id, order_type, qty, release_date, due_date, "
                            "supplier_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                            (run_id, item_id, p["current_rev_id"], otype, lot, rel, d, sup))
                        n_orders += 1
                        if rel < plan_start:
                            self._exc(run_id, item_id, "PDL", None, None, rel, lot,
                                      "應於 %s 發出（前置 %d 工作天），已逾期，請加急或調整交期" % (rel, lt))
                            n_exc += 1
                        if country:
                            self._exc(run_id, item_id, "NEW", None, None, rel, lot,
                                      "需求指定產地 %s，已選該產地的供應來源" % country)
                            n_exc += 1
                        if otype == "M":                 # 展開到下一階
                            for b in boms.get(item_id, ()):
                                if b["effective_date"] > rel or (b["obsolete_date"] and b["obsolete_date"] <= rel):
                                    continue
                                scrap = Decimal(b["scrap_rate"] or 0) if use_scrap else D0
                                cq = (lot / Decimal(b["base_qty"] or 1) * Decimal(b["qty_per"]) / (ONE - scrap))
                                req[b["child_item_id"]].append(dict(
                                    date=max(rel, plan_start), qty=cq.quantize(Decimal("0.0001")), src="P",
                                    mps_line=None, parent_po=po_id, country=b["required_country"]))
                    peg = [(run_id, item_id, d, x["qty"], x["src"], x["mps_line"], x["parent_po"], po_id)
                           for x in by_date[d]]
                    self.db.exec_many("INSERT INTO mrp_pegging (run_id, item_id, need_date, need_qty, source_type, "
                                      "mps_line_id, parent_po_id, supply_po_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", peg)
                if poh < 0 and use_safety:
                    self._exc(run_id, item_id, "SFT", None, None, None, -poh, "期末預計在庫低於安全存量")
                    n_exc += 1
                for rc in rcv:                           # 沒用到的在途量 → 建議延後或取消
                    if not rc["used"]:
                        self._exc(run_id, item_id, "CAN" if not dates or rc["date"] > dates[-1] else "DLY",
                                  rc["doc"], rc["date"], None, rc["qty"],
                                  "%s 的 %s 在計畫期間內用不到，可考慮延後或取消" % (rc["doc"], rc["qty"].normalize()))
                        n_exc += 1
        self.db.exec_many("INSERT INTO mrp_record (run_id, item_id, period_start, gross_req, scheduled_receipt, "
                          "projected_oh, net_req, planned_receipt, planned_release) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                          records)
        return dict(items=len(done_items), orders=n_orders, exceptions=n_exc)

    def _exc(self, run_id, item_id, typ, doc, ref_date, sug, q, msg):
        self.db.exec("INSERT INTO mrp_exception (run_id, item_id, msg_type, ref_doc_no, ref_date, suggest_date, qty, message) "
                     "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (run_id, item_id, typ, doc, ref_date, sug, q or 0, msg[:200]))

    # ================================================================ 查詢
    def mrp_runs(self):
        return self.db.rows("SELECT r.*, m.mps_no, u.user_name FROM mrp_run r JOIN mps_plan_h m ON m.id=r.mps_id "
                            "LEFT JOIN sys_user u ON u.id=r.run_by ORDER BY r.id DESC LIMIT 100")

    def mrp_records(self, run_id, keyword=""):
        args = [run_id]
        kw = ""
        if keyword:
            kw = " AND (i.item_code LIKE %s OR i.item_name LIKE %s)"
            args += ["%%%s%%" % keyword] * 2
        return self.db.rows(
            "SELECT r.*, i.item_code, i.item_name, i.low_level_code, i.source_type, p.release_date, p.order_type, "
            "p.id po_id FROM mrp_record r JOIN itm_item i ON i.id=r.item_id LEFT JOIN mrp_planned_order p ON "
            "p.run_id=r.run_id AND p.item_id=r.item_id AND p.due_date=r.period_start "
            "WHERE r.run_id=%s" + kw + " ORDER BY i.low_level_code, i.item_code, r.period_start", args)

    def planned_orders(self, run_id, status=None):
        return self.db.rows(
            "SELECT p.*, i.item_code, i.item_name, s.sup_name, rv.rev_code FROM mrp_planned_order p "
            "JOIN itm_item i ON i.id=p.item_id LEFT JOIN pur_supplier s ON s.id=p.supplier_id "
            "LEFT JOIN itm_revision rv ON rv.id=p.rev_id WHERE p.run_id=%s%s ORDER BY p.release_date, i.item_code"
            % ("%s", " AND p.status IN (%s)" % ",".join("'%s'" % x for x in status) if status else ""), (run_id,))

    def exceptions(self, run_id):
        return self.db.rows("SELECT e.*, i.item_code, i.item_name FROM mrp_exception e JOIN itm_item i ON i.id=e.item_id "
                            "WHERE e.run_id=%s ORDER BY FIELD(e.msg_type,'PDL','EXP','SFT','NEW','DLY','CAN'), "
                            "i.item_code", (run_id,))

    def pegging(self, run_id, item_id):
        return self.db.rows(
            "SELECT g.need_date, g.need_qty, g.source_type, pi.item_code parent_code, pi.item_name parent_name, "
            "pp.qty parent_qty, pp.release_date parent_release, m.mps_no FROM mrp_pegging g "
            "LEFT JOIN mrp_planned_order pp ON pp.id=g.parent_po_id LEFT JOIN itm_item pi ON pi.id=pp.item_id "
            "LEFT JOIN mps_plan_d md ON md.id=g.mps_line_id LEFT JOIN mps_plan_h m ON m.id=md.mps_id "
            "WHERE g.run_id=%s AND g.item_id=%s ORDER BY g.need_date", (run_id, item_id))

    # ================================================================ 計畫訂單轉單
    def firm_planned(self, ids, firm=True):
        self.need("MRP")
        self.db.exec("UPDATE mrp_planned_order SET status=%%s WHERE id IN (%s) AND status IN ('N','F')"
                     % ",".join(str(int(i)) for i in ids), ("F" if firm else "N",))

    def convert_planned(self, ids):
        """把勾選的計畫訂單轉成單據：採購件依供應商合併成採購單（草稿），自製件各開一張工單（計畫狀態）。"""
        self.need("MRP")
        rows = self.db.rows("SELECT p.*, i.item_code FROM mrp_planned_order p JOIN itm_item i ON i.id=p.item_id "
                            "WHERE p.id IN (%s) AND p.status IN ('N','F')" % ",".join(str(int(i)) for i in ids))
        if not rows:
            raise BizError("請勾選尚未轉單的計畫訂單")
        made = []
        with self.db.transaction():
            by_sup = defaultdict(list)
            for r in rows:
                if r["order_type"] == "M":
                    no = self.create_work_order(r["item_id"], r["qty"], r["release_date"], r["due_date"],
                                                planned_order_id=r["id"], rev_id=r["rev_id"])
                    self.db.exec("UPDATE mrp_planned_order SET status='C', converted_doc_no=%s WHERE id=%s", (no, r["id"]))
                    made.append(no)
                else:
                    if not r["supplier_id"]:
                        raise BizError("%s 沒有供應商，請先到「料件供應來源」設定" % r["item_code"])
                    by_sup[r["supplier_id"]].append(r)
            for sup, lines in by_sup.items():
                no = self.create_po_from_planned(sup, lines)
                made.append(no)
        self.log("CONVERT", "mrp_planned_order", ",".join(made), None, "MRP")
        return made

    # ================================================================ 產能
    def run_crp(self, mrp_run_id=None, include_wo=True, start=None, days=None):
        """細部產能 CRP：MRP 自製計畫訂單＋未完工工單 × 途程工序 → 工作中心每日負荷（自發出日起依序排程）。"""
        self.need("CRP")
        self._calendar()
        start = date(start or dt.date.today())
        days = int(days or self.param("crp_horizon_days", 60))
        end = start + dt.timedelta(days=days)
        no = self.next_no("CRP", start)
        rid = self.db.exec("INSERT INTO crp_run (run_no, run_type, mrp_run_id, horizon_start, horizon_end, run_by) "
                           "VALUES (%s,'C',%s,%s,%s,%s)", (no, mrp_run_id, start, end, self.user_id))
        cap = self._wc_capacity(start, end)
        load = defaultdict(lambda: D0)
        detail = []
        jobs = []
        if mrp_run_id:
            for r in self.db.rows("SELECT p.id, p.item_id, p.qty, p.release_date, CONCAT('計畫#', p.id) doc FROM "
                                  "mrp_planned_order p WHERE p.run_id=%s AND p.order_type='M' AND p.status IN ('N','F')",
                                  (mrp_run_id,)):
                ops = self.db.rows("SELECT d.op_seq, d.wc_id, d.setup_hours, d.run_hours FROM rou_routing_h h JOIN "
                                   "rou_routing_d d ON d.routing_id=h.id WHERE h.item_id=%s AND h.is_default=1 AND "
                                   "h.status='A' ORDER BY d.op_seq", (r["item_id"],))
                jobs.append(("P", r["doc"], r["item_id"], Decimal(r["qty"]), r["release_date"],
                             [(o["op_seq"], o["wc_id"], Decimal(o["setup_hours"]), Decimal(o["run_hours"]) * Decimal(r["qty"]))
                              for o in ops]))
        if include_wo:
            for w in self.db.rows("SELECT id, wo_no, item_id, plan_qty-completed_qty q, plan_start FROM sfc_work_order "
                                  "WHERE status IN ('P','R','S') AND plan_qty>completed_qty"):
                ops = self.db.rows("SELECT op_seq, wc_id, plan_setup_hours s, plan_run_hours r, good_qty, status FROM "
                                   "sfc_wo_operation WHERE wo_id=%s AND status<>'F' ORDER BY op_seq", (w["id"],))
                plan = self.db.value("SELECT plan_qty FROM sfc_work_order WHERE id=%s", (w["id"],)) or 1
                jobs.append(("W", w["wo_no"], w["item_id"], Decimal(w["q"]), max(w["plan_start"], start),
                             [(o["op_seq"], o["wc_id"], Decimal(o["s"]) if not o["good_qty"] else D0,
                               Decimal(o["r"]) * Decimal(w["q"]) / Decimal(plan)) for o in ops]))
        for typ, doc, item, q, rel, ops in jobs:
            day = max(rel, start)
            for seq, wc, setup, run in ops:
                hours = setup + run
                day = self._next_workday(day)
                load[(wc, day)] += hours
                detail.append((wc, day, typ, doc, item, seq, q, setup, run))
                per_day = cap.get((wc, day)) or Decimal(8)
                day = self._add_workdays(day, max(0, math.ceil(hours / per_day) - 1)) if per_day else day
        ids = {}
        for (wc, d), h in sorted(load.items(), key=lambda x: (x[0][1], x[0][0])):
            c = cap.get((wc, d), D0)
            ids[(wc, d)] = self.db.exec("INSERT INTO crp_load (run_id, wc_id, period_start, required_hours, available_hours, "
                                        "load_pct) VALUES (%s,%s,%s,%s,%s,%s)",
                                        (rid, wc, d, h, c, (h * 100 / c).quantize(Decimal("0.01")) if c else 999))
        self.db.exec_many("INSERT INTO crp_load_detail (load_id, source_type, source_doc_no, item_id, op_seq, qty, "
                          "setup_hours, run_hours) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                          [(ids[(wc, d)], typ, doc, item, seq, q, s, r) for wc, d, typ, doc, item, seq, q, s, r in detail])
        self.log("RUN", "crp_run", no, None, "CRP")
        return rid

    def _next_workday(self, d):
        import bisect
        i = bisect.bisect_left(self._cal_dates, d)
        return self._cal_dates[i] if i < len(self._cal_dates) else d

    def _add_workdays(self, d, n):
        s = self._cal_seq.get(d)
        if s is None:
            return d
        return self._cal_by_seq.get(s + n, d)

    def _wc_capacity(self, start, end):
        """工作中心每日可用工時 = 人機數 × 班次 × 每班工時 × 效率 × 利用率；例外產能覆寫。"""
        cap = {}
        wcs = self.db.rows("SELECT * FROM rou_work_center WHERE is_active=1")
        days = self.db.rows("SELECT cal_date, shift_count, is_workday FROM bas_calendar WHERE cal_date BETWEEN %s AND %s",
                            (start - dt.timedelta(days=30), end + dt.timedelta(days=90)))
        for w in wcs:
            per = (Decimal(w["resource_count"]) * Decimal(w["hours_per_shift"]) * Decimal(w["efficiency"]) *
                   Decimal(w["utilization"]))
            for d in days:
                cap[(w["id"], d["cal_date"])] = (per * Decimal(d["shift_count"])).quantize(Decimal("0.01")) \
                    if d["is_workday"] else D0
        for o in self.db.rows("SELECT * FROM rou_wc_calendar WHERE cal_date BETWEEN %s AND %s",
                              (start - dt.timedelta(days=30), end + dt.timedelta(days=90))):
            cap[(o["wc_id"], o["cal_date"])] = Decimal(o["available_hours"])
        return cap

    def run_rccp(self, mps_id):
        """粗略產能 RCCP：MPS 量 × 資源清單（沒設定時用途程整條工時）→ 各工作中心負荷。"""
        self.need("CRP")
        self._calendar()
        mps = self.db.row("SELECT * FROM mps_plan_h WHERE id=%s", (mps_id,))
        no = self.next_no("CRP", mps["horizon_start"])
        rid = self.db.exec("INSERT INTO crp_run (run_no, run_type, mps_id, horizon_start, horizon_end, run_by) "
                           "VALUES (%s,'R',%s,%s,%s,%s)", (no, mps_id, mps["horizon_start"], mps["horizon_end"],
                                                          self.user_id))
        cap = self._wc_capacity(mps["horizon_start"], mps["horizon_end"])
        load = defaultdict(lambda: D0)
        for m in self.db.rows("SELECT item_id, period_start, mps_qty FROM mps_plan_d WHERE mps_id=%s AND mps_qty>0", (mps_id,)):
            bill = self.db.rows("SELECT wc_id, hours_per_unit h, offset_days o FROM crp_bill_resource WHERE item_id=%s",
                                (m["item_id"],))
            if not bill:
                bill = self.db.rows("SELECT d.wc_id, SUM(d.run_hours + d.setup_hours/50) h, 0 o FROM rou_routing_h h "
                                    "JOIN rou_routing_d d ON d.routing_id=h.id WHERE h.item_id=%s AND h.is_default=1 "
                                    "GROUP BY d.wc_id", (m["item_id"],))
            for b in bill:
                d = self.workday_back(m["period_start"], int(b["o"] or 0))
                load[(b["wc_id"], d)] += Decimal(b["h"]) * Decimal(m["mps_qty"])
        for (wc, d), h in load.items():
            c = cap.get((wc, d), D0)
            self.db.exec("INSERT INTO crp_load (run_id, wc_id, period_start, required_hours, available_hours, load_pct) "
                         "VALUES (%s,%s,%s,%s,%s,%s)", (rid, wc, d, h, c, (h * 100 / c).quantize(Decimal("0.01")) if c else 999))
        return rid

    def crp_runs(self):
        return self.db.rows("SELECT c.*, m.run_no mrp_no, p.mps_no FROM crp_run c LEFT JOIN mrp_run m ON m.id=c.mrp_run_id "
                            "LEFT JOIN mps_plan_h p ON p.id=c.mps_id ORDER BY c.id DESC LIMIT 60")

    def crp_load(self, run_id):
        return self.db.rows("SELECT l.*, w.wc_code, w.wc_name, w.is_bottleneck FROM crp_load l JOIN rou_work_center w "
                            "ON w.id=l.wc_id WHERE l.run_id=%s ORDER BY w.wc_code, l.period_start", (run_id,))

    def crp_detail(self, load_id):
        return self.db.rows("SELECT d.*, i.item_code, i.item_name FROM crp_load_detail d JOIN itm_item i ON i.id=d.item_id "
                            "WHERE d.load_id=%s ORDER BY d.source_doc_no", (load_id,))
