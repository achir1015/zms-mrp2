"""開發用：依序開啟各畫面並截圖（網頁預覽需以 MRP_DEV_LOGIN 啟動）。

用法：python tools/shots_all.py 輸出資料夾 [畫面代號…]
"""
import base64
import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = os.environ.get("SHOT_BASE", "http://127.0.0.1:8590/")
ALL = ["home", "items", "bom", "routings", "so", "po", "mps", "mrp_run", "planned", "crp", "wo", "stock", "inv_ops", "cost",
       "currencies", "sources", "users", "help", "demo"]


def main():
    out = sys.argv[1]
    routes = sys.argv[2:] or ALL
    os.makedirs(out, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        for r in routes:
            pg = b.new_page(viewport={"width": int(os.environ.get("SHOT_W", 1500)), "height": int(os.environ.get("SHOT_H", 920))})
            pg.goto(BASE + r)
            time.sleep(float(os.environ.get("SHOT_WAIT", 10)))
            data = pg.context.new_cdp_session(pg).send("Page.captureScreenshot", {"format": "png"})["data"]
            with open(os.path.join(out, r + ".png"), "wb") as f:
                f.write(base64.b64decode(data))
            print("shot", r)
            pg.close()
        b.close()


if __name__ == "__main__":
    main()
