"""一般主檔維護：清單＋右側編輯（由 MASTERS 規格產生）。"""
import flet as ft

from . import theme as T
from .widgets import Form

I = ft.Icons
ACTIVE = ("is_active", "啟用", "b", 70)

# key: title, table, func, icon, tone, sub, fields, list(清單欄), order, pk(主鍵欄), pk_edit(可輸入主鍵), extra(額外按鈕)
MASTERS = {
    "units": dict(title="計量單位", table="bas_unit", func="BAS", icon=I.STRAIGHTEN, tone="slate", order="id",
                  fields=[("unit_code", "代碼", "s", 90), ("unit_name", "名稱", "s", 120)]),
    "currencies": dict(title="幣別", table="bas_currency", func="BAS", icon=I.CURRENCY_EXCHANGE, tone="amber",
                       pk="currency_code", pk_edit=True, order="is_base DESC, currency_code",
                       sub="本位幣只能有一個；最新匯率 = 1 外幣折合多少本位幣",
                       fields=[("currency_code", "幣別代碼", "s", 90), ("currency_name", "名稱", "s", 110),
                               ("symbol", "符號", "s", 70), ("is_base", "本位幣", "b", 70),
                               ("amount_decimals", "金額小數位", "i", 90), ("price_decimals", "單價小數位", "i", 90),
                               ("exchange_rate", "最新記帳匯率", "p", 110), ACTIVE]),
    "rates": dict(title="匯率歷史", table="bas_exchange_rate", func="BAS", icon=I.SHOW_CHART, tone="amber",
                  order="rate_date DESC, currency_code", sub="單據依單據日期帶入當天以前最近的記帳匯率（A）",
                  fields=[("currency_code", "幣別", "ref:currencies", 120), ("rate_date", "日期", "d", 110),
                          ("rate_type", "類型", "sel:A=記帳匯率,B=銀行買入,S=銀行賣出,M=中價", 110),
                          ("rate", "匯率", "p", 110), ("source", "來源", "s", 160)]),
    "countries": dict(title="國家與產地", table="bas_country", func="BAS", icon=I.PUBLIC, tone="sky",
                      pk="country_code", pk_edit=True, order="country_code",
                      fields=[("country_code", "代碼（ISO 兩碼）", "s", 120), ("country_name", "中文名稱", "s", 110),
                              ("country_name_en", "英文名稱", "s", 140), ("origin_label", "產地簡稱", "s", 90)]),
    "manufacturers": dict(title="製造商（原廠）", table="bas_manufacturer", func="BAS", icon=I.FACTORY, tone="violet",
                          order="mfr_code", sub="原廠與供應商不同：供應商可能是代理商",
                          fields=[("mfr_code", "代碼", "s", 90), ("mfr_name", "名稱", "s", 180),
                                  ("country_code", "所在國", "ref:countries", 120), ("website", "網站", "s", 200), ACTIVE]),
    "departments": dict(title="部門", table="bas_dept", func="BAS", icon=I.APARTMENT, tone="sky", order="dept_code",
                        fields=[("dept_code", "代號", "s", 90), ("dept_name", "名稱", "s", 160),
                                ("parent_id", "上層部門", "ref:depts", 140), ACTIVE]),
    "employees": dict(title="員工", table="bas_employee", func="BAS", icon=I.BADGE, tone="violet", order="emp_code",
                      fields=[("emp_code", "員工編號", "s", 100), ("emp_name", "姓名", "s", 110),
                              ("dept_id", "部門", "ref:depts", 140), ("job_title", "職稱", "s", 100),
                              ("supervisor_id", "直屬主管", "ref:employees", 130), ("phone", "電話", "s", 120), ACTIVE]),
    "warehouses": dict(title="倉庫", table="bas_warehouse", func="BAS", icon=I.WAREHOUSE, tone="blue", order="wh_code",
                       sub="「MRP 可用」關閉的倉庫（待驗、報廢）不計入可用量",
                       fields=[("wh_code", "代號", "s", 80), ("wh_name", "名稱", "s", 150),
                               ("wh_type", "類型", "sel:R=原料,F=成品,W=在製,Q=待驗,S=報廢", 90),
                               ("is_nettable", "MRP 可用", "b", 80), ("keeper_id", "倉管人員", "ref:employees", 130),
                               ACTIVE]),
    "categories": dict(title="料件分類", table="itm_category", func="ITM", icon=I.LABEL, tone="violet",
                       order="cat_code", fields=[("cat_code", "代號", "s", 90), ("cat_name", "名稱", "s", 160),
                                                 ("parent_id", "上層分類", "ref:categories", 160)]),
    "customers": dict(title="客戶", table="sal_customer", func="SAL", icon=I.STOREFRONT, tone="green", order="cust_code",
                      fields=[("cust_code", "客戶編號", "s", 100), ("cust_name", "名稱", "s", 200),
                              ("short_name", "簡稱", "s", 100), ("tax_id", "統一編號", "s", 90),
                              ("contact", "聯絡人", "s", 90), ("phone", "電話", "s", 110), ("email", "Email", "s", 160),
                              ("address", "地址", "s", 220), ("currency_code", "交易幣別", "ref:currencies", 110),
                              ("payment_terms", "付款條件", "s", 110), ("credit_limit", "信用額度", "n", 110),
                              ("sales_id", "業務", "ref:employees", 120), ACTIVE],
                      list=["cust_code", "cust_name", "currency_code", "contact", "phone", "is_active"]),
    "suppliers": dict(title="供應商", table="pur_supplier", func="PUR", icon=I.LOCAL_SHIPPING, tone="orange",
                      order="sup_code",
                      fields=[("sup_code", "供應商編號", "s", 100), ("sup_name", "名稱", "s", 200),
                              ("short_name", "簡稱", "s", 100), ("tax_id", "統一編號", "s", 90),
                              ("contact", "聯絡人", "s", 90), ("phone", "電話", "s", 110), ("email", "Email", "s", 160),
                              ("address", "地址", "s", 220), ("currency_code", "交易幣別", "ref:currencies", 110),
                              ("payment_terms", "付款條件", "s", 110), ("lead_time_days", "一般交期（天）", "i", 100), ACTIVE],
                      list=["sup_code", "sup_name", "currency_code", "lead_time_days", "contact", "phone", "is_active"]),
    "sources": dict(title="料件供應來源", table="pur_item_source", func="PUR", icon=I.HUB, tone="orange",
                    order="item_id, priority", sub="料件 × 供應商：製造商料號、產地、外幣單價、交期；MRP 依優先順序選供應商",
                    fields=[("item_id", "料件", "ref:items", 200), ("supplier_id", "供應商", "ref:suppliers", 150),
                            ("mfr_part_id", "製造商料號", "ref:mfr_parts", 170), ("origin_country", "產地", "ref:countries", 90),
                            ("unit_price", "單價", "p", 90), ("currency_code", "幣別", "ref:currencies", 90),
                            ("lead_days", "交期（天）", "i", 80), ("moq", "最小訂購量", "q", 90),
                            ("priority", "優先順序", "i", 70), ("sup_item_code", "廠商料號", "s", 120),
                            ("valid_from", "報價生效", "d", 110), ("valid_to", "報價失效", "d", 110)],
                    list=["item_id", "supplier_id", "mfr_part_id", "origin_country", "unit_price", "currency_code",
                          "lead_days", "priority"]),
    "work_centers": dict(title="工作中心", table="rou_work_center", func="ROU", icon=I.PRECISION_MANUFACTURING,
                         tone="teal", order="wc_code", sub="每日可用工時 = 人機數 × 班次 × 每班工時 × 效率 × 利用率",
                         fields=[("wc_code", "代號", "s", 90), ("wc_name", "名稱", "s", 160),
                                 ("dept_id", "部門", "ref:depts", 130), ("wc_type", "類型", "sel:M=機器,L=人工,O=委外", 80),
                                 ("resource_count", "人機數", "i", 70), ("hours_per_shift", "每班工時", "q", 80),
                                 ("efficiency", "效率", "p", 70), ("utilization", "利用率", "p", 70),
                                 ("queue_days", "等候（天）", "q", 80), ("move_days", "搬運（天）", "q", 80),
                                 ("is_bottleneck", "瓶頸站", "b", 70), ACTIVE],
                         list=["wc_code", "wc_name", "wc_type", "resource_count", "hours_per_shift", "efficiency",
                               "is_bottleneck"]),
    "machines": dict(title="機器設備", table="rou_machine", func="ROU", icon=I.BUILD, tone="slate", order="machine_code",
                     fields=[("machine_code", "設備編號", "s", 100), ("machine_name", "名稱", "s", 160),
                             ("wc_id", "工作中心", "ref:wcs", 150), ("purchase_date", "購置日期", "d", 110),
                             ("cost", "取得成本", "n", 110), ("useful_years", "耐用年限", "i", 80),
                             ("salvage_value", "估計殘值", "n", 100), ("status", "狀態", "sel:A=正常,M=保養中,D=報廢", 80)]),
    "wc_rates": dict(title="工作中心費率", table="acc_wc_rate", func="ACC", icon=I.PRICE_CHANGE, tone="rose",
                     order="period DESC, wc_id", sub="每工時的直接人工與製造費用（元／時），完工成本與標準成本使用",
                     fields=[("wc_id", "工作中心", "ref:wcs", 160), ("period", "期別", "ref:periods", 100),
                             ("labor_rate", "人工費率", "p", 100), ("overhead_rate", "製費率", "p", 100)]),
    "bill_resource": dict(title="資源清單（RCCP）", table="crp_bill_resource", func="CRP", icon=I.SPEED, tone="blue",
                          order="item_id", sub="每單位 MPS 料件約耗用瓶頸站幾小時；沒設定時用途程工時估算",
                          fields=[("item_id", "MPS 料件", "ref:items_mfg", 200), ("wc_id", "工作中心", "ref:wcs", 160),
                                  ("hours_per_unit", "每單位工時", "p", 100), ("offset_days", "提前天數", "i", 80)]),
    "ecn": dict(title="工程變更 ECN", table="bom_ecn", func="BOM", icon=I.CHANGE_CIRCLE, tone="pink", order="id DESC",
                fields=[("ecn_no", "變更單號", "s", 110), ("ecn_date", "申請日", "d", 110),
                        ("bom_id", "變更的 BOM", "ref:boms", 180), ("new_bom_id", "新版 BOM", "ref:boms", 180),
                        ("from_rev_id", "變更前版本", "ref:revisions", 150), ("to_rev_id", "變更後版本", "ref:revisions", 150),
                        ("reason", "變更原因", "s", 200), ("change_desc", "變更內容", "t", 300),
                        ("effective_date", "生效日", "d", 110), ("requested_by", "申請人", "ref:employees", 120),
                        ("status", "狀態", "sel:D=草稿,A=核准,E=已生效,X=作廢", 80)],
                list=["ecn_no", "ecn_date", "bom_id", "reason", "effective_date", "status"]),
    "account_map": dict(title="會計科目對應", table="acc_account_map", func="ACC", icon=I.ACCOUNT_TREE, tone="blue",
                        order="id", sub="拋轉到「資料助秘之一般公司會計」時使用的科目",
                        fields=[("map_code", "對應代碼", "s", 120), ("map_name", "說明", "s", 160),
                                ("account_no", "科目代號", "s", 90), ("account_name", "科目名稱", "s", 140)]),
    "calendar": dict(title="工廠行事曆", table="bas_calendar", func="BAS", icon=I.CALENDAR_MONTH, tone="green",
                     pk="cal_date", order="cal_date", sub="國定假日請改為「不上班」；MRP 前置時間以工作天計算",
                     fields=[("cal_date", "日期", "d", 110), ("is_workday", "上班", "b", 70),
                             ("work_hours", "工時", "q", 70), ("shift_count", "班次", "i", 70), ("note", "備註", "s", 200)],
                     where="cal_date BETWEEN DATE_SUB(CURDATE(), INTERVAL 30 DAY) AND DATE_ADD(CURDATE(), INTERVAL 400 DAY)"),
}


class MasterList(ft.Row):
    def __init__(self, ctx, name):
        self.ctx, self.name = ctx, name
        self.m = MASTERS[name]
        self.pk = self.m.get("pk", "id")
        self.editable = ctx.books.can(self.m["func"], 2)
        self.search = T.field("搜尋", "", width=220, prefix_icon=I.SEARCH, on_change=lambda e: self.filter())
        show = self.m.get("list") or [f[0] for f in self.m["fields"]][:9]
        fmap = {f[0]: f for f in self.m["fields"]}
        cols = []
        for k in show:
            _, t, typ, w = fmap[k]
            gt = {"n": "n", "q": "q", "p": "q", "b": "b", "d": "d", "i": "s"}.get(typ, "s")
            cols.append((k + "_show" if typ.startswith(("ref:", "sel:")) else k, t, gt, min(w, 220)))
        self.grid = T.Grid(cols, on_pick=self.edit)
        self.form_box = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        tools = [self.search, ctx.export_button(self.grid, self.m["title"])]
        if name == "calendar" and self.editable:
            tools.insert(0, T.btn("產生明後年行事曆", I.EVENT_REPEAT, lambda e: self.gen_calendar(), kind="outline"))
        left = ft.Column([T.page_header(self.m["icon"], self.m["title"], self.m.get("sub", ""), self.m["tone"]),
                          ft.Row(tools, wrap=True), self.grid], expand=True, spacing=12)
        super().__init__([left, T.card(self.form_box, width=440, padding=18)], expand=True, spacing=14,
                         data="split", vertical_alignment=ft.CrossAxisAlignment.START)
        self.reload()
        self.edit(None, refresh=False)

    def reload(self):
        m = self.m
        self.rows = self.ctx.books.master_rows(self.name)
        look = self.ctx.look
        for k, t, typ, w in m["fields"]:
            if typ.startswith("ref:"):
                for r in self.rows:
                    r[k + "_show"] = look.label(typ[4:], r.get(k)) if r.get(k) is not None else ""
            elif typ.startswith("sel:"):
                o = dict(x.split("=", 1) for x in typ[4:].split(","))
                for r in self.rows:
                    r[k + "_show"] = o.get(str(r.get(k)), r.get(k))
        self.filter(refresh=False)

    def filter(self, refresh=True):
        q = (self.search.value or "").strip().lower()
        rows = [r for r in self.rows if not q or any(q in str(v).lower() for v in r.values())]
        self.grid.set_rows(rows)
        if refresh:
            self.update()

    def edit(self, r, refresh=True):
        self.current = r
        fields = []
        for f in self.m["fields"]:
            if r and f[0] == self.pk and self.pk != "id":
                fields.append((f[0], f[1], "ro" if f[2] != "d" else "d", f[3]))
            else:
                fields.append(f)
        data = dict(r or {})
        if r is None:
            data.setdefault("is_active", True)
            data.setdefault("is_nettable", True)
        self.form = Form(self.ctx.look, fields, data, disabled=not self.editable, per_row=1)
        if r and self.pk != "id":
            self.form.inputs[self.pk].disabled = True
        acts = []
        if self.editable:
            acts = [T.btn("儲存", I.SAVE, lambda e: self.save()), T.btn("新增", I.ADD, lambda e: self.edit(None), kind="outline")]
            if r:
                acts.append(T.btn("刪除", I.DELETE_OUTLINE, lambda e: self.delete(), kind="danger"))
        self.form_box.controls = [
            ft.Row([T.icon_tile(self.m["icon"], self.m["tone"], 40),
                    ft.Text(("修改" if r else "新增") + self.m["title"], size=17, weight=ft.FontWeight.W_700)], spacing=12),
            *([] if self.editable else [T.muted("您只有查詢權限")]), self.form, ft.Row(acts, wrap=True, spacing=8)]
        if refresh:
            self.update()

    def save(self):
        c = self.ctx
        try:
            data = self.form.values()
        except Exception as e:
            c.toast(str(e), True)
            return
        b = c.books
        rid = None if self.current is None else self.current[self.pk]
        if rid is not None and self.pk != "id":
            data.pop(self.pk, None)
        if c.guard(b.save_row, self.m["table"], data, rid, self.m["func"], self.pk, ok="已儲存"):
            c.look.clear()
            self.reload()
            self.edit(None)

    def delete(self):
        rid = self.current[self.pk]

        def go():
            if self.ctx.guard(self.ctx.books.delete_row, self.m["table"], rid, self.m["func"], self.pk, ok="已刪除"):
                self.ctx.look.clear()
                self.reload()
                self.edit(None)
        self.ctx.confirm("刪除" + self.m["title"], "確定要刪除這筆資料嗎？", go, yes="刪除")

    def gen_calendar(self):
        y = self.ctx.guard(self.ctx.books.extend_calendar_years)
        if y:
            self.ctx.toast("已產生到 %d 年底（已存在的日期保留原設定）" % y)
            self.reload()
            self.update()
