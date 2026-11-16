-- ============================================================================
-- 結構驗證：用 SQL 程序實跑 MRP（低階碼 → 展開 → 淨需求 → 批量 → 位移）、CRP、先進先出發料
-- 目的：證明資料表欄位足以支撐 MRP II 運算。正式系統的運算會寫在 Python 引擎。
-- 用法：schema.sql → sample_data.sql → 本檔
-- ============================================================================
SET NAMES utf8mb4;
DELIMITER //

CREATE OR REPLACE PROCEDURE t_workday_offset(IN p_date DATE, IN p_days INT, OUT p_out DATE)
BEGIN
  -- 由工廠行事曆往前推 p_days 個工作天（需求日若是假日，先退到前一個工作天）
  DECLARE v_seq INT;
  SELECT MAX(workday_seq) INTO v_seq FROM bas_calendar WHERE cal_date <= p_date AND is_workday = 1;
  SELECT cal_date INTO p_out FROM bas_calendar WHERE workday_seq = v_seq - p_days;
END //

CREATE OR REPLACE PROCEDURE t_run_mrp(IN p_mps_id INT, IN p_today DATE)
BEGIN
  DECLARE v_run INT; DECLARE v_lvl INT DEFAULT 0; DECLARE v_max INT;
  DECLARE done INT DEFAULT 0;
  DECLARE c_item INT; DECLARE c_date DATE; DECLARE c_qty DECIMAL(18,4);
  DECLARE v_avail, v_net, v_lot, v_sr DECIMAL(18,4);
  DECLARE v_rule CHAR(3); DECLARE v_fix, v_mult, v_moq, v_ss DECIMAL(18,4); DECLARE v_lt INT;
  DECLARE v_src CHAR(1); DECLARE v_rel, v_last DATE; DECLARE v_po BIGINT;
  DECLARE cur CURSOR FOR
    SELECT r.item_id, r.need_date, SUM(r.qty) FROM t_req r JOIN itm_item i ON i.id = r.item_id
    WHERE i.low_level_code = v_lvl GROUP BY r.item_id, r.need_date ORDER BY r.item_id, r.need_date;
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

  -- 1) 低階碼：每個料件在所有 BOM 中出現的最深層級（共用料取最深）
  UPDATE itm_item SET low_level_code = 0;
  UPDATE itm_item i JOIN (
    WITH RECURSIVE x AS (
      SELECT h.parent_item_id AS item_id, 0 AS lvl FROM bom_header h
       WHERE h.status = 'A' AND h.parent_item_id NOT IN (SELECT child_item_id FROM bom_detail)
      UNION ALL
      SELECT d.child_item_id, x.lvl + 1 FROM x
        JOIN bom_header h ON h.parent_item_id = x.item_id AND h.status = 'A' AND h.is_default = 1
        JOIN bom_detail d ON d.bom_id = h.id
    ) SELECT item_id, MAX(lvl) llc FROM x GROUP BY item_id
  ) l ON l.item_id = i.id SET i.low_level_code = l.llc;
  SELECT MAX(low_level_code) INTO v_max FROM itm_item;

  INSERT INTO mrp_run (run_no, mps_id, plan_start) VALUES (CONCAT('MRP-', DATE_FORMAT(NOW(), '%Y%m%d%H%i%s')), p_mps_id, p_today);
  SET v_run = LAST_INSERT_ID();

  CREATE OR REPLACE TEMPORARY TABLE t_req (item_id INT, need_date DATE, qty DECIMAL(18,4),
    source_type CHAR(1), mps_line_id BIGINT, parent_po_id BIGINT);
  CREATE OR REPLACE TEMPORARY TABLE t_poh (item_id INT PRIMARY KEY, poh DECIMAL(18,4), last_date DATE);
  INSERT INTO t_req SELECT item_id, period_start, mps_qty, 'M', id, NULL FROM mps_plan_d WHERE mps_id = p_mps_id AND mps_qty > 0;

  WHILE v_lvl <= v_max DO
    SET done = 0;
    OPEN cur;
    lp: LOOP
      FETCH cur INTO c_item, c_date, c_qty;
      IF done THEN LEAVE lp; END IF;
      SELECT p.lot_rule, p.fixed_lot_qty, p.order_multiple, p.min_order_qty, p.safety_stock, p.lead_time_days, i.source_type
        INTO v_rule, v_fix, v_mult, v_moq, v_ss, v_lt, v_src
        FROM itm_plan p JOIN itm_item i ON i.id = p.item_id WHERE p.item_id = c_item;
      -- 2) 期初可用量：只算可用倉、排除淘汰版本；扣保留量與安全存量
      IF NOT EXISTS (SELECT 1 FROM t_poh WHERE item_id = c_item) THEN
        INSERT INTO t_poh SELECT c_item, COALESCE(SUM(b.on_hand_qty - b.allocated_qty), 0) - v_ss, NULL
          FROM inv_balance b
          JOIN bas_warehouse w ON w.id = b.warehouse_id AND w.is_nettable = 1
          LEFT JOIN itm_revision r ON r.id = b.rev_id
         WHERE b.item_id = c_item AND (r.id IS NULL OR r.status <> 'O');
      END IF;
      SELECT last_date INTO v_last FROM t_poh WHERE item_id = c_item;
      -- 預定接收：上次需求日之後、到本次需求日為止到期的未結採購＋未完工工單（不重複計算）
      SELECT COALESCE(SUM(q), 0) INTO v_sr FROM (
        SELECT d.qty - d.received_qty q, d.due_date dd FROM pur_order_d d JOIN pur_order_h h ON h.id = d.po_id
         WHERE d.item_id = c_item AND d.status = 'O' AND h.status IN ('A','P')
        UNION ALL
        SELECT plan_qty - completed_qty - scrap_qty, plan_finish FROM sfc_work_order
         WHERE item_id = c_item AND status IN ('R','S')) s
       WHERE s.dd <= c_date AND (v_last IS NULL OR s.dd > v_last);
      SELECT poh + v_sr INTO v_avail FROM t_poh WHERE item_id = c_item;
      -- 3) 淨需求 Netting
      SET v_net = GREATEST(0, c_qty - v_avail);
      -- 4) 批量法則
      SET v_lot = v_net;
      IF v_net > 0 THEN
        IF v_rule = 'FOQ' AND v_fix > 0 THEN SET v_lot = CEIL(v_net / v_fix) * v_fix; END IF;
        IF v_mult > 0 THEN SET v_lot = CEIL(v_lot / v_mult) * v_mult; END IF;
        SET v_lot = GREATEST(v_lot, v_moq);
      END IF;
      -- 5) 前置時間位移 Offsetting（工作天）
      CALL t_workday_offset(c_date, v_lt, v_rel);
      INSERT INTO mrp_record (run_id, item_id, period_start, gross_req, scheduled_receipt, projected_oh, net_req, planned_receipt, planned_release)
        VALUES (v_run, c_item, c_date, c_qty, v_sr, v_avail + v_lot - c_qty + v_ss, v_net, v_lot, v_lot);
      UPDATE t_poh SET poh = v_avail + v_lot - c_qty, last_date = c_date WHERE item_id = c_item;
      IF v_lot = 0 THEN   -- 由庫存/在途滿足：仍記錄需求來源
        INSERT INTO mrp_pegging (run_id, item_id, need_date, need_qty, source_type, mps_line_id, parent_po_id)
          SELECT v_run, c_item, c_date, qty, source_type, mps_line_id, parent_po_id
            FROM t_req WHERE item_id = c_item AND need_date = c_date;
      END IF;
      IF v_lot > 0 THEN
        INSERT INTO mrp_planned_order (run_id, item_id, rev_id, order_type, qty, release_date, due_date, supplier_id)
          VALUES (v_run, c_item, (SELECT current_rev_id FROM itm_item WHERE id = c_item),
                  IF(v_src = 'M', 'M', IF(v_src = 'O', 'O', 'P')), v_lot, v_rel, c_date,
                  (SELECT supplier_id FROM pur_item_source WHERE item_id = c_item ORDER BY priority LIMIT 1));
        SET v_po = LAST_INSERT_ID();
        INSERT INTO mrp_pegging (run_id, item_id, need_date, need_qty, source_type, mps_line_id, parent_po_id, supply_po_id)
          SELECT v_run, c_item, c_date, qty, source_type, mps_line_id, parent_po_id, v_po
            FROM t_req WHERE item_id = c_item AND need_date = c_date;
        IF v_rel < p_today THEN
          INSERT INTO mrp_exception (run_id, item_id, msg_type, suggest_date, qty, message)
            VALUES (v_run, c_item, 'PDL', v_rel, v_lot, CONCAT('應於 ', v_rel, ' 發出，已逾期，請加急或調整交期'));
        END IF;
        -- 1) 展開 Exploding：自製件的計畫訂單 → 下階毛需求（需求日 = 母件發出日）
        IF v_src = 'M' THEN
          INSERT INTO t_req
            SELECT d.child_item_id, v_rel, v_lot / h.base_qty * d.qty_per / (1 - d.scrap_rate), 'P', NULL, v_po
              FROM bom_header h JOIN bom_detail d ON d.bom_id = h.id
             WHERE h.parent_item_id = c_item AND h.status = 'A' AND h.is_default = 1
               AND d.effective_date <= v_rel AND (d.obsolete_date IS NULL OR d.obsolete_date > v_rel);
        END IF;
      END IF;
    END LOOP;
    CLOSE cur;
    SET v_lvl = v_lvl + 1;
  END WHILE;

  UPDATE mrp_run SET status = 'D', finished_at = NOW(),
    item_count = (SELECT COUNT(DISTINCT item_id) FROM mrp_record WHERE run_id = v_run),
    planned_count = (SELECT COUNT(*) FROM mrp_planned_order WHERE run_id = v_run) WHERE id = v_run;
  UPDATE mps_plan_h SET status = 'R' WHERE id = p_mps_id;

  -- CRP：自製計畫訂單 × 途程工序 → 工作中心於發出日的負荷
  INSERT INTO crp_run (run_no, run_type, mrp_run_id, horizon_start, horizon_end)
    VALUES (CONCAT('CRP-', v_run), 'C', v_run, p_today, p_today + INTERVAL 60 DAY);
  SET @crp = LAST_INSERT_ID();
  INSERT INTO crp_load (run_id, wc_id, period_start, required_hours, available_hours, load_pct)
    SELECT @crp, rd.wc_id, po.release_date, SUM(rd.setup_hours + po.qty * rd.run_hours),
           MAX(wc.resource_count * cal.shift_count * wc.hours_per_shift * wc.efficiency * wc.utilization),
           ROUND(SUM(rd.setup_hours + po.qty * rd.run_hours) * 100 /
                 MAX(wc.resource_count * cal.shift_count * wc.hours_per_shift * wc.efficiency * wc.utilization), 2)
      FROM mrp_planned_order po
      JOIN rou_routing_h rh ON rh.item_id = po.item_id AND rh.is_default = 1 AND rh.status = 'A'
      JOIN rou_routing_d rd ON rd.routing_id = rh.id
      JOIN rou_work_center wc ON wc.id = rd.wc_id
      JOIN bas_calendar cal ON cal.cal_date = po.release_date
     WHERE po.run_id = v_run AND po.order_type = 'M'
     GROUP BY rd.wc_id, po.release_date;
END //

-- 先進先出發料：依成本層入庫時間由舊到新扣減，寫入異動帳、耗用明細、批號餘額
CREATE OR REPLACE PROCEDURE t_fifo_issue(IN p_item INT, IN p_wh INT, IN p_qty DECIMAL(18,4), IN p_doc VARCHAR(20), IN p_wo INT)
BEGIN
  DECLARE v_left DECIMAL(18,4) DEFAULT p_qty; DECLARE v_take DECIMAL(18,4);
  DECLARE v_layer BIGINT; DECLARE v_rem DECIMAL(18,4); DECLARE v_cost DECIMAL(18,6); DECLARE v_lot INT; DECLARE v_rev INT;
  DECLARE v_txn BIGINT;
  INSERT INTO inv_txn (txn_time, doc_type, doc_no, item_id, warehouse_id, qty, wo_id)
    VALUES (NOW(), 'ISS', p_doc, p_item, p_wh, -p_qty, p_wo);
  SET v_txn = LAST_INSERT_ID();
  WHILE v_left > 0 DO
    SET v_layer = NULL;
    -- 由舊到新找成本層；可發量 = 層剩餘 − 該批已保留給其他工單的量
    SELECT l.id, l.remaining_qty - COALESCE(b.allocated_qty, 0), l.unit_cost, l.lot_id, l.rev_id
      INTO v_layer, v_rem, v_cost, v_lot, v_rev
      FROM inv_layer l
      LEFT JOIN inv_balance b ON b.item_id = l.item_id AND b.warehouse_id = l.warehouse_id
                             AND b.lot_key = IFNULL(l.lot_id, 0) AND b.rev_key = IFNULL(l.rev_id, 0) AND b.loc_key = 0
     WHERE l.item_id = p_item AND l.warehouse_id = p_wh AND l.is_closed = 0
       AND l.remaining_qty - COALESCE(b.allocated_qty, 0) > 0
     ORDER BY l.received_at, l.id LIMIT 1 FOR UPDATE;
    IF v_layer IS NULL THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '庫存不足，無法先進先出發料';
    END IF;
    SET v_take = LEAST(v_left, v_rem);
    UPDATE inv_layer SET remaining_qty = remaining_qty - v_take WHERE id = v_layer;
    INSERT INTO inv_layer_consume (out_txn_id, layer_id, qty, unit_cost, amount)
      VALUES (v_txn, v_layer, v_take, v_cost, ROUND(v_take * v_cost, 2));
    UPDATE inv_balance SET on_hand_qty = on_hand_qty - v_take, last_txn_at = NOW()
     WHERE item_id = p_item AND warehouse_id = p_wh AND lot_key = IFNULL(v_lot, 0) AND rev_key = IFNULL(v_rev, 0);
    SET v_left = v_left - v_take;
  END WHILE;
  UPDATE inv_txn t SET amount = -(SELECT SUM(amount) FROM inv_layer_consume WHERE out_txn_id = v_txn),
                       unit_cost = (SELECT SUM(amount) / p_qty FROM inv_layer_consume WHERE out_txn_id = v_txn)
   WHERE t.id = v_txn;
END //
DELIMITER ;

CALL t_run_mrp(1, '2026-11-16');

SELECT '=== MRP 時距表 ===' AS '';
SELECT i.item_code 料號, i.low_level_code 階, r.period_start 需求日, r.gross_req 毛需求, r.scheduled_receipt 預定接收,
       r.net_req 淨需求, r.planned_receipt 計畫量, p.release_date 發出日, p.order_type 類, s.sup_code 供應商
  FROM mrp_record r JOIN itm_item i ON i.id = r.item_id
  LEFT JOIN mrp_planned_order p ON p.run_id = r.run_id AND p.item_id = r.item_id AND p.due_date = r.period_start
  LEFT JOIN pur_supplier s ON s.id = p.supplier_id
 ORDER BY i.low_level_code, i.item_code, r.period_start;
SELECT '=== 例外訊息 ===' AS '';
SELECT i.item_code 料號, e.msg_type 類型, e.message 訊息 FROM mrp_exception e JOIN itm_item i ON i.id = e.item_id;
SELECT '=== CRP 負荷 ===' AS '';
SELECT w.wc_code 工作中心, l.period_start 日期, l.required_hours 需求工時, l.available_hours 可用工時, l.load_pct 負荷率
  FROM crp_load l JOIN rou_work_center w ON w.id = l.wc_id ORDER BY 2, 1;
SELECT '=== 共用料追溯：固態電容的需求來源 ===' AS '';
SELECT g.need_date 需求日, g.need_qty 需求量, pi.item_code 上階料, pp.qty 上階計畫量
  FROM mrp_pegging g JOIN itm_item i ON i.id = g.item_id
  LEFT JOIN mrp_planned_order pp ON pp.id = g.parent_po_id LEFT JOIN itm_item pi ON pi.id = pp.item_id
 WHERE i.item_code = 'R-CAP' ORDER BY g.need_date;
SELECT '=== 產地：固態電容 AML ===' AS '';
SELECT i.item_code 料號, m.mfr_name 製造商, a.mfr_part_no 製造商料號, c.origin_label 產地, a.priority 順序
  FROM itm_mfr_part a JOIN itm_item i ON i.id = a.item_id JOIN bas_manufacturer m ON m.id = a.manufacturer_id
  JOIN bas_country c ON c.country_code = a.origin_country WHERE i.item_code = 'R-CAP' ORDER BY a.priority;

-- 先進先出：主機板試產領 3500 個電容。日製批 3000 個中有 300 個已保留給電源工單（指定日製），
-- 所以應先扣 10/05 入庫的日製批 2700（@2.6），再扣 10/20 台製批 800（@1.8）
CALL t_fifo_issue(12, 1, 3500, 'IS202611001', NULL);
SELECT '=== 先進先出發料 3500 個固態電容 ===' AS '';
SELECT l.received_at 入庫時間, lt.lot_no 批號, c.origin_label 產地, k.qty 耗用量, k.unit_cost 單位成本, k.amount 成本,
       l.remaining_qty 層剩餘
  FROM inv_layer_consume k JOIN inv_layer l ON l.id = k.layer_id
  JOIN inv_lot lt ON lt.id = l.lot_id JOIN bas_country c ON c.country_code = lt.origin_country ORDER BY l.received_at;
SELECT doc_no 單號, qty 數量, unit_cost 平均單位成本, amount 金額 FROM inv_txn WHERE doc_no = 'IS202611001';

SELECT '=== 外幣採購換算本位幣 ===' AS '';
SELECT h.po_no 採購單, h.currency_code 幣別, h.exchange_rate 匯率, h.untaxed_amount 原幣金額, h.base_untaxed_amount 新台幣金額
  FROM pur_order_h h ORDER BY h.id;

DROP PROCEDURE t_run_mrp; DROP PROCEDURE t_workday_offset; DROP PROCEDURE t_fifo_issue;
