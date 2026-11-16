"""共用畫面元件：下拉選單資料（Lookups）、表單（Form）、可編輯明細行（LinesEditor）、分頁（tabs）。

欄位規格：(欄位, 標題, 型別, 寬度)
型別：s 文字、t 多行文字、n 金額、q 數量、p 單價／匯率、i 整數、b 是否、d 日期、
      sel:A=甲,B=乙 固定選項、ref:清單名稱 下拉（清單見 LOOKUPS）、ro 唯讀文字
"""
import datetime as dt
from decimal import Decimal

import flet as ft

from .. import rocdate
from . import theme as T



class Lookups:
    def __init__(self, books):
        self.books = books
        self.cache = {}

    def __call__(self, name):
        if name not in self.cache:
            self.cache[name] = [tuple(x) for x in self.books.lookup(name)]
        return self.cache[name]

    def label(self, name, key):
        return dict((str(k), t) for k, t in self(name)).get(str(key), "" if key is None else str(key))

    def clear(self):
        self.cache.clear()


def tabs(options, selected, on_change):
    return ft.SegmentedButton(segments=[ft.Segment(value=k, label=ft.Text(t)) for k, t in options],
                              selected=[selected], show_selected_icon=False, on_change=on_change)


def tab_value(seg):
    return (seg.selected or [None])[0]


def sel_options(typ):
    return [tuple(x.split("=", 1)) for x in typ[4:].split(",")]


def to_text(v, typ):
    if v is None:
        return ""
    if typ == "d":
        return rocdate.show(v)
    if typ in ("n",):
        return T.amt(v)
    if typ in ("q", "p"):
        return T.qfmt(v) if typ == "q" else str(Decimal(str(v)).normalize()) if Decimal(str(v)) != 0 else "0"
    return str(v)


def make_input(look, key, title, typ, width, value=None, disabled=False, on_change=None):
    """依型別產生輸入控制項。"""
    if typ == "b":
        c = T.switch(title, bool(value) if value is not None else False)
    elif typ.startswith("sel:"):
        opts = sel_options(typ)
        c = T.dropdown(title, opts, value if value not in (None, "") else opts[0][0], width=width, filterable=False)
    elif typ.startswith("ref:"):
        c = T.dropdown(title, look(typ[4:]), value if value not in (None, "") else None, width=width, blank="（無）")
    elif typ == "d":
        c = T.date_field(title, value if value else None, width=width)
        if value is None:
            c.value = ""
    elif typ in ("n", "q", "p", "i"):
        c = T.field(title, to_text(value, typ), width=width, text_align=ft.TextAlign.RIGHT)
    elif typ == "t":
        c = T.field(title, value or "", width=width, multiline=True, min_lines=2, max_lines=5)
    else:
        c = T.field(title, value or "", width=width, read_only=typ == "ro")
    c.disabled = disabled or typ == "ro"
    if on_change:
        if isinstance(c, ft.Dropdown):
            c.on_select = on_change
        else:
            c.on_change = on_change
    c.data = (key, typ)
    return c


def read_input(c):
    key, typ = c.data
    v = c.value
    if typ == "b":
        return bool(v)
    if v in (None, ""):
        return None
    if typ == "d":
        return rocdate.read(v)
    if typ in ("n", "q", "p"):
        return Decimal(str(v).replace(",", ""))
    if typ == "i":
        return int(str(v).replace(",", ""))
    return v


class Form(ft.Column):
    """依欄位規格排成多欄表單。per_row＝每列幾個欄位。"""

    def __init__(self, look, fields, data=None, disabled=False, per_row=2, on_change=None):
        self.inputs = {}
        if T.MOBILE:                    # 手機：每列最多兩個欄位
            per_row = min(per_row, 2)
        rows, cur = [], []
        for key, title, typ, width in fields:
            c = make_input(look, key, title, typ, None, (data or {}).get(key), disabled,
                           on_change=(lambda e, k=key: on_change(k)) if on_change else None)
            c.expand = True
            self.inputs[key] = c
            if typ == "t" or per_row == 1:
                if cur:
                    rows.append(ft.Row(cur, spacing=10))
                    cur = []
                rows.append(ft.Row([c]))
                continue
            cur.append(c)
            if len(cur) == per_row:
                rows.append(ft.Row(cur, spacing=10))
                cur = []
        if cur:
            rows.append(ft.Row(cur + [ft.Container(expand=True)] * (per_row - len(cur)), spacing=10))
        super().__init__(rows, spacing=12)

    def values(self):
        return {k: read_input(c) for k, c in self.inputs.items()}

    def set(self, key, value):
        c = self.inputs[key]
        c.value = value if isinstance(c, ft.Dropdown) else to_text(value, c.data[1])


class LinesEditor(ft.Column):
    """可編輯明細行：cols=[(欄位, 標題, 型別, 寬度)]；on_change(row_dict_controls, key) 讓畫面自動帶值。"""

    def __init__(self, look, cols, rows=None, disabled=False, on_change=None, on_rows=None, min_rows=1, height=None):
        self.look, self.cols, self.locked = look, cols, disabled
        self.on_change, self.on_rows, self.min_rows = on_change, on_rows, min_rows
        self.lines = []
        head = ft.Row([ft.Text("#", width=26, size=12, color=T.MUTED)] +
                      [ft.Text(t, width=w, size=12, weight=ft.FontWeight.W_700, color="#334155",
                               text_align=ft.TextAlign.RIGHT if typ in ("n", "q", "p", "i") else None)
                       for k, t, typ, w in cols], spacing=8)
        self.box = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=height is None, height=height)
        self.add_btn = T.btn("新增一行", ft.Icons.ADD, lambda e: self.add(), kind="ghost")
        self.add_btn.visible = not disabled
        total = 26 + sum(c[3] for c in cols) + 8 * (len(cols) + 1) + 60
        inner = ft.Column([ft.Container(head, bgcolor="#EEF3FA", border_radius=8,
                                        padding=ft.Padding.symmetric(horizontal=8, vertical=6)), self.box],
                          spacing=6, width=total, expand=height is None, data=T.READY)   # 手機：保持寬度、橫向捲動
        super().__init__([ft.Row([inner], scroll=ft.ScrollMode.ALWAYS, expand=height is None,
                                 vertical_alignment=ft.CrossAxisAlignment.START), self.add_btn],
                         spacing=6, expand=height is None)
        for r in rows or []:
            self.add(r, refresh=False)
        while len(self.lines) < min_rows and not disabled:
            self.add(refresh=False)

    def add(self, data=None, refresh=True):
        ctrls = {}
        cells = [ft.Text(str(len(self.lines) + 1), width=26, size=12, color=T.MUTED)]
        for key, title, typ, w in self.cols:
            c = make_input(self.look, key, "", typ, w, (data or {}).get(key), self.locked)
            if self.on_change:
                h = (lambda e, k=key, cs=ctrls: self.on_change(cs, k))
                if isinstance(c, ft.Dropdown):
                    c.on_select = h
                else:
                    c.on_blur = h
            ctrls[key] = c
            cells.append(c)
        row = ft.Row(cells, spacing=8)
        ctrls["_row"] = row
        ctrls["_data"] = data or {}
        if not self.locked:
            cells.append(ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color=T.DANGER, icon_size=18, tooltip="刪除此行",
                                       on_click=lambda e, cs=ctrls: self.remove(cs)))
        self.lines.append(ctrls)
        self.box.controls.append(row)
        if self.on_rows:
            self.on_rows()
        if refresh:
            self.update()
        return ctrls

    def remove(self, ctrls):
        self.lines.remove(ctrls)
        self.box.controls.remove(ctrls["_row"])
        for i, l in enumerate(self.lines, 1):
            l["_row"].controls[0].value = str(i)
        if not self.lines and self.min_rows:
            self.add(refresh=False)
        if self.on_rows:
            self.on_rows()
        self.update()

    def values(self):
        out = []
        for l in self.lines:
            d = dict(l["_data"])
            for k, c in l.items():
                if not k.startswith("_"):
                    d[k] = read_input(c)
            out.append(d)
        return out


def today_text():
    return rocdate.show(dt.date.today())
