"""現場控制：工單清單＋工單明細（用料、工序、領料、報工、完工）。"""
from decimal import Decimal

import flet as ft

from .. import rocdate
from . import theme as T

I = ft.Icons
WO_FILTER = [("open", "未結工單"), ("", "全部"), ("P", "計畫"), ("R", "已發放"), ("S", "生產中"),
             ("F", "完工"), ("C", "結案"), ("X", "作廢")]


class WorkOrders(ft.Row):
    def __init__(self, ctx, wo_id=None):
        self.ctx, self.b = ctx, ctx.books
        self.editable = self.b.can("SFC", 2)
        self.flt = T.dropdown("狀態", WO_FILTER, "open", width=230, filterable=False, on_select=lambda e: self.reload())
        self.grid = T.Grid([("wo_no", "工單號", "s", 110), ("item_code", "料件", "s", 100), ("plan_qty", "數量", "q", 50),
                            ("completed_qty", "完工", "qz", 50), ("plan_finish", "預計完工", "d", 76),
                            ("status", "狀態", "st:wo", 66)], on_pick=lambda r: self.open(r["id"]))
        self.panel = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)
        acts = [T.btn("新增工單", I.ADD, lambda e: self.new_dialog())] if self.editable else []
        left = ft.Column([T.page_header(I.FACTORY, "工單", "發放 → 領料 → 報工 → 完工入庫", "teal", acts), self.flt,
                          self.grid], width=540, spacing=12)
        super().__init__([left, T.card(self.panel, expand=True, padding=18)], expand=True, spacing=14,
                         vertical_alignment=ft.CrossAxisAlignment.START)
        self.reload(refresh=False)
        self.open(wo_id, refresh=False)

    def reload(self, refresh=True):
        self.grid.set_rows(self.b.wo_list(self.flt.value))
        if refresh:
            self.update()

    def open(self, wo_id, refresh=True):
        self.wo_id = wo_id
        if not wo_id:
            self.panel.controls = [T.empty_state(I.FACTORY, "請在左邊選擇工單", "MRP 的計畫訂單轉單後，工單會出現在這裡")]
            if refresh:
                self.update()
            return
        b = self.b
        w = b.v("wo_row", wo_id)
        self.w = w
        mats = b.v("wo_mats", wo_id)
        for m in mats:
            m["left"] = Decimal(m["required_qty"]) - Decimal(m["issued_qty"])
            m["how"] = {"P": "領料", "B": "倒扣", "N": "不發料"}[m["issue_type"]]
        ops = b.v("wo_ops", wo_id)
        mg = T.Grid([("item_code", "料號", "s", 100), ("item_name", "品名", "s", 150), ("required_qty", "應領", "q", 70),
                     ("issued_qty", "已領", "qz", 70), ("left", "未領", "qz", 70), ("how", "方式", "s", 50),
                     ("origin_label", "指定產地", "s", 60)], height=220, empty="尚未發放（發放時展開 BOM）")
        mg.set_rows(mats)
        og = T.Grid([("op_seq", "工序", "s", 40), ("op_name", "名稱", "s", 110), ("wc_code", "工作中心", "s", 80),
                     ("plan_run_hours", "標準工時", "q", 70), ("actual_hours", "實際工時", "qz", 70), ("good_qty", "良品", "qz", 60),
                     ("scrap_qty", "不良", "qz", 50), ("status", "狀態", "st:op", 64)], height=180, empty="尚未發放",
                    on_pick=(lambda r: self.report_dialog(r)) if self.editable and w["status"] in ("R", "S") else None)
        og.set_rows(ops)
        cost = Decimal(b.v("wo_mat_cost", wo_id) or 0)
        self.panel.controls = [
            ft.Row([T.icon_tile(I.FACTORY, "teal", 44), ft.Column([
                ft.Text("%s　%s %s" % (w["wo_no"], w["item_code"], w["item_name"]), size=18, weight=ft.FontWeight.W_800),
                T.muted("版本 %s　預計 %s ～ %s　入庫倉 %s%s" % (w["rev_code"] or "-", rocdate.show(w["plan_start"]),
                                                       rocdate.show(w["plan_finish"]), w["wh_name"] or "-",
                                                       "　訂單 %s" % w["so_no"] if w["so_no"] else ""))],
                spacing=0, expand=True), T.status_chip(w["status"], "wo")]),
            T.kpis([T.kpi("工單數量", T.qfmt(w["plan_qty"]), I.FLAG, "blue"),
                    T.kpi("已完工", T.qfmt(w["completed_qty"]), I.TASK_ALT, "green"),
                    T.kpi("已投入材料", T.amt(cost), I.PAID, "orange")]),
            ft.Row(self.actions(w), wrap=True, spacing=8),
            ft.Text("工單用料", size=15, weight=ft.FontWeight.W_700), mg,
            ft.Row([ft.Text("工單工序", size=15, weight=ft.FontWeight.W_700),
                    T.muted("（生產中可點選工序報工）", 12)]), og]
        if refresh:
            self.update()

    def actions(self, w):
        if not self.editable:
            return [T.muted("您只有查詢權限")]
        st, a = w["status"], []
        if st == "P":
            a += [T.btn("發放工單", I.ROCKET_LAUNCH, lambda e: self.do(self.b.release_wo, "已發放")),
                  T.btn("作廢", I.BLOCK, lambda e: self.do(self.b.set_wo_status, "已作廢", "X"), kind="danger")]
        if st in ("R", "S"):
            a += [T.btn("領料", I.OUTBOX, lambda e: self.issue_dialog()),
                  T.btn("完工入庫", I.MOVE_TO_INBOX, lambda e: self.complete_dialog(), kind="accent")]
        if st == "R":
            a.append(T.btn("取消發放", I.UNDO, lambda e: self.do(self.b.set_wo_status, "已取消發放", "P"), kind="ghost"))
        if st in ("S", "F", "R"):
            a.append(T.btn("結案", I.TASK_ALT, lambda e: self.ctx.confirm(
                "工單結案", "結案後不能再領料與完工，確定嗎？", lambda: self.do(self.b.set_wo_status, "已結案", "C")),
                kind="outline"))
        return a

    def do(self, fn, ok, *a):
        r = self.ctx.guard(fn, self.wo_id, *a)
        if r is not None:
            msg = ok + ("：" + "；".join(r) if isinstance(r, list) and r else "")
            self.ctx.toast(msg)
            self.reload(refresh=False)
            self.open(self.wo_id)

    def new_dialog(self):
        c = self.ctx
        item = T.dropdown("生產料件", c.look("items_mfg"), None, width=360)
        q = T.field("數量", "", width=120, text_align=ft.TextAlign.RIGHT)
        s = T.date_field("預計開工", width=160)
        f = T.date_field("預計完工", width=160)

        def go(e):
            try:
                qty = Decimal(q.value.replace(",", ""))
            except Exception:
                c.toast("請輸入數量", True)
                return
            if not item.value:
                c.toast("請選擇料件", True)
                return
            no = c.guard(self.b.create_work_order, int(item.value), qty, s.value, f.value)
            if no:
                c.close()
                c.toast("已開立工單 %s（計畫狀態），確認後按「發放工單」" % no)
                self.reload(refresh=False)
                self.open(self.b.v("wo_by_no", no))
        c.dialog("新增工單", ft.Column([item, ft.Row([q, s, f])], tight=True, spacing=12),
                 [T.btn("取消", kind="ghost", on_click=lambda e: c.close()), T.btn("開立", I.ADD, go)],
                 icon=I.FACTORY, tone="teal", width=560)

    def issue_dialog(self):
        c = self.ctx
        mats = self.b.v("wo_issue_mats", self.wo_id)
        if not mats:
            c.toast("沒有需要領的料（倒扣料會在完工時自動扣）", True)
            return
        rows, ui = [], []
        for m in mats:
            left = Decimal(m["required_qty"]) - Decimal(m["issued_qty"])
            f = T.field("", T.qfmt(min(left, Decimal(m["stock"]))), width=100, text_align=ft.TextAlign.RIGHT)
            rows.append((m["id"], f))
            ui.append(ft.Row([ft.Text("%s　%s" % (m["item_code"], m["item_name"]), width=260, size=13),
                              T.muted("未領 %s／倉庫 %s%s" % (T.qfmt(left), T.qfmt(m["stock"]),
                                                          "／限%s" % m["required_country"] if m["required_country"] else ""), 12),
                              ft.Container(expand=True), f]))
        d = T.date_field("領料日期", width=160)

        def go(e):
            lines = [dict(wo_material_id=i, qty=(f.value or "0").replace(",", "")) for i, f in rows]
            r = c.guard(self.b.issue_wo, self.wo_id, lines, d.value)
            if r:
                no, used = r
                c.close()
                origins = sorted({u[2] for u in used if u[2]})
                c.toast("已領料 %s（先進先出%s）" % (no, "，產地 " + "、".join(origins) if origins else ""))
                self.reload(refresh=False)
                self.open(self.wo_id)
        c.dialog("工單領料（依先進先出）", ft.Column([d, *ui], tight=True, spacing=10, scroll=ft.ScrollMode.AUTO),
                 [T.btn("取消", kind="ghost", on_click=lambda e: c.close()), T.btn("過帳", I.OUTBOX, go)],
                 icon=I.OUTBOX, tone="orange", width=700)

    def report_dialog(self, op):
        c = self.ctx
        emp = T.dropdown("作業員", c.look("employees"), None, width=220)
        mac = T.dropdown("機器（可空白）", c.look("machines"), None, width=220)
        good = T.field("良品", "", width=100, text_align=ft.TextAlign.RIGHT)
        scrap = T.field("不良", "0", width=90, text_align=ft.TextAlign.RIGHT)
        sh = T.field("整備工時", "0", width=100, text_align=ft.TextAlign.RIGHT)
        rh = T.field("加工工時", "", width=100, text_align=ft.TextAlign.RIGHT)
        why = T.field("不良原因", "", width=230)

        def go(e):
            try:
                vals = [Decimal((x.value or "0").replace(",", "")) for x in (good, scrap, sh, rh)]
            except Exception:
                c.toast("數字格式不正確", True)
                return
            no = c.guard(self.b.report_op, op["id"], vals[0], vals[1], vals[2], vals[3], emp.value or None, mac.value or None,
                         "M" if mac.value else "L", why.value or None)
            if no:
                c.close()
                c.toast("已報工 %s" % no)
                self.open(self.wo_id)
        c.dialog("報工：工序 %s %s（%s）" % (op["op_seq"], op["op_name"], op["wc_code"]),
                 ft.Column([ft.Row([emp, mac]), ft.Row([good, scrap, sh, rh]), why], tight=True, spacing=12),
                 [T.btn("取消", kind="ghost", on_click=lambda e: c.close()), T.btn("報工", I.TIMER, go)],
                 icon=I.TIMER, tone="violet", width=560)

    def complete_dialog(self):
        c = self.ctx
        w = self.w
        left = Decimal(w["plan_qty"]) - Decimal(w["completed_qty"])
        q = T.field("入庫數量", T.qfmt(left), width=130, text_align=ft.TextAlign.RIGHT)
        wh = T.dropdown("入庫倉", c.look("warehouses"), w["warehouse_id"], width=200)
        lot = T.field("生產批號（空白＝工單號）", "", width=220)
        d = T.date_field("入庫日期", width=160)

        def go(e):
            r = c.guard(self.b.complete_wo, self.wo_id, (q.value or "0").replace(",", ""), d.value,
                        int(wh.value) if wh.value else None, lot.value or None)
            if r:
                no, unit = r
                c.close()
                c.toast("已完工入庫 %s，單位成本 %s" % (no, T.amt(unit)))
                self.reload(refresh=False)
                self.open(self.wo_id)
        c.dialog("完工入庫", ft.Column([T.muted("倒扣料依完工比例自動扣料；單位成本＝已投入材料＋報工工時 × 工作中心費率", 12),
                                     ft.Row([q, wh]), ft.Row([lot, d])], tight=True, spacing=12),
                 [T.btn("取消", kind="ghost", on_click=lambda e: c.close()), T.btn("入庫", I.MOVE_TO_INBOX, go)],
                 icon=I.MOVE_TO_INBOX, tone="green", width=560)
