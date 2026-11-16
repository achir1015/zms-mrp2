"""手機連線服務：HTTP 登入、遠端呼叫服務方法、內部方法被拒、Decimal／日期原樣傳回、帳號停用立即生效。"""
import datetime as dt
from decimal import Decimal

import pytest

from mrp.core import BizError


def test_remote_roundtrip(biz):
    from mrp.api import ApiServer
    from mrp.remote import Client, RemoteBooks
    biz.load_demo()
    api = ApiServer(biz.db, port=0, host="127.0.0.1")
    api.start()
    try:
        port = api.httpd.server_address[1]
        c = Client("http://127.0.0.1:%d" % port)
        assert c.ping()["company"] == "範例電子科技股份有限公司"
        rb = RemoteBooks(c)
        with pytest.raises(BizError):
            rb.login("admin", "wrong")
        rb.login("admin", "admin123")
        assert rb.is_admin and rb.can("MRP", 2)
        rows = rb.v("items_list")
        assert len(rows) == 23
        it = rb.v("item", 12)
        assert it["item_code"] == "R-CAP"
        stock = rb.stock("R-CAP")
        assert isinstance(stock[0]["on_hand"], Decimal)
        run = rb.run_mrp(1, dt.date(2026, 11, 16))
        assert rb.v("mrp_pdl_count", run) == 1
        assert [x for x in rb.lookup("countries") if x[0] == "JP"]
        with pytest.raises(BizError):
            rb.post_out("ADJ", "X", 1, 12, 1, 1)          # 內部方法不開放
        with pytest.raises(BizError):
            rb.save_row("sys_user", {"user_name": "x"}, 1)  # 不在白名單
        # 新增一個查詢人員，用手機登入後不能維護
        biz.save_user(None, "viewer", "查詢員", [biz.db.value("SELECT id FROM sys_role WHERE role_code='VIEW'")],
                      True, "view123")
        rv = RemoteBooks(Client("http://127.0.0.1:%d" % port))
        rv.login("viewer", "view123")
        assert rv.v("items_list")
        with pytest.raises(BizError):
            rv.save_row("itm_item", {"item_name": "改名"}, 12)
        with pytest.raises(BizError):
            rv.v("audit")                                  # 系統管理權限
        uid = biz.db.value("SELECT id FROM sys_user WHERE user_code='viewer'")
        biz.db.exec("UPDATE sys_user SET is_active=0 WHERE id=%s", (uid,))
        with pytest.raises(BizError):
            rv.v("items_list")                             # 停用立即生效
    finally:
        api.stop()
