"""一般單據：客戶訂單、採購單、請購單、需求預測（左清單＋右編輯），以及進貨驗收、出貨。"""
from decimal import Decimal

import flet as ft

from .. import rocdate
from ..ops import DOCS
from . import theme as T
from .widgets import Form, LinesEditor, today_text

I = ft.Icons
UI = {
    "SO": dict(icon=I.ASSIGNMENT, tone="green", sub="客戶下單；核准後列入主生產排程並可出貨",
               head=[("order_date", "訂單日期", "d", 0), ("customer_id", "客戶", "ref:customers", 0),
                     ("cust_po_no", "客戶採購單號", "s", 0), ("currency_code", "幣別", "ref:currencies", 0),
                     ("exchange_rate", "匯率（空白自動）", "p", 0),
                     ("tax_type", "稅別", "sel:1=應稅外加,2=應稅內含,3=零稅率,4=免稅", 0),
                     ("tax_rate", "稅率", "p", 0), ("sales_id", "業務", "ref:employees", 0), ("note", "備註", "s", 0)],
               lines=[("item_id", "料件", "ref:items", 250), ("rev_id", "版本", "ref:revisions", 140),
                      ("qty", "數量", "q", 90), ("unit_price", "單價", "p", 100), ("due_date", "交期", "d", 130)]),
    "PO": dict(icon=I.SHOPPING_CART, tone="orange", sub="向供應商下單；單價、製造商料號與產地由供應來源帶入；未進貨量＝預定接收",
               head=[("po_date", "採購日期", "d", 0), ("supplier_id", "供應商", "ref:suppliers", 0),
                     ("po_type", "類別", "sel:N=一般採購,O=委外加工", 0), ("currency_code", "幣別", "ref:currencies", 0),
                     ("exchange_rate", "匯率（空白自動）", "p", 0),
                     ("tax_type", "稅別", "sel:1=應稅外加,2=應稅內含,3=零稅率,4=免稅", 0),
                     ("tax_rate", "稅率", "p", 0), ("buyer_id", "採購人員", "ref:employees", 0), ("note", "備註", "s", 0)],
               lines=[("item_id", "料件", "ref:items", 230), ("rev_id", "版本", "ref:revisions", 130),
                      ("mfr_part_id", "製造商料號", "ref:mfr_parts", 170), ("origin_country", "產地", "ref:countries", 100),
                      ("qty", "數量", "q", 80), ("unit_price", "單價", "p", 90), ("due_date", "到貨日", "d", 130)]),
    "PR": dict(icon=I.REQUEST_PAGE, tone="amber", sub="需要購買的料件與需求日；核准後轉採購單",
               head=[("pr_date", "請購日期", "d", 0), ("dept_id", "請購部門", "ref:depts", 0),
                     ("requester_id", "請購人", "ref:employees", 0), ("note", "備註", "s", 0)],
               lines=[("item_id", "料件", "ref:items", 260), ("rev_id", "版本", "ref:revisions", 140), ("qty", "數量", "q", 90),
                      ("need_date", "需求日", "d", 130), ("suggest_supplier_id", "建議供應商", "ref:suppliers", 170)]),
    "FC": dict(icon=I.INSIGHTS, tone="sky", sub="料件 × 期間的預測量；核准後產生 MPS 時取預測與訂單較大者",
               head=[("fc_date", "預測日期", "d", 0), ("method", "方法", "sel:M=人工,A=移動平均,E=指數平滑,T=趨勢", 0),
                     ("bucket_type", "時距", "sel:M=月,W=週,D=日", 0), ("note", "備註", "s", 0)],
               lines=[("item_id", "料件", "ref:items", 280), ("customer_id", "客戶（可空白）", "ref:customers", 180),
                      ("period_start", "期間起日", "d", 130), ("forecast_qty", "預測量", "q", 100)]),
}
STATUS_FILTER = [("", "全部"), ("D", "草稿"), ("A", "已核准"), ("P", "部分"), ("C", "結案"), ("X", "作廢")]


class DocScreen(ft.Row):
    def __init__(self, ctx, kind, doc_id=None):
        self.ctx, self.kind, self.b = ctx, kind, ctx.books
        self.d, self.u = DOCS[kind], UI[kind]
        self.editable = self.b.can(self.d["func"], 2)
        self.search = T.field("搜尋單號／對象", "", width=180, prefix_icon=I.SEARCH, on_submit=lambda e: self.reload())
        self.status = T.dropdown("狀態", STATUS_FILTER, "", width=110, filterable=False, on_select=lambda e: self.reload())
        cols = [("doc_no", "單號", "s", 100), ("doc_date", "日期", "d", 74), ("party", "對象", "s", 90),
                ("status", "狀態", "st:doc", 64)]
        if self.d["fx"]:
            cols.insert(3, ("base_untaxed_amount", "NT$", "n", 70))
        self.grid = T.Grid(cols, on_pick=lambda r: self.open(r["id"]))
        self.panel = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)
        left = ft.Column([T.page_header(self.u["icon"], self.d["title"], self.u["sub"], self.u["tone"]),
                          ft.Row([self.search, self.status]), self.grid,
                          T.btn("新增" + self.d["title"], I.ADD, lambda e: self.open(None)) if self.editable else
                          ft.Container()], width=430, spacing=12)
        super().__init__([left, T.card(self.panel, expand=True, padding=18)], expand=True, spacing=14,
                         vertical_alignment=ft.CrossAxisAlignment.START)
        self.doc_id = doc_id
        self.reload(refresh=False)
        self.open(doc_id, refresh=False)

    def reload(self, refresh=True):
        self.grid.set_rows(self.b.doc_list(self.kind, (self.search.value or "").strip(), self.status.value or None))
        if refresh:
            self.update()

    def open(self, doc_id, refresh=True):
        self.doc_id = doc_id
        if doc_id:
            h, lines = self.b.doc(self.kind, doc_id)
        else:
            h, lines = {self.d["date"]: rocdate.today(), "status": "D", "tax_type": "1", "po_type": "N", "method": "M",
                        "bucket_type": "M", "currency_code": self.b.base_currency(),
                        "tax_rate": Decimal(self.b.param("default_tax_rate", "0.05"))}, []
            h["exchange_rate"] = None
        self.h = h
        locked = h["status"] != "D" or not self.editable
        self.head = Form(self.ctx.look, self.u["head"], h, disabled=locked, per_row=3,
                         on_change=self.head_changed)
        self.lines = LinesEditor(self.ctx.look, self.u["lines"], lines, disabled=locked, on_change=self.line_changed,
                                 height=300)
        self.totals = ft.Row(spacing=18)
        self.calc()
        no = h.get(self.d["no"])
        acts = self.actions(h)
        self.panel.controls = [
            ft.Row([T.icon_tile(self.u["icon"], self.u["tone"], 44),
                    ft.Column([ft.Text(no or "新" + self.d["title"], size=19, weight=ft.FontWeight.W_800),
                               T.muted("修改後按「儲存」；核准後就不能修改" if not locked else "已核准或結案，只能查看")],
                              spacing=0, expand=True), T.status_chip(h["status"])]),
            self.head, ft.Text("明細", size=15, weight=ft.FontWeight.W_700), self.lines, self.totals,
            ft.Row(acts, wrap=True, spacing=8)]
        extra = self.extra_info(h)
        if extra:
            self.panel.controls.append(extra)
        if refresh:
            self.update()

    def actions(self, h):
        if not self.editable:
            return [T.muted("您只有查詢權限")]
        st = h["status"]
        a = []
        if st == "D":
            a.append(T.btn("儲存", I.SAVE, lambda e: self.save()))
            if self.doc_id:
                a += [T.btn("核准", I.VERIFIED, lambda e: self.status_to("A"), kind="accent"),
                      T.btn("作廢", I.BLOCK, lambda e: self.status_to("X"), kind="danger")]
        if st == "A":
            a.append(T.btn("取消核准", I.UNDO, lambda e: self.status_to("D"), kind="outline"))
        if st in ("A", "P") and self.kind == "PO":
            a.insert(0, T.btn("進貨驗收", I.INVENTORY, lambda e: receive_dialog(self.ctx, self.doc_id, self.after_post)))
        if st in ("A", "P") and self.kind == "SO":
            a.insert(0, T.btn("出貨", I.LOCAL_SHIPPING, lambda e: ship_dialog(self.ctx, self.doc_id, self.after_post)))
            a.append(T.btn("依此訂單開工單", I.FACTORY, lambda e: self.so_to_wo(), kind="outline"))
        if st == "A" and self.kind == "PR":
            a.insert(0, T.btn("轉採購單", I.SHOPPING_CART, lambda e: self.pr_to_po()))
        if st in ("A", "P") and self.kind in ("PO", "SO"):
            a.append(T.btn("結案", I.TASK_ALT, lambda e: self.status_to("C"), kind="outline"))
        return a

    def extra_info(self, h):
        if self.kind == "PO" and self.doc_id:
            rows = self.b.v("po_receipts", self.doc_id)
            if rows:
                g = T.Grid([("rcv_no", "進貨單", "s", 110), ("rcv_date", "日期", "d", 80), ("item_code", "料件", "s", 100),
                            ("accept_qty", "合格", "q", 60), ("reject_qty", "驗退", "qz", 50), ("lot_no", "批號", "s", 100),
                            ("origin_label", "產地", "s", 44), ("date_code", "D/C", "s", 50), ("base_amount", "NT$", "n", 80)],
                           height=170)
                g.set_rows(rows)
                return ft.Column([ft.Text("進貨紀錄", size=14, weight=ft.FontWeight.W_700), g], spacing=6)
        if self.kind == "SO" and self.doc_id:
            rows = self.b.v("so_ships", self.doc_id)
            if rows:
                g = T.Grid([("ship_no", "出貨單", "s", 110), ("ship_date", "日期", "d", 80), ("item_code", "料件", "s", 110),
                            ("qty", "數量", "q", 60), ("lot_no", "批號", "s", 140), ("base_amount", "NT$", "n", 90)], height=150)
                g.set_rows(rows)
                return ft.Column([ft.Text("出貨紀錄", size=14, weight=ft.FontWeight.W_700), g], spacing=6)
        return None

    # ---------------------------------------------------------------- 自動帶值
    def head_changed(self, key):
        if key == "supplier_id" and self.kind == "PO":
            sid = self.head.inputs["supplier_id"].value
            if sid:
                cur = self.b.v("supplier_currency", sid)
                self.head.inputs["currency_code"].value = cur
                self.head.inputs["exchange_rate"].value = ""
                self.head.update()
        if key == "customer_id" and self.kind == "SO":
            cid = self.head.inputs["customer_id"].value
            if cid:
                self.head.inputs["currency_code"].value = self.b.v("customer_currency", cid)
                self.head.update()
        self.calc(refresh=True)

    def line_changed(self, cs, key):
        if key == "item_id" and cs["item_id"].value:
            item = int(cs["item_id"].value)
            if "rev_id" in cs and not cs["rev_id"].value:
                cs["rev_id"].value = str(self.b.v("item_current_rev", item) or "") or None
            if self.kind == "PO":
                sup = self.head.inputs["supplier_id"].value
                src = self.b.source_for(item, int(sup)) if sup else None
                if src:
                    cs["unit_price"].value = str(Decimal(src["unit_price"]).normalize())
                    cs["mfr_part_id"].value = str(src["mfr_part_id"]) if src["mfr_part_id"] else None
                    cs["origin_country"].value = src["origin_country"]
                elif sup:
                    self.ctx.toast("此供應商沒有這個料件的供應來源，請自行輸入單價", True)
            cs["_row"].update()
        self.calc(refresh=True)

    def calc(self, refresh=False):
        if not self.d["fx"]:
            n = len([l for l in self.lines.lines if l["item_id"].value])
            self.totals.controls = [T.muted("共 %d 項" % n, 13)]
        else:
            tot = Decimal(0)
            for l in self.lines.lines:
                try:
                    tot += Decimal(str(l["qty"].value or 0).replace(",", "")) * Decimal(str(l["unit_price"].value or 0).replace(",", ""))
                except Exception:
                    pass
            cur = self.head.inputs["currency_code"].value or "TWD"
            try:
                rate = Decimal(str(self.head.inputs["exchange_rate"].value).replace(",", "")) \
                    if self.head.inputs["exchange_rate"].value else self.b.rate_on(cur, self.head.inputs[self.d["date"]].value)
            except Exception:
                rate = Decimal(1)
            self.totals.controls = [ft.Text("原幣未稅 %s %s" % (cur, T.amt(tot)), size=14),
                                    ft.Text("匯率 %s" % rate.normalize(), size=14, color=T.MUTED),
                                    ft.Text("約合新台幣 %s" % T.amt((tot * rate).quantize(Decimal("0.01"))), size=16,
                                            weight=ft.FontWeight.W_800, color=T.PRIMARY)]
        if refresh:
            try:
                self.totals.update()
            except Exception:
                pass

    # ---------------------------------------------------------------- 動作
    def save(self):
        c = self.ctx
        try:
            h = self.head.values()
            lines = self.lines.values()
        except Exception as e:
            c.toast(str(e), True)
            return
        r = c.guard(self.b.save_doc, self.kind, self.doc_id, h, lines)
        if r:
            c.toast("已儲存 %s" % r[1])
            self.reload(refresh=False)
            self.open(r[0])

    def status_to(self, st):
        names = {"A": "核准", "D": "取消核准", "X": "作廢", "C": "結案"}

        def go():
            if self.ctx.guard(self.b.set_doc_status, self.kind, self.doc_id, st, ok="已%s" % names[st]):
                self.reload(refresh=False)
                self.open(self.doc_id)
        if st in ("X", "C"):
            self.ctx.confirm(names[st], "確定要%s這張單據嗎？" % names[st], go, yes=names[st])
        else:
            go()

    def after_post(self, msg):
        self.ctx.toast(msg)
        self.reload(refresh=False)
        self.open(self.doc_id)

    def pr_to_po(self):
        r = self.ctx.guard(self.b.pr_to_po, self.doc_id)
        if r:
            self.ctx.toast("已產生採購單草稿：%s" % "、".join(r))
            self.reload(refresh=False)
            self.open(self.doc_id)

    def so_to_wo(self):
        r = self.ctx.guard(self.b.so_to_wo, self.doc_id)
        if r:
            self.ctx.toast("已開立工單（計畫狀態）：%s" % "、".join(r))


def receive_dialog(ctx, po_id, done):
    b = ctx.books
    po = b.v("po_for_receive", po_id)
    lines = b.v("po_open_lines", po_id)
    if not lines:
        ctx.toast("此採購單已全部進貨", True)
        return
    dt_ = T.date_field("進貨日期", width=160)
    wh = T.dropdown("入庫倉", ctx.look("warehouses"), b.v("wh_by_code", "RM"), width=200)
    inv = T.field("發票號碼", "", width=150)
    rows = []
    ui = [ft.Row([ft.Text(t, width=w, size=12, weight=ft.FontWeight.W_700) for t, w in
                  [("料件", 170), ("未交", 60), ("合格量", 80), ("驗退", 60), ("批號", 120), ("D/C", 70), ("產地", 120)]])]
    for l in lines:
        open_q = Decimal(l["qty"]) - Decimal(l["received_qty"])
        r = dict(id=l["id"], acc=T.field("", T.qfmt(open_q), width=80, text_align=ft.TextAlign.RIGHT),
                 rej=T.field("", "", width=60, text_align=ft.TextAlign.RIGHT), lot=T.field("", "", width=120),
                 dc=T.field("", "", width=70),
                 org=T.dropdown("", ctx.look("countries"), l["origin_country"], width=120))
        rows.append(r)
        ui.append(ft.Row([ft.Text(l["item_code"], width=170, size=13, tooltip=l["item_name"]),
                          ft.Text(T.qfmt(open_q), width=60, size=13), r["acc"], r["rej"], r["lot"], r["dc"], r["org"]]))
    rate = b.rate_on(po["currency_code"])
    info = T.muted("%s　%s　幣別 %s，採購匯率 %s；入庫成本依進貨日匯率（今天 %s）換算新台幣" % (
        po["po_no"], po["sup_name"], po["currency_code"], Decimal(po["exchange_rate"]).normalize(), rate.normalize()), 12)

    def go(e):
        data = [dict(po_line_id=r["id"], accept_qty=r["acc"].value or 0, reject_qty=r["rej"].value or 0,
                     lot_no=r["lot"].value or None, date_code=r["dc"].value or None, origin_country=r["org"].value or None)
                for r in rows]
        no = ctx.guard(b.receive_po, po_id, data, dt_.value, int(wh.value), inv.value or None)
        if no:
            ctx.close()
            done("已進貨入庫：%s" % no)
    ctx.dialog("進貨驗收", ft.Column([info, ft.Row([dt_, wh, inv]), *ui], tight=True, spacing=10, scroll=ft.ScrollMode.AUTO),
               [T.btn("取消", kind="ghost", on_click=lambda e: ctx.close()), T.btn("過帳入庫", I.INVENTORY, go)],
               icon=I.INVENTORY, tone="orange", width=820)


def ship_dialog(ctx, so_id, done):
    b = ctx.books
    lines = b.v("so_open_lines", so_id)
    if not lines:
        ctx.toast("此訂單已全部出貨", True)
        return
    dt_ = T.date_field("出貨日期", width=160)
    wh = T.dropdown("出貨倉", ctx.look("warehouses"), b.v("wh_by_code", "FG"), width=200)
    inv = T.field("發票號碼", "", width=150)
    rows, ui = [], []
    for l in lines:
        open_q = Decimal(l["qty"]) - Decimal(l["shipped_qty"])
        f = T.field("", T.qfmt(min(open_q, Decimal(l["fg"]))), width=90, text_align=ft.TextAlign.RIGHT)
        rows.append((l["id"], f))
        ui.append(ft.Row([ft.Text("%s　%s" % (l["item_code"], l["item_name"]), width=260, size=13),
                          T.muted("未出 %s／成品可用 %s" % (T.qfmt(open_q), T.qfmt(l["fg"])), 12), f]))

    def go(e):
        no = ctx.guard(b.ship_so, so_id, [dict(so_line_id=i, qty=f.value or 0) for i, f in rows], dt_.value,
                       int(wh.value), inv.value or None)
        if no:
            ctx.close()
            done("已出貨：%s（依先進先出扣庫存）" % no)
    ctx.dialog("出貨", ft.Column([ft.Row([dt_, wh, inv]), *ui], tight=True, spacing=10),
               [T.btn("取消", kind="ghost", on_click=lambda e: ctx.close()), T.btn("出貨過帳", I.LOCAL_SHIPPING, go)],
               icon=I.LOCAL_SHIPPING, tone="green", width=680)


_ = today_text
