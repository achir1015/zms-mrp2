"""具名查詢：畫面需要的唯讀查詢都登記在這裡，透過 Biz.v(名稱, 參數…) 執行。

手機版經由電腦的連線服務呼叫同一個方法，所以手機只能執行這裡登記過的 SQL（不能送任意 SQL），
每個查詢也都綁定模組權限（查詢等級）。
(權限模組, 回傳型態 rows／row／value, SQL)
"""

VIEWS = {
    # ---------------------------------------------------------------- 共用
    "item": ("", "row", "SELECT * FROM itm_item WHERE id=%s"),
    "item_stock": ("", "value", "SELECT COALESCE(SUM(on_hand_qty),0) FROM inv_balance WHERE item_id=%s"),
    "wh_by_code": ("", "value", "SELECT id FROM bas_warehouse WHERE wh_code=%s"),
    "supplier_currency": ("", "value", "SELECT currency_code FROM pur_supplier WHERE id=%s"),
    "customer_currency": ("", "value", "SELECT currency_code FROM sal_customer WHERE id=%s"),
    "item_current_rev": ("", "value", "SELECT current_rev_id FROM itm_item WHERE id=%s"),
    # ---------------------------------------------------------------- 系統
    "params": ("SYS", "rows", "SELECT * FROM sys_param ORDER BY param_key"),
    "audit": ("SYS", "rows",
              "SELECT a.created_at, u.user_name, a.action, a.table_name, a.record_key, a.func_code FROM sys_audit_log a "
              "LEFT JOIN sys_user u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 800"),
    # ---------------------------------------------------------------- 料件
    "items_list": ("ITM", "rows",
                   "SELECT i.*, IF(i.source_type='M','自製',IF(i.source_type='O','委外','採購')) source, i.low_level_code llc, "
                   "r.rev_code rev, p.lead_time_days, p.lot_rule FROM itm_item i LEFT JOIN itm_revision r ON "
                   "r.id=i.current_rev_id LEFT JOIN itm_plan p ON p.item_id=i.id ORDER BY i.item_code"),
    "item_plan": ("ITM", "row", "SELECT * FROM itm_plan WHERE item_id=%s"),
    "item_revisions": ("ITM", "rows",
                       "SELECT r.*, p.rev_code prev_code, IF(r.id=i.current_rev_id,'★','') cur FROM itm_revision r "
                       "JOIN itm_item i ON i.id=r.item_id LEFT JOIN itm_revision p ON p.id=r.prev_rev_id "
                       "WHERE r.item_id=%s ORDER BY r.rev_code"),
    "item_aml": ("ITM", "rows",
                 "SELECT a.*, m.mfr_name, c.origin_label, r.rev_code FROM itm_mfr_part a JOIN bas_manufacturer m ON "
                 "m.id=a.manufacturer_id LEFT JOIN bas_country c ON c.country_code=a.origin_country LEFT JOIN itm_revision r "
                 "ON r.id=a.rev_id WHERE a.item_id=%s ORDER BY a.priority"),
    "item_sources": ("ITM", "rows",
                     "SELECT s.*, p.sup_name, a.mfr_part_no, c.origin_label FROM pur_item_source s JOIN pur_supplier p ON "
                     "p.id=s.supplier_id LEFT JOIN itm_mfr_part a ON a.id=s.mfr_part_id LEFT JOIN bas_country c ON "
                     "c.country_code=s.origin_country WHERE s.item_id=%s ORDER BY s.priority"),
    # ---------------------------------------------------------------- BOM、途程
    "bom_parents": ("BOM", "rows",
                    "SELECT i.id, i.item_code, i.item_name, h.bom_ver ver, h.status st FROM itm_item i LEFT JOIN bom_header h "
                    "ON h.parent_item_id=i.id AND h.is_default=1 WHERE i.source_type<>'P' AND i.is_active=1 ORDER BY i.item_code"),
    "bom_head_of": ("BOM", "row",
                    "SELECT * FROM bom_header WHERE parent_item_id=%s ORDER BY is_default DESC, id DESC LIMIT 1"),
    "bom_lines": ("BOM", "rows", "SELECT * FROM bom_detail WHERE bom_id=%s ORDER BY line_no"),
    "bom_where_used": ("BOM", "rows",
                       "SELECT i.item_code, i.item_name, h.bom_ver, d.qty_per, h.status FROM bom_detail d JOIN bom_header h "
                       "ON h.id=d.bom_id JOIN itm_item i ON i.id=h.parent_item_id WHERE d.child_item_id=%s ORDER BY i.item_code"),
    "bom_children": ("BOM", "rows",
                     "SELECT d.*, h.base_qty, i.item_code, i.item_name, i.source_type FROM bom_header h JOIN bom_detail d ON "
                     "d.bom_id=h.id JOIN itm_item i ON i.id=d.child_item_id WHERE h.parent_item_id=%s AND h.is_default=1 "
                     "ORDER BY d.line_no"),
    "rou_parents": ("ROU", "rows",
                    "SELECT i.id, i.item_code, i.item_name, h.routing_ver ver, h.status st FROM itm_item i LEFT JOIN "
                    "rou_routing_h h ON h.item_id=i.id AND h.is_default=1 WHERE i.source_type<>'P' AND i.is_active=1 "
                    "ORDER BY i.item_code"),
    "rou_head_of": ("ROU", "row", "SELECT * FROM rou_routing_h WHERE item_id=%s ORDER BY is_default DESC, id DESC LIMIT 1"),
    "rou_lines": ("ROU", "rows", "SELECT * FROM rou_routing_d WHERE routing_id=%s ORDER BY op_seq"),
    # ---------------------------------------------------------------- 單據
    "po_receipts": ("PUR", "rows",
                    "SELECT h.rcv_no, h.rcv_date, i.item_code, d.accept_qty, d.reject_qty, d.lot_no, c.origin_label, "
                    "d.date_code, d.base_amount FROM pur_receipt_d d JOIN pur_receipt_h h ON h.id=d.rcv_id JOIN itm_item i "
                    "ON i.id=d.item_id JOIN pur_order_d p ON p.id=d.po_line_id LEFT JOIN bas_country c ON "
                    "c.country_code=d.origin_country WHERE p.po_id=%s ORDER BY h.id"),
    "so_ships": ("SAL", "rows",
                 "SELECT h.ship_no, h.ship_date, i.item_code, d.qty, d.lot_no, d.base_amount FROM sal_ship_d d JOIN sal_ship_h h "
                 "ON h.id=d.ship_id JOIN itm_item i ON i.id=d.item_id JOIN sal_order_d s ON s.id=d.so_line_id "
                 "WHERE s.so_id=%s ORDER BY h.id"),
    "po_for_receive": ("PUR", "row",
                       "SELECT h.*, s.sup_name FROM pur_order_h h JOIN pur_supplier s ON s.id=h.supplier_id WHERE h.id=%s"),
    "po_open_lines": ("PUR", "rows",
                      "SELECT d.*, i.item_code, i.item_name FROM pur_order_d d JOIN itm_item i ON i.id=d.item_id WHERE "
                      "d.po_id=%s AND d.status='O' ORDER BY d.line_no"),
    "so_open_lines": ("SAL", "rows",
                      "SELECT d.*, i.item_code, i.item_name, (SELECT COALESCE(SUM(x.on_hand_qty-x.allocated_qty),0) FROM "
                      "inv_balance x JOIN bas_warehouse w ON w.id=x.warehouse_id WHERE x.item_id=d.item_id AND w.wh_code='FG') "
                      "fg FROM sal_order_d d JOIN itm_item i ON i.id=d.item_id WHERE d.so_id=%s AND d.status='O' "
                      "ORDER BY d.line_no"),
    # ---------------------------------------------------------------- MPS／MRP
    "mps_list": ("MPS", "rows",
                 "SELECT h.*, (SELECT COUNT(*) FROM mps_plan_d d WHERE d.mps_id=h.id) n_lines FROM mps_plan_h h "
                 "ORDER BY h.id DESC"),
    "mps_open": ("MRP", "rows", "SELECT * FROM mps_plan_h WHERE status<>'X' ORDER BY id DESC"),
    "mps_head": ("MPS", "row", "SELECT * FROM mps_plan_h WHERE id=%s"),
    "mps_lines": ("MPS", "rows",
                  "SELECT d.*, i.item_code, i.item_name, (SELECT GROUP_CONCAT(o.so_no SEPARATOR '、') FROM mps_demand_link k "
                  "JOIN sal_order_d sd ON sd.id=k.so_line_id JOIN sal_order_h o ON o.id=sd.so_id WHERE k.mps_line_id=d.id) "
                  "orders FROM mps_plan_d d JOIN itm_item i ON i.id=d.item_id WHERE d.mps_id=%s "
                  "ORDER BY i.item_code, d.period_start"),
    "mrp_run_row": ("MRP", "row", "SELECT * FROM mrp_run WHERE id=%s"),
    "mrp_exc_count": ("MRP", "value", "SELECT COUNT(*) FROM mrp_exception WHERE run_id=%s"),
    "mrp_pdl_count": ("MRP", "value", "SELECT COUNT(*) FROM mrp_exception WHERE run_id=%s AND msg_type='PDL'"),
    # ---------------------------------------------------------------- 工單
    "wo_row": ("SFC", "row",
               "SELECT w.*, i.item_code, i.item_name, r.rev_code, wh.wh_name, so.so_no FROM sfc_work_order w JOIN itm_item i "
               "ON i.id=w.item_id LEFT JOIN itm_revision r ON r.id=w.rev_id LEFT JOIN bas_warehouse wh ON "
               "wh.id=w.warehouse_id LEFT JOIN sal_order_d sd ON sd.id=w.so_line_id LEFT JOIN sal_order_h so ON "
               "so.id=sd.so_id WHERE w.id=%s"),
    "wo_mats": ("SFC", "rows",
                "SELECT m.*, i.item_code, i.item_name, c.origin_label FROM sfc_wo_material m JOIN itm_item i ON "
                "i.id=m.item_id LEFT JOIN bas_country c ON c.country_code=m.required_country WHERE m.wo_id=%s "
                "ORDER BY m.line_no"),
    "wo_ops": ("SFC", "rows",
               "SELECT o.*, c.wc_code, c.wc_name FROM sfc_wo_operation o JOIN rou_work_center c ON c.id=o.wc_id "
               "WHERE o.wo_id=%s ORDER BY o.op_seq"),
    "wo_mat_cost": ("SFC", "value", "SELECT COALESCE(-SUM(amount),0) FROM inv_txn WHERE wo_id=%s AND doc_type='ISS'"),
    "wo_by_no": ("SFC", "value", "SELECT id FROM sfc_work_order WHERE wo_no=%s"),
    "wo_issue_mats": ("SFC", "rows",
                      "SELECT m.*, i.item_code, i.item_name, (SELECT COALESCE(SUM(b.on_hand_qty),0) FROM inv_balance b "
                      "WHERE b.item_id=m.item_id AND b.warehouse_id=m.warehouse_id) stock FROM sfc_wo_material m JOIN "
                      "itm_item i ON i.id=m.item_id WHERE m.wo_id=%s AND m.issue_type='P' AND m.required_qty>m.issued_qty "
                      "ORDER BY m.line_no"),
    # ---------------------------------------------------------------- 成本
    "cost_std": ("ACC", "rows",
                 "SELECT c.*, i.item_code, i.item_name, i.item_type, i.low_level_code FROM acc_item_cost c JOIN itm_item i "
                 "ON i.id=c.item_id WHERE c.cost_type='S' AND c.period=%s ORDER BY i.low_level_code, i.item_code"),
    "cost_var": ("ACC", "rows",
                 "SELECT v.*, i.item_code, i.item_name FROM acc_variance v LEFT JOIN itm_item i ON i.id=v.item_id "
                 "WHERE v.period=%s ORDER BY v.id DESC"),
    "cost_val": ("ACC", "rows",
                 "SELECT i.item_code, i.item_name, i.item_type, SUM(l.remaining_qty) q, SUM(l.remaining_qty*l.unit_cost) v, "
                 "SUM(l.remaining_qty*l.unit_cost)/NULLIF(SUM(l.remaining_qty),0) avg FROM inv_layer l JOIN itm_item i ON "
                 "i.id=l.item_id WHERE l.is_closed=0 GROUP BY i.id ORDER BY v DESC"),
}

# 下拉選單（所有登入者都可讀；只有代號與名稱）
LOOKUPS = {
    "items": "SELECT id k, CONCAT(item_code,'　',item_name) t FROM itm_item WHERE is_active=1 ORDER BY item_code",
    "items_all": "SELECT id k, CONCAT(item_code,'　',item_name) t FROM itm_item ORDER BY item_code",
    "items_mfg": "SELECT id k, CONCAT(item_code,'　',item_name) t FROM itm_item WHERE is_active=1 AND source_type<>'P' "
                 "ORDER BY item_code",
    "suppliers": "SELECT id k, CONCAT(sup_code,'　',COALESCE(short_name,sup_name)) t FROM pur_supplier WHERE is_active=1 "
                 "ORDER BY sup_code",
    "customers": "SELECT id k, CONCAT(cust_code,'　',COALESCE(short_name,cust_name)) t FROM sal_customer WHERE is_active=1 "
                 "ORDER BY cust_code",
    "warehouses": "SELECT id k, CONCAT(wh_code,'　',wh_name) t FROM bas_warehouse WHERE is_active=1 ORDER BY wh_code",
    "employees": "SELECT id k, CONCAT(emp_code,'　',emp_name) t FROM bas_employee WHERE is_active=1 ORDER BY emp_code",
    "depts": "SELECT id k, CONCAT(dept_code,'　',dept_name) t FROM bas_dept WHERE is_active=1 ORDER BY dept_code",
    "categories": "SELECT id k, CONCAT(cat_code,'　',cat_name) t FROM itm_category ORDER BY cat_code",
    "units": "SELECT id k, unit_name t FROM bas_unit ORDER BY id",
    "currencies": "SELECT currency_code k, CONCAT(currency_code,'　',currency_name) t FROM bas_currency WHERE is_active=1 "
                  "ORDER BY is_base DESC, currency_code",
    "countries": "SELECT country_code k, CONCAT(country_code,'　',COALESCE(origin_label,country_name)) t FROM bas_country "
                 "ORDER BY FIELD(country_code,'TW','JP','US','KR','CN') DESC, country_code",
    "manufacturers": "SELECT id k, CONCAT(mfr_code,'　',mfr_name) t FROM bas_manufacturer WHERE is_active=1 ORDER BY mfr_code",
    "wcs": "SELECT id k, CONCAT(wc_code,'　',wc_name) t FROM rou_work_center WHERE is_active=1 ORDER BY wc_code",
    "machines": "SELECT id k, CONCAT(machine_code,'　',machine_name) t FROM rou_machine ORDER BY machine_code",
    "revisions": "SELECT r.id k, CONCAT(i.item_code,' Rev ',r.rev_code) t FROM itm_revision r JOIN itm_item i ON "
                 "i.id=r.item_id ORDER BY i.item_code, r.rev_code",
    "mfr_parts": "SELECT a.id k, CONCAT(a.mfr_part_no,'（',COALESCE(c.origin_label,a.origin_country),'）') t FROM itm_mfr_part a "
                 "LEFT JOIN bas_country c ON c.country_code=a.origin_country ORDER BY a.mfr_part_no",
    "periods": "SELECT period k, CONCAT(LEFT(period,4),'/',RIGHT(period,2)) t FROM acc_period ORDER BY period DESC",
    "boms": "SELECT h.id k, CONCAT(i.item_code,' 版本 ',h.bom_ver) t FROM bom_header h JOIN itm_item i ON "
            "i.id=h.parent_item_id ORDER BY i.item_code, h.bom_ver",
}

# 可用一般維護（save_row／delete_row／master_rows）的資料表：權限模組, 主鍵
TABLES = {
    "bas_unit": ("BAS", "id"), "bas_currency": ("BAS", "currency_code"), "bas_exchange_rate": ("BAS", "id"),
    "bas_country": ("BAS", "country_code"), "bas_manufacturer": ("BAS", "id"), "bas_dept": ("BAS", "id"),
    "bas_employee": ("BAS", "id"), "bas_warehouse": ("BAS", "id"), "bas_calendar": ("BAS", "cal_date"),
    "itm_category": ("ITM", "id"), "itm_item": ("ITM", "id"), "itm_plan": ("ITM", "item_id"),
    "itm_revision": ("ITM", "id"), "itm_mfr_part": ("ITM", "id"),
    "sal_customer": ("SAL", "id"), "pur_supplier": ("PUR", "id"), "pur_item_source": ("PUR", "id"),
    "rou_work_center": ("ROU", "id"), "rou_machine": ("ROU", "id"), "acc_wc_rate": ("ACC", "id"),
    "crp_bill_resource": ("CRP", "id"), "bom_ecn": ("BOM", "id"), "acc_account_map": ("ACC", "id"),
    "bom_header": ("BOM", "id"), "rou_routing_h": ("ROU", "id"),
}
