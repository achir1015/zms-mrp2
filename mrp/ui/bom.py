"""物料清單 BOM 與途程：左邊選母件，右邊編輯單頭與明細；BOM 另有多階展開與反查（用在哪裡）。"""
from decimal import Decimal

import flet as ft

from . import theme as T
from .widgets import Form, LinesEditor, tab_value, tabs

I = ft.Icons
BOM_LINES = [("child_item_id", "元件", "ref:items", 230), ("qty_per", "用量", "q", 70), ("scrap_rate", "損耗率", "p", 64),
             ("child_rev_id", "指定版本", "ref:revisions", 140), ("required_country", "指定產地", "ref:countries", 110),
             ("op_seq", "工序", "i", 54), ("issue_type", "發料", "sel:P=領料,B=倒扣,N=不發料", 86),
             ("is_phantom", "虛設", "b", 50), ("effective_date", "生效日", "d", 120), ("obsolete_date", "失效日", "d", 120)]
BOM_HEAD = [("bom_ver", "版本", "s", 0), ("base_qty", "基準量（每幾個母件）", "q", 0), ("parent_rev_id", "母件版本", "ref:revisions", 0),
            ("is_default", "預設 BOM（MRP 使用）", "b", 0), ("note", "備註", "s", 0)]
ROU_LINES = [("op_seq", "工序", "i", 60), ("op_name", "工序名稱", "s", 150), ("wc_id", "工作中心", "ref:wcs", 190),
             ("setup_hours", "整備工時／批", "q", 90), ("run_hours", "加工工時／件", "p", 90), ("is_outsource", "委外", "b", 50),
             ("supplier_id", "委外廠商", "ref:suppliers", 160), ("is_report_point", "報工點", "b", 60)]
ROU_HEAD = [("routing_ver", "版本", "s", 0), ("rev_id", "適用版本（空白＝全部）", "ref:revisions", 0),
            ("is_default", "預設途程", "b", 0), ("note", "備註", "s", 0)]


class _Editor(ft.Row):
    kind = "bom"

    def __init__(self, ctx, item_id=None):
        self.ctx, self.b = ctx, ctx.books
        self.func = "BOM" if self.kind == "bom" else "ROU"
        self.editable = self.b.can(self.func, 2)
        self.search = T.field("搜尋母件", "", width=200, prefix_icon=I.SEARCH, on_change=lambda e: self.filter())
        self.grid = T.Grid([("item_code", "料號", "s", 100), ("item_name", "品名", "s", 130), ("ver", "版本", "s", 40),
                            ("st", "狀態", "st:doc", 64)], on_pick=lambda r: self.open(r["id"]))
        self.panel = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)
        title, sub, icon, tone = self.meta()
        left = ft.Column([T.page_header(icon, title, sub, tone), self.search, self.grid], width=440, spacing=12)
        super().__init__([left, T.card(self.panel, expand=True, padding=18)], expand=True, spacing=14,
                         vertical_alignment=ft.CrossAxisAlignment.START)
        self.item_id = item_id
        self.reload()
        self.render(refresh=False)

    def filter(self, refresh=True):
        q = (self.search.value or "").lower()
        self.grid.set_rows([r for r in self.rows if not q or q in (r["item_code"] + r["item_name"]).lower()])
        if refresh:
            self.update()

    def open(self, item_id):
        self.item_id = item_id
        self.render()


class BomScreen(_Editor):
    kind = "bom"

    def meta(self):
        return "物料清單 BOM", "產品結構：元件、用量、損耗、指定版本與產地", I.ACCOUNT_TREE, "violet"

    def reload(self):
        self.rows = self.b.db.rows(
            "SELECT i.id, i.item_code, i.item_name, h.bom_ver ver, h.status st FROM itm_item i LEFT JOIN bom_header h ON "
            "h.parent_item_id=i.id AND h.is_default=1 WHERE i.source_type<>'P' AND i.is_active=1 ORDER BY i.item_code")
        self.filter(refresh=False)

    def render(self, refresh=True):
        if not self.item_id:
            self.panel.controls = [T.empty_state(I.ACCOUNT_TREE, "請在左邊選擇母件（自製或委外料件）")]
            if refresh:
                self.update()
            return
        it = self.b.db.row("SELECT * FROM itm_item WHERE id=%s", (self.item_id,))
        self.h = self.b.db.row("SELECT * FROM bom_header WHERE parent_item_id=%s ORDER BY is_default DESC, id DESC LIMIT 1",
                               (self.item_id,))
        h = self.h or {"bom_ver": "01", "base_qty": 1, "is_default": True, "parent_rev_id": it["current_rev_id"]}
        lines = self.b.db.rows("SELECT * FROM bom_detail WHERE bom_id=%s ORDER BY line_no", (h["id"],)) if self.h else []
        locked = bool(self.h and self.h["status"] != "D") or not self.editable
        self.head = Form(self.ctx.look, BOM_HEAD, h, disabled=locked, per_row=3)
        self.lines = LinesEditor(self.ctx.look, BOM_LINES, lines, disabled=locked, height=330)
        acts = []
        if self.editable:
            if not self.h or self.h["status"] == "D":
                acts += [T.btn("儲存", I.SAVE, lambda e: self.save())]
                if self.h:
                    acts.append(T.btn("核准", I.VERIFIED, lambda e: self.set_status("A"), kind="accent"))
            elif self.h["status"] == "A":
                acts.append(T.btn("取消核准（修改）", I.EDIT, lambda e: self.set_status("D"), kind="outline"))
            if self.h:
                acts.append(T.btn("複製成新版本", I.COPY_ALL, lambda e: self.copy_version(), kind="ghost"))
        self.view = tabs([("tree", "多階展開"), ("used", "用在哪裡")], "tree", lambda e: self.render_view())
        self.qty = T.field("展開數量", "1", width=110, text_align=ft.TextAlign.RIGHT, on_submit=lambda e: self.render_view())
        self.view_box = ft.Column(spacing=8)
        self.panel.controls = [
            ft.Row([T.icon_tile(I.ACCOUNT_TREE, "violet", 44), ft.Column([
                ft.Text("%s　%s" % (it["item_code"], it["item_name"]), size=18, weight=ft.FontWeight.W_800),
                T.muted("BOM 核准後才會被 MRP 與工單使用" if not self.h or self.h["status"] == "D" else "已核准：要修改請先取消核准")],
                spacing=0, expand=True), T.status_chip(self.h["status"]) if self.h else T.chip("尚未建立", "amber")]),
            self.head, ft.Text("元件（單階）", size=15, weight=ft.FontWeight.W_700), self.lines,
            ft.Row(acts, spacing=8, wrap=True), ft.Divider(),
            ft.Row([self.view, ft.Container(expand=True), self.qty,
                    T.btn("展開", I.PLAY_ARROW, lambda e: self.render_view(), kind="outline")]), self.view_box]
        self.render_view(refresh=False)
        if refresh:
            self.update()

    def render_view(self, refresh=True):
        if tab_value(self.view) == "tree":
            try:
                q = Decimal((self.qty.value or "1").replace(",", ""))
            except Exception:
                q = Decimal(1)
            rows = []
            self._tree(self.item_id, q, 1, rows, set())
            g = T.Grid([("lvl", "階", "s", 60), ("item_code", "料號", "s", 120), ("item_name", "品名", "s", 170),
                        ("qty_per", "單位用量", "q", 70), ("total", "總需求", "q", 90), ("origin", "指定產地", "s", 60),
                        ("source", "來源", "s", 50)], height=320)
            g.set_rows(rows)
        else:
            rows = self.b.db.rows("SELECT i.item_code, i.item_name, h.bom_ver, d.qty_per, h.status FROM bom_detail d JOIN "
                                  "bom_header h ON h.id=d.bom_id JOIN itm_item i ON i.id=h.parent_item_id WHERE "
                                  "d.child_item_id=%s ORDER BY i.item_code", (self.item_id,))
            g = T.Grid([("item_code", "母件", "s", 120), ("item_name", "品名", "s", 200), ("bom_ver", "版本", "s", 50),
                        ("qty_per", "用量", "q", 70), ("status", "狀態", "st:doc", 70)], height=240,
                       empty="此料件沒有被其他 BOM 使用")
            g.set_rows(rows)
        self.view_box.controls = [g]
        if refresh:
            self.update()

    def _tree(self, item_id, q, lvl, out, path):
        if item_id in path or lvl > 20:
            return
        for d in self.b.db.rows(
                "SELECT d.*, h.base_qty, i.item_code, i.item_name, i.source_type FROM bom_header h JOIN bom_detail d ON "
                "d.bom_id=h.id JOIN itm_item i ON i.id=d.child_item_id WHERE h.parent_item_id=%s AND h.is_default=1 "
                "ORDER BY d.line_no", (item_id,)):
            tot = q / Decimal(d["base_qty"] or 1) * Decimal(d["qty_per"]) / (1 - Decimal(d["scrap_rate"] or 0))
            out.append(dict(lvl="．" * (lvl - 1) + str(lvl), item_code=d["item_code"], item_name=d["item_name"],
                            qty_per=d["qty_per"], total=tot.quantize(Decimal("0.0001")), origin=d["required_country"] or "",
                            source={"M": "自製", "O": "委外"}.get(d["source_type"], "採購")))
            if d["source_type"] != "P":
                self._tree(d["child_item_id"], tot, lvl + 1, out, path | {item_id})

    def save(self):
        c = self.ctx
        try:
            h = self.head.values()
            lines = [l for l in self.lines.values() if l.get("child_item_id")]
        except Exception as e:
            c.toast(str(e), True)
            return
        if not lines:
            c.toast("請至少輸入一個元件", True)
            return
        for l in lines:
            if int(l["child_item_id"]) == self.item_id:
                c.toast("元件不能是母件自己", True)
                return
            if not l.get("qty_per") or l["qty_per"] <= 0:
                c.toast("用量要大於 0", True)
                return

        def go():
            db = self.b.db
            with db.transaction():
                hv = dict(h, parent_item_id=self.item_id, base_qty=h.get("base_qty") or 1, bom_ver=h.get("bom_ver") or "01")
                bid = self.b.save_row("bom_header", hv, self.h and self.h["id"], "BOM")
                if hv.get("is_default"):
                    db.exec("UPDATE bom_header SET is_default=0 WHERE parent_item_id=%s AND id<>%s", (self.item_id, bid))
                db.exec("DELETE FROM bom_detail WHERE bom_id=%s", (bid,))
                for i, l in enumerate(lines, 1):
                    l = {k: v for k, v in l.items() if k in [x[0] for x in BOM_LINES]}
                    l.update(bom_id=bid, line_no=i, scrap_rate=l.get("scrap_rate") or 0,
                             effective_date=l.get("effective_date") or "2000-01-01", issue_type=l.get("issue_type") or "P",
                             is_phantom=int(bool(l.get("is_phantom"))))
                    db.exec("INSERT INTO bom_detail (%s) VALUES (%s)" % (", ".join(l), ", ".join(["%s"] * len(l))),
                            list(l.values()))
                self.b.compute_low_level_codes()
        if c.guard(go, ok="BOM 已儲存（草稿）；確認無誤請按「核准」"):
            c.look.clear()
            self.reload()
            self.render()

    def set_status(self, st):
        def go():
            if st == "A":
                self.b.compute_low_level_codes()       # 檢查循環
            self.b.db.exec("UPDATE bom_header SET status=%s, approved_by=%s, approved_at=IF(%s='A',NOW(),NULL) WHERE id=%s",
                           (st, self.b.user_id if st == "A" else None, st, self.h["id"]))
            self.b.log("STATUS", "bom_header", self.h["id"], st, "BOM")
        if self.ctx.guard(go, ok="已核准" if st == "A" else "已取消核准，可以修改"):
            self.reload()
            self.render()

    def copy_version(self):
        def go():
            db = self.b.db
            vers = [r["bom_ver"] for r in db.rows("SELECT bom_ver FROM bom_header WHERE parent_item_id=%s", (self.item_id,))]
            n = 1
            while "%02d" % n in vers:
                n += 1
            with db.transaction():
                nid = db.exec("INSERT INTO bom_header (parent_item_id, parent_rev_id, bom_ver, base_qty, is_default, status, "
                              "note, created_by) SELECT parent_item_id, parent_rev_id, %s, base_qty, 0, 'D', note, %s FROM "
                              "bom_header WHERE id=%s", ("%02d" % n, self.b.user_id, self.h["id"]))
                db.exec("INSERT INTO bom_detail (bom_id, line_no, child_item_id, child_rev_id, required_country, qty_per, "
                        "scrap_rate, op_seq, issue_type, is_phantom, effective_date, obsolete_date, note) SELECT %s, line_no, "
                        "child_item_id, child_rev_id, required_country, qty_per, scrap_rate, op_seq, issue_type, is_phantom, "
                        "effective_date, obsolete_date, note FROM bom_detail WHERE bom_id=%s", (nid, self.h["id"]))
            return "%02d" % n
        v = self.ctx.guard(go)
        if v:
            self.ctx.toast("已複製成版本 %s（草稿，非預設）；可建立工程變更單記錄改版" % v)


class RoutingScreen(_Editor):
    kind = "rou"

    def meta(self):
        return "途程", "工序、工作中心、整備與加工工時（產能計算與工單工序的依據）", I.ROUTE, "teal"

    def reload(self):
        self.rows = self.b.db.rows(
            "SELECT i.id, i.item_code, i.item_name, h.routing_ver ver, h.status st FROM itm_item i LEFT JOIN rou_routing_h h "
            "ON h.item_id=i.id AND h.is_default=1 WHERE i.source_type<>'P' AND i.is_active=1 ORDER BY i.item_code")
        self.filter(refresh=False)

    def render(self, refresh=True):
        if not self.item_id:
            self.panel.controls = [T.empty_state(I.ROUTE, "請在左邊選擇料件")]
            if refresh:
                self.update()
            return
        it = self.b.db.row("SELECT * FROM itm_item WHERE id=%s", (self.item_id,))
        self.h = self.b.db.row("SELECT * FROM rou_routing_h WHERE item_id=%s ORDER BY is_default DESC, id DESC LIMIT 1",
                               (self.item_id,))
        h = self.h or {"routing_ver": "01", "is_default": True}
        lines = self.b.db.rows("SELECT * FROM rou_routing_d WHERE routing_id=%s ORDER BY op_seq", (h["id"],)) if self.h else []
        dis = not self.editable
        self.head = Form(self.ctx.look, ROU_HEAD, h, disabled=dis, per_row=2)
        self.lines = LinesEditor(self.ctx.look, ROU_LINES, lines, disabled=dis, height=360)
        acts = [T.btn("儲存並生效", I.SAVE, lambda e: self.save())] if self.editable else []
        hours = sum((Decimal(l["run_hours"]) for l in lines), Decimal(0))
        self.panel.controls = [
            ft.Row([T.icon_tile(I.ROUTE, "teal", 44), ft.Column([
                ft.Text("%s　%s" % (it["item_code"], it["item_name"]), size=18, weight=ft.FontWeight.W_800),
                T.muted("每單位加工工時合計 %s 小時" % T.qfmt(hours))], spacing=0, expand=True),
                T.status_chip(self.h["status"]) if self.h else T.chip("尚未建立", "amber")]),
            self.head, ft.Text("工序", size=15, weight=ft.FontWeight.W_700), self.lines, ft.Row(acts)]
        if refresh:
            self.update()

    def save(self):
        c = self.ctx
        try:
            h = self.head.values()
            lines = [l for l in self.lines.values() if l.get("wc_id")]
        except Exception as e:
            c.toast(str(e), True)
            return
        if not lines:
            c.toast("請至少輸入一道工序", True)
            return
        seqs = [l.get("op_seq") for l in lines]
        if None in seqs or len(set(seqs)) != len(seqs):
            c.toast("工序號碼不能空白或重複（建議 10、20、30…）", True)
            return

        def go():
            db = self.b.db
            with db.transaction():
                hv = dict(h, item_id=self.item_id, routing_ver=h.get("routing_ver") or "01", status="A")
                rid = self.b.save_row("rou_routing_h", hv, self.h and self.h["id"], "ROU")
                if hv.get("is_default"):
                    db.exec("UPDATE rou_routing_h SET is_default=0 WHERE item_id=%s AND id<>%s", (self.item_id, rid))
                db.exec("DELETE FROM rou_routing_d WHERE routing_id=%s", (rid,))
                for l in lines:
                    l = {k: v for k, v in l.items() if k in [x[0] for x in ROU_LINES]}
                    l.update(routing_id=rid, op_name=l.get("op_name") or "工序 %s" % l["op_seq"],
                             setup_hours=l.get("setup_hours") or 0, run_hours=l.get("run_hours") or 0,
                             is_outsource=int(bool(l.get("is_outsource"))), is_report_point=int(bool(l.get("is_report_point"))))
                    db.exec("INSERT INTO rou_routing_d (%s) VALUES (%s)" % (", ".join(l), ", ".join(["%s"] * len(l))),
                            list(l.values()))
        if c.guard(go, ok="途程已儲存"):
            self.reload()
            self.render()
