"""開發用：手機版網頁預覽（http://127.0.0.1:8591），連到本機的手機連線服務（python main.py --server）。"""
import os
import runpy
import sys

here = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("MRP_WEB_PORT", "8591")
os.environ.setdefault("FLET_FORCE_WEB_SERVER", "true")
os.environ.setdefault("MRP_MOBILE", "1")
os.environ.setdefault("MRP_DATA_DIR", os.path.join(here, "data_mobile"))
os.environ.setdefault("MRP_DEV_SERVER", "http://127.0.0.1:8795")
os.environ.setdefault("MRP_DEV_LOGIN", "admin:admin123")
os.chdir(here)
sys.path.insert(0, here)
runpy.run_path(os.path.join(here, "main.py"), run_name="__main__")
