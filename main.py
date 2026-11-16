"""資料助秘之物料需求II生產製造系統 — 程式進入點。

桌面版：python main.py
網頁預覽（測試用）：設定環境變數 MRP_WEB_PORT=8590 後執行 python main.py（http://127.0.0.1:8590）
"""
import os
import sys

import flet as ft

from mrp.settings import resource_dir
from mrp.ui.shell import main

if __name__ == "__main__":
    if getattr(sys, "frozen", False) and os.name == "nt":
        try:   # 工作列顯示本程式的圖示（而不是 Python／Flet 的）
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ZMS.MRP2")
        except Exception:
            pass
    assets = os.path.join(resource_dir(), "assets")
    port = os.environ.get("MRP_WEB_PORT")
    if port:
        ft.run(main, view=None, port=int(port), host="127.0.0.1", assets_dir=assets)
    else:
        ft.run(main, assets_dir=assets)
