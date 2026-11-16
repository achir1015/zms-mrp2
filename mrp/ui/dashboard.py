"""首頁：關鍵數字、MRP II 流程捷徑、最近一次 MRP 例外訊息、產能負荷。"""
import flet as ft

from .. import APP_VERSION
from . import theme as T

I = ft.Icons
FLOW = [("forecast", I.INSIGHTS, "需求預測", "sky"), ("so", I.ASSIGNMENT, "客戶訂單", "green"),
        ("mps", I.EVENT_NOTE, "主生產排程", "blue"), ("mrp_run", I.SCHEMA, "MRP", "violet"),
        ("crp", I.SPEED, "產能 CRP", "rose"), ("po", I.SHOPPING_CART, "採購進貨", "orange"),
        ("wo", I.FACTORY, "工單生產", "teal"), ("stock", I.WAREHOUSE, "存貨 FIFO", "violet"), ("cost", I.CALCULATE, "成本會計", "rose")]


class Dashboard(ft.Column):
    def __init__(self, ctx):
        self.ctx = ctx
        b = ctx.books
        v = b.db.value
        go = ctx.app.go
        items = v("SELECT COUNT(*) FROM itm_item WHERE is_active=1")
        so = v("SELECT COUNT(*) FROM sal_order_h WHERE status IN ('A','P')")
        po = v("SELECT COALESCE(SUM((d.qty-d.received_qty)*d.unit_price*h.exchange_rate),0) FROM pur_order_d d JOIN pur_order_h h "
               "ON h.id=d.po_id WHERE d.status='O' AND h.status IN ('A','P')")
        wo = v("SELECT COUNT(*) FROM sfc_work_order WHERE status IN ('R','S')")
        val = v("SELECT COALESCE(SUM(remaining_qty*unit_cost),0) FROM inv_layer WHERE is_closed=0")
        run = b.db.row("SELECT * FROM mrp_run WHERE status='D' ORDER BY id DESC LIMIT 1")
        kp = T.kpis([T.kpi("料件", str(items), I.CATEGORY, "teal", on_click=lambda e: go("items")),
                     T.kpi("未結客戶訂單", str(so), I.ASSIGNMENT, "green", on_click=lambda e: go("so")),
                     T.kpi("在途採購（NT$）", T.amt(round(po)), I.LOCAL_SHIPPING, "orange", on_click=lambda e: go("po")),
                     T.kpi("生產中工單", str(wo), I.FACTORY, "violet", on_click=lambda e: go("wo")),
                     T.kpi("庫存金額（FIFO）", T.amt(round(val)), I.WAREHOUSE, "blue", on_click=lambda e: go("stock"))])
        flow = []
        for i, (sid, icon, text, tone) in enumerate(FLOW):
            if i:
                flow.append(ft.Icon(I.ARROW_FORWARD_ROUNDED, color="#94A3B8", size=18))
            flow.append(ft.Container(ft.Column([T.icon_tile(icon, tone, 46, radius=14),
                                                ft.Text(text, size=12, weight=ft.FontWeight.W_600)],
                                               horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                                     on_click=lambda e, s=sid: go(s), ink=True, border_radius=12, padding=6))
        flow_card = T.card(ft.Column([ft.Text("MRP II 作業流程（點選前往）", size=15, weight=ft.FontWeight.W_700),
                                      ft.Row(flow, alignment=ft.MainAxisAlignment.SPACE_AROUND, wrap=True,
                                             vertical_alignment=ft.CrossAxisAlignment.CENTER)], spacing=10), padding=16)
        if run:
            ex = b.exceptions(run["id"])[:12]
            g = T.Grid([("msg_type", "類型", "st:msg", 96), ("item_code", "料號", "s", 100), ("message", "訊息", "s", 330)],
                       height=320, empty="沒有例外訊息 👍")
            g.set_rows(ex)
            exc = T.card(ft.Column([ft.Row([ft.Text("最近一次 MRP 例外訊息（%s）" % run["run_no"], size=15,
                                                    weight=ft.FontWeight.W_700, expand=True),
                                            T.btn("查看全部", I.OPEN_IN_NEW, lambda e: go("mrp_run", run_id=run["id"], tab="exc"),
                                                  kind="ghost")]), g], spacing=8), expand=True, padding=16)
        else:
            empty = b.has_business_data()
            exc = T.card(ft.Column([ft.Text("開始使用", size=15, weight=ft.FontWeight.W_700),
                                    T.muted("還沒有執行過 MRP。" + ("請建立 MPS 後執行 MRP。" if empty else
                                                                "可以先到「系統管理 → 範例資料」載入電子業範例試跑。")),
                                    T.btn("載入電子業範例" if not empty else "主生產排程", I.ROCKET_LAUNCH,
                                          lambda e: go("demo" if not empty else "mps"))], spacing=10), expand=True, padding=16)
        load = b.db.rows("SELECT w.wc_code, w.wc_name, MAX(l.load_pct) mx, SUM(l.load_pct>100) over_days FROM crp_load l "
                         "JOIN rou_work_center w ON w.id=l.wc_id WHERE l.run_id=(SELECT MAX(id) FROM crp_run) GROUP BY w.id "
                         "ORDER BY mx DESC")
        bars = []
        for r in load:
            pct = float(r["mx"] or 0)
            color = T.SUCCESS if pct <= 80 else T.WARN if pct <= 100 else T.DANGER
            bars.append(ft.Column([ft.Row([ft.Text("%s %s" % (r["wc_code"], r["wc_name"]), size=13, expand=True),
                                           ft.Text("最高 %d%%" % round(pct), size=13, color=color, weight=ft.FontWeight.W_700)]),
                                   ft.ProgressBar(value=min(pct, 150) / 150, color=color, bgcolor="#EEF2F7", bar_height=8,
                                                  border_radius=4)], spacing=4))
        cap = T.card(ft.Column([ft.Row([ft.Text("工作中心負荷（最近一次產能運算）", size=15, weight=ft.FontWeight.W_700,
                                                expand=True), T.btn("CRP", I.OPEN_IN_NEW, lambda e: go("crp"), kind="ghost")]),
                                *(bars or [T.muted("尚未執行產能運算")])], spacing=10, scroll=ft.ScrollMode.AUTO),
                     width=420, padding=16)
        comp = b.company().get("company_name") or ""
        super().__init__([
            ft.Row([ft.Column([ft.Text("您好，%s" % b.user["user_name"], size=24, weight=ft.FontWeight.W_800),
                               T.muted("%s　資料助秘之物料需求II生產製造系統 v%s" % (comp, APP_VERSION))], spacing=2,
                              expand=True)]),
            kp, flow_card, ft.Row([exc, cap], expand=True, spacing=14, vertical_alignment=ft.CrossAxisAlignment.START)],
            spacing=16, expand=True, scroll=ft.ScrollMode.AUTO)
