"""測試用資料庫：在 tests/_db 啟動一份獨立的內建 MariaDB（埠自動找空的），每個測試模組重建資料庫。"""
import os
import shutil
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
os.environ["MRP_DATA_DIR"] = os.path.join(HERE, "tests", "_db")


@pytest.fixture(scope="session")
def server():
    from mrp.dbserver import LocalDatabaseServer, listening
    from mrp.settings import Settings
    st = Settings.load()
    st.database = "zms_mrp2_test"
    p = 3420
    while listening("127.0.0.1", p):
        p += 1
    st.port = p
    st.save()
    srv = LocalDatabaseServer(st)
    srv.start()
    yield st
    srv.stop()


@pytest.fixture()
def biz(server):
    from mrp.biz import Biz
    from mrp.database import DB
    db = DB(server)
    c = db.connect(use_db=False)
    with c.cursor() as cur:
        cur.execute("DROP DATABASE IF EXISTS zms_mrp2_test")
    c.close()
    db.prepare()
    b = Biz(db)
    b.create_first_admin("admin", "測試管理員", "admin123")
    b.login("admin", "admin123")
    yield b
    db.close()


def pytest_sessionfinish(session, exitstatus):
    pass


_ = shutil
