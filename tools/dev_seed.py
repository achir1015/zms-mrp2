"""開發用：在專案 data/ 的資料庫建立管理員（admin／admin123）並載入電子業範例。

用法：.venv\\Scripts\\python tools\\dev_seed.py [--reset]
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from mrp.biz import Biz  # noqa: E402
from mrp.database import DB  # noqa: E402
from mrp.dbserver import LocalDatabaseServer  # noqa: E402
from mrp.settings import Settings  # noqa: E402

st = Settings.load()
srv = LocalDatabaseServer(st)
srv.start()
db = DB(st)
if "--reset" in sys.argv:
    c = db.connect(use_db=False)
    with c.cursor() as cur:
        cur.execute("DROP DATABASE IF EXISTS `%s`" % st.database)
    c.close()
db.prepare()
st.save()
b = Biz(db)
if not b.has_users():
    b.create_first_admin("admin", "系統管理員", "admin123")
b.login("admin", "admin123")
if not b.has_business_data():
    b.load_demo()
    print("demo loaded")
print("ok", st.port)
srv.proc = None   # 不關閉（網頁預覽還要用）
