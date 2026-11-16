"""使用說明：左邊目錄、右邊內容；每一節都能語音朗讀（預先產生的神經語音 MP3，沒有時改用線上／內建語音）。"""
import flet as ft

from ..help_text import GUIDE
from ..voice import speaker
from . import theme as T

I = ft.Icons
GROUPS = [("認識系統", ["intro", "quickstart", "flow", "home"]),
          ("基本資料與料件", ["company", "currencies", "countries", "manufacturers", "warehouses", "calendar", "units",
                         "departments", "employees", "customers", "suppliers", "items", "categories"]),
          ("產品結構與產能", ["bom", "ecn", "routings", "work_centers", "machines", "wc_rates"]),
          ("需求與規劃", ["forecast", "so", "ship", "mps", "mrp_run", "planned", "crp"]),
          ("採購、生產、存貨", ["pr", "po", "receive", "wo", "stock", "inv_ops"]),
          ("成本與系統", ["cost", "account_map", "users", "backup", "update", "audit", "demo", "help"])]
TITLES = {k: (t, x) for k, t, x in GUIDE}
ORDER = [k for _, ks in GROUPS for k in ks if k in TITLES]
FLOW = [(I.INSIGHTS, "預測／訂單", "sky"), (I.EVENT_NOTE, "MPS", "blue"), (I.ACCOUNT_TREE, "BOM 展開", "violet"),
        (I.REMOVE_CIRCLE_OUTLINE, "淨需求", "orange"), (I.SCHEDULE, "前置時間位移", "amber"), (I.SPEED, "CRP", "rose"),
        (I.SHOPPING_CART, "採購", "orange"), (I.FACTORY, "工單", "teal"), (I.WAREHOUSE, "FIFO 存貨", "violet"),
        (I.CALCULATE, "成本", "rose")]


class Help(ft.Row):
    def __init__(self, ctx, key="intro"):
        self.ctx = ctx
        self.toc = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        self.body = ft.Column(spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)
        flow = []
        for i, (icon, text, tone) in enumerate(FLOW):
            if i:
                flow.append(ft.Icon(I.ARROW_FORWARD_ROUNDED, color="#94A3B8", size=18))
            flow.append(ft.Column([T.icon_tile(icon, tone, 42, radius=12), ft.Text(text, size=11, weight=ft.FontWeight.W_600)],
                                  horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4))
        banner = T.card(ft.Column([ft.Text("MRP II 作業流程", size=15, weight=ft.FontWeight.W_700),
                                   ft.Row(flow, alignment=ft.MainAxisAlignment.SPACE_AROUND, wrap=True,
                                          vertical_alignment=ft.CrossAxisAlignment.CENTER)], spacing=8), padding=14)
        super().__init__([T.card(self.toc, width=290, padding=12),
                          ft.Column([banner, T.card(self.body, expand=True, padding=26)], expand=True, spacing=14)],
                         expand=True, spacing=14, vertical_alignment=ft.CrossAxisAlignment.START)
        self.show(key if key in TITLES else "intro", refresh=False)

    def show(self, key, refresh=True):
        self.sec = key
        toc = []
        for g, keys in GROUPS:
            toc.append(ft.Container(ft.Text(g, size=12, weight=ft.FontWeight.W_700, color=T.MUTED),
                                    padding=ft.Padding.only(left=8, top=10, bottom=4)))
            for k in keys:
                if k not in TITLES:
                    continue
                sel = k == key
                toc.append(ft.Container(ft.Text(TITLES[k][0], size=13, color=T.PRIMARY if sel else T.TEXT,
                                                weight=ft.FontWeight.W_700 if sel else ft.FontWeight.W_500),
                                        padding=ft.Padding.symmetric(horizontal=10, vertical=6), border_radius=10,
                                        bgcolor="#E3EDFF" if sel else None, ink=True, on_click=lambda e, k=k: self.show(k)))
        self.toc.controls = toc
        title, text = TITLES[key]
        paras = [p + "。" for p in text.split("。") if p.strip()]
        can_go = self.ctx.app.find(key) and key not in ("help", "intro", "quickstart", "flow")
        self.body.controls = [
            ft.Row([T.icon_tile(I.MENU_BOOK, "blue", 54, radius=16),
                    ft.Column([T.muted("操作說明", 12), ft.Text(title, size=23, weight=ft.FontWeight.W_800)], spacing=0,
                              expand=True),
                    T.btn("朗讀", I.VOLUME_UP, lambda e: speaker.say_help(key, "%s。%s" % (title, text)), kind="accent"),
                    T.btn("停止", I.STOP_CIRCLE, lambda e: speaker.stop(), kind="outline")]),
            *[ft.Text(p, size=15, color="#334155", selectable=True) for p in paras],
            ft.Divider(),
            ft.Row([T.btn("上一節", I.CHEVRON_LEFT, lambda e: self.step(-1), kind="ghost"), ft.Container(expand=True),
                    *([T.btn("前往此功能", I.OPEN_IN_NEW, lambda e: self.ctx.app.go(key), kind="outline")] if can_go else []),
                    T.btn("下一節", I.CHEVRON_RIGHT, lambda e: self.step(1), kind="ghost")])]
        if refresh:
            speaker.stop()
            self.update()

    def step(self, d):
        self.show(ORDER[(ORDER.index(self.sec) + d) % len(ORDER)])
