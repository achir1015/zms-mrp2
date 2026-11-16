"""網頁預覽（開發測試用）：http://127.0.0.1:8590，資料放在專案 data/（與安裝版分開）。"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)
os.environ.setdefault("MRP_WEB_PORT", "8590")
os.environ.setdefault("FLET_FORCE_WEB_SERVER", "true")
runpy.run_path(os.path.join(HERE, "main.py"), run_name="__main__")
