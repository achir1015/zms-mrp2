"""系統管理：使用者與權限、公司設定、備份還原、版本更新與捷徑、操作紀錄、範例資料。"""
import datetime as dt
import os
import sys

import flet as ft

from .. import APP_NAME, APP_VERSION, maintenance
from ..seed import FUNCS
from . import theme as T
from .widgets import Form

I = ft.Icons
MAC = sys.platform == "darwin"
LEVELS = [("0", "無"), ("1", "查詢"), ("2", "維護")]


class Users(ft.Column):
    def __init__(self, ctx):
        self.ctx, self.b = ctx, ctx.books
        self.grid = T.Grid([("user_code", "帳號", "s", 110), ("user_name", "姓名", "s", 120), ("roles", "角色", "s", 260),
                            ("is_active", "啟用", "b", 50), ("last_login_at", "最後登入", "d", 130)],
                           on_pick=lambda r: self.user_dialog(r))
        self.roles = T.Grid([("role_code", "代碼", "s", 90), ("role_name", "角色", "s", 140)], on_pick=self.perm_dialog,
                            height=470)
        super().__init__([T.page_header(I.ADMIN_PANEL_SETTINGS, "使用者與權限", "每個角色可設定 14 個模組的「查詢」或「維護」權限",
                                        "pink", [T.btn("新增使用者", I.PERSON_ADD, lambda e: self.user_dialog(None))]),
                          ft.Row([ft.Column([self.grid], expand=True),
                                  T.card(ft.Column([ft.Text("角色（點選設定權限）", size=15, weight=ft.FontWeight.W_700),
                                                    self.roles], spacing=8), width=320, padding=14)], expand=True, spacing=14,
                                 vertical_alignment=ft.CrossAxisAlignment.START)], spacing=12, expand=True)
        self.reload()

    def reload(self, refresh=False):
        self.grid.set_rows(self.b.users())
        self.roles.set_rows(self.b.roles())
        if refresh:
            self.update()

    def user_dialog(self, u):
        c = self.ctx
        code = T.field("帳號", u and u["user_code"] or "", width=200)
        name = T.field("姓名", u and u["user_name"] or "", width=200)
        pw = T.field("密碼（修改時空白＝不變）" if u else "密碼（至少 6 個字）", "", width=260, password=True,
                     can_reveal_password=True)
        active = T.switch("啟用", True if not u else bool(u["is_active"]))
        emp = T.dropdown("對應員工", c.look("employees"), None, width=220, blank="（無）")
        mine = set((u["role_ids"] or "").split(",")) if u else set()
        checks = [ft.Checkbox(label=r["role_name"], value=str(r["id"]) in mine, data=r["id"]) for r in self.b.roles()]

        def save(e):
            rid = c.guard(self.b.save_user, u and u["id"], code.value, name.value, [x.data for x in checks if x.value],
                          active.value, pw.value or None, int(emp.value) if emp.value else None)
            if rid:
                c.close()
                c.toast("已儲存")
                self.reload(True)
        c.dialog("修改使用者" if u else "新增使用者", ft.Column([ft.Row([code, name]), ft.Row([pw, emp]), active,
                                                          ft.Text("角色", weight=ft.FontWeight.W_700),
                                                          ft.Row(checks, wrap=True)], tight=True, spacing=12),
                 [T.btn("取消", kind="ghost", on_click=lambda e: c.close()), T.btn("儲存", I.SAVE, save)],
                 icon=I.PERSON, tone="pink", width=600)

    def perm_dialog(self, role):
        c = self.ctx
        cur = self.b.role_perms(role["id"])
        segs = {}
        rows = []
        for f, name, _ in FUNCS:
            s = ft.SegmentedButton(segments=[ft.Segment(value=k, label=ft.Text(t)) for k, t in LEVELS],
                                   selected=[str(cur.get(f, 0))], show_selected_icon=False)
            segs[f] = s
            rows.append(ft.Row([ft.Text(name, width=170), s]))

        def save(e):
            if c.guard(self.b.save_role_perms, role["id"], {f: int(s.selected[0]) for f, s in segs.items()}, ok="權限已儲存"):
                c.close()
        c.dialog("角色權限：%s" % role["role_name"], ft.Column(rows, tight=True, spacing=6, scroll=ft.ScrollMode.AUTO,
                                                           height=480),
                 [T.btn("取消", kind="ghost", on_click=lambda e: c.close())] +
                 ([T.btn("儲存", I.SAVE, save)] if role["role_code"] != "ADMIN" else [T.muted("系統管理員一律全部權限")]),
                 icon=I.SECURITY, tone="pink", width=520)


COMPANY = [("company_name", "公司名稱", "s", 0), ("tax_id", "統一編號", "s", 0), ("owner_name", "負責人", "s", 0),
           ("phone", "電話", "s", 0), ("address", "地址", "s", 0), ("base_currency", "本位幣", "ref:currencies", 0),
           ("fiscal_start_month", "會計年度起始月", "i", 0)]


class Company(ft.Column):
    def __init__(self, ctx):
        self.ctx, self.b = ctx, ctx.books
        self.f = Form(ctx.look, COMPANY, self.b.company(), disabled=not self.b.can("SYS", 2))
        params = self.b.db.rows("SELECT * FROM sys_param ORDER BY param_key")
        self.pf = {p["param_key"]: T.field(p["description"] or p["param_key"], p["param_value"], width=200) for p in params}
        super().__init__([T.page_header(I.BUSINESS, "公司設定", "公司資料與系統參數", "blue"),
                          T.card(ft.Column([self.f, ft.Divider(), ft.Text("系統參數", size=15, weight=ft.FontWeight.W_700),
                                            ft.Row(list(self.pf.values()), wrap=True),
                                            ft.Row([T.btn("儲存", I.SAVE, lambda e: self.save())])], spacing=12), padding=20)],
                         spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    def save(self):
        d = self.f.values()

        def go():
            self.b.save_company(d)
            for k, f in self.pf.items():
                self.b.set_param(k, f.value)
        self.ctx.guard(go, ok="已儲存")


class Backup(ft.Column):
    def __init__(self, ctx):
        self.ctx = ctx
        st = ctx.app.st
        super().__init__([T.page_header(I.BACKUP, "備份與還原", "整個資料庫備份成一個 .sql.gz 檔；建議每天下班前備份", "green"),
                          ft.Row([T.card(ft.Column([T.icon_tile(I.BACKUP, "green", 52), ft.Text("備份", size=17,
                                                                                               weight=ft.FontWeight.W_700),
                                                    T.muted("資料夾：%s" % os.path.dirname(st.datadir), 12),
                                                    T.btn("立即備份", I.SAVE_ALT, self.backup)], spacing=10), expand=True),
                                  T.card(ft.Column([T.icon_tile(I.RESTORE, "rose", 52), ft.Text("還原", size=17,
                                                                                              weight=ft.FontWeight.W_700),
                                                    T.muted("還原會覆蓋目前所有資料，請先備份！", 12),
                                                    T.btn("選擇備份檔還原", I.RESTORE, self.restore, kind="danger")], spacing=10),
                                         expand=True)], spacing=14)], spacing=12)

    async def backup(self, e):
        path = await self.ctx.save_as("MRP2備份_%s.sql.gz" % dt.datetime.now().strftime("%Y%m%d_%H%M"), "gz")
        if path:
            size = self.ctx.guard(maintenance.backup, self.ctx.app.st, path)
            if size:
                self.ctx.toast("已備份（%.1f MB）" % (size / 1e6))

    async def restore(self, e):
        files = await ft.FilePicker().pick_files(dialog_title="選擇備份檔", allowed_extensions=["gz", "sql"])
        if not files:
            return
        path = files[0].path

        def go():
            if self.ctx.guard(maintenance.restore, self.ctx.app.st, path, ok="已還原，請重新登入"):
                self.ctx.app.logout()
        self.ctx.confirm("還原資料庫", "目前所有資料都會被備份檔內容取代，確定嗎？", go, yes="還原")


class Update(ft.Column):
    def __init__(self, ctx):
        self.ctx = ctx
        self.status = ft.Column(spacing=10)
        self.bar = ft.ProgressBar(value=0, visible=False, color=T.ACCENT, bgcolor="#E6F4F1", bar_height=8, border_radius=4)
        super().__init__([
            T.page_header(I.SYSTEM_UPDATE, "版本更新與捷徑", "程式開啟時會自動檢查新版本", "rose"),
            ft.Row([T.card(ft.Column([
                ft.Row([ft.Image(src="icon.png", width=64, height=64),
                        ft.Column([ft.Text(APP_NAME, size=18, weight=ft.FontWeight.W_800),
                                   T.chip("目前版本 v%s" % APP_VERSION, "blue", I.VERIFIED)], spacing=6)], spacing=14),
                self.status, self.bar, ft.Row([T.btn("檢查更新", I.REFRESH, lambda e: self.check())])], spacing=14),
                expand=True, padding=22),
                T.card(ft.Column([T.icon_tile(I.SHORTCUT, "teal", 52, radius=16),
                                  ft.Text("桌面捷徑", size=17, weight=ft.FontWeight.W_700),
                                  T.muted("App 在「應用程式」資料夾，可拖到 Dock 常駐；也可以在桌面建立替身。" if MAC else
                                          "安裝時已建立桌面與開始功能表捷徑；如果不見了，按下面按鈕重建。", 12),
                                  T.btn("在桌面建立替身" if MAC else "重建桌面捷徑",
                                        I.DESKTOP_MAC if MAC else I.DESKTOP_WINDOWS, lambda e: self.shortcut(), kind="accent")],
                                 spacing=10), width=340, padding=22)], spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.START),
            T.card(ft.Column([ft.Text("系統資訊", size=15, weight=ft.FontWeight.W_700),
                              T.muted("系統開發：吳玉柱 先生 與 Claude AI Opus 5.5", 13),
                              T.muted("資料庫：MariaDB（本機內建，埠 %s）　介面：Flet　語音：微軟神經語音／Windows 內建語音"
                                      % ctx.app.st.port, 13)], spacing=6), padding=18)],
            spacing=14, expand=True, scroll=ft.ScrollMode.AUTO)
        info = ctx.app.update_info
        if info:
            self.show_info(info, refresh=False)
        else:
            self.status.controls = [T.muted("按「檢查更新」查詢是否有新版本。", 13)]

    def check(self):
        self.status.controls = [ft.Row([ft.ProgressRing(width=18, height=18), T.muted("檢查中…")])]
        self.update()

        def work():
            try:
                info = maintenance.check_update()
            except Exception as ex:
                self.status.controls = [ft.Row([ft.Icon(I.WIFI_OFF, color=T.WARN),
                                                ft.Text("無法連線更新伺服器：%s" % ex, size=13, color=T.WARN)])]
                self.update()
                return
            if not info:
                self.status.controls = [ft.Row([ft.Icon(I.CHECK_CIRCLE, color=T.SUCCESS),
                                                ft.Text("已是最新版本", size=14, color=T.SUCCESS)])]
                self.update()
                return
            self.ctx.app.update_info = info
            self.show_info(info)
        self.ctx.page.run_thread(work)

    def show_info(self, info, refresh=True):
        self.status.controls = [
            ft.Row([T.icon_tile(I.NEW_RELEASES, "green", 36),
                    ft.Text("有新版本 v%s" % info["version"], size=16, weight=ft.FontWeight.W_700, color=T.SUCCESS)]),
            ft.Container(ft.Text((info["notes"] or "（無更新說明）").strip()[:900], size=13, selectable=True),
                         bgcolor="#F7F9FC", border_radius=10, padding=12),
            ft.Row([T.btn("下載並安裝", I.DOWNLOAD, lambda e: self.install(info), kind="accent"),
                    T.btn("略過此版本", I.SKIP_NEXT, lambda e: self.skip(info), kind="ghost")])]
        if refresh:
            self.update()

    def skip(self, info):
        self.ctx.app.st.skipped_version = info["version"]
        self.ctx.app.st.save()
        self.ctx.app.update_banner.visible = False
        self.ctx.toast("已略過 v%s" % info["version"])
        self.ctx.page.update()

    def install(self, info):
        if not info.get("name"):
            self.ctx.toast("找不到安裝檔，請到發佈頁下載", True)
            return
        self.bar.visible = True
        self.bar.value = 0
        self.update()

        def work():
            try:
                path = maintenance.download(info["url"], lambda p: (setattr(self.bar, "value", p), self.bar.update()))
            except Exception as ex:
                self.ctx.toast("下載失敗：%s" % ex, True)
                return
            self.ctx.toast("下載完成，正在安裝新版（程式會自動關閉並重新開啟）…")
            self.ctx.app.shutdown()
            maintenance.launch_installer(path)
            os._exit(0)
        self.ctx.page.run_thread(work)

    def shortcut(self):
        self.ctx.guard(maintenance.create_desktop_shortcut, ok="已在桌面建立替身" if MAC else "已在桌面建立捷徑")


class Audit(ft.Column):
    def __init__(self, ctx):
        rows = ctx.books.db.rows("SELECT a.created_at, u.user_name, a.action, a.table_name, a.record_key, a.func_code FROM "
                                 "sys_audit_log a LEFT JOIN sys_user u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 800")
        g = T.Grid([("created_at", "時間", "d", 130), ("user_name", "使用者", "s", 100), ("action", "動作", "s", 70),
                    ("func_code", "模組", "s", 50), ("table_name", "資料表", "s", 140), ("record_key", "單號／鍵值", "s", 200)])
        g.set_rows(rows)
        super().__init__([T.page_header(I.HISTORY, "操作紀錄", "最近 800 筆登入、新增、修改、刪除、過帳紀錄", "slate",
                                        [ctx.export_button(g, "操作紀錄")]), g], spacing=12, expand=True)


class Demo(ft.Column):
    def __init__(self, ctx):
        self.ctx = ctx
        has = ctx.books.has_business_data()
        items = [("三種成品", "ATX 主機板、650W 金牌電源供應器、USB 3.0 四埠集線器"),
                 ("三階 BOM、共用料", "固態電容、MOSFET、USB 母座、說明書跨產品共用；電源變壓器自製繞線"),
                 ("料件版本", "主機板 PCB Rev A 已淘汰（120 片不計入 MRP）、Rev B 量產；Hub IC 韌體 1.0／1.2 可互換"),
                 ("台日美韓產地", "日製／台製電容、美製／韓製 MOSFET、韓製 DDR5 插槽；電源的電容指定日製"),
                 ("外幣與匯率", "日圓、美元、韓元採購；美元接單；匯率歷史"),
                 ("先進先出", "期初庫存分批入庫（不同入庫時間與成本），領料依先進先出扣減"),
                 ("訂單與 MPS", "主機板 300 片、電源 200 台、集線器 500 個，已建好主生產排程，可直接執行 MRP")]
        super().__init__([
            T.page_header(I.ROCKET_LAUNCH, "電子業範例資料", "載入後可以直接試跑 MPS → MRP → CRP → 轉單 → 工單", "amber"),
            T.card(ft.Column([*[ft.Row([ft.Icon(I.CHECK_CIRCLE, color=T.SUCCESS, size=20),
                                        ft.Text(t, size=14, weight=ft.FontWeight.W_700, width=150),
                                        ft.Text(s, size=14, expand=True)]) for t, s in items],
                              ft.Divider(),
                              T.muted("範例只能載入到空白資料庫（還沒有任何料件時）。日期為 2026 年 11～12 月。", 13),
                              T.btn("載入範例資料", I.DOWNLOAD, lambda e: self.load(), disabled=has) if not has else
                              T.chip("已經有料件資料，不能再載入範例", "slate")], spacing=10), padding=22)],
            spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    def load(self):
        if self.ctx.guard(self.ctx.books.load_demo, ok="已載入電子業範例資料"):
            self.ctx.look.clear()
            self.ctx.app.go("mps")
