"""從 1.1.1 的資料庫結構升級：升級敘述不可重建資料表（複製或就地重建都會在最後改名）（Windows 上可能被防毒鎖檔而把表弄壞）。"""
import os
import copy

from mrp.database import DB
from mrp.seed import seed_all

OLD = os.path.join(os.path.dirname(__file__), "fixtures", "schema_1.1.1.sql")


def test_upgrade_from_111_without_table_copy(server):
    st = copy.copy(server)
    st.database = "zms_mrp2_upgrade_test"
    db = DB(st)
    c = db.connect(use_db=False)
    with c.cursor() as cur:
        cur.execute("DROP DATABASE IF EXISTS zms_mrp2_upgrade_test")
        cur.execute("CREATE DATABASE zms_mrp2_upgrade_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    c.close()
    try:
        with open(OLD, encoding="utf-8") as f:
            db.run_script(f.read())
        db.exec("SET FOREIGN_KEY_CHECKS = 1")
        seed_all(db)
        db.exec("UPDATE acc_account_map SET account_no='2171' WHERE map_code='AP'")      # 1.1.1 的預設值
        db.exec("DELETE FROM acc_account_map WHERE map_code='FX_GAIN'")
        db.exec("INSERT IGNORE INTO sys_schema_version (version, app_version, note) VALUES ('1.0.0','1.1.1','測試')")
        db.exec("SET SESSION alter_algorithm = 'NOCOPY'")    # 需要重建（複製或重建再改名）的 ALTER 會直接報錯
        assert db.prepare() is False
        vers = {r["version"] for r in db.rows("SELECT version FROM sys_schema_version")}
        assert {"1.0.0", "1.2.0"} <= vers
        ddl = db.row("SHOW CREATE TABLE acc_voucher_h")["Create Table"]
        assert "batch_id" in ddl and "fk_acc_voucher_h_batch_id" in ddl
        assert db.value("SELECT account_no FROM acc_account_map WHERE map_code='AP'") == "2131"
        assert db.value("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() "
                        "AND column_name='gl_batch_id'") == 4
        per = db.row("SELECT period, start_date FROM acc_period ORDER BY period LIMIT 1")
        db.exec("INSERT INTO acc_voucher_h (voucher_no, voucher_date, period, source_type) VALUES ('RP-1', %s, %s, 'RPT')",
                (per["start_date"], per["period"]))       # 報工類別（RPT）可以寫入
    finally:
        db.close()
