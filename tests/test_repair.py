"""1.2.0 升級失敗留下的半壞傳票表：啟動時自動修復，再升級到最新版。

三種狀態（Windows 筆電實際遇過 A 與 B）：
A：.frm 不見、.ibd 與 InnoDB 字典還在 → CREATE 報 1050「already exists」
B：只剩 .frm、字典沒有 → 1932「doesn't exist in engine」
C：只剩 .ibd 孤兒、字典沒有 → CREATE 報 errno 184「Tablespace already exists」
"""
import copy
import os
import shutil

import pytest

from mrp.database import DB
from mrp.seed import seed_all

OLD = os.path.join(os.path.dirname(__file__), "fixtures", "schema_1.1.1.sql")
NAME = "zms_mrp2_repair_test"


def old_db(server):
    st = copy.copy(server)
    st.database = NAME
    db = DB(st)
    c = db.connect(use_db=False)
    with c.cursor() as cur:
        cur.execute("DROP DATABASE IF EXISTS `%s`" % NAME)
        cur.execute("CREATE DATABASE `%s` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci" % NAME)
    c.close()
    with open(OLD, encoding="utf-8") as f:
        db.run_script(f.read())
    db.exec("SET FOREIGN_KEY_CHECKS = 1")
    seed_all(db)
    db.exec("INSERT IGNORE INTO sys_schema_version (version, app_version, note) VALUES ('1.0.0','1.1.1','測試')")
    db.exec("FLUSH TABLES")
    return st, db, os.path.join(st.datadir, NAME)


def keep_only(db, d, keep):
    """把 acc_voucher_h 弄成只剩 keep 這個副檔名的檔案（字典裡沒有這個表）。"""
    src = os.path.join(d, "acc_voucher_h" + keep)
    tmp = src + ".keep"
    shutil.copy2(src, tmp)
    db.exec("SET SESSION foreign_key_checks = 0")
    db.exec("DROP TABLE acc_voucher_h")
    db.exec("SET SESSION foreign_key_checks = 1")
    os.replace(tmp, src)


@pytest.mark.parametrize("state", ["A", "B", "C"])
def test_repair_half_broken_voucher_table(server, state):
    st, db, d = old_db(server)
    try:
        if state == "A":
            os.remove(os.path.join(d, "acc_voucher_h.frm"))
        else:
            keep_only(db, d, ".frm" if state == "B" else ".ibd")
        db.close()
        broken = db._errno("SELECT 1 FROM acc_voucher_h LIMIT 0")
        assert broken in (1146, 1932)
        assert db.prepare() is False                       # 修復後照常升級
        assert {"1.0.0", "1.2.0"} <= {r["version"] for r in db.rows("SELECT version FROM sys_schema_version")}
        ddl = db.row("SHOW CREATE TABLE acc_voucher_h")["Create Table"]
        assert "batch_id" in ddl
        per = db.row("SELECT period, start_date FROM acc_period ORDER BY period LIMIT 1")
        db.exec("INSERT INTO acc_voucher_h (voucher_no, voucher_date, period, source_type) VALUES ('RP-1', %s, %s, 'RPT')",
                (per["start_date"], per["period"]))
        backup = os.path.join(os.path.dirname(st.datadir), "orphan-backup")
        assert any(f.startswith(NAME) and "acc_voucher_h" in f for f in os.listdir(backup))
        assert db.prepare() is False                       # 再開一次：沒有東西要修
        assert db.repair_broken_tables() == []
    finally:
        db.close()
