"""成本：標準成本累算、料件成本、成本差異（採購價差、匯兌差異…）。"""
import datetime as dt

import flet as ft

from . import theme as T
from .widgets import tab_value, tabs

I = ft.Icons


class CostScreen(ft.Column):
    def __init__(self, ctx):
        self.ctx, self.b = ctx, ctx.books
        self.period = T.dropdown("期別", ctx.look("periods"), dt.date.today().strftime("%Y%m"), width=140, filterable=False,
                                 on_select=lambda e: self.render())
        self.tab = tabs([("std", "標準成本"), ("var", "成本差異"), ("val", "存貨價值")], "std", lambda e: self.render())
        acts = [T.btn("累算標準成本", I.CALCULATE, lambda e: self.roll())] if self.b.can("ACC", 2) else []
        self.body = ft.Column(spacing=10, expand=True)
        super().__init__([T.page_header(I.CALCULATE, "成本", "標準成本＝元件成本 ＋ 途程工時 × 費率；存貨依先進先出計價", "rose",
                                        acts), ft.Row([self.period, self.tab]), self.body], spacing=12, expand=True)
        self.render(refresh=False)

    def roll(self):
        n = self.ctx.guard(self.b.roll_up_cost, self.period.value)
        if n:
            self.ctx.toast("已累算 %d 個料件的標準成本" % n)
            self.render()

    def render(self, refresh=True):
        t, p = tab_value(self.tab), self.period.value
        if t == "std":
            rows = self.b.v("cost_std", p)
            g = T.Grid([("item_code", "料號", "s", 110), ("item_name", "品名", "s", 180), ("item_type", "類型", "st:itype", 70),
                        ("low_level_code", "階", "s", 30), ("material_cost", "材料", "q", 90), ("labor_cost", "人工", "q", 80),
                        ("overhead_cost", "製費", "q", 80), ("total_cost", "標準成本", "q", 100)],
                       empty="本期尚未累算，請按「累算標準成本」")
        elif t == "var":
            rows = self.b.v("cost_var", p)
            names = {"PPV": "採購價差", "MUV": "用料差異", "LEV": "人工效率", "OHV": "製費差異", "YLD": "良率差異",
                     "FXV": "匯兌差異"}
            for r in rows:
                r["type_name"] = names.get(r["variance_type"], r["variance_type"])
            g = T.Grid([("type_name", "差異類型", "s", 90), ("item_code", "料號", "s", 110), ("item_name", "品名", "s", 170),
                        ("ref_doc_no", "單號", "s", 120), ("amount", "金額（正＝不利）", "n", 110), ("note", "說明", "s", 260)],
                       totals=("amount",), empty="本期沒有成本差異")
        else:
            rows = self.b.v("cost_val")
            g = T.Grid([("item_code", "料號", "s", 110), ("item_name", "品名", "s", 180), ("item_type", "類型", "st:itype", 70),
                        ("q", "剩餘數量", "q", 90), ("avg", "先進先出平均成本", "q", 110), ("v", "存貨價值", "n", 110)],
                       totals=("v",))
        g.set_rows(rows)
        self.body.controls = [ft.Row([ft.Container(expand=True), self.ctx.export_button(g, "成本")]), g]
        if refresh:
            self.update()
