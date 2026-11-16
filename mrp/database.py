"""MariaDB 連線（PyMySQL）、建表與版本升級。

* 建表：mrp/schema.sql（由 db/schema_spec.py 產生）
* 升級：UPGRADES 依版本號列出 SQL；已記錄在 sys_schema_version 的版本不會重跑（系統更新後自動套用）
"""
import os
import threading
from contextlib import contextmanager

import pymysql
import pymysql.cursors

from . import SCHEMA_VERSION
from .settings import Settings

UPGRADES = {
    # 會計拋轉：拋轉批次、來源單據標記；科目對應改成與「資料助秘之一般公司會計」預設科目表一致（使用者沒改過的才更正）
    "1.2.0": [
        "ALTER TABLE acc_voucher_h MODIFY voucher_no VARCHAR(30) NOT NULL COMMENT '傳票參考號（來源單號）'",
        "ALTER TABLE acc_voucher_h ADD COLUMN IF NOT EXISTS batch_id INT NULL COMMENT '所屬拋轉批次' AFTER voucher_no",
        # 升級敘述一律不可重建資料表（複製或就地重建，最後都要把檔案改名；Windows 上曾改名失敗而把表弄壞）：
        # 關閉外鍵檢查時加外鍵只改中繼資料；CHECK 只刪不重建（類別由程式控管，新資料庫仍有新的 CHECK）；
        # 加欄位與加索引要分開下（合在一起會重建）。tests/test_upgrade.py 以 alter_algorithm=NOCOPY 把關
        "SET SESSION foreign_key_checks = 0",
        "ALTER TABLE acc_voucher_h ADD FOREIGN KEY IF NOT EXISTS fk_acc_voucher_h_batch_id (batch_id) REFERENCES acc_gl_batch (id)",
        "SET SESSION foreign_key_checks = 1",
        "ALTER TABLE acc_voucher_h DROP CONSTRAINT IF EXISTS ck_acc_voucher_h_1",
        "ALTER TABLE pur_receipt_h ADD COLUMN IF NOT EXISTS gl_batch_id INT NULL COMMENT '會計拋轉批次（空白＝尚未拋轉）'",
        "ALTER TABLE pur_receipt_h ADD INDEX IF NOT EXISTS ix_pur_receipt_h_gl (gl_batch_id)",
        "ALTER TABLE sal_ship_h ADD COLUMN IF NOT EXISTS gl_batch_id INT NULL COMMENT '會計拋轉批次（空白＝尚未拋轉）'",
        "ALTER TABLE sal_ship_h ADD INDEX IF NOT EXISTS ix_sal_ship_h_gl (gl_batch_id)",
        "ALTER TABLE inv_txn ADD COLUMN IF NOT EXISTS gl_batch_id INT NULL COMMENT '會計拋轉批次（空白＝尚未拋轉）'",
        "ALTER TABLE inv_txn ADD INDEX IF NOT EXISTS ix_inv_txn_gl (gl_batch_id)",
        "ALTER TABLE sfc_report ADD COLUMN IF NOT EXISTS gl_batch_id INT NULL COMMENT '會計拋轉批次（空白＝尚未拋轉）'",
        "ALTER TABLE sfc_report ADD INDEX IF NOT EXISTS ix_sfc_report_gl (gl_batch_id)",
        "UPDATE acc_account_map SET account_no='1212', account_name='原料' WHERE map_code='INV_RAW' AND account_no='1231'",
        "UPDATE acc_account_map SET account_no='1213', account_name='在製品' WHERE map_code='INV_WIP' AND account_no='1232'",
        "UPDATE acc_account_map SET account_no='1214', account_name='製成品' WHERE map_code='INV_FG' AND account_no='1233'",
        "UPDATE acc_account_map SET account_no='1161', account_name='進項稅額' WHERE map_code='VAT_IN' AND account_no='1268'",
        "UPDATE acc_account_map SET account_no='2131', account_name='應付帳款' WHERE map_code='AP' AND account_no='2171'",
        "UPDATE acc_account_map SET account_no='1141', account_name='應收帳款' WHERE map_code='AR' AND account_no='1191'",
        "UPDATE acc_account_map SET account_no='2161', account_name='銷項稅額' WHERE map_code='VAT_OUT' AND account_no='2204'",
        "UPDATE acc_account_map SET account_no='5122', account_name='已分攤直接人工' WHERE map_code='LABOR_APPLIED' AND account_no='5121'",
        "UPDATE acc_account_map SET account_no='5123', account_name='已分攤製造費用' WHERE map_code='OH_APPLIED' AND account_no='5131'",
        "UPDATE acc_account_map SET account_no='5118', account_name='採購價格差異' WHERE map_code='PPV' AND account_no='5141'",
        "UPDATE acc_account_map SET account_no='5119', account_name='材料用量差異' WHERE map_code='MUV' AND account_no='5142'",
        "UPDATE acc_account_map SET account_no='5116', account_name='存貨報廢損失' WHERE map_code='SCRAP' AND account_no='5143'",
        "UPDATE acc_account_map SET account_no='5115', account_name='存貨盤盈虧' WHERE map_code='INV_ADJ' AND account_no='5144'",
        "UPDATE acc_account_map SET account_no='7221', account_name='兌換損失' WHERE map_code='FXV' AND account_no='7151'",
        "INSERT IGNORE INTO acc_account_map (map_code, map_name, account_no, account_name) VALUES ('FX_GAIN', '兌換利益', '7131', '兌換利益')",
    ],
}


def _ver(s):
    return tuple(int(x) for x in s.split("."))


class DB:
    def __init__(self, st: Settings):
        self.st = st
        self._tl = threading.local()

    def connect(self, use_db=True):
        return pymysql.connect(host=self.st.host, port=int(self.st.port), user=self.st.user,
                               password=self.st.password, database=self.st.database if use_db else None,
                               charset="utf8mb4", autocommit=True, connect_timeout=8,
                               cursorclass=pymysql.cursors.DictCursor)

    @property
    def conn(self):
        c = getattr(self._tl, "c", None)
        if c is not None:
            try:
                c.ping(reconnect=False)
                return c
            except Exception:
                pass
        c = self.connect()
        self._tl.c = c
        return c

    def close(self):
        c = getattr(self._tl, "c", None)
        if c is not None:
            try:
                c.close()
            except Exception:
                pass
            self._tl.c = None

    def rows(self, sql, args=None):
        with self.conn.cursor() as cur:
            cur.execute(sql, args)
            return list(cur.fetchall())

    def row(self, sql, args=None):
        with self.conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchone()

    def value(self, sql, args=None):
        r = self.row(sql, args)
        return None if r is None else next(iter(r.values()))

    def exec(self, sql, args=None):
        with self.conn.cursor() as cur:
            n = cur.execute(sql, args)
            return cur.lastrowid if sql.lstrip()[:6].upper() in ("INSERT", "REPLAC") else n

    def exec_many(self, sql, seq):
        seq = list(seq)
        if not seq:
            return 0
        with self.conn.cursor() as cur:
            return cur.executemany(sql, seq)

    @contextmanager
    def transaction(self):
        c = self.conn
        if getattr(self._tl, "depth", 0):          # 巢狀：併入外層交易
            self._tl.depth += 1
            try:
                yield
            finally:
                self._tl.depth -= 1
            return
        self._tl.depth = 1
        c.begin()
        try:
            yield
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            self._tl.depth = 0

    # ------------------------------------------------------------ 建立／升級
    def run_script(self, text):
        for stmt in split_sql(text):
            self.exec(stmt)

    def prepare(self):
        """建立資料庫與資料表；第一次使用時寫入預設資料；依版本套用升級。回傳 True＝全新資料庫。"""
        c = self.connect(use_db=False)
        try:
            with c.cursor() as cur:
                cur.execute("CREATE DATABASE IF NOT EXISTS `%s` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                            % self.st.database.replace("`", ""))
        finally:
            c.close()
        fresh = not self.value("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s "
                               "AND table_name='sys_function'", (self.st.database,))
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "schema.sql"), encoding="utf-8") as f:
            self.run_script(f.read())
        self.exec("SET FOREIGN_KEY_CHECKS = 1")
        done = {r["version"] for r in self.rows("SELECT version FROM sys_schema_version")}
        if fresh or not self.value("SELECT COUNT(*) FROM sys_function"):
            from .seed import seed_all
            seed_all(self)
        for v in sorted(UPGRADES, key=_ver):
            if v not in done:
                for stmt in UPGRADES[v]:
                    self.exec(stmt)
                self.exec("INSERT INTO sys_schema_version (version, app_version, note) VALUES (%s, %s, '自動升級')",
                          (v, SCHEMA_VERSION))
        return fresh


def split_sql(text):
    """把腳本切成單一敘述（略過註解行；支援 DELIMITER //）。"""
    out, buf, delim = [], [], ";"
    for line in text.splitlines():
        s = line.strip()
        if s.upper().startswith("DELIMITER "):
            delim = s.split()[1]
            continue
        if not buf and (not s or s.startswith("--")):
            continue
        buf.append(line)
        if "--" in s and "'" not in s.split("--", 1)[1]:     # 行尾註解：判斷結尾分號前先去掉
            s = s.split(" --", 1)[0].rstrip() if " --" in s else s
        if s.endswith(delim):
            if buf[-1].strip() != s:
                buf[-1] = buf[-1][: buf[-1].index(s) + len(s)]
            stmt = "\n".join(buf).rstrip()
            out.append(stmt[: -len(delim)].rstrip())
            buf = []
    if buf and "".join(buf).strip():
        out.append("\n".join(buf))
    return out


def explain_error(e) -> str:
    s = str(e.args[1] if len(getattr(e, "args", ())) > 1 else e)
    if "auth_gssapi" in s:
        return ("帳號或密碼錯誤（Windows 版 MariaDB 密碼不對時會改用 Windows 驗證）。"
                "請建立專用帳號：CREATE USER 'mrp'@'localhost' IDENTIFIED BY '密碼'; "
                "GRANT ALL ON zms_mrp2.* TO 'mrp'@'localhost';")
    if "Access denied" in s:
        return "帳號或密碼錯誤：" + s
    if "Can't connect" in s or "10061" in s or "timed out" in s:
        return "伺服器沒有回應，請確認 MariaDB 已啟動、位址與連接埠正確：" + s
    return s


def try_connect(host, port, user, password, database):
    try:
        c = pymysql.connect(host=host, port=int(port), user=user, password=password, connect_timeout=5)
    except Exception as e:
        return False, explain_error(e)
    try:
        with c.cursor() as cur:
            cur.execute("SELECT VERSION()")
            ver = cur.fetchone()[0]
            cur.execute("SHOW DATABASES LIKE %s", (database,))
            has = cur.fetchone() is not None
        return True, "連線成功（MariaDB %s），資料庫 %s %s" % (ver, database, "已存在" if has else "不存在，儲存後自動建立")
    finally:
        c.close()
