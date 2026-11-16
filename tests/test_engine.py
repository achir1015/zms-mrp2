"""引擎測試：電子業範例 → MPS → MRP → 轉單 → 工單發放／先進先出領料／完工 → 外幣進貨 → 出貨。"""
import datetime as dt
from decimal import Decimal as D

import pytest

from mrp.core import BizError


def rec(b, run, code):
    return [r for r in b.mrp_records(run) if r["item_code"] == code]


def item(b, code):
    return b.db.value("SELECT id FROM itm_item WHERE item_code=%s", (code,))


def test_seed_and_comments(biz):
    assert biz.db.value("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='zms_mrp2_test'") == 95
    assert biz.db.value("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='zms_mrp2_test' "
                        "AND column_comment=''") == 0
    assert biz.db.value("SELECT COUNT(*) FROM sys_function") == 14
    assert biz.next_no("PO", dt.date(2026, 11, 16)) == "PO2026110001"
    assert biz.next_no("PO", dt.date(2026, 11, 20)) == "PO2026110002"
    assert biz.rate_on("USD") > 30


def test_mrp_electronics(biz):
    biz.load_demo()
    run = biz.run_mrp(1, "2026-11-16")
    mb = rec(biz, run, "F-MB-A1")[0]
    assert (mb["net_req"], mb["planned_receipt"], mb["release_date"]) == (D(290), D(290), dt.date(2026, 12, 16))
    pcb = rec(biz, run, "R-PCB-MB")[0]
    assert pcb["net_req"] == 220 and pcb["planned_receipt"] == 250          # 淘汰 Rev A 不計、50 倍數
    chip = rec(biz, run, "R-CHIPSET")[0]
    assert chip["net_req"] == 30                                            # 待驗倉不計、美元在途 150
    cap = rec(biz, run, "R-CAP")
    assert [r["gross_req"] for r in cap] == [D(940), D(690), D("3151.5152")]
    assert all(r["planned_receipt"] == 0 for r in cap)
    usb = rec(biz, run, "R-USBA")
    assert usb[0]["net_req"] == 480 and usb[0]["planned_receipt"] == 500    # 在途 11/28 建議提前到 11/27
    ex = {(e["item_code"], e["msg_type"]) for e in biz.exceptions(run)}
    assert ("R-HUBIC", "PDL") in ex and ("R-USBA", "EXP") in ex
    po = [p for p in biz.planned_orders(run) if p["item_code"] == "R-CAP"]
    assert po == []
    # 電源 PCBA 的電容指定日製 → 需求追溯
    peg = biz.pegging(run, item(biz, "R-CAP"))
    assert {p["parent_code"] for p in peg} == {"S-PCBA-HUB", "S-PCBA-PSU", "S-PCBA-MB"}
    crp = biz.run_crp(run)
    assert biz.crp_load(crp)


def test_convert_release_issue_complete(biz):
    biz.load_demo()
    run = biz.run_mrp(1, "2026-11-16")
    pcba_psu = [p for p in biz.planned_orders(run) if p["item_code"] == "S-PCBA-PSU"][0]
    hub = [p for p in biz.planned_orders(run) if p["item_code"] == "R-HUBIC"][0]
    made = biz.convert_planned([pcba_psu["id"], hub["id"]])
    assert any(m.startswith("WO") for m in made) and any(m.startswith("PO") for m in made)
    wo = biz.db.row("SELECT * FROM sfc_work_order WHERE planned_order_id=%s", (pcba_psu["id"],))
    notes = biz.release_wo(wo["id"])
    assert any("JP" in n for n in notes)                                   # 日製電容已保留
    cap_m = biz.db.row("SELECT * FROM sfc_wo_material WHERE wo_id=%s AND item_id=%s", (wo["id"], item(biz, "R-CAP")))
    assert cap_m["required_country"] == "JP" and cap_m["required_qty"] == wo["plan_qty"] * 6
    with pytest.raises(BizError):                                         # 電源 PCB 還沒進貨 → 擋下
        biz.issue_wo(wo["id"])
    no, used = biz.issue_wo(wo["id"], [dict(wo_material_id=cap_m["id"], qty=cap_m["required_qty"])])
    caps = [u for u in used if u[0] == item(biz, "R-CAP")]
    assert caps and all(u[2] == "JP" for u in caps)                       # 只領日製
    op = biz.db.row("SELECT id FROM sfc_wo_operation WHERE wo_id=%s ORDER BY op_seq LIMIT 1", (wo["id"],))
    biz.report_op(op["id"], wo["plan_qty"], 0, 1.5, 2.0, employee_id=4)
    cno, unit = biz.complete_wo(wo["id"], wo["plan_qty"])
    assert unit > 0
    assert biz.db.value("SELECT status FROM sfc_work_order WHERE id=%s", (wo["id"],)) == "F"


def test_fifo_and_fx(biz):
    biz.load_demo()
    cap, rm = item(biz, "R-CAP"), 1
    # 主機板試產領 3500：日製批 3000 中 300 保留給電源工單 → 日製 2700 + 台製 800
    cost, used = biz.post_out("ADJ", "T1", 1, cap, rm, 3500)
    assert [(u[1], u[2]) for u in used] == [("JP", D(2700)), ("TW", D(800))]
    assert cost == D("8460.00")
    with pytest.raises(BizError):
        biz.post_out("ADJ", "T2", 1, cap, rm, 999999)
    # 日圓採購進貨：進貨日匯率換算新台幣成本
    biz.set_doc_status("PO", 1, "A") if biz.db.value("SELECT status FROM pur_order_h WHERE id=1") == "D" else None
    line = biz.db.row("SELECT * FROM pur_order_d WHERE po_id=1")
    no = biz.receive_po(1, [dict(po_line_id=line["id"], accept_qty=2000, lot_no="CAP-JP-2647", date_code="2645",
                                 origin_country="JP")], "2026-11-16")
    lay = biz.db.row("SELECT * FROM inv_layer l JOIN inv_txn x ON x.id=l.in_txn_id WHERE x.doc_no=%s", (no,))
    assert lay["unit_cost"] == D("2.544000")                              # ¥12 × 0.2120
    assert biz.db.value("SELECT COUNT(*) FROM acc_variance WHERE variance_type='FXV' AND ref_doc_no=%s", (no,)) == 1
    assert biz.db.value("SELECT status FROM pur_order_h WHERE id=1") == "C"


def test_ship_and_transfer(biz):
    biz.load_demo()
    hub = item(biz, "F-HUB-4P")
    no = biz.ship_so(3, [dict(so_line_id=3, qty=30)], "2026-11-16")
    assert biz.db.value("SELECT shipped_qty FROM sal_order_d WHERE id=3") == 30
    with pytest.raises(BizError):
        biz.ship_so(3, [dict(so_line_id=3, qty=30)], "2026-11-16")           # 只剩 20
    t = biz.transfer_stock(item(biz, "R-FAN"), 1, 4, 10)
    assert biz.db.value("SELECT SUM(on_hand_qty) FROM inv_balance WHERE item_id=%s AND warehouse_id=4",
                        (item(biz, "R-FAN"),)) == 10
    assert no and t and hub


def test_generate_mps_and_cost(biz):
    biz.load_demo()
    mid = biz.generate_mps("2026-11-16", 60)
    lines = biz.db.rows("SELECT * FROM mps_plan_d WHERE mps_id=%s", (mid,))
    assert {(l["item_id"], l["mps_qty"]) for l in lines} == {(1, 300), (2, 200), (3, 500)}
    n = biz.roll_up_cost("202611")
    assert n == 23
    mb = biz.db.row("SELECT * FROM acc_item_cost WHERE item_id=1 AND cost_type='S'")
    assert mb["material_cost"] > 1000 and mb["labor_cost"] > 0
