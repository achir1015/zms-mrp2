"""會計拋轉：產生拋轉（期間、類別 → 預覽分錄 → 產生批次）與拋轉紀錄（匯出拋轉檔、直接傳送、取消拋轉）。"""
import datetime as dt
import flet as ft

from .. import rocdate
from ..gl import SCOPES, AcctClient
from . import theme as T
from .widgets import tab_value, tabs

I = ft.Icons
STATUS = {"N": ("已產生", "amber"), "E": ("已匯出檔案", "sky"), "S": ("已傳送會計", "green"), "X": ("已取消", "slate")}


class GLTransfer(ft.Column):
    def __init__(self, ctx, tab="new"):
        self.ctx, self.b = ctx, ctx.books
        self.editable = self.b.can("ACC", 2)
        today = dt.date.today()
        self.f = T.date_field("期間起", today.replace(day=1), width=160)
        self.t = T.date_field("期間迄", today, width=160)
        self.checks = {k: ft.Checkbox(label=v, value=True) for k, v in SCOPES.items()}
        self.tab = tabs([("new", "產生拋轉"), ("list", "拋轉紀錄")], tab, lambda e: self.render())
        self.body = ft.Column(spacing=12, expand=True)
        super().__init__([T.page_header(I.SYNC_ALT, "會計拋轉", "把進貨、領料、報工、完工、出貨、庫存調整轉成傳票，送到「資料助秘之一般公司會計」",
                                        "rose"), self.tab, self.body], spacing=12, expand=True)
        self.render(refresh=False)

    def render(self, refresh=True):
        if tab_value(self.tab) == "new":
            self.r_new()
        else:
            self.r_list()
        if refresh:
            self.update()

    # ---------------------------------------------------------------- 產生拋轉
    def r_new(self):
        self.pending = ft.Row(wrap=True, spacing=8, run_spacing=4)
        self.preview = ft.Column(spacing=8, expand=True)
        acts = [T.btn("預覽分錄", I.PREVIEW, lambda e: self.do_preview(), kind="outline")]
        if self.editable:
            acts.append(T.btn("產生拋轉批次", I.SYNC_ALT, lambda e: self.do_create()))
        self.body.controls = [
            T.card(ft.Column([ft.Row([self.f, self.t, T.btn("查詢待拋轉", I.SEARCH, lambda e: self.load_pending(), kind="ghost")],
                                     wrap=True),
                              self.pending, ft.Row(acts, spacing=8)],
                             spacing=10), padding=16),
            T.muted("金額一律為新台幣；期初開帳與調撥不拋轉。會計系統沒有的明細科目、客戶、廠商，匯入時會自動建立。", 12),
            self.preview]
        self.load_pending(refresh=False)

    def period(self):
        f, t = rocdate.read(self.f.value), rocdate.read(self.t.value)
        if f > t:
            raise ValueError("期間起不能晚於期間迄")
        return f, t

    def scopes(self):
        return [k for k, c in self.checks.items() if c.value]

    def load_pending(self, refresh=True):
        p = self.ctx.guard(lambda: self.b.gl_pending(*self.period()))
        if p:
            self.pending.controls = [ft.Container(ft.Row([self.checks[k], T.chip("待拋轉 %d" % n, "orange" if n else "slate")],
                                                         spacing=0, tight=True), width=250) for k, n in p.items()]
        if refresh:
            self.update()

    def do_preview(self):
        r = self.ctx.guard(lambda: self.b.gl_preview(*self.period(), self.scopes()))
        if not r:
            return
        vouchers, _ = r
        names = {x["account_no"]: x["account_name"] for x in self.b.master_rows("account_map")}
        rows = []
        for v in vouchers:
            for i, x in enumerate(v["lines"]):
                rows.append(dict(ref=v["ref"] if i == 0 else "", d=v["date"] if i == 0 else None,
                                 src=SCOPES[v["src"]] if i == 0 else "", account=x["account"],
                                 name=names.get(x["account"], ""), partner=x["partner"], debit=x["debit"] or None,
                                 credit=x["credit"] or None, summary=x["summary"]))
        g = T.Grid([("ref", "參考號", "s", 120), ("d", "日期", "d", 80), ("src", "類別", "s", 90), ("account", "科目", "s", 50),
                    ("name", "科目名稱", "s", 120), ("partner", "往來", "s", 60), ("debit", "借方", "nz", 90),
                    ("credit", "貸方", "nz", 90), ("summary", "摘要", "s", 240)], totals=("debit", "credit"),
                   empty="這段期間沒有尚未拋轉的交易")
        g.set_rows(rows)
        self.preview.controls = [ft.Text("預覽：%d 張傳票" % len(vouchers), size=15, weight=ft.FontWeight.W_700), g]
        self.update()

    def do_create(self):
        bid = self.ctx.guard(lambda: self.b.create_gl_batch(*self.period(), self.scopes()))
        if bid:
            b = self.b.gl_batch(bid)
            self.ctx.toast("已產生拋轉批次 %s（%d 張傳票）；請匯出拋轉檔或直接傳送到會計系統" % (b["batch_no"], b["voucher_count"]))
            self.tab.selected = ["list"]
            self.render()

    # ---------------------------------------------------------------- 拋轉紀錄
    def r_list(self):
        rows = self.b.gl_batches()
        for r in rows:
            r["st"] = STATUS.get(r["status"], ("", "slate"))[0]
            r["period"] = "%s～%s" % (rocdate.show(r["date_from"]), rocdate.show(r["date_to"]))
            r["scope_names"] = "、".join(SCOPES.get(s, s) for s in (r["scope"] or "").split(",") if s)
        self.grid = T.Grid([("batch_no", "批次", "s", 120), ("period", "期間", "s", 170), ("voucher_count", "傳票", "s", 40),
                            ("total", "借方合計", "n", 100), ("st", "狀態", "s", 80), ("scope_names", "類別", "s", 220),
                            ("result", "結果", "s", 280)], on_pick=self.pick, empty="還沒有拋轉紀錄")
        self.grid.set_rows(rows)
        self.body.controls = [T.muted("點選批次可以查看傳票、匯出拋轉檔、直接傳送到會計系統或取消拋轉。", 12), self.grid]

    def pick(self, r):
        c = self.ctx
        lines = self.b.gl_batch_vouchers(r["id"])
        last = None
        for x in lines:
            if x["voucher_no"] == last:
                x["voucher_no"], x["voucher_date"], x["source_type"] = "", None, ""
            else:
                last = x["voucher_no"]
                x["source_type"] = SCOPES.get(x["source_type"], x["source_type"])
        g = T.Grid([("voucher_no", "參考號", "s", 110), ("voucher_date", "日期", "d", 80), ("source_type", "類別", "s", 80),
                    ("account_no", "科目", "s", 50), ("account_name", "名稱", "s", 110), ("dr_amount", "借方", "nz", 90),
                    ("cr_amount", "貸方", "nz", 90), ("summary", "摘要", "s", 220)], totals=("dr_amount", "cr_amount"),
                   height=380, empty="（已取消的批次沒有傳票）")
        g.set_rows(lines)
        acts = [T.btn("關閉", kind="ghost", on_click=lambda e: c.close())]
        if self.editable and r["status"] != "X":
            acts = [T.btn("取消拋轉", I.UNDO, lambda e: self.cancel(r), kind="danger"),
                    T.btn("匯出拋轉檔", I.DOWNLOAD, lambda e: self.ctx.page.run_task(self.export, r), kind="outline"),
                    T.btn("傳送到會計系統", I.SEND, lambda e: self.send_dialog(r))] + acts
        c.dialog("拋轉批次 %s（%s）" % (r["batch_no"], r["st"]), ft.Column([T.muted(r["result"] or "", 12), g], tight=True),
                 acts, icon=I.SYNC_ALT, tone="rose", width=920)

    async def export(self, r):
        path = await self.ctx.save_as("MRP2拋轉_%s.zmsgl" % r["batch_no"], "zmsgl")
        if path and self.ctx.guard(self.b.export_gl_batch, r["id"], path,
                                   ok="已匯出，請在會計系統「傳票作業 → 拋轉匯入」選擇此檔案"):
            self.ctx.close()
            self.render()

    def _remote_form(self, title, go_text, on_go):
        c, st = self.ctx, self.ctx.app.st
        url = T.field("會計系統連線網址", st.extra.get("acct_url", "127.0.0.1:8765"), width=260,
                      hint_text="會計系統「系統管理 → 手機連線」顯示的網址")
        uid = T.field("會計系統帳號", st.extra.get("acct_user", ""), width=180)
        pw = T.field("密碼", "", width=180, password=True, can_reveal_password=True)
        msg = ft.Text("", size=13)

        def client():
            st.extra["acct_url"], st.extra["acct_user"] = url.value.strip(), uid.value.strip()
            st.save()
            return AcctClient(url.value, uid.value, pw.value)

        def test(e):
            try:
                info = client().ping()
                msg.value, msg.color = "連線成功：%s %s（%s）" % (info.get("app", ""), info.get("version", ""),
                                                           info.get("company", "")), T.SUCCESS
            except Exception as ex:
                msg.value, msg.color = str(ex), T.DANGER
            msg.update()

        def go(e):
            if c.guard(on_go, client()):
                c.close()
                self.render()
        c.dialog(title, ft.Column([T.muted("會計系統要開著，並在「系統管理 → 手機連線」打開連線服務；用會計系統的帳號登入，"
                                           "匯入後產生「未審核」傳票。", 12), url, ft.Row([uid, pw]), msg], tight=True, spacing=12),
                 [T.btn("取消", kind="ghost", on_click=lambda e: c.close()),
                  T.btn("測試連線", I.WIFI_TETHERING, test, kind="outline"), T.btn(go_text, I.SEND, go)],
                 icon=I.SEND, tone="green", width=560)

    def send_dialog(self, r):
        def go(remote):
            res = self.b.send_gl_batch(r["id"], remote)
            nos = res.get("voucher_nos") or []
            self.ctx.toast("已送達會計系統：%d 張未審核傳票 %s" % (len(nos), ("%s～%s" % (nos[0], nos[-1])) if nos else ""))
        self._remote_form("傳送到會計系統：%s" % r["batch_no"], "傳送", go)

    def cancel(self, r):
        if r["status"] == "S":                 # 已傳送：要連到會計系統刪除未審核傳票
            self._remote_form("取消拋轉：%s（會一併刪除會計系統的未審核傳票）" % r["batch_no"], "取消拋轉",
                              lambda remote: self.b.cancel_gl_batch(r["id"], remote))
            return

        def go():
            if self.ctx.guard(self.b.cancel_gl_batch, r["id"], ok="已取消拋轉，來源單據可以重新拋轉"):
                self.ctx.close()
                self.render()
        self.ctx.confirm("取消拋轉", "取消後這批傳票作廢，來源單據回到待拋轉。若已把拋轉檔匯入會計系統，"
                                     "請先在會計系統取消該批匯入。確定嗎？", go, yes="取消拋轉")

