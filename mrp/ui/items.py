"""料件主檔：清單＋右側分頁（基本資料、計畫參數、版本、核可製造商與產地、供應來源）。"""
import flet as ft

from . import theme as T
from .widgets import Form, tab_value, tabs

I = ft.Icons

BASIC = [("item_code", "料號", "s", 0), ("item_name", "品名", "s", 0), ("spec", "規格", "s", 0),
         ("item_type", "類型", "sel:F=成品,S=半成品,R=原物料,P=包材,X=虛設件", 0),
         ("source_type", "來源", "sel:P=採購,M=自製,O=委外", 0), ("category_id", "分類", "ref:categories", 0),
         ("unit_id", "庫存單位", "ref:units", 0), ("purchase_unit_id", "採購單位", "ref:units", 0),
         ("barcode", "條碼", "s", 0), ("drawing_no", "圖號", "s", 0), ("weight_kg", "單位重量（kg）", "q", 0),
         ("is_lot_control", "批號管理", "b", 0), ("is_active", "啟用", "b", 0), ("note", "備註", "t", 0)]
PLAN = [("is_mps_item", "列入主生產排程（MPS 料件）", "b", 0), ("planner_id", "生管／採購負責人", "ref:employees", 0),
        ("default_wh_id", "預設倉庫", "ref:warehouses", 0), ("lead_time_days", "前置時間（工作天）", "i", 0),
        ("safety_lead_days", "安全前置時間", "i", 0), ("safety_stock", "安全存量", "q", 0),
        ("reorder_point", "再訂購點", "q", 0),
        ("lot_rule", "批量法則", "sel:LFL=逐批（需多少買多少）,FOQ=固定批量,EOQ=經濟訂購量,POQ=期間訂購（合併數期）", 0),
        ("fixed_lot_qty", "固定批量", "q", 0), ("min_order_qty", "最小訂購量", "q", 0),
        ("order_multiple", "訂購倍數", "q", 0), ("poq_periods", "POQ 合併期數", "i", 0),
        ("annual_demand", "年需求量（EOQ）", "q", 0), ("order_cost", "每次訂購成本（EOQ）", "n", 0),
        ("holding_rate", "年持有成本率（EOQ）", "p", 0), ("yield_rate", "良率", "p", 0),
        ("issue_rule", "發料原則", "sel:F=先進先出,E=先到期先出,M=人工指定", 0),
        ("cost_method", "成本計價", "sel:F=先進先出,W=月加權平均,S=標準成本", 0),
        ("demand_fence_days", "需求時柵（天）", "i", 0), ("planning_fence_days", "計畫時柵（天）", "i", 0)]
REV = [("rev_code", "版本碼", "s", 0), ("status", "狀態", "sel:A=量產,D=設計中,P=試產,H=暫停,O=淘汰", 0),
       ("effective_date", "生效日", "d", 0), ("obsolete_date", "失效日", "d", 0),
       ("is_interchangeable", "可與前一版互換（MRP 合併計算）", "b", 0), ("prev_rev_id", "前一版本", "ref:revisions", 0),
       ("firmware_ver", "韌體／BIOS 版本", "s", 0), ("drawing_no", "圖號", "s", 0),
       ("gerber_file", "線路圖／Gerber 路徑", "s", 0), ("rev_desc", "版本差異說明", "t", 0)]
AML = [("manufacturer_id", "製造商", "ref:manufacturers", 0), ("mfr_part_no", "製造商料號 MPN", "s", 0),
       ("origin_country", "原產國", "ref:countries", 0), ("rev_id", "適用版本（空白＝全部）", "ref:revisions", 0),
       ("approval_status", "核可狀態", "sel:A=核可,T=試用,R=不核可", 0), ("priority", "優先順序", "i", 0),
       ("rohs", "符合 RoHS", "b", 0), ("datasheet", "規格書路徑", "s", 0)]


class Items(ft.Row):
    def __init__(self, ctx, item_id=None):
        self.ctx = ctx
        self.b = ctx.books
        self.editable = self.b.can("ITM", 2)
        self.search = T.field("搜尋料號、品名、規格", "", width=230, prefix_icon=I.SEARCH, on_change=lambda e: self.filter())
        self.typ = T.dropdown("類型", [("", "全部"), ("F", "成品"), ("S", "半成品"), ("R", "原物料"), ("P", "包材")], "",
                              width=120, filterable=False, on_select=lambda e: self.filter())
        self.grid = T.Grid([("item_code", "料號", "s", 110), ("item_name", "品名", "s", 170), ("item_type", "類型", "st:itype", 80),
                            ("source", "來源", "s", 50), ("rev", "版本", "s", 50), ("lead_time_days", "前置", "s", 40),
                            ("lot_rule", "批量", "s", 50), ("llc", "階", "s", 30)], on_pick=lambda r: self.open(r["id"]))
        self.tab = tabs([("basic", "基本資料"), ("plan", "計畫參數"), ("rev", "版本"), ("aml", "產地 AML"),
                         ("src", "供應來源")], "basic", lambda e: self.render())
        self.body = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        self.title = ft.Text("新增料件", size=17, weight=ft.FontWeight.W_700)
        left = ft.Column([T.page_header(I.CATEGORY, "料件主檔", "成品、半成品、原物料；版本、產地與 MRP 計畫參數", "teal"),
                          ft.Row([self.search, self.typ, ctx.export_button(self.grid, "料件主檔")], wrap=True),
                          self.grid], expand=True, spacing=12)
        right = T.card(ft.Column([ft.Row([T.icon_tile(I.CATEGORY, "teal", 40), self.title], spacing=12), self.tab,
                                  self.body], spacing=12, expand=True), width=520, padding=18)
        super().__init__([left, right], expand=True, spacing=14, data="split", vertical_alignment=ft.CrossAxisAlignment.START)
        self.item_id = item_id
        self.reload()
        self.render(refresh=False)

    def reload(self):
        self.rows = self.b.v("items_list")
        self.filter(refresh=False)

    def filter(self, refresh=True):
        q = (self.search.value or "").strip().lower()
        t = self.typ.value or ""
        rows = [r for r in self.rows if (not t or r["item_type"] == t) and
                (not q or q in (r["item_code"] + r["item_name"] + (r["spec"] or "")).lower())]
        self.grid.set_rows(rows)
        if refresh:
            self.update()

    def open(self, item_id):
        self.item_id = item_id
        self.render()

    def render(self, refresh=True):
        t = tab_value(self.tab)
        it = self.b.v("item", self.item_id) if self.item_id else None
        self.title.value = "%s　%s" % (it["item_code"], it["item_name"]) if it else "新增料件"
        if not it and t != "basic":
            self.body.controls = [T.muted("請先在左邊選一個料件，或在「基本資料」新增料件")]
        else:
            getattr(self, "r_" + t)(it)
        if refresh:
            self.update()

    def _acts(self, save, extra=()):
        if not self.editable:
            return ft.Row([T.muted("您只有查詢權限")])
        return ft.Row([T.btn("儲存", I.SAVE, lambda e: save()), *extra], wrap=True, spacing=8)

    # ---------------------------------------------------------------- 基本資料
    def r_basic(self, it):
        data = dict(it or {"item_type": "R", "source_type": "P", "is_active": True, "unit_id": 1})
        self.f = Form(self.ctx.look, BASIC, data, disabled=not self.editable)
        extra = [T.btn("新增料件", I.ADD, lambda e: self.open(None), kind="outline")]
        if it:
            extra.append(T.btn("刪除", I.DELETE_OUTLINE, lambda e: self.delete(), kind="danger"))
            extra.append(T.chip("庫存 %s" % T.qfmt(self.b.v("item_stock", it["id"])), "violet", I.WAREHOUSE))
        self.body.controls = [self.f, self._acts(self.save_basic, extra)]

    def save_basic(self):
        c = self.ctx
        try:
            d = self.f.values()
        except Exception as e:
            c.toast(str(e), True)
            return
        if not d.get("item_code") or not d.get("item_name"):
            c.toast("請輸入料號與品名", True)
            return
        new = self.item_id is None
        rid = c.guard(self.b.create_item, d) if new else c.guard(self.b.save_row, "itm_item", d, self.item_id)
        if rid:
            c.toast("已儲存" + ("（已建立計畫參數與版本 A）" if new else ""))
            c.look.clear()
            self.item_id = rid
            self.reload()
            self.render()

    def delete(self):
        def go():
            if self.ctx.guard(self.b.delete_item, self.item_id, ok="已刪除"):
                self.ctx.look.clear()
                self.item_id = None
                self.reload()
                self.render()
        self.ctx.confirm("刪除料件", "確定要刪除這個料件嗎？（已被 BOM、單據或庫存使用的料件不能刪除，可改為停用）", go, yes="刪除")

    def r_plan(self, it):
        p = self.b.item_plan(it["id"])
        self.f = Form(self.ctx.look, PLAN, p, disabled=not self.editable)
        eoq = T.btn("計算經濟訂購量", I.CALCULATE, lambda e: self.calc_eoq(), kind="outline")
        self.body.controls = [ft.Container(ft.Text("經濟訂購量 EOQ = √(2 × 年需求 × 每次訂購成本 ÷ (單價 × 持有成本率))",
                                                   size=12, color=T.MUTED)),
                              self.f, ft.Row([T.chip("目前 EOQ：%s" % T.qfmt(p["eoq_qty"]), "sky")]),
                              self._acts(self.save_plan, [eoq])]

    def save_plan(self):
        c = self.ctx
        try:
            d = self.f.values()
        except Exception as e:
            c.toast(str(e), True)
            return
        d = {k: (v if v is not None else 0) if k not in ("planner_id", "default_wh_id") else v for k, v in d.items()}
        if c.guard(self.b.save_row, "itm_plan", d, self.item_id, "ITM", "item_id", ok="計畫參數已儲存"):
            self.reload()
            self.render()

    def calc_eoq(self):
        eoq = self.ctx.guard(self.b.calc_eoq, self.item_id)
        if eoq:
            self.ctx.toast("經濟訂購量 = %s" % T.qfmt(eoq))
            self.render()

    def r_rev(self, it):
        rows = self.b.v("item_revisions", it["id"])
        g = T.Grid([("cur", "目前", "s", 34), ("rev_code", "版本", "s", 50), ("status", "狀態", "st:rev", 70),
                    ("effective_date", "生效", "d", 80), ("is_interchangeable", "可互換", "b", 50),
                    ("firmware_ver", "韌體", "s", 70), ("rev_desc", "說明", "s", 120)],
                   on_pick=lambda r: self.rev_dialog(r), height=220)
        g.set_rows(rows)
        acts = [T.btn("新增版本", I.ADD, lambda e: self.rev_dialog(None))] if self.editable else []
        self.body.controls = [T.muted("同一料號的不同版本（PCB Rev A／B、韌體 1.0／1.2）。★＝目前量產版；淘汰版的庫存 MRP 不計。", 12),
                              g, ft.Row(acts)]

    def rev_dialog(self, r):
        c = self.ctx
        f = Form(c.look, REV, r or {"status": "A", "is_interchangeable": True}, disabled=not self.editable, per_row=2)
        cur = T.switch("設為目前量產版本", bool(r and r["id"] == self.b.v("item_current_rev", self.item_id)))

        def save(e):
            d = f.values()
            d["item_id"] = self.item_id
            rid = c.guard(self.b.save_row, "itm_revision", d, r and r["id"], "ITM")
            if rid:
                if cur.value:
                    self.b.set_current_rev(self.item_id, rid)
                c.look.clear()
                c.close()
                c.toast("版本已儲存")
                self.reload()
                self.render()
        c.dialog("修改版本" if r else "新增版本", ft.Column([f, cur], tight=True, spacing=12),
                 [T.btn("取消", kind="ghost", on_click=lambda e: c.close())] +
                 ([T.btn("儲存", I.SAVE, save)] if self.editable else []), icon=I.LAYERS, tone="violet", width=620)

    # ---------------------------------------------------------------- 核可製造商與產地
    def r_aml(self, it):
        rows = self.b.v("item_aml", it["id"])
        g = T.Grid([("priority", "順序", "s", 34), ("mfr_name", "製造商", "s", 110), ("mfr_part_no", "製造商料號", "s", 120),
                    ("origin_label", "產地", "s", 50), ("rev_code", "版本", "s", 40), ("approval_status", "核可", "s", 40)],
                   on_pick=lambda r: self.aml_dialog(r), height=220)
        g.set_rows(rows)
        acts = [T.btn("新增製造商料號", I.ADD, lambda e: self.aml_dialog(None))] if self.editable else []
        self.body.controls = [T.muted("同一料號可由多家原廠供應（例如日製、台製），各有製造商料號與原產地。", 12), g, ft.Row(acts)]

    def aml_dialog(self, r):
        c = self.ctx
        f = Form(c.look, AML, r or {"approval_status": "A", "priority": 1, "rohs": True}, disabled=not self.editable)

        def save(e):
            d = f.values()
            d["item_id"] = self.item_id
            if c.guard(self.b.save_row, "itm_mfr_part", d, r and r["id"], "ITM"):
                c.look.clear()
                c.close()
                c.toast("已儲存")
                self.render()

        def delete(e):
            if c.guard(self.b.delete_row, "itm_mfr_part", r["id"], "ITM", ok="已刪除"):
                c.look.clear()
                c.close()
                self.render()
        acts = [T.btn("取消", kind="ghost", on_click=lambda e: c.close())]
        if self.editable:
            acts += ([T.btn("刪除", I.DELETE_OUTLINE, delete, kind="danger")] if r else []) + [T.btn("儲存", I.SAVE, save)]
        c.dialog("核可製造商料號", f, acts, icon=I.PUBLIC, tone="sky", width=600)

    # ---------------------------------------------------------------- 供應來源
    def r_src(self, it):
        rows = self.b.v("item_sources", it["id"])
        g = T.Grid([("priority", "順序", "s", 34), ("sup_name", "供應商", "s", 110), ("origin_label", "產地", "s", 44),
                    ("unit_price", "單價", "q", 70), ("currency_code", "幣別", "s", 40), ("lead_days", "交期", "s", 40),
                    ("moq", "MOQ", "q", 50)], height=220)
        g.set_rows(rows)
        self.body.controls = [T.muted("採購單價、幣別、交期與產地；到「採購作業 → 料件供應來源」維護。", 12), g,
                              T.btn("前往料件供應來源", I.OPEN_IN_NEW, lambda e: self.ctx.app.go("sources"), kind="outline")]
