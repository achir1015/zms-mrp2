"""共用基礎：錯誤類別、數字格式、登入與權限、操作紀錄、單據編號、公司與參數、基本資料維護。

所有規則都在服務層檢查（畫面只負責顯示），日後手機版透過 API 也共用同一套。
"""
import datetime as dt
import json
import re
from decimal import ROUND_HALF_UP, Decimal

import pymysql

from . import passwords, rocdate
from .seed import FUNCS

IDENT = re.compile(r"^[a-z_][a-z0-9_]{0,63}$")
CENT = Decimal("0.01")
Q4 = Decimal("0.0001")
Q6 = Decimal("0.000001")
D0 = Decimal(0)


class BizError(Exception):
    """可以直接顯示給使用者看的錯誤。"""


def dec(v, q=Q4) -> Decimal:
    if v in (None, ""):
        return D0
    if isinstance(v, str):
        v = v.replace(",", "").strip() or "0"
    try:
        return Decimal(str(v)).quantize(q, ROUND_HALF_UP)
    except Exception:
        raise BizError("數字格式不正確：%s" % v)


def money(v) -> Decimal:
    return dec(v, CENT)


def qty(v) -> Decimal:
    return dec(v, Q4)


def price(v) -> Decimal:
    return dec(v, Q6)


def date(v) -> dt.date:
    if isinstance(v, dt.date):
        return v
    try:
        return rocdate.read(v)
    except ValueError as e:
        raise BizError(str(e))


def friendly_db_error(e):
    code = e.args[0] if getattr(e, "args", None) else 0
    msg = str(e.args[1]) if len(getattr(e, "args", ())) > 1 else str(e)
    if code == 1062:
        return "資料重複：%s" % msg.split("for key")[0].replace("Duplicate entry", "已有相同的").strip()
    if code in (1451,):
        return "這筆資料已被其他資料使用，不能刪除（可改為停用）"
    if code in (1452,):
        return "參照的資料不存在，請重新選擇"
    if code in (3819, 4025):
        return "資料不符合規則：%s" % msg
    if code == 1048:
        return "必填欄位未填：%s" % msg.split("'")[1] if "'" in msg else msg
    return msg


class Base:
    def __init__(self, db):
        self.db = db
        self.user = None
        self.perms = {}
        self.is_admin = False

    # ================================================================ 登入、權限、紀錄
    @property
    def uid(self):
        return self.user["user_code"] if self.user else ""

    @property
    def user_id(self):
        return self.user["id"] if self.user else None

    def has_users(self) -> bool:
        return bool(self.db.value("SELECT COUNT(*) FROM sys_user"))

    def create_first_admin(self, code, name, pw):
        if self.has_users():
            raise BizError("已經有使用者，請直接登入")
        self._check_pw(pw)
        code = (code or "").strip()
        if not code:
            raise BizError("請輸入帳號")
        uid = self.db.exec("INSERT INTO sys_user (user_code, user_name, password_hash) VALUES (%s,%s,%s)",
                           (code, (name or "系統管理員").strip(), passwords.make(pw)))
        rid = self.db.value("SELECT id FROM sys_role WHERE role_code='ADMIN'")
        self.db.exec("INSERT INTO sys_user_role (user_id, role_id) VALUES (%s,%s)", (uid, rid))

    @staticmethod
    def _check_pw(pw):
        if len(pw or "") < 6:
            raise BizError("密碼至少 6 個字")

    def login(self, code, pw):
        u = self.db.row("SELECT * FROM sys_user WHERE user_code=%s", ((code or "").strip(),))
        if not u or not passwords.verify(pw, u["password_hash"]):
            self.db.exec("INSERT INTO sys_audit_log (action, record_key) VALUES ('LOGINFAIL', %s)", ((code or "")[:60],))
            raise BizError("帳號或密碼錯誤")
        if not u["is_active"]:
            raise BizError("此帳號已停用，請洽系統管理員")
        self._load_user(u)
        self.db.exec("UPDATE sys_user SET last_login_at=NOW() WHERE id=%s", (u["id"],))
        self.log("LOGIN", "sys_user", u["user_code"])
        return self.user

    def _load_user(self, u):
        self.user = u
        roles = self.db.rows("SELECT r.role_code, r.role_name FROM sys_user_role ur JOIN sys_role r ON r.id=ur.role_id "
                             "WHERE ur.user_id=%s", (u["id"],))
        self.user["roles"] = "、".join(r["role_name"] for r in roles)
        self.is_admin = any(r["role_code"] == "ADMIN" for r in roles)
        self.perms = {}
        for r in self.db.rows("SELECT p.func_code, MAX(p.can_view) v, MAX(p.can_edit OR p.can_add) e FROM sys_user_role ur "
                              "JOIN sys_role_perm p ON p.role_id=ur.role_id WHERE ur.user_id=%s GROUP BY p.func_code",
                              (u["id"],)):
            self.perms[r["func_code"]] = 2 if r["e"] else (1 if r["v"] else 0)
        self.user["is_admin"] = self.is_admin

    def refresh_user(self):
        """重新讀取使用者狀態與權限（手機每次呼叫都會做；停用或改權限立即生效）。回傳 False＝已停用。"""
        u = self.db.row("SELECT * FROM sys_user WHERE id=%s", (self.user_id,))
        if not u or not u["is_active"]:
            return False
        self._load_user(u)
        return True

    def logout(self):
        if self.user:
            self.log("LOGOUT", "sys_user", self.uid)
        self.user, self.perms, self.is_admin = None, {}, False

    def level(self, func) -> int:
        if not self.user:
            return 0
        if self.is_admin:
            return 2
        return int(self.perms.get(func, 0))

    def can(self, func, lvl=1) -> bool:
        return self.level(func) >= lvl

    def need(self, func, lvl=2):
        if not self.can(func, lvl):
            from .seed import FUNC_NAMES
            raise BizError("您沒有「%s」的%s權限" % (FUNC_NAMES.get(func, func), "維護" if lvl >= 2 else "查詢"))

    def log(self, action, table="", key="", detail=None, func=""):
        try:
            self.db.exec("INSERT INTO sys_audit_log (user_id, func_code, action, table_name, record_key, detail) "
                         "VALUES (%s,%s,%s,%s,%s,%s)",
                         (self.user_id, func[:30], action[:10], table[:40], str(key)[:60],
                          json.dumps(detail, ensure_ascii=False, default=str) if detail is not None else None))
        except Exception:
            pass

    def change_password(self, old, new):
        if not passwords.verify(old, self.user["password_hash"]):
            raise BizError("目前密碼不正確")
        self._check_pw(new)
        h = passwords.make(new)
        self.db.exec("UPDATE sys_user SET password_hash=%s WHERE id=%s", (h, self.user_id))
        self.user["password_hash"] = h

    # ================================================================ 單據編號
    def next_no(self, doc_type, d=None):
        """依 sys_doc_type 的前綴與格式取號，例：PO2611 0001 → PO2611000 1；每月重新起算。"""
        d = date(d or rocdate.today())
        period = d.strftime("%Y%m")
        with self.db.transaction():
            t = self.db.row("SELECT prefix, no_format FROM sys_doc_type WHERE doc_type=%s", (doc_type,))
            if not t:
                raise BizError("單別 %s 尚未設定" % doc_type)
            self.db.exec("INSERT IGNORE INTO sys_doc_seq (doc_type, period, last_no) VALUES (%s,%s,0)", (doc_type, period))
            n = self.db.value("SELECT last_no FROM sys_doc_seq WHERE doc_type=%s AND period=%s FOR UPDATE",
                              (doc_type, period)) + 1
            self.db.exec("UPDATE sys_doc_seq SET last_no=%s WHERE doc_type=%s AND period=%s", (n, doc_type, period))
        fmt = t["no_format"] or "{prefix}{yyyymm}{seq:4}"
        return (fmt.replace("{prefix}", t["prefix"]).replace("{yyyymm}", period).replace("{yymm}", period[2:])
                .replace("{seq:4}", "%04d" % n).replace("{seq:3}", "%03d" % n).replace("{seq}", str(n)))

    # ================================================================ 公司、參數
    def company(self):
        return self.db.row("SELECT * FROM sys_company WHERE id=1") or {}

    def save_company(self, data):
        self.need("SYS")
        cols = ["company_name", "tax_id", "owner_name", "phone", "address", "base_currency", "fiscal_start_month"]
        self.db.exec("UPDATE sys_company SET %s WHERE id=1" % ", ".join("%s=%%s" % c for c in cols),
                     [data.get(c) or None if c not in ("company_name", "base_currency", "fiscal_start_month")
                      else data.get(c) for c in cols])
        self.log("EDIT", "sys_company", 1, data, "SYS")

    def param(self, key, default=None):
        v = self.db.value("SELECT param_value FROM sys_param WHERE param_key=%s", (key,))
        return default if v is None else v

    def set_param(self, key, value, desc=None):
        self.need("SYS")
        self.db.exec("INSERT INTO sys_param (param_key, param_value, description) VALUES (%s,%s,%s) "
                     "ON DUPLICATE KEY UPDATE param_value=VALUES(param_value)", (key, str(value), desc))

    def base_currency(self):
        return self.db.value("SELECT currency_code FROM bas_currency WHERE is_base=1") or "TWD"

    def rate_on(self, currency, d=None):
        """單據日的記帳匯率：先找當天以前最近一筆匯率歷史，沒有再用幣別的最新匯率。"""
        if not currency or currency == self.base_currency():
            return Decimal(1)
        d = date(d or rocdate.today())
        r = self.db.value("SELECT rate FROM bas_exchange_rate WHERE currency_code=%s AND rate_type='A' AND rate_date<=%s "
                          "ORDER BY rate_date DESC LIMIT 1", (currency, d))
        if r is None:
            r = self.db.value("SELECT exchange_rate FROM bas_currency WHERE currency_code=%s", (currency,))
        if r is None:
            raise BizError("找不到幣別 %s" % currency)
        return Decimal(str(r))

    # ================================================================ 一般資料表維護
    @staticmethod
    def _table(table, key=None):
        """只允許登記過的資料表；權限模組與主鍵由資料表決定（手機呼叫時也不能指定別的）。"""
        from .views import TABLES
        if table not in TABLES:
            raise BizError("不允許維護的資料表：%s" % table)
        func, pk = TABLES[table]
        key = key or pk
        if not IDENT.match(key):
            raise BizError("欄位名稱不正確")
        return func, key

    def save_row(self, table, data, row_id=None, func=None, key=None):
        """新增或修改一筆（data 只含要寫入的欄位）。回傳主鍵值。"""
        func, key = self._table(table, key)
        self.need(func)
        data = {k: (None if v == "" else v) for k, v in data.items()}
        if not all(IDENT.match(k) for k in data):
            raise BizError("欄位名稱不正確")
        if table == "bas_currency" and data.get("is_base"):
            self.db.exec("UPDATE bas_currency SET is_base=0")
        try:
            return self._save_row(table, data, row_id, func, key)
        finally:
            if table == "bas_calendar":
                from .seed import renumber_calendar
                renumber_calendar(self.db)

    def _save_row(self, table, data, row_id, func, key):
        try:
            if row_id in (None, ""):
                cols = list(data)
                new_id = self.db.exec("INSERT INTO `%s` (%s) VALUES (%s)" % (
                    table, ", ".join("`%s`" % c for c in cols), ", ".join(["%s"] * len(cols))),
                    [data[c] for c in cols])
                rid = data.get(key) if key != "id" else new_id
                self.log("ADD", table, rid, data, func)
                return rid
            if data:
                self.db.exec("UPDATE `%s` SET %s WHERE `%s`=%%s" % (
                    table, ", ".join("`%s`=%%s" % c for c in data), key), list(data.values()) + [row_id])
            self.log("EDIT", table, row_id, data, func)
            return row_id
        except pymysql.MySQLError as e:
            raise BizError(friendly_db_error(e))

    def delete_row(self, table, row_id, func=None, key=None):
        func, key = self._table(table, key)
        self.need(func)
        try:
            self.db.exec("DELETE FROM `%s` WHERE `%s`=%%s" % (table, key), (row_id,))
        except pymysql.MySQLError as e:
            raise BizError(friendly_db_error(e))
        self.log("DEL", table, row_id, None, func)

    # ================================================================ 使用者
    def users(self):
        self.need("SYS", 1)
        return self.db.rows("SELECT u.id, u.user_code, u.user_name, u.is_active, u.last_login_at, "
                            "GROUP_CONCAT(r.role_name ORDER BY r.id SEPARATOR '、') roles, "
                            "GROUP_CONCAT(r.id ORDER BY r.id) role_ids FROM sys_user u "
                            "LEFT JOIN sys_user_role ur ON ur.user_id=u.id LEFT JOIN sys_role r ON r.id=ur.role_id "
                            "GROUP BY u.id ORDER BY u.user_code")

    def roles(self):
        self.need("SYS", 1)
        return self.db.rows("SELECT * FROM sys_role ORDER BY id")

    def save_user(self, uid, code, name, role_ids, active=True, password=None, employee_id=None):
        self.need("SYS")
        if not (code or "").strip() or not (name or "").strip():
            raise BizError("請輸入帳號與姓名")
        if not role_ids:
            raise BizError("請至少勾選一個角色")
        with self.db.transaction():
            if uid:
                self.db.exec("UPDATE sys_user SET user_code=%s, user_name=%s, is_active=%s, employee_id=%s WHERE id=%s",
                             (code.strip(), name.strip(), int(bool(active)), employee_id or None, uid))
            else:
                self._check_pw(password)
                try:
                    uid = self.db.exec("INSERT INTO sys_user (user_code, user_name, password_hash, is_active, employee_id) "
                                       "VALUES (%s,%s,%s,%s,%s)", (code.strip(), name.strip(), passwords.make(password),
                                                                   int(bool(active)), employee_id or None))
                except pymysql.MySQLError as e:
                    raise BizError(friendly_db_error(e))
            if password and uid:
                self._check_pw(password)
                self.db.exec("UPDATE sys_user SET password_hash=%s WHERE id=%s", (passwords.make(password), uid))
            self.db.exec("DELETE FROM sys_user_role WHERE user_id=%s", (uid,))
            self.db.exec_many("INSERT INTO sys_user_role (user_id, role_id) VALUES (%s,%s)", [(uid, r) for r in role_ids])
            if not self.db.value("SELECT COUNT(*) FROM sys_user u JOIN sys_user_role ur ON ur.user_id=u.id "
                                 "JOIN sys_role r ON r.id=ur.role_id WHERE r.role_code='ADMIN' AND u.is_active=1"):
                raise BizError("至少要保留一位啟用中的系統管理員")
        self.log("EDIT", "sys_user", code, {"roles": role_ids}, "SYS")
        return uid

    def role_perms(self, role_id):
        self.need("SYS", 1)
        return {r["func_code"]: 2 if r["can_edit"] else (1 if r["can_view"] else 0)
                for r in self.db.rows("SELECT * FROM sys_role_perm WHERE role_id=%s", (role_id,))}

    def save_role_perms(self, role_id, levels):
        self.need("SYS")
        for f, *_ in FUNCS:
            lvl = int(levels.get(f, 0))
            self.db.exec("REPLACE INTO sys_role_perm (role_id, func_code, can_view, can_add, can_edit, can_delete, "
                         "can_approve, can_print) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                         (role_id, f, int(lvl >= 1), int(lvl >= 2), int(lvl >= 2), int(lvl >= 2), int(lvl >= 2),
                          int(lvl >= 1)))
        self.log("EDIT", "sys_role_perm", role_id, levels, "SYS")
