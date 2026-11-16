-- ============================================================================
-- 範例資料：電子組裝廠（主機板、電源供應器、USB 集線器）
--   * 三階 BOM、共用料（電容、MOSFET、USB 母座、說明書跨產品共用）
--   * 料件版本（PCB Rev A 淘汰／Rev B 量產；Hub IC 韌體 1.0／1.2 可互換）
--   * 產地（台製、日製、美製、韓製）與核可製造商料號 AML
--   * 外幣採購（美元、日圓、韓元）與匯率歷史
--   * 先進先出成本層
-- 公司、製造商、供應商、客戶名稱皆為虛構。先執行 schema.sql 再執行本檔。
-- ============================================================================
SET NAMES utf8mb4;

INSERT INTO sys_company (id, company_name, tax_id) VALUES (1, '範例電子科技股份有限公司', '12345675');

-- 幣別與匯率（1 外幣 = ? 新台幣）
INSERT INTO bas_currency (currency_code, currency_name, symbol, is_base, amount_decimals, exchange_rate) VALUES
('TWD','新台幣','NT$',1,0,1),('USD','美元','US$',0,2,32.10),('JPY','日圓','¥',0,0,0.2120),
('KRW','韓元','₩',0,0,0.02350),('CNY','人民幣','CN¥',0,2,4.420),('EUR','歐元','€',0,2,34.80);
INSERT INTO bas_exchange_rate (currency_code, rate_date, rate_type, rate, source) VALUES
('USD','2026-10-05','A',31.85,'臺灣銀行牌告'),('USD','2026-11-02','A',32.05,'臺灣銀行牌告'),('USD','2026-11-16','A',32.10,'臺灣銀行牌告'),
('JPY','2026-10-05','A',0.2165,'臺灣銀行牌告'),('JPY','2026-11-02','A',0.2138,'臺灣銀行牌告'),('JPY','2026-11-16','A',0.2120,'臺灣銀行牌告'),
('KRW','2026-11-02','A',0.02340,'臺灣銀行牌告'),('KRW','2026-11-16','A',0.02350,'臺灣銀行牌告'),
('USD','2026-11-16','B',32.00,'臺灣銀行牌告'),('USD','2026-11-16','S',32.20,'臺灣銀行牌告');

INSERT INTO bas_country (country_code, country_name, country_name_en, origin_label) VALUES
('TW','台灣','Taiwan','台製'),('JP','日本','Japan','日製'),('US','美國','United States','美製'),
('KR','韓國','Korea','韓製'),('CN','中國','China','陸製'),('MY','馬來西亞','Malaysia','馬製');

INSERT INTO sys_doc_type (doc_type, doc_name, module, prefix, inv_effect) VALUES
('SO','客戶訂單','SAL','SO',0),('SHP','出貨單','SAL','SH',-1),('PR','請購單','PUR','PR',0),('PO','採購單','PUR','PO',0),
('RCV','進貨單','PUR','RC',1),('WO','工單','SFC','WO',0),('REQ','請料單','SFC','RQ',0),('ISS','領料單','SFC','IS',-1),
('RTN','退料單','SFC','RT',1),('CMP','完工入庫','SFC','CP',1),('TRF','調撥單','INV','TF',0),('ADJ','調整單','INV','AJ',0),
('BEG','期初開帳','INV','BG',1);

INSERT INTO bas_unit (id, unit_code, unit_name) VALUES (1,'PNL','片'),(2,'EA','個'),(3,'SET','台'),(4,'M','公尺'),(5,'PC','條'),(6,'CPY','份');
INSERT INTO bas_dept (id, dept_code, dept_name) VALUES (1,'PM','生管課'),(2,'PU','採購課'),(3,'SMT','SMT 課'),(4,'ASY','組裝課');
INSERT INTO bas_employee (id, emp_code, emp_name, dept_id, job_title) VALUES
(1,'E001','王生管',1,'生管'),(2,'E002','李採購',2,'採購'),(3,'E003','陳組長',3,'SMT 組長'),(4,'E004','林作業員',4,'作業員');
UPDATE bas_employee SET supervisor_id = 3 WHERE id = 4;
INSERT INTO bas_warehouse (id, wh_code, wh_name, wh_type, is_nettable) VALUES
(1,'RM','原料倉','R',1),(2,'FG','成品倉','F',1),(3,'QC','IQC 待驗倉','Q',0),(4,'WIP','在製倉','W',1),(5,'SC','報廢倉','S',0);

-- 工廠行事曆：2026-10-01 ～ 2026-12-31，週六日休
INSERT INTO bas_calendar (cal_date, is_workday, work_hours)
WITH RECURSIVE d AS (SELECT DATE '2026-10-01' AS dt UNION ALL SELECT dt + INTERVAL 1 DAY FROM d WHERE dt < '2026-12-31')
SELECT dt, IF(WEEKDAY(dt) >= 5, 0, 1), IF(WEEKDAY(dt) >= 5, 0, 8) FROM d;
UPDATE bas_calendar c JOIN (
  SELECT cal_date, ROW_NUMBER() OVER (ORDER BY cal_date) AS seq FROM bas_calendar WHERE is_workday = 1
) w ON w.cal_date = c.cal_date SET c.workday_seq = w.seq;

INSERT INTO bas_manufacturer (id, mfr_code, mfr_name, country_code) VALUES
(1,'TWM','台灣精密電子','TW'),(2,'JPC','日本電容工業','JP'),(3,'USS','美洲半導體','US'),(4,'KRS','韓星電子元件','KR'),
(5,'TWP','永信電路板','TW'),(6,'JPK','日本精密連接器','JP'),(7,'TWC','順和連接器','TW');

INSERT INTO itm_category (id, cat_code, cat_name) VALUES (1,'FG','電腦週邊成品'),(2,'PCBA','PCBA 半成品'),(3,'IC','IC 與主動元件'),
(4,'PAS','被動元件'),(5,'MEC','機構件與包材');

-- 料件：F 成品、S 半成品、R 原物料、P 包材；M 自製、P 採購
INSERT INTO itm_item (id, item_code, item_name, spec, item_type, source_type, category_id, unit_id) VALUES
( 1,'F-MB-A1',    'ATX 主機板 A1',          'DDR5×4、USB 3.0×4',   'F','M',1,1),
( 2,'F-PSU-650',  '650W 金牌電源供應器',    '80 PLUS Gold、全模組', 'F','M',1,3),
( 3,'F-HUB-4P',   'USB 3.0 四埠集線器',     'USB-C 上行',           'F','M',1,2),
( 4,'S-PCBA-MB',  '主機板 PCBA',            NULL,'S','M',2,1),
( 5,'S-PCBA-PSU', '電源 PCBA',              NULL,'S','M',2,1),
( 6,'S-PCBA-HUB', '集線器 PCBA',            NULL,'S','M',2,1),
( 7,'S-XFMR',     '主變壓器（自製繞線）',   'EE40',                 'S','M',2,2),
( 8,'R-PCB-MB',   '主機板 6 層 PCB',        'FR-4 1.6mm',           'R','P',3,1),
( 9,'R-CHIPSET',  '主機板晶片組',           NULL,'R','P',3,2),
(10,'R-SOCKET',   'CPU 插座',               'LGA1700',              'R','P',5,2),
(11,'R-DIMM',     'DDR5 記憶體插槽',        '288pin',               'R','P',5,2),
(12,'R-CAP',      '固態電容 470uF 16V',     '8×12mm',               'R','P',4,2),
(13,'R-MOSFET',   '功率 MOSFET 40V',        'DFN5×6',               'R','P',3,2),
(14,'R-USBA',     'USB 3.0 A 型母座',       '9pin 立式',            'R','P',5,2),
(15,'R-HUBIC',    'USB Hub 控制 IC',        'QFN-48',               'R','P',3,2),
(16,'R-PCB-PSU',  '電源 2 層 PCB',          'FR-4 1.6mm 2oz',       'R','P',3,1),
(17,'R-CORE',     '鐵氧體磁芯',             'EE40',                 'R','P',4,2),
(18,'R-WIRE',     '漆包線',                 '0.5mm',                'R','P',4,4),
(19,'R-CASE-PSU', '電源外殼',               'ATX 標準',             'R','P',5,2),
(20,'R-FAN',      '12cm 靜音風扇',          '液態軸承',             'R','P',5,2),
(21,'R-CABLE',    'USB-C 傳輸線',           '1m',                   'R','P',5,5),
(22,'R-CASE-HUB', '集線器鋁合金外殼',       NULL,'R','P',5,2),
(23,'P-MANUAL',   '說明書保卡組',           NULL,'P','P',5,6);

-- 版本：每個料件先建 Rev A（id 同料件 id），再加新版本
INSERT INTO itm_revision (id, item_id, rev_code, status, effective_date) SELECT id, id, 'A', 'A', '2026-01-01' FROM itm_item;
UPDATE itm_revision SET firmware_ver = 'BIOS 1.0' WHERE id = 1;
UPDATE itm_revision SET status = 'O', obsolete_date = '2026-10-31', rev_desc = '舊版線路，USB 走線有串擾，淘汰' WHERE id = 8;
UPDATE itm_revision SET firmware_ver = 'FW 1.0' WHERE id = 15;
INSERT INTO itm_revision (id, item_id, rev_code, rev_desc, status, effective_date, is_interchangeable, prev_rev_id, firmware_ver) VALUES
(24, 8,'B','修正 USB 走線，與 Rev A 不可互換','A','2026-11-01',0,8,NULL),
(25,15,'B','韌體 1.2 改善相容性，可與 Rev A 互換','A','2026-11-01',1,15,'FW 1.2');
UPDATE itm_item i SET current_rev_id = CASE i.id WHEN 8 THEN 24 WHEN 15 THEN 25 ELSE i.id END;

-- 核可製造商料號 AML（同料號多產地）
INSERT INTO itm_mfr_part (id, item_id, rev_id, manufacturer_id, mfr_part_no, origin_country, priority) VALUES
( 1,12,NULL,2,'JC-470M16-8X12','JP',1),   -- 固態電容：日製優先
( 2,12,NULL,1,'TM-SC470-16',   'TW',2),   --           台製次選
( 3,13,NULL,3,'US-MF4060N',    'US',1),   -- MOSFET：美製
( 4,13,NULL,4,'KR-PM40N06',    'KR',2),   --         韓製
( 5, 9,NULL,3,'US-CS760',      'US',1),   -- 晶片組：美製
( 6,15,  25,1,'TM-HUB3104-B',  'TW',1),   -- Hub IC：台製（Rev B）
( 7,14,NULL,7,'TC-UA3-9P',     'TW',1),   -- USB 母座：台製
( 8,14,NULL,6,'JK-USB3A-V',    'JP',2),   --           日製
( 9,11,NULL,4,'KR-D5S288',     'KR',1),   -- DDR5 插槽：韓製
(10, 8,  24,5,'YS-6L-MBB',     'TW',1),   -- PCB Rev B：台製
(11,16,NULL,5,'YS-2L-PSU',     'TW',1),
(12,10,NULL,7,'TC-LGA1700',    'TW',1),
(13,17,NULL,2,'JC-FC-EE40',    'JP',1);

INSERT INTO itm_plan (item_id, planner_id, default_wh_id, lead_time_days, safety_stock, lot_rule, fixed_lot_qty, order_multiple, is_mps_item) VALUES
( 1,1,2, 2,  10,'LFL',   0,  0,1),( 2,1,2, 2,  5,'LFL',  0,  0,1),( 3,1,2, 1, 20,'LFL',   0,  0,1),
( 4,1,1, 2,   0,'LFL',   0,  0,0),( 5,1,1, 2,  0,'LFL',  0,  0,0),( 6,1,1, 1,  0,'LFL',   0,  0,0),( 7,1,1, 3, 0,'LFL',0,0,0),
( 8,2,1,10,   0,'LFL',   0, 50,0),( 9,2,1,15, 20,'LFL',  0,  0,0),(10,2,1, 7,  0,'LFL',   0,100,0),(11,2,1, 7, 0,'LFL',0,500,0),
(12,2,1, 5,1000,'FOQ',2000,  0,0),(13,2,1, 5,  0,'LFL',  0,500,0),(14,2,1, 6,  0,'LFL',   0,100,0),(15,2,1,12,50,'LFL',0,0,0),
(16,2,1, 8,   0,'LFL',   0, 50,0),(17,2,1, 6,  0,'LFL',  0,  0,0),(18,2,1, 4,  0,'LFL',   0,500,0),(19,2,1, 5, 0,'LFL',0,0,0),
(20,2,1, 5,   0,'LFL',   0,100,0),(21,2,1, 4,  0,'LFL',  0,100,0),(22,2,1, 5,  0,'LFL',   0,  0,0),(23,2,1, 3, 0,'FOQ',1000,0,0);

-- BOM（電源 PCBA 的固態電容指定日製）
INSERT INTO bom_header (id, parent_item_id, parent_rev_id, bom_ver, status) VALUES
(1,1,1,'01','A'),(2,2,2,'01','A'),(3,3,3,'01','A'),(4,4,4,'01','A'),(5,5,5,'01','A'),(6,6,6,'01','A'),(7,7,7,'01','A');
INSERT INTO bom_detail (bom_id, line_no, child_item_id, child_rev_id, required_country, qty_per, scrap_rate, op_seq, effective_date) VALUES
(1,1, 4,NULL,NULL, 1,   0,   10,'2026-01-01'),(1,2,23,NULL,NULL,1,0,10,'2026-01-01'),
(2,1, 5,NULL,NULL, 1,   0,   10,'2026-01-01'),(2,2,19,NULL,NULL,1,0,10,'2026-01-01'),(2,3,20,NULL,NULL,1,0,10,'2026-01-01'),(2,4,23,NULL,NULL,1,0,10,'2026-01-01'),
(3,1, 6,NULL,NULL, 1,   0,   10,'2026-01-01'),(3,2,22,NULL,NULL,1,0,10,'2026-01-01'),(3,3,21,NULL,NULL,1,0,10,'2026-01-01'),(3,4,23,NULL,NULL,1,0,10,'2026-01-01'),
(4,1, 8,  24,NULL, 1,   0,   10,'2026-11-01'),   -- 指定 PCB Rev B
(4,2, 9,NULL,NULL, 1,   0,   10,'2026-01-01'),(4,3,10,NULL,NULL,1,0,20,'2026-01-01'),(4,4,11,NULL,NULL,4,0,20,'2026-01-01'),
(4,5,12,NULL,NULL,12,0.01,   10,'2026-01-01'),(4,6,13,NULL,NULL,8,0.01,10,'2026-01-01'),(4,7,14,NULL,NULL,4,0,20,'2026-01-01'),
(5,1,16,NULL,NULL, 1,   0,   10,'2026-01-01'),(5,2, 7,NULL,NULL,1,0,20,'2026-01-01'),
(5,3,12,NULL,'JP', 6,   0,   10,'2026-01-01'),   -- 客戶要求日製電容
(5,4,13,NULL,NULL, 4,   0,   10,'2026-01-01'),
(6,1,15,NULL,NULL, 1,   0,   10,'2026-01-01'),(6,2,14,NULL,NULL,4,0,10,'2026-01-01'),(6,3,12,NULL,NULL,2,0,10,'2026-01-01'),
(7,1,17,NULL,NULL, 1,   0,   10,'2026-01-01'),(7,2,18,NULL,NULL,3.5,0.02,10,'2026-01-01');

-- 工作中心、機器、途程
INSERT INTO rou_work_center (id, wc_code, wc_name, dept_id, wc_type, resource_count, hours_per_shift, efficiency, is_bottleneck) VALUES
(1,'WC-SMT', 'SMT 表面黏著線',3,'M',2,8,0.95,1),(2,'WC-DIP','插件波焊線',3,'L',4,8,0.90,0),
(3,'WC-ASSY','組裝測試線',  4,'L',6,8,0.90,1),(4,'WC-COIL','繞線站',   4,'M',2,8,0.95,0),(5,'WC-BURN','燒機室',4,'M',4,8,1.00,0);
INSERT INTO rou_machine (machine_code, machine_name, wc_id, purchase_date, cost, useful_years, salvage_value) VALUES
('SMT-01','高速貼片機 1 號',1,'2024-03-01',8500000,8,500000),('SMT-02','高速貼片機 2 號',1,'2025-02-01',9200000,8,500000),
('RFL-01','十溫區迴焊爐',1,'2024-03-01',2800000,10,200000),('CL-01','自動繞線機',4,'2023-06-01',650000,6,30000),
('BI-01','燒機架（64 位）',5,'2024-09-01',480000,5,20000);
INSERT INTO rou_routing_h (id, item_id, routing_ver, status) SELECT id, id, '01', 'A' FROM itm_item WHERE source_type = 'M';
INSERT INTO rou_routing_d (routing_id, op_seq, op_name, wc_id, setup_hours, run_hours) VALUES
(1,10,'主機板組裝測試',3,0.5,0.05),(2,10,'電源組裝',3,0.5,0.08),(2,20,'燒機測試',5,0.2,0.10),(3,10,'集線器組裝',3,0.3,0.02),
(4,10,'SMT 打件',1,2.0,0.02),(4,20,'插件波焊',2,1.0,0.03),(5,10,'SMT 打件',1,1.5,0.015),(5,20,'插件波焊',2,1.0,0.04),
(6,10,'SMT 打件',1,1.0,0.008),(7,10,'變壓器繞線',4,0.5,0.05);

-- 供應商（代理商）與供應來源：外幣報價
INSERT INTO pur_supplier (id, sup_code, sup_name, currency_code, lead_time_days) VALUES
(1,'S001','聯成晶片代理','USD',15),(2,'S002','富達電子零件','JPY',5),(3,'S003','永信電路板','TWD',10),
(4,'S004','順和機構件','TWD',5),(5,'S005','韓星台灣分公司','KRW',7);
INSERT INTO pur_item_source (item_id, supplier_id, mfr_part_id, origin_country, unit_price, currency_code, lead_days, priority) VALUES
(12,2, 1,'JP',   12.0,'JPY',5,1),(12,4, 2,'TW', 1.80,'TWD',5,2),
(13,1, 3,'US',  0.42,'USD',5,1),(13,5, 4,'KR',  540,'KRW',7,2),
( 9,1, 5,'US', 18.50,'USD',15,1),(15,4, 6,'TW', 38.0,'TWD',12,1),
(14,4, 7,'TW',  6.50,'TWD',6,1),(14,2, 8,'JP',   42,'JPY',6,2),
(11,5, 9,'KR',  1100,'KRW',7,1),( 8,3,10,'TW', 185,'TWD',10,1),(16,3,11,'TW',62,'TWD',8,1),
(10,4,12,'TW',  45,'TWD',7,1),(17,2,13,'JP', 95,'JPY',6,1),
(18,4,NULL,NULL,0.8,'TWD',4,1),(19,4,NULL,NULL,120,'TWD',5,1),(20,4,NULL,NULL,68,'TWD',5,1),
(21,4,NULL,NULL,25,'TWD',4,1),(22,4,NULL,NULL,85,'TWD',5,1),(23,4,NULL,NULL,6,'TWD',3,1);

-- 期初庫存：批號、餘額、異動帳、先進先出成本層一次建立
INSERT INTO inv_lot (id, item_id, rev_id, mfr_part_id, origin_country, date_code, lot_no, received_at) VALUES
(1,12,12,1,'JP','2638','CAP-JP-2610A','2026-10-05 09:00'),   -- 日製電容，較早入庫
(2,12,12,2,'TW','2642','CAP-TW-2610B','2026-10-20 09:00'),   -- 台製電容，較晚入庫
(3, 8, 8,NULL,'TW','2620','PCB-A-2606','2026-06-10 09:00'),  -- 淘汰的 Rev A
(4, 8,24,10,'TW','2644','PCB-B-2611','2026-11-03 09:00'),
(5,15,15,NULL,'TW','2630','HUB-A-2608','2026-08-12 09:00'),
(6, 9, 9,5,'US','2640','CS-2610','2026-10-08 09:00');
CREATE TEMPORARY TABLE t_open (item_id INT, wh INT, lot_id INT, rev_id INT, qty DECIMAL(18,4), cost DECIMAL(18,6), rcv DATETIME);
INSERT INTO t_open VALUES
( 1,2,NULL, 1,  20,3150,'2026-10-30'),( 2,2,NULL, 2,  10,2380,'2026-10-30'),( 3,2,NULL, 3,  50, 520,'2026-10-30'),
( 4,1,NULL, 4,  30,2650,'2026-10-28'),(12,1,   1,12,3000,2.60,'2026-10-05'),(12,1,   2,12,2000,1.80,'2026-10-20'),
(13,1,NULL,13,1200,13.4,'2026-10-12'),(14,1,NULL,14, 800,6.50,'2026-10-15'),(23,1,NULL,23, 600,6.00,'2026-10-01'),
( 9,1,   6, 9, 100, 589,'2026-10-08'),( 9,3,   6, 9,  50, 593,'2026-11-14'),       -- 待驗倉 50 個晶片組不計入 MRP
( 8,1,   3, 8, 120, 176,'2026-06-10'),( 8,1,   4,24,  40, 185,'2026-11-03'),       -- Rev A 120 片淘汰不可用
(15,1,   5,15, 100,  38,'2026-08-12'),(10,1,NULL,10,  50,  45,'2026-10-10'),(11,1,NULL,11, 400,25.9,'2026-10-10'),
(17,1,NULL,17, 100,20.6,'2026-10-10'),(18,1,NULL,18, 500, 0.8,'2026-10-10'),(19,1,NULL,19,  50, 120,'2026-10-10'),
(20,1,NULL,20,  80,  68,'2026-10-10'),(21,1,NULL,21, 100,  25,'2026-10-10'),(22,1,NULL,22, 200,  85,'2026-10-10');
INSERT INTO inv_balance (item_id, warehouse_id, lot_id, rev_id, on_hand_qty, last_txn_at) SELECT item_id, wh, lot_id, rev_id, qty, rcv FROM t_open;
INSERT INTO inv_txn (txn_time, doc_type, doc_no, item_id, rev_id, warehouse_id, lot_id, qty, unit_cost, amount)
  SELECT rcv, 'BEG', 'BG202610001', item_id, rev_id, wh, lot_id, qty, cost, ROUND(qty * cost, 2) FROM t_open;
INSERT INTO inv_layer (item_id, warehouse_id, lot_id, rev_id, in_txn_id, received_at, in_qty, remaining_qty, unit_cost)
  SELECT item_id, warehouse_id, lot_id, rev_id, id, txn_time, qty, qty, unit_cost FROM inv_txn WHERE doc_type = 'BEG';
DROP TEMPORARY TABLE t_open;

-- 在途外幣採購（預定接收）
INSERT INTO pur_order_h (id, po_no, po_date, supplier_id, currency_code, exchange_rate, untaxed_amount, base_untaxed_amount, status) VALUES
(1,'PO202611001','2026-11-02',2,'JPY',0.2138,24000,  5131,'A'),   -- 日製電容 2000 個 × ¥12
(2,'PO202611002','2026-11-02',1,'USD',32.05, 2775, 88939,'A'),    -- 美製晶片組 150 個 × US$18.5
(3,'PO202611003','2026-11-02',4,'TWD',1,     6500,  6500,'P');    -- 台製 USB 母座 1000 個，已到 400
INSERT INTO pur_order_d (po_id, line_no, item_id, rev_id, mfr_part_id, origin_country, qty, unit_price, amount, base_amount, due_date, received_qty) VALUES
(1,1,12,NULL,1,'JP',2000,12,   24000, 5131,'2026-11-25',0),
(2,1, 9,NULL,5,'US', 150,18.5,  2775,88939,'2026-12-01',0),
(3,1,14,NULL,7,'TW',1000,6.5,   6500, 6500,'2026-11-28',400);

-- 客戶訂單（美元接單）與 MPS
INSERT INTO sal_customer (id, cust_code, cust_name, currency_code) VALUES
(1,'C001','北美系統整合商','USD'),(2,'C002','歐洲伺服器組裝廠','USD'),(3,'C003','台灣電商平台','TWD');
INSERT INTO sal_order_h (id, so_no, order_date, customer_id, currency_code, exchange_rate, untaxed_amount, base_untaxed_amount, status) VALUES
(1,'SO202611001','2026-11-10',1,'USD',32.05,36000,1153800,'A'),
(2,'SO202611002','2026-11-11',2,'USD',32.05,17000, 544850,'A'),
(3,'SO202611003','2026-11-12',3,'TWD',1,  290000, 290000,'A');
INSERT INTO sal_order_d (id, so_id, line_no, item_id, rev_id, qty, unit_price, amount, base_amount, due_date) VALUES
(1,1,1,1,1,300,120,36000,1153800,'2026-12-18'),(2,2,1,2,2,200,85,17000,544850,'2026-12-15'),(3,3,1,3,3,500,580,290000,290000,'2026-12-01');

INSERT INTO mps_plan_h (id, mps_no, plan_date, bucket_type, horizon_start, horizon_end, status) VALUES
(1,'MPS-202611-01','2026-11-16','D','2026-11-16','2026-12-31','C');
INSERT INTO mps_plan_d (id, mps_id, item_id, period_start, order_qty, mps_qty) VALUES
(1,1,1,'2026-12-18',300,300),(2,1,2,'2026-12-15',200,200),(3,1,3,'2026-12-01',500,500);
INSERT INTO mps_demand_link (mps_line_id, demand_type, so_line_id, linked_qty) VALUES (1,'S',1,300),(2,'S',2,200),(3,'S',3,500);

-- 生產中工單：電源 PCBA 100 片，已完工 20（預定接收 80）；未領電容 300 → 保留量
INSERT INTO sfc_work_order (id, wo_no, item_id, rev_id, bom_id, routing_id, plan_qty, completed_qty, plan_start, plan_finish, warehouse_id, status) VALUES
(1,'WO202611001',5,5,5,5,100,20,'2026-11-16','2026-11-20',1,'S');
INSERT INTO sfc_wo_material (wo_id, line_no, item_id, required_country, required_qty, issued_qty, op_seq, warehouse_id, required_date) VALUES
(1,1,16,NULL,100,100,10,1,'2026-11-16'),(1,2,7,NULL,100,100,20,1,'2026-11-16'),
(1,3,12,'JP',600,300,10,1,'2026-11-16'),(1,4,13,NULL,400,400,10,1,'2026-11-16');
INSERT INTO sfc_wo_operation (wo_id, op_seq, op_name, wc_id, plan_setup_hours, plan_run_hours) VALUES
(1,10,'SMT 打件',1,1.5,1.5),(1,20,'插件波焊',2,1.0,4.0);
UPDATE inv_balance SET allocated_qty = 300 WHERE item_id = 12 AND lot_id = 1;   -- 指定日製 → 保留日製批

INSERT INTO acc_period (period, start_date, end_date) VALUES ('202610','2026-10-01','2026-10-31'),('202611','2026-11-01','2026-11-30'),('202612','2026-12-01','2026-12-31');
INSERT INTO acc_wc_rate (wc_id, period, labor_rate, overhead_rate) VALUES
(1,'202611',320,1150),(2,'202611',260,300),(3,'202611',250,180),(4,'202611',260,220),(5,'202611',200,150);
