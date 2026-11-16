"""會計拋轉：MRP II 交易產生的傳票批次借貸平衡、存貨科目與存貨異動帳一致，並實際匯入「資料助秘之一般公司會計」。"""
import datetime as dt
import json
import os
import sys
from decimal import Decimal as D

import pytest

ACCT = os.environ.get("ZMS_ACCT_SRC", r"E:\財務會計幫幫忙\zms-accounting")
DAY = dt.date(2026, 11, 16)


def item(b, code):
    return b.db.value("SELECT id FROM itm_item WHERE item_code=%s", (code,))


def make_transactions(b):
    """進貨（日圓）、工單發放／領料／報工／完工、出貨、報廢調整。"""
    b.load_demo()
    line = b.db.row("SELECT * FROM pur_order_d WHERE po_id=1")
    b.receive_po(1, [dict(po_line_id=line["id"], accept_qty=2000, lot_no="CAP-JP-2647", origin_country="JP")], DAY)
    run = b.run_mrp(1, DAY)
    po = [p for p in b.planned_orders(run) if p["item_code"] == "S-PCBA-PSU"][0]
    b.convert_planned([po["id"]])
    wo = b.db.row("SELECT * FROM sfc_work_order WHERE planned_order_id=%s", (po["id"],))
    b.release_wo(wo["id"])
    cap = b.db.row("SELECT * FROM sfc_wo_material WHERE wo_id=%s AND item_id=%s", (wo["id"], item(b, "R-CAP")))
    b.issue_wo(wo["id"], [dict(wo_material_id=cap["id"], qty=cap["required_qty"])], DAY)
    op = b.db.row("SELECT id FROM sfc_wo_operation WHERE wo_id=%s ORDER BY op_seq LIMIT 1", (wo["id"],))
    b.report_op(op["id"], 20, 0, 1.5, 3.0, employee_id=4, start=dt.datetime(2026, 11, 16, 9))
    b.complete_wo(wo["id"], 20, DAY)                     # 半成品：借貸都在在製品 → 不產生傳票
    no = b.create_work_order(item(b, "F-MB-A1"), 2, DAY, DAY)  # 成品：主機板 2 片，領料後完工 → 借 製成品／貸 在製品
    fg = b.db.value("SELECT id FROM sfc_work_order WHERE wo_no=%s", (no,))
    b.release_wo(fg)
    b.issue_wo(fg, None, DAY)
    b.complete_wo(fg, 2, DAY)
    b.set_doc_status("SO", 1, "A") if b.db.value("SELECT status FROM sal_order_h WHERE id=1") == "D" else None
    b.ship_so(3, [dict(so_line_id=3, qty=30)], DAY)      # 集線器 30 個（新台幣，外加 5%）
    b.adjust_stock(item(b, "R-FAN"), 1, -2, "S", note="損壞報廢", when=DAY)
    return wo


def test_gl_batch_balanced_and_matches_stock(biz):
    b = biz
    make_transactions(b)
    pend = b.gl_pending(DAY, DAY)
    assert pend["PUR"] == 1 and pend["SHP"] == 1 and pend["ISS"] == 2 and pend["RPT"] == 1 and pend["ADJ"] == 1
    vouchers, sources = b.gl_preview(DAY, DAY)
    assert {v["src"] for v in vouchers} == {"PUR", "ISS", "RPT", "CMP", "SHP", "ADJ"}
    for v in vouchers:
        assert sum(x["debit"] for x in v["lines"]) == sum(x["credit"] for x in v["lines"]) == v["total"], v["ref"]
    bid = b.create_gl_batch(DAY, DAY)
    assert all(n == 0 for n in b.gl_pending(DAY, DAY).values())          # 全部標記為已拋轉（含不需傳票的半成品完工）
    with pytest.raises(Exception, match="沒有尚未拋轉"):
        b.create_gl_batch(DAY, DAY)
    # 原料科目的變動＝存貨異動帳中原料／包材的進出（期初、調撥不拋轉）
    raw = b.db.value("SELECT SUM(d.dr_amount-d.cr_amount) FROM acc_voucher_d d JOIN acc_voucher_h h ON h.id=d.voucher_id "
                     "WHERE h.batch_id=%s AND d.account_no='1212'", (bid,))
    sub = b.db.value("SELECT SUM(x.amount) FROM inv_txn x JOIN itm_item i ON i.id=x.item_id WHERE x.gl_batch_id=%s "
                     "AND i.item_type IN ('R','P')", (bid,))
    assert raw == sub
    # 出貨：應收＝未稅 × 1.05
    ship = b.db.row("SELECT * FROM sal_ship_h WHERE ship_no IN (SELECT voucher_no FROM acc_voucher_h WHERE batch_id=%s)", (bid,))
    ar = b.db.value("SELECT d.dr_amount FROM acc_voucher_d d JOIN acc_voucher_h h ON h.id=d.voucher_id WHERE h.batch_id=%s "
                    "AND d.account_no='1141'", (bid,))
    assert ar == (D(ship["base_untaxed_amount"]) * D("1.05")).quantize(D("0.01"))
    # 取消拋轉 → 全部回到待拋轉
    b.cancel_gl_batch(bid)
    assert b.gl_pending(DAY, DAY)["PUR"] == 1
    assert b.db.value("SELECT COUNT(*) FROM acc_voucher_h WHERE batch_id=%s", (bid,)) == 0


@pytest.mark.skipif(not os.path.isdir(os.path.join(ACCT, "acct")), reason="沒有會計系統原始碼")
def test_batch_imports_into_accounting(biz, server):
    sys.path.insert(0, ACCT)
    from acct.books import Books
    from acct.database import DB as ADB
    from acct.settings import Settings as ASettings
    st = ASettings(port=server.port, password=server.password, database="mrp_acct_link_test",
                   mariadb_bin=server.mariadb_bin, datadir=server.datadir)
    d = ADB(st)
    c = d.connect(use_db=False)
    with c.cursor() as cur:
        cur.execute("DROP DATABASE IF EXISTS mrp_acct_link_test")
    c.close()
    d.prepare()
    a = Books(d)
    a.create_first_admin("admin", "會計", "admin123")
    a.login("admin", "admin123")
    a.save_company(name="範例電子科技股份有限公司", tax_id="12345675", owner="", phone="", address="",
                   fiscal_start_month=1, auto_post=0, separate_approver=0)
    try:
        b = biz
        make_transactions(b)
        bid = b.create_gl_batch(DAY, DAY)
        batch = json.loads(json.dumps(b.gl_batch(bid)["data"]))
        pv = a.preview_gl_batch(batch)
        assert pv["count"] == len(batch["vouchers"])
        res = a.import_gl_batch(batch)
        assert res["count"] == len(batch["vouchers"])
        td, tc = a.db.row("SELECT SUM(debit) d, SUM(credit) c FROM voucher_lines").values()
        assert td == tc
        # 會計系統沒有的明細科目自動建立；客戶、廠商自動建立
        for code in ("5122", "5123"):
            assert a.db.value("SELECT 1 FROM accounts WHERE code=%s", (code,))
        assert a.db.value("SELECT 1 FROM partners WHERE kind='C' AND code='C003'")
        assert a.db.value("SELECT 1 FROM partners WHERE kind='V' AND code='S002'")
        mine = b.db.value("SELECT SUM(d.dr_amount) FROM acc_voucher_d d JOIN acc_voucher_h h ON h.id=d.voucher_id "
                          "WHERE h.batch_id=%s", (bid,))
        assert td == mine
        with pytest.raises(Exception, match="已在"):
            a.import_gl_batch(batch)                     # 不重複匯入
    finally:
        d.close()
