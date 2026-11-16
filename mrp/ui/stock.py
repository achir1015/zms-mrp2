"""存貨：庫存查詢（批號、版本、產地、先進先出成本層、異動明細）與庫存作業（期初、調整、調撥）。"""
from decimal import Decimal

import flet as ft

from . import theme as T
from .widgets import tab_value, tabs

I = ft.Icons


class StockQuery(ft.Row):
    def __init__(self, ctx, item_id=None):
        self.ctx, self.b = ctx, ctx.books
        self.kw = T.field("搜尋料件", "", width=200, prefix_icon=I.SEARCH, on_submit=lambda e: self.reload())
        self.wh = T.dropdown("倉庫", [("", "全部倉庫")] + ctx.look("warehouses"), "", width=170, filterable=False,
                             on_select=lambda e: self.reload())
        self.short = T.switch("只看低於安全存量", False, on_change=lambda e: self.reload())
        self.grid = T.Grid([("item_code", "料號", "s", 100), ("item_name", "品名", "s", 140), ("on_hand", "現有", "q", 70),
                            ("usable", "MRP 可用", "q", 70), ("allocated", "保留", "qz", 50), ("safety_stock", "安全", "qz", 50),
                            ("value", "庫存金額", "n", 80)], on_pick=lambda r: self.open(r["item_id"]),
                           row_style=lambda r: {"color": T.DANGER} if Decimal(r["usable"]) < Decimal(r["safety_stock"] or 0)
                           else None)
        self.tab = tabs([("lot", "批號／版本／產地"), ("layer", "先進先出成本層"), ("ledger", "異動明細")], "lot",
                        lambda e: self.render())
        self.title = ft.Text("", size=17, weight=ft.FontWeight.W_700)
        self.body = ft.Column(spacing=10, expand=True)
        left = ft.Column([T.page_header(I.WAREHOUSE, "庫存查詢", "紅字＝低於安全存量；MRP 可用不含待驗倉、報廢倉與淘汰版本", "violet"),
                          ft.Row([self.kw, self.wh, self.short], wrap=True), self.grid], expand=True, spacing=12)
        right = T.card(ft.Column([self.title, self.tab, self.body], spacing=12, expand=True), width=600, padding=18)
        super().__init__([left, right], expand=True, spacing=14, vertical_alignment=ft.CrossAxisAlignment.START)
        self.item_id = item_id
        self.reload(refresh=False)
        self.render(refresh=False)

    def reload(self, refresh=True):
        self.rows = self.b.stock((self.kw.value or "").strip(), int(self.wh.value) if self.wh.value else None,
                                 self.short.value)
        self.grid.set_rows(self.rows)
        if refresh:
            self.update()

    def open(self, item_id):
        self.item_id = item_id
        self.render()

    def render(self, refresh=True):
        if not self.item_id:
            self.title.value = "選擇料件查看明細"
            self.body.controls = [T.muted("點選左邊的料件")]
        else:
            it = self.b.v("item", self.item_id)
            self.title.value = "%s　%s" % (it["item_code"], it["item_name"])
            t = tab_value(self.tab)
            if t == "lot":
                g = T.Grid([("wh_name", "倉庫", "s", 80), ("lot_no", "批號", "s", 110), ("rev_code", "版本", "s", 40),
                            ("rev_status", "版本狀態", "st:rev", 70), ("origin_label", "產地", "s", 44), ("date_code", "D/C", "s", 44),
                            ("on_hand_qty", "現有", "q", 70), ("allocated_qty", "保留", "qz", 60)], height=420)
                g.set_rows(self.b.stock_detail(self.item_id))
            elif t == "layer":
                g = T.Grid([("received_at", "入庫時間", "d", 80), ("wh_name", "倉庫", "s", 70), ("lot_no", "批號", "s", 100),
                            ("origin_label", "產地", "s", 40), ("in_qty", "入庫量", "q", 60), ("remaining_qty", "剩餘", "q", 60),
                            ("unit_cost", "單位成本", "q", 70), ("value", "金額", "n", 70), ("doc_no", "來源單號", "s", 110)],
                           height=420, totals=("value",))
                g.set_rows(self.b.layers(self.item_id))
                g = ft.Column([T.muted("出庫時由最上面（最早入庫）的成本層開始扣；已保留給工單的量不會被其他出庫扣走", 12), g])
            else:
                g = T.Grid([("txn_time", "時間", "d", 80), ("doc_name", "單據", "s", 70), ("doc_no", "單號", "s", 110),
                            ("wh_name", "倉庫", "s", 60), ("lot_no", "批號", "s", 90), ("origin_label", "產地", "s", 40),
                            ("qty_in", "入", "qz", 60), ("qty_out", "出", "qz", 60), ("balance", "結存", "q", 60),
                            ("unit_cost", "單位成本", "q", 64)], height=420)
                g.set_rows(self.b.ledger(self.item_id))
            self.body.controls = [g]
        if refresh:
            self.update()


class InvOps(ft.Column):
    def __init__(self, ctx):
        self.ctx, self.b = ctx, ctx.books
        look = ctx.look
        ed = self.b.can("INV", 2)
        # 期初開帳
        self.o_item = T.dropdown("料件", look("items"), None, width=300)
        self.o_wh = T.dropdown("倉庫", look("warehouses"), None, width=180)
        self.o_qty = T.field("數量", "", width=110, text_align=ft.TextAlign.RIGHT)
        self.o_cost = T.field("單位成本（NT$）", "", width=140, text_align=ft.TextAlign.RIGHT)
        self.o_lot = T.field("批號", "", width=150)
        self.o_org = T.dropdown("產地", look("countries"), None, width=130)
        self.o_dc = T.field("D/C", "", width=90)
        self.o_rev = T.dropdown("版本", look("revisions"), None, width=170)
        self.o_date = T.date_field("入庫日期", width=160)
        # 調整
        self.a_item = T.dropdown("料件", look("items"), None, width=300)
        self.a_wh = T.dropdown("倉庫", look("warehouses"), None, width=180)
        self.a_qty = T.field("調整量（正增負減）", "", width=160, text_align=ft.TextAlign.RIGHT)
        self.a_reason = T.dropdown("原因", [("O", "其他"), ("C", "盤點差異"), ("S", "報廢")], "O", width=130, filterable=False)
        self.a_note = T.field("說明", "", width=260)
        # 調撥
        self.t_item = T.dropdown("料件", look("items"), None, width=300)
        self.t_from = T.dropdown("撥出倉", look("warehouses"), None, width=180)
        self.t_to = T.dropdown("撥入倉", look("warehouses"), None, width=180)
        self.t_qty = T.field("數量", "", width=110, text_align=ft.TextAlign.RIGHT)

        def sec(icon, tone, title, sub, rows, btn):
            return T.card(ft.Column([ft.Row([T.icon_tile(icon, tone, 40), ft.Column([
                ft.Text(title, size=16, weight=ft.FontWeight.W_700), T.muted(sub, 12)], spacing=0)], spacing=12),
                *rows, ft.Row([btn]) if ed else T.muted("您只有查詢權限")], spacing=12))
        super().__init__([
            T.page_header(I.TUNE, "庫存作業", "期初開帳、庫存調整、倉庫調撥（減少與調撥都依先進先出）", "violet"),
            sec(I.FLAG, "rose", "期初開帳", "系統上線時輸入現有庫存；每筆建立一個先進先出成本層",
                [ft.Row([self.o_item, self.o_wh, self.o_rev], wrap=True),
                 ft.Row([self.o_qty, self.o_cost, self.o_lot, self.o_org, self.o_dc, self.o_date], wrap=True)],
                T.btn("開帳入庫", I.FLAG, lambda e: self.opening())),
            sec(I.TUNE, "orange", "庫存調整", "增加：以最近成本入庫；減少：依先進先出扣減",
                [ft.Row([self.a_item, self.a_wh, self.a_qty, self.a_reason, self.a_note], wrap=True)],
                T.btn("調整過帳", I.TUNE, lambda e: self.adjust())),
            sec(I.SWAP_HORIZ, "sky", "倉庫調撥", "保留原入庫時間與批號，先進先出順序不變",
                [ft.Row([self.t_item, self.t_from, self.t_to, self.t_qty], wrap=True)],
                T.btn("調撥過帳", I.SWAP_HORIZ, lambda e: self.transfer()))], spacing=14, scroll=ft.ScrollMode.AUTO,
            expand=True)

    def _n(self, f):
        return Decimal((f.value or "0").replace(",", ""))

    def opening(self):
        if not (self.o_item.value and self.o_wh.value):
            self.ctx.toast("請選擇料件與倉庫", True)
            return
        no = self.ctx.guard(self.b.opening_stock, int(self.o_item.value), int(self.o_wh.value), self._n(self.o_qty),
                            self._n(self.o_cost), self.o_lot.value or None, self.o_org.value or None, self.o_dc.value or None,
                            int(self.o_rev.value) if self.o_rev.value else None, None, self.o_date.value)
        if no:
            self.ctx.toast("已開帳 %s" % no)
            self.o_qty.value = self.o_lot.value = ""
            self.update()

    def adjust(self):
        if not (self.a_item.value and self.a_wh.value):
            self.ctx.toast("請選擇料件與倉庫", True)
            return
        no = self.ctx.guard(self.b.adjust_stock, int(self.a_item.value), int(self.a_wh.value), self._n(self.a_qty),
                            self.a_reason.value, None, self.a_note.value or None)
        if no:
            self.ctx.toast("已調整 %s" % no)

    def transfer(self):
        if not (self.t_item.value and self.t_from.value and self.t_to.value):
            self.ctx.toast("請選擇料件、撥出倉與撥入倉", True)
            return
        no = self.ctx.guard(self.b.transfer_stock, int(self.t_item.value), int(self.t_from.value), int(self.t_to.value),
                            self._n(self.t_qty))
        if no:
            self.ctx.toast("已調撥 %s" % no)
