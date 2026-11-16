"""規劃畫面：主生產排程 MPS、執行 MRP（時距表、計畫訂單、例外訊息、需求追溯）、產能需求 CRP。"""
import datetime as dt
from collections import defaultdict
from decimal import Decimal

import flet as ft

from .. import rocdate
from . import theme as T
from .widgets import tab_value, tabs

I = ft.Icons


# ================================================================ MPS
class MpsScreen(ft.Row):
    def __init__(self, ctx, mps_id=None):
        self.ctx, self.b = ctx, ctx.books
        self.editable = self.b.can("MPS", 2)
        self.grid = T.Grid([("mps_no", "排程單號", "s", 120), ("plan_date", "編製日", "d", 80), ("n_lines", "筆數", "s", 40),
                            ("status", "狀態", "st:mps", 90)], on_pick=lambda r: self.open(r["id"]))
        self.panel = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)
        acts = [T.btn("產生 MPS", I.AUTO_AWESOME, lambda e: self.gen_dialog())] if self.editable else []
        left = ft.Column([T.page_header(I.EVENT_NOTE, "主生產排程 MPS", "由未出貨訂單與預測產生；MPS 量＝要滿足的需求",
                                        "blue", acts), self.grid], width=430, spacing=12)
        super().__init__([left, T.card(self.panel, expand=True, padding=18)], expand=True, spacing=14,
                         vertical_alignment=ft.CrossAxisAlignment.START)
        self.reload(refresh=False)
        self.open(mps_id or (self.rows[0]["id"] if self.rows else None), refresh=False)

    def reload(self, refresh=True):
        self.rows = self.b.db.rows("SELECT h.*, (SELECT COUNT(*) FROM mps_plan_d d WHERE d.mps_id=h.id) n_lines FROM "
                                   "mps_plan_h h ORDER BY h.id DESC")
        self.grid.set_rows(self.rows)
        if refresh:
            self.update()

    def open(self, mid, refresh=True):
        self.mid = mid
        if not mid:
            self.panel.controls = [T.empty_state(I.EVENT_NOTE, "還沒有主生產排程", "按「產生 MPS」由客戶訂單與預測產生")]
        else:
            h = self.b.db.row("SELECT * FROM mps_plan_h WHERE id=%s", (mid,))
            lines = self.b.db.rows("SELECT d.*, i.item_code, i.item_name, (SELECT GROUP_CONCAT(o.so_no SEPARATOR '、') FROM "
                                   "mps_demand_link k JOIN sal_order_d sd ON sd.id=k.so_line_id JOIN sal_order_h o ON "
                                   "o.id=sd.so_id WHERE k.mps_line_id=d.id) orders FROM mps_plan_d d JOIN itm_item i ON "
                                   "i.id=d.item_id WHERE d.mps_id=%s ORDER BY i.item_code, d.period_start", (mid,))
            g = T.Grid([("item_code", "料件", "s", 110), ("item_name", "品名", "s", 170), ("period_start", "需求日", "d", 90),
                        ("forecast_qty", "預測", "qz", 70), ("order_qty", "訂單", "qz", 70), ("mps_qty", "MPS 量", "q", 80),
                        ("orders", "來源訂單", "s", 160)], on_pick=self.edit_qty)
            g.set_rows(lines)
            acts = []
            if self.editable and h["status"] != "X":
                acts = [T.btn("執行 MRP", I.PLAY_CIRCLE, lambda e: self.ctx.app.go("mrp_run", mps_id=mid), kind="accent"),
                        T.btn("粗略產能 RCCP", I.SPEED, lambda e: self.rccp(), kind="outline"),
                        T.btn("作廢", I.BLOCK, lambda e: self.void(), kind="danger")]
            self.panel.controls = [
                ft.Row([T.icon_tile(I.EVENT_NOTE, "blue", 44), ft.Column([
                    ft.Text(h["mps_no"], size=19, weight=ft.FontWeight.W_800),
                    T.muted("計畫期間 %s ～ %s；點選明細可修改 MPS 量" % (rocdate.show(h["horizon_start"]),
                                                                rocdate.show(h["horizon_end"])))], spacing=0, expand=True),
                    T.status_chip(h["status"], "mps")]), g, ft.Row(acts, spacing=8, wrap=True)]
        if refresh:
            self.update()

    def gen_dialog(self):
        c = self.ctx
        start = T.date_field("計畫起日", width=170)
        days = T.field("計畫天數", self.b.param("mrp_horizon_days", "120"), width=120, text_align=ft.TextAlign.RIGHT)
        fc = T.switch("包含已核准的需求預測", True)

        def go(e):
            mid = c.guard(self.b.generate_mps, start.value, int(days.value or 120), fc.value)
            if mid:
                c.close()
                c.toast("已產生主生產排程")
                self.reload(refresh=False)
                self.open(mid)
        c.dialog("產生主生產排程", ft.Column([
            T.muted("把計畫期間內「已核准、未出貨」的客戶訂單與預測，依 MPS 料件與日期整理成主生產排程。"
                    "每期需求取預測未沖銷量與訂單量較大者。料件要在「計畫參數」勾選列入主生產排程。", 13),
            ft.Row([start, days]), fc], tight=True, spacing=12),
            [T.btn("取消", kind="ghost", on_click=lambda e: c.close()), T.btn("產生", I.AUTO_AWESOME, go)],
            icon=I.EVENT_NOTE, width=520)

    def edit_qty(self, r):
        if not self.editable:
            return
        c = self.ctx
        q = T.field("MPS 量", T.qfmt(r["mps_qty"]), width=160, text_align=ft.TextAlign.RIGHT, autofocus=True)
        d = T.date_field("需求日", r["period_start"], width=170)

        def go(e):
            try:
                v = Decimal(q.value.replace(",", ""))
                day = rocdate.read(d.value)
            except Exception:
                c.toast("數字或日期格式不正確", True)
                return
            self.b.db.exec("UPDATE mps_plan_d SET mps_qty=%s, period_start=%s, is_firm=1 WHERE id=%s", (v, day, r["id"]))
            self.b.log("EDIT", "mps_plan_d", r["id"], {"mps_qty": v}, "MPS")
            c.close()
            self.open(self.mid)
        c.dialog("修改 MPS：%s" % r["item_code"], ft.Row([d, q]), [T.btn("取消", kind="ghost", on_click=lambda e: c.close()),
                                                                 T.btn("儲存", I.SAVE, go)], icon=I.EDIT, width=420)

    def rccp(self):
        rid = self.ctx.guard(self.b.run_rccp, self.mid)
        if rid:
            self.ctx.app.go("crp", run_id=rid)

    def void(self):
        def go():
            self.b.db.exec("UPDATE mps_plan_h SET status='X' WHERE id=%s", (self.mid,))
            self.reload(refresh=False)
            self.open(self.mid)
        self.ctx.confirm("作廢主生產排程", "作廢後不能再執行 MRP，確定嗎？", go, yes="作廢")


# ================================================================ MRP
class MrpScreen(ft.Column):
    def __init__(self, ctx, mps_id=None, run_id=None, tab="rec"):
        self.ctx, self.b = ctx, ctx.books
        self.editable = self.b.can("MRP", 2)
        mps = [(r["id"], "%s（%s）" % (r["mps_no"], rocdate.show(r["plan_date"]))) for r in
               self.b.db.rows("SELECT * FROM mps_plan_h WHERE status<>'X' ORDER BY id DESC")]
        self.mps = T.dropdown("主生產排程", mps, mps_id or (mps[0][0] if mps else None), width=260, filterable=False)
        self.start = T.date_field("計畫起日", width=160)
        self.ss = T.switch("考慮安全存量", True)
        self.scrap = T.switch("考慮損耗率", True)
        runs = self.b.mrp_runs()
        self.run = T.dropdown("執行結果", [(r["id"], "%s　%s" % (r["run_no"], r["mps_no"])) for r in runs],
                              run_id or (runs[0]["id"] if runs else None), width=280, filterable=False,
                              on_select=lambda e: self.render())
        self.tab = tabs([("rec", "MRP 時距表"), ("po", "計畫訂單"), ("exc", "例外訊息")], tab, lambda e: self.render())
        self.kw = T.field("搜尋料件", "", width=170, prefix_icon=I.SEARCH, on_submit=lambda e: self.render())
        self.summary = ft.Row(spacing=10, wrap=True)
        self.body = ft.Column(spacing=10, expand=True)
        runbar = ft.Row([self.mps, self.start, self.ss, self.scrap,
                         T.btn("執行 MRP", I.PLAY_CIRCLE, lambda e: self.do_run(), kind="accent")], wrap=True, spacing=12)
        super().__init__([T.page_header(I.SCHEMA, "物料需求規劃 MRP",
                                        "展開 → 淨需求 → 批量 → 前置時間位移；產生計畫訂單與例外訊息", "violet"),
                          T.card(runbar, padding=14) if self.editable else ft.Container(),
                          ft.Row([self.run, self.tab, self.kw]), self.summary,
                          self.body], spacing=12, expand=True)
        self.render(refresh=False)

    def do_run(self):
        if not self.mps.value:
            self.ctx.toast("請先產生主生產排程", True)
            return
        self.ctx.toast("MRP 運算中，請稍候…")
        rid = self.ctx.guard(self.b.run_mrp, int(self.mps.value), self.start.value, self.ss.value, self.scrap.value)
        if rid:
            self.ctx.app.go("mrp_run", run_id=rid, tab="rec")

    def render(self, refresh=True):
        rid = int(self.run.value) if self.run.value else None
        if not rid:
            self.body.controls = [T.empty_state(I.SCHEMA, "還沒有執行過 MRP", "選擇主生產排程後按「執行 MRP」")]
            if refresh:
                self.update()
            return
        r = self.b.db.row("SELECT * FROM mrp_run WHERE id=%s", (rid,))
        n_exc = self.b.db.value("SELECT COUNT(*) FROM mrp_exception WHERE run_id=%s", (rid,))
        pdl = self.b.db.value("SELECT COUNT(*) FROM mrp_exception WHERE run_id=%s AND msg_type='PDL'", (rid,))
        self.summary.controls = [T.chip("料件 %s" % r["item_count"], "blue"), T.chip("計畫訂單 %s" % r["planned_count"], "teal"),
                                 T.chip("例外 %s" % n_exc, "orange"), *([T.chip("逾期 %s" % pdl, "rose", I.WARNING)] if pdl else [])]
        getattr(self, "r_" + tab_value(self.tab))(rid)
        if refresh:
            self.update()

    def r_rec(self, rid):
        rows = self.b.mrp_records(rid, (self.kw.value or "").strip())
        g = T.Grid([("item_code", "料號", "s", 100), ("item_name", "品名", "s", 150), ("low_level_code", "階", "s", 26),
                    ("period_start", "需求日", "d", 80), ("gross_req", "毛需求", "q", 80), ("scheduled_receipt", "預定接收", "qz", 70),
                    ("projected_oh", "預計在庫", "q", 76), ("net_req", "淨需求", "qz", 76), ("planned_receipt", "計畫接收", "qz", 76),
                    ("release_date", "計畫發出日", "d", 86), ("order_type", "類", "st:otype", 54)],
                   on_pick=lambda r: self.peg(rid, r),
                   row_style=lambda r: {"color": T.DANGER} if r["release_date"] and r["release_date"] < dt.date.today() else None)
        g.set_rows(rows)
        self.body.controls = [T.muted("淨需求 = 毛需求 − (可用庫存 − 工單已分配 − 安全存量) − 預定接收；紅字＝發出日已過。點選一列看需求追溯。", 12), g]

    def r_po(self, rid):
        rows = self.b.planned_orders(rid)
        self.po_grid = T.Grid([("item_code", "料號", "s", 100), ("item_name", "品名", "s", 150), ("rev_code", "版本", "s", 40),
                               ("order_type", "類", "st:otype", 54), ("qty", "數量", "q", 80), ("release_date", "發出日", "d", 80),
                               ("due_date", "需求日", "d", 80), ("sup_name", "建議供應商", "s", 110), ("status", "狀態", "st:po", 70),
                               ("converted_doc_no", "轉出單號", "s", 110)], selectable=self.editable)
        self.po_grid.set_rows(rows)
        acts = []
        if self.editable:
            acts = [T.btn("轉成採購單／工單", I.SYNC_ALT, lambda e: self.convert()),
                    T.btn("確認（Firm）", I.LOCK, lambda e: self.firm(True), kind="outline"),
                    T.btn("取消確認", I.LOCK_OPEN, lambda e: self.firm(False), kind="ghost")]
        self.body.controls = [ft.Row(acts, spacing=8),
                              T.muted("勾選後轉單：採購件依供應商合併成採購單草稿，自製件各開一張工單（計畫狀態）。", 12),
                              self.po_grid]

    def r_exc(self, rid):
        rows = self.b.exceptions(rid)
        g = T.Grid([("msg_type", "類型", "st:msg", 100), ("item_code", "料號", "s", 100), ("item_name", "品名", "s", 150),
                    ("ref_doc_no", "相關單號", "s", 110), ("ref_date", "原日期", "d", 80), ("suggest_date", "建議日期", "d", 80),
                    ("qty", "數量", "qz", 70), ("message", "訊息", "s", 330)], empty="沒有例外訊息")
        g.set_rows(rows)
        self.body.controls = [g]

    def convert(self):
        ids = [r["id"] for r in self.po_grid.selected_rows() if r["status"] in ("N", "F")]
        if not ids:
            self.ctx.toast("請勾選尚未轉單的計畫訂單", True)
            return
        made = self.ctx.guard(self.b.convert_planned, ids)
        if made:
            self.ctx.toast("已轉出：%s" % "、".join(made))
            self.render()

    def firm(self, on):
        ids = [r["id"] for r in self.po_grid.selected_rows()]
        if ids and self.ctx.guard(self.b.firm_planned, ids, on):
            self.render()

    def peg(self, rid, r):
        rows = self.b.pegging(rid, r["item_id"])
        for x in rows:
            x["src"] = {"M": "MPS " + (x["mps_no"] or ""), "P": "上階計畫訂單", "W": "工單", "S": "安全存量"}.get(x["source_type"], "")
        g = T.Grid([("need_date", "需求日", "d", 80), ("need_qty", "需求量", "q", 80), ("src", "來源", "s", 140),
                    ("parent_code", "上階料號", "s", 100), ("parent_name", "上階品名", "s", 140),
                    ("parent_qty", "上階計畫量", "qz", 80)], height=300)
        g.set_rows(rows)
        self.ctx.dialog("需求追溯：%s　%s" % (r["item_code"], r["item_name"]), g,
                        [T.btn("關閉", on_click=lambda e: self.ctx.close())], icon=I.ACCOUNT_TREE, tone="violet", width=760)


# ================================================================ CRP
class CrpScreen(ft.Column):
    def __init__(self, ctx, run_id=None):
        self.ctx, self.b = ctx, ctx.books
        runs = self.b.crp_runs()
        self.run = T.dropdown("產能運算結果", [(r["id"], "%s　%s %s" % (r["run_no"], "RCCP" if r["run_type"] == "R" else "CRP",
                                                                     r["mrp_no"] or r["mps_no"] or "")) for r in runs],
                              run_id or (runs[0]["id"] if runs else None), width=330, filterable=False,
                              on_select=lambda e: self.render())
        mruns = self.b.mrp_runs()
        self.mrp = T.dropdown("依據 MRP", [(r["id"], r["run_no"]) for r in mruns], mruns[0]["id"] if mruns else None,
                              width=220, filterable=False)
        self.wo = T.switch("包含未完工工單", True)
        self.body = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)
        bar = ft.Row([self.mrp, self.wo, T.btn("執行 CRP", I.PLAY_CIRCLE, lambda e: self.do_run(), kind="accent")],
                     spacing=12) if self.b.can("CRP", 2) else ft.Container()
        super().__init__([T.page_header(I.SPEED, "產能需求規劃 CRP", "計畫訂單與工單的工序排到工作中心每一天；超過 100% 即超載",
                                        "rose", [bar]), ft.Row([self.run]), self.body], spacing=12, expand=True)
        self.render(refresh=False)

    def do_run(self):
        rid = self.ctx.guard(self.b.run_crp, int(self.mrp.value) if self.mrp.value else None, self.wo.value)
        if rid:
            self.ctx.app.go("crp", run_id=rid)

    def render(self, refresh=True):
        rid = int(self.run.value) if self.run.value else None
        if not rid:
            self.body.controls = [T.empty_state(I.SPEED, "還沒有產能運算結果", "先執行 MRP，再按「執行 CRP」")]
            if refresh:
                self.update()
            return
        rows = self.b.crp_load(rid)
        days = sorted({r["period_start"] for r in rows})
        by = defaultdict(dict)
        names = {}
        for r in rows:
            by[r["wc_id"]][r["period_start"]] = r
            names[r["wc_id"]] = (r["wc_code"], r["wc_name"], r["is_bottleneck"])
        head = [ft.Container(ft.Text("工作中心", size=12, weight=ft.FontWeight.W_700), width=170)] + \
               [ft.Container(ft.Text(rocdate.show(d)[4:], size=11, color=T.MUTED), width=58, alignment=ft.Alignment.CENTER)
                for d in days]
        lines = [ft.Row(head, spacing=4)]
        for wc, cells in by.items():
            code, name, bn = names[wc]
            row = [ft.Container(ft.Row([ft.Text("%s %s" % (code, name), size=13, weight=ft.FontWeight.W_600, expand=True),
                                        *([T.chip("瓶頸", "rose", size=10)] if bn else [])]), width=170)]
            for d in days:
                c = cells.get(d)
                if not c:
                    row.append(ft.Container(width=58, height=40))
                    continue
                pct = float(c["load_pct"])
                color = "#DCFCE7" if pct <= 80 else "#FEF1C7" if pct <= 100 else "#FFE4E8"
                fg = T.SUCCESS if pct <= 80 else T.WARN if pct <= 100 else T.DANGER
                row.append(ft.Container(ft.Column([ft.Text("%d%%" % round(pct), size=13, weight=ft.FontWeight.W_800, color=fg),
                                                   ft.Text("%s/%s" % (T.qfmt(round(c["required_hours"], 1)),
                                                                      T.qfmt(round(c["available_hours"], 1))), size=9,
                                                           color=T.MUTED)], spacing=0,
                                                  horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                        width=58, height=40, bgcolor=color, border_radius=8, alignment=ft.Alignment.CENTER,
                                        tooltip="需求 %s 小時／可用 %s 小時" % (c["required_hours"], c["available_hours"]),
                                        on_click=lambda e, c=c: self.detail(c)))
            lines.append(ft.Row(row, spacing=4))
        over = [r for r in rows if r["load_pct"] > 100]
        legend = ft.Row([T.chip("≤80% 正常", "green"), T.chip("80～100% 偏高", "amber"), T.chip(">100% 超載", "rose"),
                         T.muted("每格：負荷率與需求／可用工時；點格子看來源", 12)], spacing=8)
        tot = ft.Row([T.kpi("超載格數", str(len(over)), I.WARNING, "rose"),
                      T.kpi("最高負荷", "%d%%" % max((float(r["load_pct"]) for r in rows), default=0), I.SPEED, "orange"),
                      T.kpi("需求工時合計", T.qfmt(sum((r["required_hours"] for r in rows), Decimal(0))), I.SCHEDULE, "blue")],
                     spacing=14)
        self.body.controls = [tot, legend, T.card(ft.Row([ft.Column(lines, spacing=4)], scroll=ft.ScrollMode.AUTO), padding=14)]
        if refresh:
            self.update()

    def detail(self, c):
        rows = self.b.crp_detail(c["id"])
        g = T.Grid([("source_doc_no", "來源", "s", 110), ("item_code", "料號", "s", 100), ("item_name", "品名", "s", 150),
                    ("op_seq", "工序", "s", 40), ("qty", "數量", "q", 70), ("setup_hours", "整備", "q", 60),
                    ("run_hours", "加工", "q", 70)], height=280, empty="（RCCP 沒有來源明細）")
        g.set_rows(rows)
        self.ctx.dialog("%s　%s 負荷來源" % (c["wc_code"], rocdate.show(c["period_start"])), g,
                        [T.btn("關閉", on_click=lambda e: self.ctx.close())], icon=I.SPEED, tone="rose", width=700)
