-- ============================================================================
-- 資料助秘之物料需求II生產製造系統（ZMS MRP II）— MariaDB 建表腳本
-- 由 db/schema_spec.py 自動產生，請勿手改；修改規格後重新執行產生器
-- 資料表 96 張；字元集 utf8mb4；引擎 InnoDB
-- ============================================================================
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ─────────────── SYS 系統管理（12 張）───────────────
-- 公司基本資料：單一公司設定（固定 1 筆）
CREATE TABLE IF NOT EXISTS `sys_company` (
  `id` TINYINT NOT NULL DEFAULT 1 COMMENT '固定 1',
  `company_name` VARCHAR(100) NOT NULL COMMENT '公司名稱',
  `tax_id` CHAR(8) COMMENT '統一編號',
  `owner_name` VARCHAR(50) COMMENT '負責人',
  `phone` VARCHAR(30) COMMENT '電話',
  `address` VARCHAR(200) COMMENT '地址',
  `base_currency` CHAR(3) NOT NULL DEFAULT 'TWD' COMMENT '本位幣',
  `fiscal_start_month` TINYINT NOT NULL DEFAULT 1 COMMENT '會計年度起始月',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_sys_company_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sys_company_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_sys_company_1` CHECK (id = 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='公司基本資料';

-- 系統參數：鍵值式參數（MRP 時距、預設倉、API 埠等）
CREATE TABLE IF NOT EXISTS `sys_param` (
  `param_key` VARCHAR(60) NOT NULL COMMENT '參數鍵',
  `param_value` VARCHAR(500) COMMENT '參數值',
  `description` VARCHAR(200) COMMENT '說明',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`param_key`),
  CONSTRAINT `fk_sys_param_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sys_param_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系統參數';

-- 資料庫版本：系統更新時逐版套用資料庫升級腳本的紀錄
CREATE TABLE IF NOT EXISTS `sys_schema_version` (
  `version` VARCHAR(20) NOT NULL COMMENT '版本號，如 1.0.0',
  `applied_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '套用時間',
  `app_version` VARCHAR(20) COMMENT '套用時的程式版本',
  `note` VARCHAR(500) COMMENT '備註',
  PRIMARY KEY (`version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='資料庫版本';

-- 功能清單：選單上的每個作業（權限與說明文件的依據）
CREATE TABLE IF NOT EXISTS `sys_function` (
  `func_code` VARCHAR(30) NOT NULL COMMENT '功能代碼，如 MRP010',
  `func_name` VARCHAR(60) NOT NULL COMMENT '功能名稱',
  `module` CHAR(3) NOT NULL COMMENT '所屬模組前綴',
  `sort_no` SMALLINT NOT NULL DEFAULT 0 COMMENT '排序',
  PRIMARY KEY (`func_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='功能清單';

-- 角色：權限群組
CREATE TABLE IF NOT EXISTS `sys_role` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `role_code` VARCHAR(20) NOT NULL COMMENT '角色代碼',
  `role_name` VARCHAR(50) NOT NULL COMMENT '角色名稱',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sys_role_role_code` (`role_code`),
  CONSTRAINT `fk_sys_role_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sys_role_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色';

-- 角色權限：角色 × 功能（多對多）的權限明細
CREATE TABLE IF NOT EXISTS `sys_role_perm` (
  `role_id` INT NOT NULL COMMENT '角色',
  `func_code` VARCHAR(30) NOT NULL COMMENT '功能',
  `can_view` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '查詢',
  `can_add` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '新增',
  `can_edit` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '修改',
  `can_delete` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '刪除',
  `can_approve` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '核准',
  `can_print` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '列印/匯出',
  PRIMARY KEY (`role_id`, `func_code`),
  CONSTRAINT `fk_sys_role_perm_role_id` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sys_role_perm_func_code` FOREIGN KEY (`func_code`) REFERENCES `sys_function` (`func_code`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色權限';

-- 使用者：登入帳號；可對應一位員工（一對一）
CREATE TABLE IF NOT EXISTS `sys_user` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `user_code` VARCHAR(30) NOT NULL COMMENT '帳號',
  `user_name` VARCHAR(50) NOT NULL COMMENT '姓名',
  `password_hash` VARCHAR(255) NOT NULL COMMENT '密碼雜湊（PBKDF2）',
  `employee_id` INT COMMENT '對應員工（1:1）',
  `last_login_at` DATETIME COMMENT '最後登入',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '啟用 1/停用 0',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sys_user_user_code` (`user_code`),
  UNIQUE KEY `uk_sys_user_employee_id` (`employee_id`),
  CONSTRAINT `fk_sys_user_employee_id` FOREIGN KEY (`employee_id`) REFERENCES `bas_employee` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sys_user_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sys_user_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='使用者';

-- 使用者角色：使用者 × 角色（多對多橋接表）
CREATE TABLE IF NOT EXISTS `sys_user_role` (
  `user_id` INT NOT NULL COMMENT '使用者',
  `role_id` INT NOT NULL COMMENT '角色',
  PRIMARY KEY (`user_id`, `role_id`),
  CONSTRAINT `fk_sys_user_role_user_id` FOREIGN KEY (`user_id`) REFERENCES `sys_user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sys_user_role_role_id` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='使用者角色';

-- 單據類別：統一表單代碼與編號規則；存貨異動方向
CREATE TABLE IF NOT EXISTS `sys_doc_type` (
  `doc_type` VARCHAR(10) NOT NULL COMMENT '單別，如 PO、WO、ISS',
  `doc_name` VARCHAR(40) NOT NULL COMMENT '單據名稱',
  `module` CHAR(3) NOT NULL COMMENT '所屬模組',
  `prefix` VARCHAR(10) NOT NULL COMMENT '編號前綴',
  `no_format` VARCHAR(30) NOT NULL DEFAULT '{prefix}{yyyymm}{seq:4}' COMMENT '編號格式，如 {prefix}{yyyymm}{seq:4}',
  `inv_effect` TINYINT NOT NULL DEFAULT 0 COMMENT '存貨影響：1 入庫、-1 出庫、0 不影響',
  PRIMARY KEY (`doc_type`),
  CONSTRAINT `ck_sys_doc_type_1` CHECK (inv_effect IN (-1,0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='單據類別';

-- 單據流水號：各單別每期最後號碼
CREATE TABLE IF NOT EXISTS `sys_doc_seq` (
  `doc_type` VARCHAR(10) NOT NULL COMMENT '單別',
  `period` CHAR(6) NOT NULL COMMENT '期別 yyyymm',
  `last_no` INT NOT NULL DEFAULT 0 COMMENT '最後流水號',
  PRIMARY KEY (`doc_type`, `period`),
  CONSTRAINT `fk_sys_doc_seq_doc_type` FOREIGN KEY (`doc_type`) REFERENCES `sys_doc_type` (`doc_type`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='單據流水號';

-- 操作紀錄：新增/修改/刪除/核准的稽核軌跡
CREATE TABLE IF NOT EXISTS `sys_audit_log` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `user_id` INT COMMENT '使用者',
  `func_code` VARCHAR(30) COMMENT '功能',
  `action` VARCHAR(10) NOT NULL COMMENT 'ADD/EDIT/DEL/APPROVE/LOGIN',
  `table_name` VARCHAR(40) COMMENT '資料表',
  `record_key` VARCHAR(60) COMMENT '主鍵或單號',
  `detail` LONGTEXT COMMENT '異動內容 JSON',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '時間',
  PRIMARY KEY (`id`),
  KEY `ix_sys_audit_log_1` (`created_at`),
  CONSTRAINT `fk_sys_audit_log_user_id` FOREIGN KEY (`user_id`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_sys_audit_log_1` CHECK (detail IS NULL OR JSON_VALID(detail))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='操作紀錄';

-- 語音教學說明：每個功能的說明文件與語音朗讀稿
CREATE TABLE IF NOT EXISTS `sys_help_topic` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `func_code` VARCHAR(30) COMMENT '對應功能（可空白=總說明）',
  `title` VARCHAR(100) NOT NULL COMMENT '標題',
  `content` TEXT NOT NULL COMMENT '說明內容（Markdown）',
  `voice_script` TEXT COMMENT '語音朗讀稿',
  `sort_no` SMALLINT NOT NULL DEFAULT 0 COMMENT '排序',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_sys_help_topic_func_code` FOREIGN KEY (`func_code`) REFERENCES `sys_function` (`func_code`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sys_help_topic_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sys_help_topic_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='語音教學說明';

-- ─────────────── BAS 基本資料（10 張）───────────────
-- 計量單位：個、台、公斤、公尺…
CREATE TABLE IF NOT EXISTS `bas_unit` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `unit_code` VARCHAR(10) NOT NULL COMMENT '單位代碼',
  `unit_name` VARCHAR(20) NOT NULL COMMENT '單位名稱',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_bas_unit_unit_code` (`unit_code`),
  CONSTRAINT `fk_bas_unit_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bas_unit_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='計量單位';

-- 幣別：幣別主檔（ISO 4217）：TWD、USD、JPY、KRW、CNY、EUR…
CREATE TABLE IF NOT EXISTS `bas_currency` (
  `currency_code` CHAR(3) NOT NULL COMMENT '幣別代碼',
  `currency_name` VARCHAR(20) NOT NULL COMMENT '名稱，如 新台幣、美元、日圓',
  `symbol` VARCHAR(5) COMMENT '符號，如 NT$、US$、¥、₩',
  `is_base` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否本位幣（僅一個）',
  `amount_decimals` TINYINT NOT NULL DEFAULT 2 COMMENT '金額小數位（日圓、韓元為 0）',
  `price_decimals` TINYINT NOT NULL DEFAULT 4 COMMENT '單價小數位',
  `exchange_rate` DECIMAL(18,6) NOT NULL DEFAULT 1 COMMENT '最新記帳匯率（1 外幣 = ? 本位幣）',
  `rate_updated_at` DATETIME COMMENT '最新匯率更新時間',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '啟用 1/停用 0',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`currency_code`),
  CONSTRAINT `fk_bas_currency_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bas_currency_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='幣別';

-- 匯率歷史：幣別 × 日期 × 匯率類型；單據依單據日期帶入匯率
CREATE TABLE IF NOT EXISTS `bas_exchange_rate` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `currency_code` CHAR(3) NOT NULL COMMENT '幣別',
  `rate_date` DATE NOT NULL COMMENT '匯率日期',
  `rate_type` CHAR(1) NOT NULL DEFAULT 'A' COMMENT 'B 銀行買入、S 銀行賣出、M 中價、A 記帳匯率',
  `rate` DECIMAL(18,6) NOT NULL COMMENT '匯率（1 外幣 = ? 本位幣）',
  `source` VARCHAR(30) COMMENT '來源，如 臺灣銀行牌告、人工輸入',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_bas_exchange_rate_1` (`currency_code`, `rate_date`, `rate_type`),
  KEY `ix_bas_exchange_rate_1` (`rate_date`),
  CONSTRAINT `fk_bas_exchange_rate_currency_code` FOREIGN KEY (`currency_code`) REFERENCES `bas_currency` (`currency_code`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bas_exchange_rate_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bas_exchange_rate_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_bas_exchange_rate_1` CHECK (rate > 0),
  CONSTRAINT `ck_bas_exchange_rate_2` CHECK (rate_type IN ('B','S','M','A'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='匯率歷史';

-- 國家/產地：原產國代碼（ISO 3166 兩碼）：TW 台灣、JP 日本、US 美國、KR 韓國…
CREATE TABLE IF NOT EXISTS `bas_country` (
  `country_code` CHAR(2) NOT NULL COMMENT '國家代碼',
  `country_name` VARCHAR(30) NOT NULL COMMENT '中文名稱',
  `country_name_en` VARCHAR(50) COMMENT '英文名稱',
  `origin_label` VARCHAR(10) COMMENT '產地簡稱，如 台製、日製',
  PRIMARY KEY (`country_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='國家/產地';

-- 製造商：原廠（與供應商不同：供應商可能是代理商）
CREATE TABLE IF NOT EXISTS `bas_manufacturer` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `mfr_code` VARCHAR(20) NOT NULL COMMENT '製造商代碼',
  `mfr_name` VARCHAR(100) NOT NULL COMMENT '製造商名稱',
  `country_code` CHAR(2) COMMENT '總部所在國',
  `website` VARCHAR(200) COMMENT '網站',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '啟用 1/停用 0',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_bas_manufacturer_mfr_code` (`mfr_code`),
  CONSTRAINT `fk_bas_manufacturer_country_code` FOREIGN KEY (`country_code`) REFERENCES `bas_country` (`country_code`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bas_manufacturer_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bas_manufacturer_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='製造商';

-- 部門：組織部門（自我參照形成樹狀）
CREATE TABLE IF NOT EXISTS `bas_dept` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `dept_code` VARCHAR(10) NOT NULL COMMENT '部門代碼',
  `dept_name` VARCHAR(50) NOT NULL COMMENT '部門名稱',
  `parent_id` INT COMMENT '上層部門（自我參照 N:1）',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '啟用 1/停用 0',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_bas_dept_dept_code` (`dept_code`),
  CONSTRAINT `fk_bas_dept_parent_id` FOREIGN KEY (`parent_id`) REFERENCES `bas_dept` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bas_dept_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bas_dept_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='部門';

-- 員工：生管、採購、現場人員等
CREATE TABLE IF NOT EXISTS `bas_employee` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `emp_code` VARCHAR(20) NOT NULL COMMENT '員工編號',
  `emp_name` VARCHAR(50) NOT NULL COMMENT '姓名',
  `dept_id` INT COMMENT '部門',
  `job_title` VARCHAR(30) COMMENT '職稱',
  `supervisor_id` INT COMMENT '直屬主管（自我參照）',
  `phone` VARCHAR(30) COMMENT '電話',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '啟用 1/停用 0',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_bas_employee_emp_code` (`emp_code`),
  CONSTRAINT `fk_bas_employee_dept_id` FOREIGN KEY (`dept_id`) REFERENCES `bas_dept` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bas_employee_supervisor_id` FOREIGN KEY (`supervisor_id`) REFERENCES `bas_employee` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bas_employee_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bas_employee_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='員工';

-- 倉庫：原料倉、成品倉、在製倉、待驗倉…
CREATE TABLE IF NOT EXISTS `bas_warehouse` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `wh_code` VARCHAR(10) NOT NULL COMMENT '倉庫代碼',
  `wh_name` VARCHAR(50) NOT NULL COMMENT '倉庫名稱',
  `wh_type` CHAR(1) NOT NULL DEFAULT 'R' COMMENT 'R 原料、F 成品、W 在製、Q 待驗、S 報廢',
  `is_nettable` TINYINT(1) NOT NULL DEFAULT 1 COMMENT 'MRP 是否計入可用量',
  `keeper_id` INT COMMENT '倉管人員',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '啟用 1/停用 0',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_bas_warehouse_wh_code` (`wh_code`),
  CONSTRAINT `fk_bas_warehouse_keeper_id` FOREIGN KEY (`keeper_id`) REFERENCES `bas_employee` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bas_warehouse_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bas_warehouse_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_bas_warehouse_1` CHECK (wh_type IN ('R','F','W','Q','S'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='倉庫';

-- 儲位：倉庫內儲位（倉庫 1:N 儲位）
CREATE TABLE IF NOT EXISTS `bas_location` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `warehouse_id` INT NOT NULL COMMENT '倉庫',
  `loc_code` VARCHAR(20) NOT NULL COMMENT '儲位代碼',
  `loc_name` VARCHAR(50) COMMENT '儲位名稱',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_bas_location_1` (`warehouse_id`, `loc_code`),
  CONSTRAINT `fk_bas_location_warehouse_id` FOREIGN KEY (`warehouse_id`) REFERENCES `bas_warehouse` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bas_location_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bas_location_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='儲位';

-- 工廠行事曆：每日是否上班與工時；前置時間以工作天位移
CREATE TABLE IF NOT EXISTS `bas_calendar` (
  `cal_date` DATE NOT NULL COMMENT '日期',
  `is_workday` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否上班',
  `work_hours` DECIMAL(5,2) NOT NULL DEFAULT 8 COMMENT '標準工時',
  `shift_count` TINYINT NOT NULL DEFAULT 1 COMMENT '班次',
  `workday_seq` INT COMMENT '工作天序號（位移計算用）',
  `note` VARCHAR(500) COMMENT '備註',
  PRIMARY KEY (`cal_date`),
  KEY `ix_bas_calendar_1` (`workday_seq`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工廠行事曆';

-- ─────────────── ITM 料件主檔（6 張）───────────────
-- 料件分類：分類樹；亦作為產銷計畫的產品族
CREATE TABLE IF NOT EXISTS `itm_category` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `cat_code` VARCHAR(20) NOT NULL COMMENT '分類代碼',
  `cat_name` VARCHAR(50) NOT NULL COMMENT '分類名稱',
  `parent_id` INT COMMENT '上層分類',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_itm_category_cat_code` (`cat_code`),
  CONSTRAINT `fk_itm_category_parent_id` FOREIGN KEY (`parent_id`) REFERENCES `itm_category` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_category_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_category_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='料件分類';

-- 料件主檔：所有成品、半成品、原物料、包材
CREATE TABLE IF NOT EXISTS `itm_item` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `item_code` VARCHAR(40) NOT NULL COMMENT '料號',
  `item_name` VARCHAR(100) NOT NULL COMMENT '品名',
  `spec` VARCHAR(200) COMMENT '規格',
  `item_type` CHAR(1) NOT NULL COMMENT 'F 成品、S 半成品、R 原物料、P 包材、X 虛設件',
  `source_type` CHAR(1) NOT NULL DEFAULT 'P' COMMENT 'M 自製、P 採購、O 委外',
  `category_id` INT COMMENT '分類',
  `unit_id` INT NOT NULL COMMENT '庫存單位',
  `purchase_unit_id` INT COMMENT '採購單位',
  `current_rev_id` INT COMMENT '目前量產版本',
  `low_level_code` SMALLINT NOT NULL DEFAULT 0 COMMENT '低階碼（BOM 最深層級，MRP 由上而下逐階計算用）',
  `is_lot_control` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '批號管理',
  `barcode` VARCHAR(40) COMMENT '條碼',
  `drawing_no` VARCHAR(40) COMMENT '圖號',
  `weight_kg` DECIMAL(12,4) COMMENT '單位重量',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '啟用 1/停用 0',
  `note` VARCHAR(500) COMMENT '備註',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_itm_item_item_code` (`item_code`),
  KEY `ix_itm_item_1` (`item_type`),
  KEY `ix_itm_item_2` (`low_level_code`),
  CONSTRAINT `fk_itm_item_category_id` FOREIGN KEY (`category_id`) REFERENCES `itm_category` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_item_unit_id` FOREIGN KEY (`unit_id`) REFERENCES `bas_unit` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_item_purchase_unit_id` FOREIGN KEY (`purchase_unit_id`) REFERENCES `bas_unit` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_item_current_rev_id` FOREIGN KEY (`current_rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_item_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_item_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_itm_item_1` CHECK (item_type IN ('F','S','R','P','X')),
  CONSTRAINT `ck_itm_item_2` CHECK (source_type IN ('M','P','O'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='料件主檔';

-- 料件版本：同一料號的不同版本（PCB Rev A/B、韌體 1.0/1.1）；料件 1:N 版本
CREATE TABLE IF NOT EXISTS `itm_revision` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `item_id` INT NOT NULL COMMENT '料件',
  `rev_code` VARCHAR(10) NOT NULL COMMENT '版本碼，如 A、B、1.0、1.1',
  `rev_desc` VARCHAR(200) COMMENT '版本差異說明',
  `status` CHAR(1) NOT NULL DEFAULT 'A' COMMENT 'D 設計中、P 試產、A 量產、H 暫停、O 淘汰（淘汰版庫存不計入 MRP）',
  `effective_date` DATE NOT NULL DEFAULT '2000-01-01' COMMENT '生效日',
  `obsolete_date` DATE COMMENT '失效日',
  `is_interchangeable` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '可與前一版互換（MRP 合併計算）',
  `prev_rev_id` INT COMMENT '前一版本（自我參照）',
  `firmware_ver` VARCHAR(30) COMMENT '韌體/BIOS 版本',
  `drawing_no` VARCHAR(40) COMMENT '圖號',
  `gerber_file` VARCHAR(200) COMMENT '線路圖/Gerber 檔案路徑',
  `ecn_id` INT COMMENT '由哪張工程變更產生',
  `note` VARCHAR(500) COMMENT '備註',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_itm_revision_1` (`item_id`, `rev_code`),
  KEY `ix_itm_revision_1` (`item_id`, `status`),
  CONSTRAINT `fk_itm_revision_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_revision_prev_rev_id` FOREIGN KEY (`prev_rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_revision_ecn_id` FOREIGN KEY (`ecn_id`) REFERENCES `bom_ecn` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_revision_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_revision_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_itm_revision_1` CHECK (status IN ('D','P','A','H','O'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='料件版本';

-- 核可製造商料號 AML：料件 × 版本 × 製造商：製造商料號與原產地（同料號可有台製、日製、美製、韓製來源）
CREATE TABLE IF NOT EXISTS `itm_mfr_part` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `item_id` INT NOT NULL COMMENT '料件',
  `rev_id` INT COMMENT '適用版本（空白=全部版本）',
  `manufacturer_id` INT NOT NULL COMMENT '製造商',
  `mfr_part_no` VARCHAR(60) NOT NULL COMMENT '製造商料號 MPN',
  `origin_country` CHAR(2) NOT NULL COMMENT '原產國',
  `approval_status` CHAR(1) NOT NULL DEFAULT 'A' COMMENT 'A 核可、T 試用、R 不核可',
  `priority` TINYINT NOT NULL DEFAULT 1 COMMENT '優先順序（1 最優先）',
  `rohs` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '符合 RoHS',
  `datasheet` VARCHAR(200) COMMENT '規格書路徑',
  `note` VARCHAR(500) COMMENT '備註',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_itm_mfr_part_1` (`item_id`, `manufacturer_id`, `mfr_part_no`),
  KEY `ix_itm_mfr_part_1` (`origin_country`),
  KEY `ix_itm_mfr_part_2` (`item_id`, `rev_id`),
  CONSTRAINT `fk_itm_mfr_part_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_mfr_part_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_mfr_part_manufacturer_id` FOREIGN KEY (`manufacturer_id`) REFERENCES `bas_manufacturer` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_mfr_part_origin_country` FOREIGN KEY (`origin_country`) REFERENCES `bas_country` (`country_code`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_mfr_part_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_mfr_part_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_itm_mfr_part_1` CHECK (approval_status IN ('A','T','R'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='核可製造商料號 AML';

-- 料件計畫參數：與料件一對一；MRP 批量法則、前置時間、安全存量、EOQ
CREATE TABLE IF NOT EXISTS `itm_plan` (
  `item_id` INT NOT NULL COMMENT '料件（1:1）',
  `planner_id` INT COMMENT '生管/採購負責人',
  `default_wh_id` INT COMMENT '預設倉庫',
  `lead_time_days` SMALLINT NOT NULL DEFAULT 0 COMMENT '前置時間（工作天）',
  `safety_lead_days` SMALLINT NOT NULL DEFAULT 0 COMMENT '安全前置時間',
  `safety_stock` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '安全存量',
  `reorder_point` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '再訂購點',
  `lot_rule` CHAR(3) NOT NULL DEFAULT 'LFL' COMMENT '批量法則：LFL 逐批、FOQ 固定量、EOQ 經濟批量、POQ 期間訂購',
  `fixed_lot_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '固定批量（FOQ）',
  `min_order_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '最小訂購量',
  `order_multiple` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '訂購倍數',
  `poq_periods` SMALLINT NOT NULL DEFAULT 1 COMMENT 'POQ 合併期數',
  `annual_demand` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '年需求量（EOQ 用）',
  `order_cost` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '每次訂購/整備成本（EOQ 用）',
  `holding_rate` DECIMAL(6,4) NOT NULL DEFAULT 0.2 COMMENT '年持有成本率（EOQ 用）',
  `eoq_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '計算後經濟訂購量',
  `yield_rate` DECIMAL(6,4) NOT NULL DEFAULT 1 COMMENT '良率',
  `issue_rule` CHAR(1) NOT NULL DEFAULT 'F' COMMENT '發料原則：F 先進先出、E 先到期先出、M 人工指定',
  `cost_method` CHAR(1) NOT NULL DEFAULT 'F' COMMENT '成本計價：F 先進先出、W 月加權平均、S 標準成本',
  `is_mps_item` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '列入主生產排程',
  `demand_fence_days` SMALLINT NOT NULL DEFAULT 0 COMMENT '需求時柵',
  `planning_fence_days` SMALLINT NOT NULL DEFAULT 0 COMMENT '計畫時柵',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`item_id`),
  CONSTRAINT `fk_itm_plan_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_itm_plan_planner_id` FOREIGN KEY (`planner_id`) REFERENCES `bas_employee` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_plan_default_wh_id` FOREIGN KEY (`default_wh_id`) REFERENCES `bas_warehouse` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_plan_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_plan_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_itm_plan_1` CHECK (lot_rule IN ('LFL','FOQ','EOQ','POQ')),
  CONSTRAINT `ck_itm_plan_2` CHECK (issue_rule IN ('F','E','M')),
  CONSTRAINT `ck_itm_plan_3` CHECK (cost_method IN ('F','W','S'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='料件計畫參數';

-- 單位換算：料件專屬或通用的單位換算
CREATE TABLE IF NOT EXISTS `itm_unit_conv` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `item_id` INT COMMENT '料件（空白=通用）',
  `from_unit_id` INT NOT NULL COMMENT '來源單位',
  `to_unit_id` INT NOT NULL COMMENT '目的單位',
  `factor` DECIMAL(18,6) NOT NULL COMMENT '1 來源 = factor 目的',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_itm_unit_conv_1` (`item_id`, `from_unit_id`, `to_unit_id`),
  CONSTRAINT `fk_itm_unit_conv_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_unit_conv_from_unit_id` FOREIGN KEY (`from_unit_id`) REFERENCES `bas_unit` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_unit_conv_to_unit_id` FOREIGN KEY (`to_unit_id`) REFERENCES `bas_unit` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_unit_conv_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_itm_unit_conv_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='單位換算';

-- ─────────────── FCT 需求預測（3 張）───────────────
-- 產銷計畫：長期：產品族 × 月份的銷售/生產/庫存目標（S&OP）
CREATE TABLE IF NOT EXISTS `fct_sop_plan` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `plan_year` SMALLINT NOT NULL COMMENT '年度',
  `plan_month` TINYINT NOT NULL COMMENT '月份',
  `category_id` INT NOT NULL COMMENT '產品族',
  `sales_plan_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '銷售計畫量',
  `prod_plan_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '生產計畫量',
  `target_inv_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '目標庫存',
  `sales_plan_amt` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '銷售計畫金額',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_fct_sop_plan_1` (`plan_year`, `plan_month`, `category_id`),
  CONSTRAINT `fk_fct_sop_plan_category_id` FOREIGN KEY (`category_id`) REFERENCES `itm_category` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_fct_sop_plan_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_fct_sop_plan_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_fct_sop_plan_1` CHECK (plan_month BETWEEN 1 AND 12)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='產銷計畫';

-- 需求預測單頭：一次預測（版本）
CREATE TABLE IF NOT EXISTS `fct_forecast_h` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `fc_no` VARCHAR(20) NOT NULL COMMENT '預測單號',
  `fc_date` DATE NOT NULL COMMENT '預測日期',
  `method` CHAR(1) NOT NULL DEFAULT 'M' COMMENT 'M 人工、A 移動平均、E 指數平滑、T 趨勢',
  `bucket_type` CHAR(1) NOT NULL DEFAULT 'M' COMMENT '時距：D 日、W 週、M 月',
  `status` CHAR(1) NOT NULL DEFAULT 'D' COMMENT 'D 草稿、A 核准、X 作廢',
  `note` VARCHAR(500) COMMENT '備註',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_fct_forecast_h_fc_no` (`fc_no`),
  CONSTRAINT `fk_fct_forecast_h_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_fct_forecast_h_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_fct_forecast_h_1` CHECK (method IN ('M','A','E','T')),
  CONSTRAINT `ck_fct_forecast_h_2` CHECK (bucket_type IN ('D','W','M')),
  CONSTRAINT `ck_fct_forecast_h_3` CHECK (status IN ('D','A','X'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='需求預測單頭';

-- 需求預測單身：料件 × 期間的預測量；被訂單沖銷的量另記
CREATE TABLE IF NOT EXISTS `fct_forecast_d` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `forecast_id` INT NOT NULL COMMENT '預測單頭',
  `item_id` INT NOT NULL COMMENT '料件',
  `customer_id` INT COMMENT '客戶（可空白）',
  `period_start` DATE NOT NULL COMMENT '期間起日',
  `forecast_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '預測量',
  `consumed_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '已被訂單沖銷量',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_fct_forecast_d_1` (`forecast_id`, `item_id`, `customer_id`, `period_start`),
  CONSTRAINT `fk_fct_forecast_d_forecast_id` FOREIGN KEY (`forecast_id`) REFERENCES `fct_forecast_h` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_fct_forecast_d_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_fct_forecast_d_customer_id` FOREIGN KEY (`customer_id`) REFERENCES `sal_customer` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='需求預測單身';

-- ─────────────── SAL 客戶訂單（5 張）───────────────
-- 客戶：客戶主檔
CREATE TABLE IF NOT EXISTS `sal_customer` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `cust_code` VARCHAR(20) NOT NULL COMMENT '客戶編號',
  `cust_name` VARCHAR(100) NOT NULL COMMENT '客戶名稱',
  `short_name` VARCHAR(30) COMMENT '簡稱',
  `tax_id` CHAR(8) COMMENT '統一編號',
  `contact` VARCHAR(50) COMMENT '聯絡人',
  `phone` VARCHAR(30) COMMENT '電話',
  `email` VARCHAR(100) COMMENT 'Email',
  `address` VARCHAR(200) COMMENT '地址',
  `currency_code` CHAR(3) NOT NULL DEFAULT 'TWD' COMMENT '交易幣別',
  `payment_terms` VARCHAR(30) COMMENT '付款條件',
  `credit_limit` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '信用額度',
  `sales_id` INT COMMENT '業務',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '啟用 1/停用 0',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sal_customer_cust_code` (`cust_code`),
  CONSTRAINT `fk_sal_customer_currency_code` FOREIGN KEY (`currency_code`) REFERENCES `bas_currency` (`currency_code`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sal_customer_sales_id` FOREIGN KEY (`sales_id`) REFERENCES `bas_employee` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sal_customer_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sal_customer_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='客戶';

-- 客戶訂單單頭：接單（獨立需求來源）
CREATE TABLE IF NOT EXISTS `sal_order_h` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `so_no` VARCHAR(20) NOT NULL COMMENT '訂單號',
  `order_date` DATE NOT NULL COMMENT '訂單日期',
  `customer_id` INT NOT NULL COMMENT '客戶',
  `cust_po_no` VARCHAR(40) COMMENT '客戶採購單號',
  `currency_code` CHAR(3) NOT NULL DEFAULT 'TWD' COMMENT '幣別',
  `exchange_rate` DECIMAL(18,6) NOT NULL DEFAULT 1 COMMENT '匯率',
  `tax_type` CHAR(1) NOT NULL DEFAULT '1' COMMENT '1 應稅外加、2 應稅內含、3 零稅、4 免稅',
  `tax_rate` DECIMAL(5,4) NOT NULL DEFAULT 0.05 COMMENT '稅率',
  `sales_id` INT COMMENT '業務',
  `untaxed_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '未稅金額',
  `tax_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '稅額',
  `base_untaxed_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '本位幣未稅金額',
  `base_tax_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '本位幣稅額',
  `status` CHAR(1) NOT NULL DEFAULT 'D' COMMENT 'D 草稿、A 核准、P 部分出貨、C 結案、X 作廢',
  `note` VARCHAR(500) COMMENT '備註',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sal_order_h_so_no` (`so_no`),
  KEY `ix_sal_order_h_1` (`order_date`),
  KEY `ix_sal_order_h_2` (`currency_code`),
  CONSTRAINT `fk_sal_order_h_customer_id` FOREIGN KEY (`customer_id`) REFERENCES `sal_customer` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sal_order_h_currency_code` FOREIGN KEY (`currency_code`) REFERENCES `bas_currency` (`currency_code`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sal_order_h_sales_id` FOREIGN KEY (`sales_id`) REFERENCES `bas_employee` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sal_order_h_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sal_order_h_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_sal_order_h_1` CHECK (status IN ('D','A','P','C','X'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='客戶訂單單頭';

-- 客戶訂單單身：每個料件的訂購量與交期
CREATE TABLE IF NOT EXISTS `sal_order_d` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `so_id` INT NOT NULL COMMENT '訂單單頭',
  `line_no` SMALLINT NOT NULL COMMENT '項次',
  `item_id` INT NOT NULL COMMENT '料件',
  `rev_id` INT COMMENT '訂購版本（空白=目前量產版）',
  `qty` DECIMAL(18,4) NOT NULL COMMENT '訂購量',
  `unit_price` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '單價',
  `amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '金額',
  `base_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '本位幣金額',
  `due_date` DATE NOT NULL COMMENT '客戶交期',
  `promised_date` DATE COMMENT '承諾交期（ATP）',
  `shipped_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '已出貨量',
  `status` CHAR(1) NOT NULL DEFAULT 'O' COMMENT 'O 未結、C 結案、X 取消',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sal_order_d_1` (`so_id`, `line_no`),
  KEY `ix_sal_order_d_1` (`item_id`, `due_date`),
  KEY `ix_sal_order_d_2` (`item_id`, `rev_id`),
  CONSTRAINT `fk_sal_order_d_so_id` FOREIGN KEY (`so_id`) REFERENCES `sal_order_h` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sal_order_d_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sal_order_d_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='客戶訂單單身';

-- 出貨單頭：依訂單出貨、扣成品庫存
CREATE TABLE IF NOT EXISTS `sal_ship_h` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `ship_no` VARCHAR(20) NOT NULL COMMENT '出貨單號',
  `ship_date` DATE NOT NULL COMMENT '出貨日',
  `customer_id` INT NOT NULL COMMENT '客戶',
  `warehouse_id` INT NOT NULL COMMENT '出貨倉',
  `invoice_no` VARCHAR(20) COMMENT '發票號碼',
  `untaxed_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '未稅金額',
  `tax_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '稅額',
  `currency_code` CHAR(3) NOT NULL DEFAULT 'TWD' COMMENT '幣別',
  `exchange_rate` DECIMAL(18,6) NOT NULL DEFAULT 1 COMMENT '匯率（1 外幣 = ? 本位幣，依單據日帶入）',
  `base_untaxed_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '本位幣未稅金額',
  `base_tax_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '本位幣稅額',
  `status` CHAR(1) NOT NULL DEFAULT 'D' COMMENT 'D 草稿、A 已過帳、X 作廢',
  `gl_batch_id` INT COMMENT '會計拋轉批次（空白＝尚未拋轉）',
  `note` VARCHAR(500) COMMENT '備註',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sal_ship_h_ship_no` (`ship_no`),
  KEY `ix_sal_ship_h_1` (`currency_code`),
  KEY `ix_sal_ship_h_2` (`gl_batch_id`),
  CONSTRAINT `fk_sal_ship_h_customer_id` FOREIGN KEY (`customer_id`) REFERENCES `sal_customer` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sal_ship_h_warehouse_id` FOREIGN KEY (`warehouse_id`) REFERENCES `bas_warehouse` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sal_ship_h_currency_code` FOREIGN KEY (`currency_code`) REFERENCES `bas_currency` (`currency_code`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sal_ship_h_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sal_ship_h_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_sal_ship_h_1` CHECK (status IN ('D','A','X'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='出貨單頭';

-- 出貨單身：出貨料件與對應訂單明細
CREATE TABLE IF NOT EXISTS `sal_ship_d` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `ship_id` INT NOT NULL COMMENT '出貨單頭',
  `line_no` SMALLINT NOT NULL COMMENT '項次',
  `so_line_id` BIGINT COMMENT '訂單明細',
  `item_id` INT NOT NULL COMMENT '料件',
  `rev_id` INT COMMENT '出貨版本',
  `lot_no` VARCHAR(30) COMMENT '批號',
  `location_id` INT COMMENT '儲位',
  `qty` DECIMAL(18,4) NOT NULL COMMENT '數量',
  `unit_price` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '單價',
  `amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '金額',
  `base_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '本位幣金額',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sal_ship_d_1` (`ship_id`, `line_no`),
  KEY `ix_sal_ship_d_1` (`item_id`, `rev_id`),
  CONSTRAINT `fk_sal_ship_d_ship_id` FOREIGN KEY (`ship_id`) REFERENCES `sal_ship_h` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sal_ship_d_so_line_id` FOREIGN KEY (`so_line_id`) REFERENCES `sal_order_d` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sal_ship_d_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sal_ship_d_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sal_ship_d_location_id` FOREIGN KEY (`location_id`) REFERENCES `bas_location` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='出貨單身';

-- ─────────────── ROU 途程與工作中心（5 張）───────────────
-- 工作中心：產能計算單位（機台群、產線、人工站）
CREATE TABLE IF NOT EXISTS `rou_work_center` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `wc_code` VARCHAR(20) NOT NULL COMMENT '工作中心代碼',
  `wc_name` VARCHAR(50) NOT NULL COMMENT '名稱',
  `dept_id` INT COMMENT '所屬部門',
  `wc_type` CHAR(1) NOT NULL DEFAULT 'M' COMMENT 'M 機器、L 人工、O 委外',
  `resource_count` SMALLINT NOT NULL DEFAULT 1 COMMENT '機台/人數',
  `hours_per_shift` DECIMAL(5,2) NOT NULL DEFAULT 8 COMMENT '每班工時',
  `efficiency` DECIMAL(6,4) NOT NULL DEFAULT 1 COMMENT '效率',
  `utilization` DECIMAL(6,4) NOT NULL DEFAULT 1 COMMENT '利用率',
  `queue_days` DECIMAL(6,2) NOT NULL DEFAULT 0 COMMENT '等候時間（天）',
  `move_days` DECIMAL(6,2) NOT NULL DEFAULT 0 COMMENT '搬運時間（天）',
  `is_bottleneck` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '瓶頸站（RCCP 檢核）',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '啟用 1/停用 0',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_rou_work_center_wc_code` (`wc_code`),
  CONSTRAINT `fk_rou_work_center_dept_id` FOREIGN KEY (`dept_id`) REFERENCES `bas_dept` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_rou_work_center_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_rou_work_center_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_rou_work_center_1` CHECK (wc_type IN ('M','L','O'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作中心';

-- 工作中心例外產能：某天加班、停機、保養時覆寫可用工時
CREATE TABLE IF NOT EXISTS `rou_wc_calendar` (
  `wc_id` INT NOT NULL COMMENT '工作中心',
  `cal_date` DATE NOT NULL COMMENT '日期',
  `available_hours` DECIMAL(8,2) NOT NULL COMMENT '當日可用工時',
  `reason` VARCHAR(100) COMMENT '原因',
  PRIMARY KEY (`wc_id`, `cal_date`),
  CONSTRAINT `fk_rou_wc_calendar_wc_id` FOREIGN KEY (`wc_id`) REFERENCES `rou_work_center` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作中心例外產能';

-- 機器設備：工作中心內的設備；購置成本與耐用年限供製費分攤
CREATE TABLE IF NOT EXISTS `rou_machine` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `machine_code` VARCHAR(20) NOT NULL COMMENT '設備編號',
  `machine_name` VARCHAR(50) NOT NULL COMMENT '名稱',
  `wc_id` INT NOT NULL COMMENT '所屬工作中心',
  `purchase_date` DATE COMMENT '購置日期',
  `cost` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '取得成本',
  `useful_years` SMALLINT NOT NULL DEFAULT 5 COMMENT '耐用年限',
  `salvage_value` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '估計殘值',
  `status` CHAR(1) NOT NULL DEFAULT 'A' COMMENT 'A 正常、M 保養中、D 報廢',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_rou_machine_machine_code` (`machine_code`),
  CONSTRAINT `fk_rou_machine_wc_id` FOREIGN KEY (`wc_id`) REFERENCES `rou_work_center` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_rou_machine_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_rou_machine_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_rou_machine_1` CHECK (status IN ('A','M','D'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='機器設備';

-- 途程單頭：料件的製造途程版本
CREATE TABLE IF NOT EXISTS `rou_routing_h` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `item_id` INT NOT NULL COMMENT '料件',
  `rev_id` INT COMMENT '適用版本（空白=全部版本）',
  `routing_ver` VARCHAR(10) NOT NULL DEFAULT '01' COMMENT '版本',
  `is_default` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '預設途程',
  `status` CHAR(1) NOT NULL DEFAULT 'D' COMMENT 'D 草稿、A 生效、X 失效',
  `note` VARCHAR(500) COMMENT '備註',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_rou_routing_h_1` (`item_id`, `routing_ver`),
  KEY `ix_rou_routing_h_1` (`item_id`, `rev_id`),
  CONSTRAINT `fk_rou_routing_h_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_rou_routing_h_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_rou_routing_h_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_rou_routing_h_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_rou_routing_h_1` CHECK (status IN ('D','A','X'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='途程單頭';

-- 途程工序：每道工序在哪個工作中心、整備與加工工時
CREATE TABLE IF NOT EXISTS `rou_routing_d` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `routing_id` INT NOT NULL COMMENT '途程單頭',
  `op_seq` SMALLINT NOT NULL COMMENT '工序 10、20、30…',
  `op_name` VARCHAR(50) NOT NULL COMMENT '工序名稱',
  `wc_id` INT NOT NULL COMMENT '工作中心',
  `setup_hours` DECIMAL(10,4) NOT NULL DEFAULT 0 COMMENT '整備工時（每批）',
  `run_hours` DECIMAL(10,6) NOT NULL DEFAULT 0 COMMENT '加工工時（每單位）',
  `is_outsource` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '委外工序',
  `supplier_id` INT COMMENT '委外廠商',
  `is_report_point` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '報工點',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_rou_routing_d_1` (`routing_id`, `op_seq`),
  CONSTRAINT `fk_rou_routing_d_routing_id` FOREIGN KEY (`routing_id`) REFERENCES `rou_routing_h` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_rou_routing_d_wc_id` FOREIGN KEY (`wc_id`) REFERENCES `rou_work_center` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_rou_routing_d_supplier_id` FOREIGN KEY (`supplier_id`) REFERENCES `pur_supplier` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='途程工序';

-- ─────────────── BOM 物料清單（4 張）───────────────
-- BOM 單頭：母件的產品結構版本（料件自我多對多關係的單頭）
CREATE TABLE IF NOT EXISTS `bom_header` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `parent_item_id` INT NOT NULL COMMENT '母件',
  `parent_rev_id` INT COMMENT '母件版本（此 BOM 適用的版本）',
  `bom_ver` VARCHAR(10) NOT NULL DEFAULT '01' COMMENT '版本',
  `base_qty` DECIMAL(18,4) NOT NULL DEFAULT 1 COMMENT '基準量（每幾個母件）',
  `is_default` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '預設 BOM',
  `status` CHAR(1) NOT NULL DEFAULT 'D' COMMENT 'D 草稿、A 核准、X 失效',
  `approved_by` INT COMMENT '核准人',
  `approved_at` DATETIME COMMENT '核准時間',
  `note` VARCHAR(500) COMMENT '備註',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_bom_header_1` (`parent_item_id`, `bom_ver`),
  KEY `ix_bom_header_1` (`parent_item_id`, `parent_rev_id`),
  CONSTRAINT `fk_bom_header_parent_item_id` FOREIGN KEY (`parent_item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bom_header_parent_rev_id` FOREIGN KEY (`parent_rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bom_header_approved_by` FOREIGN KEY (`approved_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bom_header_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bom_header_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_bom_header_1` CHECK (status IN ('D','A','X'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='BOM 單頭';

-- BOM 單身：元件、用量、損耗率、生效區間（展開 Exploding 的依據）
CREATE TABLE IF NOT EXISTS `bom_detail` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `bom_id` INT NOT NULL COMMENT 'BOM 單頭',
  `line_no` SMALLINT NOT NULL COMMENT '項次',
  `child_item_id` INT NOT NULL COMMENT '元件',
  `child_rev_id` INT COMMENT '指定元件版本（空白=不限，可互換版本皆可）',
  `required_country` CHAR(2) COMMENT '指定產地（空白=不限，如客戶要求日製電容）',
  `qty_per` DECIMAL(18,4) NOT NULL COMMENT '組成用量（每基準量）',
  `scrap_rate` DECIMAL(6,4) NOT NULL DEFAULT 0 COMMENT '損耗率',
  `op_seq` SMALLINT COMMENT '投入工序',
  `issue_type` CHAR(1) NOT NULL DEFAULT 'P' COMMENT 'P 領料、B 倒扣（完工扣料）、N 不發料',
  `is_phantom` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '虛設件（展開時穿透）',
  `effective_date` DATE NOT NULL DEFAULT '2000-01-01' COMMENT '生效日',
  `obsolete_date` DATE COMMENT '失效日',
  `note` VARCHAR(500) COMMENT '備註',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_bom_detail_1` (`bom_id`, `line_no`),
  KEY `ix_bom_detail_1` (`child_item_id`),
  KEY `ix_bom_detail_2` (`child_item_id`, `child_rev_id`),
  CONSTRAINT `fk_bom_detail_bom_id` FOREIGN KEY (`bom_id`) REFERENCES `bom_header` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bom_detail_child_item_id` FOREIGN KEY (`child_item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bom_detail_child_rev_id` FOREIGN KEY (`child_rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bom_detail_required_country` FOREIGN KEY (`required_country`) REFERENCES `bas_country` (`country_code`) ON DELETE RESTRICT,
  CONSTRAINT `ck_bom_detail_1` CHECK (qty_per > 0),
  CONSTRAINT `ck_bom_detail_2` CHECK (issue_type IN ('P','B','N'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='BOM 單身';

-- 替代料：BOM 元件可用的替代料（BOM 單身 1:N）
CREATE TABLE IF NOT EXISTS `bom_substitute` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `bom_detail_id` INT NOT NULL COMMENT 'BOM 單身',
  `sub_item_id` INT NOT NULL COMMENT '替代料件',
  `sub_rev_id` INT COMMENT '替代料版本',
  `sub_qty_per` DECIMAL(18,4) NOT NULL COMMENT '替代用量',
  `priority` TINYINT NOT NULL DEFAULT 1 COMMENT '優先順序',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_bom_substitute_1` (`bom_detail_id`, `sub_item_id`),
  KEY `ix_bom_substitute_1` (`sub_item_id`, `sub_rev_id`),
  CONSTRAINT `fk_bom_substitute_bom_detail_id` FOREIGN KEY (`bom_detail_id`) REFERENCES `bom_detail` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_bom_substitute_sub_item_id` FOREIGN KEY (`sub_item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bom_substitute_sub_rev_id` FOREIGN KEY (`sub_rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='替代料';

-- 工程變更：ECN：BOM 改版的申請、核准與生效日
CREATE TABLE IF NOT EXISTS `bom_ecn` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `ecn_no` VARCHAR(20) NOT NULL COMMENT '變更單號',
  `ecn_date` DATE NOT NULL COMMENT '申請日',
  `bom_id` INT NOT NULL COMMENT '變更的 BOM',
  `new_bom_id` INT COMMENT '新版 BOM',
  `from_rev_id` INT COMMENT '變更前版本',
  `to_rev_id` INT COMMENT '變更後版本',
  `reason` VARCHAR(200) NOT NULL COMMENT '變更原因',
  `change_desc` TEXT COMMENT '變更內容',
  `effective_date` DATE NOT NULL COMMENT '生效日',
  `requested_by` INT COMMENT '申請人',
  `status` CHAR(1) NOT NULL DEFAULT 'D' COMMENT 'D 草稿、A 核准、E 已生效、X 作廢',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_bom_ecn_ecn_no` (`ecn_no`),
  CONSTRAINT `fk_bom_ecn_bom_id` FOREIGN KEY (`bom_id`) REFERENCES `bom_header` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bom_ecn_new_bom_id` FOREIGN KEY (`new_bom_id`) REFERENCES `bom_header` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bom_ecn_from_rev_id` FOREIGN KEY (`from_rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bom_ecn_to_rev_id` FOREIGN KEY (`to_rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bom_ecn_requested_by` FOREIGN KEY (`requested_by`) REFERENCES `bas_employee` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bom_ecn_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_bom_ecn_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_bom_ecn_1` CHECK (status IN ('D','A','E','X'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工程變更';

-- ─────────────── MPS 主生產排程（3 張）───────────────
-- 主生產排程單頭：MPS 版本：時距、計畫期間、凍結期
CREATE TABLE IF NOT EXISTS `mps_plan_h` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `mps_no` VARCHAR(20) NOT NULL COMMENT '排程單號',
  `plan_date` DATE NOT NULL COMMENT '編製日',
  `bucket_type` CHAR(1) NOT NULL DEFAULT 'W' COMMENT '時距 D/W/M',
  `horizon_start` DATE NOT NULL COMMENT '計畫起日',
  `horizon_end` DATE NOT NULL COMMENT '計畫迄日',
  `frozen_until` DATE COMMENT '凍結期（之前不可變動）',
  `forecast_id` INT COMMENT '引用預測',
  `status` CHAR(1) NOT NULL DEFAULT 'D' COMMENT 'D 草稿、C 確認、R 已執行 MRP、X 作廢',
  `note` VARCHAR(500) COMMENT '備註',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_mps_plan_h_mps_no` (`mps_no`),
  CONSTRAINT `fk_mps_plan_h_forecast_id` FOREIGN KEY (`forecast_id`) REFERENCES `fct_forecast_h` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_mps_plan_h_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_mps_plan_h_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_mps_plan_h_1` CHECK (bucket_type IN ('D','W','M')),
  CONSTRAINT `ck_mps_plan_h_2` CHECK (status IN ('D','C','R','X')),
  CONSTRAINT `ck_mps_plan_h_3` CHECK (horizon_end >= horizon_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='主生產排程單頭';

-- 主生產排程明細：MPS 料件 × 期間：預測、訂單、預計庫存、MPS 量、ATP
CREATE TABLE IF NOT EXISTS `mps_plan_d` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `mps_id` INT NOT NULL COMMENT '排程單頭',
  `item_id` INT NOT NULL COMMENT '料件（is_mps_item）',
  `period_start` DATE NOT NULL COMMENT '期間起日',
  `forecast_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '預測需求',
  `order_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '訂單需求',
  `projected_oh` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '預計在庫量',
  `mps_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '主排程量（完工量）',
  `atp_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '可承諾量 ATP',
  `is_firm` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '人工確定（不被重算覆蓋）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_mps_plan_d_1` (`mps_id`, `item_id`, `period_start`),
  CONSTRAINT `fk_mps_plan_d_mps_id` FOREIGN KEY (`mps_id`) REFERENCES `mps_plan_h` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mps_plan_d_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='主生產排程明細';

-- MPS 需求對應：MPS 明細 ↔ 訂單/預測明細（多對多橋接表，部分數量）
CREATE TABLE IF NOT EXISTS `mps_demand_link` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `mps_line_id` BIGINT NOT NULL COMMENT 'MPS 明細',
  `demand_type` CHAR(1) NOT NULL COMMENT 'S 訂單、F 預測',
  `so_line_id` BIGINT COMMENT '訂單明細',
  `fc_line_id` BIGINT COMMENT '預測明細',
  `linked_qty` DECIMAL(18,4) NOT NULL COMMENT '對應數量',
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_mps_demand_link_mps_line_id` FOREIGN KEY (`mps_line_id`) REFERENCES `mps_plan_d` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mps_demand_link_so_line_id` FOREIGN KEY (`so_line_id`) REFERENCES `sal_order_d` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_mps_demand_link_fc_line_id` FOREIGN KEY (`fc_line_id`) REFERENCES `fct_forecast_d` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_mps_demand_link_1` CHECK (demand_type IN ('S','F')),
  CONSTRAINT `ck_mps_demand_link_2` CHECK ((demand_type='S' AND so_line_id IS NOT NULL) OR (demand_type='F' AND fc_line_id IS NOT NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MPS 需求對應';

-- ─────────────── MRP 物料需求規劃（5 張）───────────────
-- MRP 執行批次：每次 MRP 運算的參數與結果摘要
CREATE TABLE IF NOT EXISTS `mrp_run` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `run_no` VARCHAR(20) NOT NULL COMMENT '執行編號',
  `mps_id` INT NOT NULL COMMENT '依據 MPS',
  `run_mode` CHAR(1) NOT NULL DEFAULT 'R' COMMENT 'R 全部重算（再生法）、N 淨變法',
  `plan_start` DATE NOT NULL COMMENT '計畫起日',
  `horizon_days` SMALLINT NOT NULL DEFAULT 90 COMMENT '計畫天數',
  `bucket_type` CHAR(1) NOT NULL DEFAULT 'D' COMMENT '時距 D/W/M',
  `use_safety_stock` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '考慮安全存量',
  `use_scrap` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '考慮損耗率',
  `started_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '開始',
  `finished_at` DATETIME COMMENT '結束',
  `run_by` INT COMMENT '執行人',
  `item_count` INT NOT NULL DEFAULT 0 COMMENT '計算料件數',
  `planned_count` INT NOT NULL DEFAULT 0 COMMENT '產生計畫訂單數',
  `status` CHAR(1) NOT NULL DEFAULT 'R' COMMENT 'R 執行中、D 完成、E 錯誤',
  `message` VARCHAR(500) COMMENT '訊息',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_mrp_run_run_no` (`run_no`),
  CONSTRAINT `fk_mrp_run_mps_id` FOREIGN KEY (`mps_id`) REFERENCES `mps_plan_h` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_mrp_run_run_by` FOREIGN KEY (`run_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_mrp_run_1` CHECK (run_mode IN ('R','N')),
  CONSTRAINT `ck_mrp_run_2` CHECK (status IN ('R','D','E'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MRP 執行批次';

-- MRP 時距表：MRP 經典表格：料件 × 期間的毛需求、預定接收、預計在庫、淨需求、計畫接收/發出
CREATE TABLE IF NOT EXISTS `mrp_record` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `run_id` INT NOT NULL COMMENT '執行批次',
  `item_id` INT NOT NULL COMMENT '料件',
  `period_start` DATE NOT NULL COMMENT '期間起日',
  `gross_req` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '毛需求（展開 Exploding）',
  `scheduled_receipt` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '預定接收（在途採購/工單）',
  `projected_oh` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '預計在庫量',
  `net_req` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '淨需求（Netting）',
  `planned_receipt` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '計畫訂單接收（批量後）',
  `planned_release` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '計畫訂單發出（前置時間位移 Offsetting）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_mrp_record_1` (`run_id`, `item_id`, `period_start`),
  CONSTRAINT `fk_mrp_record_run_id` FOREIGN KEY (`run_id`) REFERENCES `mrp_run` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mrp_record_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MRP 時距表';

-- MRP 計畫訂單：建議採購/製造/委外；確認後轉請購單或工單
CREATE TABLE IF NOT EXISTS `mrp_planned_order` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `run_id` INT NOT NULL COMMENT '執行批次',
  `item_id` INT NOT NULL COMMENT '料件',
  `rev_id` INT COMMENT '建議版本',
  `order_type` CHAR(1) NOT NULL COMMENT 'P 採購、M 製造、O 委外',
  `qty` DECIMAL(18,4) NOT NULL COMMENT '建議量',
  `release_date` DATE NOT NULL COMMENT '建議發出日（需求日 − 前置時間）',
  `due_date` DATE NOT NULL COMMENT '需求日',
  `supplier_id` INT COMMENT '建議供應商',
  `status` CHAR(1) NOT NULL DEFAULT 'N' COMMENT 'N 建議、F 確認、C 已轉單、X 取消',
  `converted_doc_no` VARCHAR(20) COMMENT '轉出單號（請購/工單）',
  PRIMARY KEY (`id`),
  KEY `ix_mrp_planned_order_1` (`item_id`, `due_date`),
  KEY `ix_mrp_planned_order_2` (`item_id`, `rev_id`),
  CONSTRAINT `fk_mrp_planned_order_run_id` FOREIGN KEY (`run_id`) REFERENCES `mrp_run` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mrp_planned_order_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_mrp_planned_order_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_mrp_planned_order_supplier_id` FOREIGN KEY (`supplier_id`) REFERENCES `pur_supplier` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_mrp_planned_order_1` CHECK (order_type IN ('P','M','O')),
  CONSTRAINT `ck_mrp_planned_order_2` CHECK (status IN ('N','F','C','X')),
  CONSTRAINT `ck_mrp_planned_order_3` CHECK (due_date >= release_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MRP 計畫訂單';

-- 需求追溯：每筆需求從哪裡來（上階計畫單/MPS/訂單/工單用料），供 pegging 查詢
CREATE TABLE IF NOT EXISTS `mrp_pegging` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `run_id` INT NOT NULL COMMENT '執行批次',
  `item_id` INT NOT NULL COMMENT '需求料件',
  `need_date` DATE NOT NULL COMMENT '需求日',
  `need_qty` DECIMAL(18,4) NOT NULL COMMENT '需求量',
  `source_type` CHAR(1) NOT NULL COMMENT 'M MPS、P 上階計畫單、W 工單用料、S 安全存量',
  `mps_line_id` BIGINT COMMENT '來源 MPS 明細',
  `parent_po_id` BIGINT COMMENT '來源上階計畫訂單',
  `source_doc_no` VARCHAR(20) COMMENT '來源單號（工單等）',
  `supply_po_id` BIGINT COMMENT '滿足此需求的計畫訂單',
  PRIMARY KEY (`id`),
  KEY `ix_mrp_pegging_1` (`run_id`, `item_id`),
  CONSTRAINT `fk_mrp_pegging_run_id` FOREIGN KEY (`run_id`) REFERENCES `mrp_run` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mrp_pegging_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_mrp_pegging_mps_line_id` FOREIGN KEY (`mps_line_id`) REFERENCES `mps_plan_d` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_mrp_pegging_parent_po_id` FOREIGN KEY (`parent_po_id`) REFERENCES `mrp_planned_order` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_mrp_pegging_supply_po_id` FOREIGN KEY (`supply_po_id`) REFERENCES `mrp_planned_order` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_mrp_pegging_1` CHECK (source_type IN ('M','P','W','S'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='需求追溯';

-- MRP 例外訊息：行動建議：提前、延後、取消、逾期、低於安全存量
CREATE TABLE IF NOT EXISTS `mrp_exception` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `run_id` INT NOT NULL COMMENT '執行批次',
  `item_id` INT NOT NULL COMMENT '料件',
  `msg_type` CHAR(3) NOT NULL COMMENT 'NEW 新增、EXP 提前、DLY 延後、CAN 取消、PDL 已逾期、SFT 低於安全存量',
  `ref_doc_no` VARCHAR(20) COMMENT '相關單號',
  `ref_date` DATE COMMENT '原日期',
  `suggest_date` DATE COMMENT '建議日期',
  `qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '數量',
  `message` VARCHAR(200) NOT NULL COMMENT '訊息',
  `is_handled` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '已處理',
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_mrp_exception_run_id` FOREIGN KEY (`run_id`) REFERENCES `mrp_run` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mrp_exception_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_mrp_exception_1` CHECK (msg_type IN ('NEW','EXP','DLY','CAN','PDL','SFT'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MRP 例外訊息';

-- ─────────────── CRP 產能需求規劃（4 張）───────────────
-- 資源清單：RCCP 用：每單位 MPS 料件約耗用各瓶頸站多少工時
CREATE TABLE IF NOT EXISTS `crp_bill_resource` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `item_id` INT NOT NULL COMMENT 'MPS 料件',
  `wc_id` INT NOT NULL COMMENT '工作中心',
  `hours_per_unit` DECIMAL(12,6) NOT NULL COMMENT '每單位工時',
  `offset_days` SMALLINT NOT NULL DEFAULT 0 COMMENT '相對完工日提前天數',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_crp_bill_resource_1` (`item_id`, `wc_id`),
  CONSTRAINT `fk_crp_bill_resource_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_crp_bill_resource_wc_id` FOREIGN KEY (`wc_id`) REFERENCES `rou_work_center` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='資源清單';

-- 產能運算批次：RCCP（依 MPS）或 CRP（依 MRP 計畫單＋已發放工單）
CREATE TABLE IF NOT EXISTS `crp_run` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `run_no` VARCHAR(20) NOT NULL COMMENT '執行編號',
  `run_type` CHAR(1) NOT NULL COMMENT 'R 粗略產能 RCCP、C 細部產能 CRP',
  `mps_id` INT COMMENT '依據 MPS',
  `mrp_run_id` INT COMMENT '依據 MRP',
  `horizon_start` DATE NOT NULL COMMENT '期間起',
  `horizon_end` DATE NOT NULL COMMENT '期間迄',
  `bucket_type` CHAR(1) NOT NULL DEFAULT 'D' COMMENT '時距 D/W/M',
  `run_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '執行時間',
  `run_by` INT COMMENT '執行人',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_crp_run_run_no` (`run_no`),
  CONSTRAINT `fk_crp_run_mps_id` FOREIGN KEY (`mps_id`) REFERENCES `mps_plan_h` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_crp_run_mrp_run_id` FOREIGN KEY (`mrp_run_id`) REFERENCES `mrp_run` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_crp_run_run_by` FOREIGN KEY (`run_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_crp_run_1` CHECK (run_type IN ('R','C'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='產能運算批次';

-- 工作中心負荷：工作中心 × 期間：需求工時、可用工時、負荷率
CREATE TABLE IF NOT EXISTS `crp_load` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `run_id` INT NOT NULL COMMENT '產能批次',
  `wc_id` INT NOT NULL COMMENT '工作中心',
  `period_start` DATE NOT NULL COMMENT '期間起日',
  `required_hours` DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT '需求工時',
  `available_hours` DECIMAL(12,2) NOT NULL DEFAULT 0 COMMENT '可用工時',
  `load_pct` DECIMAL(8,2) NOT NULL DEFAULT 0 COMMENT '負荷率 %',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_crp_load_1` (`run_id`, `wc_id`, `period_start`),
  CONSTRAINT `fk_crp_load_run_id` FOREIGN KEY (`run_id`) REFERENCES `crp_run` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_crp_load_wc_id` FOREIGN KEY (`wc_id`) REFERENCES `rou_work_center` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作中心負荷';

-- 負荷來源明細：負荷由哪張計畫單/工單的哪道工序產生
CREATE TABLE IF NOT EXISTS `crp_load_detail` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `load_id` BIGINT NOT NULL COMMENT '負荷',
  `source_type` CHAR(1) NOT NULL COMMENT 'M MPS、P 計畫訂單、W 工單',
  `source_doc_no` VARCHAR(20) NOT NULL COMMENT '來源單號',
  `item_id` INT NOT NULL COMMENT '料件',
  `op_seq` SMALLINT COMMENT '工序',
  `qty` DECIMAL(18,4) NOT NULL COMMENT '數量',
  `setup_hours` DECIMAL(12,4) NOT NULL DEFAULT 0 COMMENT '整備工時',
  `run_hours` DECIMAL(12,4) NOT NULL DEFAULT 0 COMMENT '加工工時',
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_crp_load_detail_load_id` FOREIGN KEY (`load_id`) REFERENCES `crp_load` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_crp_load_detail_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_crp_load_detail_1` CHECK (source_type IN ('M','P','W'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='負荷來源明細';

-- ─────────────── PUR 採購管理（8 張）───────────────
-- 供應商：供應商與委外廠商
CREATE TABLE IF NOT EXISTS `pur_supplier` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `sup_code` VARCHAR(20) NOT NULL COMMENT '供應商編號',
  `sup_name` VARCHAR(100) NOT NULL COMMENT '名稱',
  `short_name` VARCHAR(30) COMMENT '簡稱',
  `tax_id` CHAR(8) COMMENT '統一編號',
  `contact` VARCHAR(50) COMMENT '聯絡人',
  `phone` VARCHAR(30) COMMENT '電話',
  `email` VARCHAR(100) COMMENT 'Email',
  `address` VARCHAR(200) COMMENT '地址',
  `currency_code` CHAR(3) NOT NULL DEFAULT 'TWD' COMMENT '交易幣別',
  `payment_terms` VARCHAR(30) COMMENT '付款條件',
  `lead_time_days` SMALLINT NOT NULL DEFAULT 0 COMMENT '一般交期（天）',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '啟用 1/停用 0',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_pur_supplier_sup_code` (`sup_code`),
  CONSTRAINT `fk_pur_supplier_currency_code` FOREIGN KEY (`currency_code`) REFERENCES `bas_currency` (`currency_code`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_supplier_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_supplier_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='供應商';

-- 料件供應來源：料件 × 供應商（多對多橋接表）：報價、交期、MOQ、優先序
CREATE TABLE IF NOT EXISTS `pur_item_source` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `item_id` INT NOT NULL COMMENT '料件',
  `supplier_id` INT NOT NULL COMMENT '供應商',
  `rev_id` INT COMMENT '核可版本（空白=全部版本）',
  `mfr_part_id` INT COMMENT '供應的製造商料號',
  `origin_country` CHAR(2) COMMENT '原產國',
  `sup_item_code` VARCHAR(40) COMMENT '廠商料號',
  `unit_price` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '單價',
  `currency_code` CHAR(3) NOT NULL DEFAULT 'TWD' COMMENT '幣別',
  `lead_days` SMALLINT NOT NULL DEFAULT 0 COMMENT '交期（天）',
  `moq` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '最小訂購量',
  `priority` TINYINT NOT NULL DEFAULT 1 COMMENT '優先順序（1 最優先）',
  `valid_from` DATE COMMENT '報價生效',
  `valid_to` DATE COMMENT '報價失效',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_pur_item_source_1` (`item_id`, `supplier_id`, `mfr_part_id`),
  KEY `ix_pur_item_source_1` (`item_id`, `rev_id`),
  KEY `ix_pur_item_source_2` (`item_id`, `origin_country`),
  CONSTRAINT `fk_pur_item_source_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_item_source_supplier_id` FOREIGN KEY (`supplier_id`) REFERENCES `pur_supplier` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_item_source_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_item_source_mfr_part_id` FOREIGN KEY (`mfr_part_id`) REFERENCES `itm_mfr_part` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_item_source_origin_country` FOREIGN KEY (`origin_country`) REFERENCES `bas_country` (`country_code`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_item_source_currency_code` FOREIGN KEY (`currency_code`) REFERENCES `bas_currency` (`currency_code`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_item_source_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_item_source_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='料件供應來源';

-- 請購單頭：MRP 計畫訂單或人工請購
CREATE TABLE IF NOT EXISTS `pur_req_h` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `pr_no` VARCHAR(20) NOT NULL COMMENT '請購單號',
  `pr_date` DATE NOT NULL COMMENT '請購日',
  `dept_id` INT COMMENT '請購部門',
  `requester_id` INT COMMENT '請購人',
  `source` CHAR(1) NOT NULL DEFAULT 'M' COMMENT 'M 人工、R MRP 轉入',
  `status` CHAR(1) NOT NULL DEFAULT 'D' COMMENT 'D 草稿、A 核准、P 部分轉採購、C 結案、X 作廢',
  `note` VARCHAR(500) COMMENT '備註',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_pur_req_h_pr_no` (`pr_no`),
  CONSTRAINT `fk_pur_req_h_dept_id` FOREIGN KEY (`dept_id`) REFERENCES `bas_dept` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_req_h_requester_id` FOREIGN KEY (`requester_id`) REFERENCES `bas_employee` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_req_h_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_req_h_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_pur_req_h_1` CHECK (status IN ('D','A','P','C','X'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='請購單頭';

-- 請購單身：請購料件與需求日
CREATE TABLE IF NOT EXISTS `pur_req_d` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `pr_id` INT NOT NULL COMMENT '請購單頭',
  `line_no` SMALLINT NOT NULL COMMENT '項次',
  `item_id` INT NOT NULL COMMENT '料件',
  `rev_id` INT COMMENT '請購版本',
  `qty` DECIMAL(18,4) NOT NULL COMMENT '請購量',
  `need_date` DATE NOT NULL COMMENT '需求日',
  `suggest_supplier_id` INT COMMENT '建議供應商',
  `planned_order_id` BIGINT COMMENT '來源 MRP 計畫訂單',
  `ordered_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '已轉採購量',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_pur_req_d_1` (`pr_id`, `line_no`),
  KEY `ix_pur_req_d_1` (`item_id`, `rev_id`),
  CONSTRAINT `fk_pur_req_d_pr_id` FOREIGN KEY (`pr_id`) REFERENCES `pur_req_h` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_pur_req_d_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_req_d_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_req_d_suggest_supplier_id` FOREIGN KEY (`suggest_supplier_id`) REFERENCES `pur_supplier` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_req_d_planned_order_id` FOREIGN KEY (`planned_order_id`) REFERENCES `mrp_planned_order` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='請購單身';

-- 採購單頭：對供應商下單；未交量即 MRP 的預定接收
CREATE TABLE IF NOT EXISTS `pur_order_h` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `po_no` VARCHAR(20) NOT NULL COMMENT '採購單號',
  `po_date` DATE NOT NULL COMMENT '採購日',
  `supplier_id` INT NOT NULL COMMENT '供應商',
  `po_type` CHAR(1) NOT NULL DEFAULT 'N' COMMENT 'N 一般、O 委外加工',
  `currency_code` CHAR(3) NOT NULL DEFAULT 'TWD' COMMENT '幣別',
  `exchange_rate` DECIMAL(18,6) NOT NULL DEFAULT 1 COMMENT '匯率',
  `tax_type` CHAR(1) NOT NULL DEFAULT '1' COMMENT '1 外加、2 內含、3 零稅、4 免稅',
  `tax_rate` DECIMAL(5,4) NOT NULL DEFAULT 0.05 COMMENT '稅率',
  `buyer_id` INT COMMENT '採購人員',
  `untaxed_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '未稅金額',
  `tax_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '稅額',
  `base_untaxed_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '本位幣未稅金額',
  `base_tax_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '本位幣稅額',
  `status` CHAR(1) NOT NULL DEFAULT 'D' COMMENT 'D 草稿、A 核准、P 部分到貨、C 結案、X 作廢',
  `note` VARCHAR(500) COMMENT '備註',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_pur_order_h_po_no` (`po_no`),
  KEY `ix_pur_order_h_1` (`po_date`),
  KEY `ix_pur_order_h_2` (`currency_code`),
  CONSTRAINT `fk_pur_order_h_supplier_id` FOREIGN KEY (`supplier_id`) REFERENCES `pur_supplier` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_order_h_currency_code` FOREIGN KEY (`currency_code`) REFERENCES `bas_currency` (`currency_code`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_order_h_buyer_id` FOREIGN KEY (`buyer_id`) REFERENCES `bas_employee` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_order_h_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_order_h_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_pur_order_h_1` CHECK (po_type IN ('N','O')),
  CONSTRAINT `ck_pur_order_h_2` CHECK (status IN ('D','A','P','C','X'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='採購單頭';

-- 採購單身：採購料件、單價、交期、已交量
CREATE TABLE IF NOT EXISTS `pur_order_d` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `po_id` INT NOT NULL COMMENT '採購單頭',
  `line_no` SMALLINT NOT NULL COMMENT '項次',
  `item_id` INT NOT NULL COMMENT '料件',
  `rev_id` INT COMMENT '採購版本',
  `mfr_part_id` INT COMMENT '指定製造商料號',
  `origin_country` CHAR(2) COMMENT '指定原產國',
  `qty` DECIMAL(18,4) NOT NULL COMMENT '採購量',
  `unit_price` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '單價',
  `amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '金額',
  `base_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '本位幣金額',
  `due_date` DATE NOT NULL COMMENT '預定到貨日',
  `received_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '已驗收量',
  `pr_line_id` BIGINT COMMENT '來源請購明細',
  `wo_id` INT COMMENT '委外對應工單',
  `status` CHAR(1) NOT NULL DEFAULT 'O' COMMENT 'O 未結、C 結案、X 取消',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_pur_order_d_1` (`po_id`, `line_no`),
  KEY `ix_pur_order_d_1` (`item_id`, `due_date`),
  KEY `ix_pur_order_d_2` (`item_id`, `rev_id`),
  KEY `ix_pur_order_d_3` (`item_id`, `origin_country`),
  CONSTRAINT `fk_pur_order_d_po_id` FOREIGN KEY (`po_id`) REFERENCES `pur_order_h` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_pur_order_d_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_order_d_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_order_d_mfr_part_id` FOREIGN KEY (`mfr_part_id`) REFERENCES `itm_mfr_part` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_order_d_origin_country` FOREIGN KEY (`origin_country`) REFERENCES `bas_country` (`country_code`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_order_d_pr_line_id` FOREIGN KEY (`pr_line_id`) REFERENCES `pur_req_d` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_order_d_wo_id` FOREIGN KEY (`wo_id`) REFERENCES `sfc_work_order` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='採購單身';

-- 進貨驗收單頭：到貨、驗收、入庫
CREATE TABLE IF NOT EXISTS `pur_receipt_h` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `rcv_no` VARCHAR(20) NOT NULL COMMENT '進貨單號',
  `rcv_date` DATE NOT NULL COMMENT '進貨日',
  `supplier_id` INT NOT NULL COMMENT '供應商',
  `warehouse_id` INT NOT NULL COMMENT '入庫倉',
  `invoice_no` VARCHAR(20) COMMENT '發票號碼',
  `untaxed_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '未稅金額',
  `tax_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '稅額',
  `currency_code` CHAR(3) NOT NULL DEFAULT 'TWD' COMMENT '幣別',
  `exchange_rate` DECIMAL(18,6) NOT NULL DEFAULT 1 COMMENT '匯率（1 外幣 = ? 本位幣，依單據日帶入）',
  `base_untaxed_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '本位幣未稅金額',
  `base_tax_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '本位幣稅額',
  `status` CHAR(1) NOT NULL DEFAULT 'D' COMMENT 'D 草稿、A 已入庫、X 作廢',
  `gl_batch_id` INT COMMENT '會計拋轉批次（空白＝尚未拋轉）',
  `note` VARCHAR(500) COMMENT '備註',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_pur_receipt_h_rcv_no` (`rcv_no`),
  KEY `ix_pur_receipt_h_1` (`currency_code`),
  KEY `ix_pur_receipt_h_2` (`gl_batch_id`),
  CONSTRAINT `fk_pur_receipt_h_supplier_id` FOREIGN KEY (`supplier_id`) REFERENCES `pur_supplier` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_receipt_h_warehouse_id` FOREIGN KEY (`warehouse_id`) REFERENCES `bas_warehouse` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_receipt_h_currency_code` FOREIGN KEY (`currency_code`) REFERENCES `bas_currency` (`currency_code`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_receipt_h_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_receipt_h_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_pur_receipt_h_1` CHECK (status IN ('D','A','X'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='進貨驗收單頭';

-- 進貨驗收單身：每項的實收、合格、退回數量
CREATE TABLE IF NOT EXISTS `pur_receipt_d` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `rcv_id` INT NOT NULL COMMENT '進貨單頭',
  `line_no` SMALLINT NOT NULL COMMENT '項次',
  `po_line_id` BIGINT COMMENT '採購明細',
  `item_id` INT NOT NULL COMMENT '料件',
  `rev_id` INT COMMENT '實收版本',
  `mfr_part_id` INT COMMENT '實收製造商料號',
  `origin_country` CHAR(2) COMMENT '實收原產國',
  `date_code` VARCHAR(10) COMMENT '生產週別 Date Code，如 2645',
  `coo_cert_no` VARCHAR(40) COMMENT '原產地證明書號',
  `lot_no` VARCHAR(30) COMMENT '批號',
  `location_id` INT COMMENT '儲位',
  `receive_qty` DECIMAL(18,4) NOT NULL COMMENT '實收量',
  `accept_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '合格量',
  `reject_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '驗退量',
  `unit_price` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '單價',
  `amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '金額',
  `base_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '本位幣金額',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_pur_receipt_d_1` (`rcv_id`, `line_no`),
  KEY `ix_pur_receipt_d_1` (`item_id`, `rev_id`),
  KEY `ix_pur_receipt_d_2` (`item_id`, `origin_country`),
  CONSTRAINT `fk_pur_receipt_d_rcv_id` FOREIGN KEY (`rcv_id`) REFERENCES `pur_receipt_h` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_pur_receipt_d_po_line_id` FOREIGN KEY (`po_line_id`) REFERENCES `pur_order_d` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_receipt_d_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_receipt_d_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_receipt_d_mfr_part_id` FOREIGN KEY (`mfr_part_id`) REFERENCES `itm_mfr_part` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_receipt_d_origin_country` FOREIGN KEY (`origin_country`) REFERENCES `bas_country` (`country_code`) ON DELETE RESTRICT,
  CONSTRAINT `fk_pur_receipt_d_location_id` FOREIGN KEY (`location_id`) REFERENCES `bas_location` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='進貨驗收單身';

-- ─────────────── SFC 現場控制（10 張）───────────────
-- 工單（製令）：製造命令：生產什麼、多少、何時；未完工量即預定接收
CREATE TABLE IF NOT EXISTS `sfc_work_order` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `wo_no` VARCHAR(20) NOT NULL COMMENT '工單號',
  `wo_type` CHAR(1) NOT NULL DEFAULT 'S' COMMENT 'S 一般、R 重工、O 委外',
  `item_id` INT NOT NULL COMMENT '生產料件',
  `rev_id` INT COMMENT '生產版本',
  `bom_id` INT COMMENT '使用 BOM',
  `routing_id` INT COMMENT '使用途程',
  `plan_qty` DECIMAL(18,4) NOT NULL COMMENT '預計產量',
  `completed_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '已完工入庫量',
  `scrap_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '報廢量',
  `plan_start` DATE NOT NULL COMMENT '預計開工',
  `plan_finish` DATE NOT NULL COMMENT '預計完工',
  `actual_start` DATETIME COMMENT '實際開工',
  `actual_finish` DATETIME COMMENT '實際完工',
  `so_line_id` BIGINT COMMENT '訂單生產對應',
  `planned_order_id` BIGINT COMMENT '來源 MRP 計畫訂單',
  `parent_wo_id` INT COMMENT '上階工單（自我參照）',
  `warehouse_id` INT COMMENT '完工入庫倉',
  `supervisor_id` INT COMMENT '生產線主管',
  `priority` TINYINT NOT NULL DEFAULT 5 COMMENT '優先序',
  `status` CHAR(1) NOT NULL DEFAULT 'P' COMMENT 'P 計畫、R 已發放、S 生產中、F 完工、C 結案、X 作廢',
  `note` VARCHAR(500) COMMENT '備註',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sfc_work_order_wo_no` (`wo_no`),
  KEY `ix_sfc_work_order_1` (`item_id`, `plan_finish`),
  KEY `ix_sfc_work_order_2` (`status`),
  KEY `ix_sfc_work_order_3` (`item_id`, `rev_id`),
  CONSTRAINT `fk_sfc_work_order_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_work_order_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_work_order_bom_id` FOREIGN KEY (`bom_id`) REFERENCES `bom_header` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_work_order_routing_id` FOREIGN KEY (`routing_id`) REFERENCES `rou_routing_h` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_work_order_so_line_id` FOREIGN KEY (`so_line_id`) REFERENCES `sal_order_d` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_work_order_planned_order_id` FOREIGN KEY (`planned_order_id`) REFERENCES `mrp_planned_order` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_work_order_parent_wo_id` FOREIGN KEY (`parent_wo_id`) REFERENCES `sfc_work_order` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_work_order_warehouse_id` FOREIGN KEY (`warehouse_id`) REFERENCES `bas_warehouse` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_work_order_supervisor_id` FOREIGN KEY (`supervisor_id`) REFERENCES `bas_employee` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_work_order_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_work_order_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_sfc_work_order_1` CHECK (wo_type IN ('S','R','O')),
  CONSTRAINT `ck_sfc_work_order_2` CHECK (status IN ('P','R','S','F','C','X')),
  CONSTRAINT `ck_sfc_work_order_3` CHECK (plan_finish >= plan_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工單（製令）';

-- 工單用料：工單發放時由 BOM 展開；應領量即 MRP 的已分配量
CREATE TABLE IF NOT EXISTS `sfc_wo_material` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `wo_id` INT NOT NULL COMMENT '工單',
  `line_no` SMALLINT NOT NULL COMMENT '項次',
  `item_id` INT NOT NULL COMMENT '用料',
  `rev_id` INT COMMENT '用料版本',
  `required_country` CHAR(2) COMMENT '指定產地（由 BOM 帶入）',
  `required_qty` DECIMAL(18,4) NOT NULL COMMENT '應領量',
  `issued_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '已領量',
  `op_seq` SMALLINT COMMENT '投入工序',
  `issue_type` CHAR(1) NOT NULL DEFAULT 'P' COMMENT 'P 領料、B 倒扣、N 不發料',
  `warehouse_id` INT COMMENT '發料倉',
  `required_date` DATE NOT NULL COMMENT '需用日',
  `substitute_for_id` BIGINT COMMENT '替代哪一筆用料（自我參照）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sfc_wo_material_1` (`wo_id`, `line_no`),
  KEY `ix_sfc_wo_material_1` (`item_id`),
  KEY `ix_sfc_wo_material_2` (`item_id`, `rev_id`),
  CONSTRAINT `fk_sfc_wo_material_wo_id` FOREIGN KEY (`wo_id`) REFERENCES `sfc_work_order` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sfc_wo_material_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_wo_material_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_wo_material_required_country` FOREIGN KEY (`required_country`) REFERENCES `bas_country` (`country_code`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_wo_material_warehouse_id` FOREIGN KEY (`warehouse_id`) REFERENCES `bas_warehouse` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_wo_material_substitute_for_id` FOREIGN KEY (`substitute_for_id`) REFERENCES `sfc_wo_material` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工單用料';

-- 工單工序：工單發放時由途程複製；排程、實績、狀態
CREATE TABLE IF NOT EXISTS `sfc_wo_operation` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `wo_id` INT NOT NULL COMMENT '工單',
  `op_seq` SMALLINT NOT NULL COMMENT '工序',
  `op_name` VARCHAR(50) NOT NULL COMMENT '工序名稱',
  `wc_id` INT NOT NULL COMMENT '工作中心',
  `plan_setup_hours` DECIMAL(12,4) NOT NULL DEFAULT 0 COMMENT '標準整備工時',
  `plan_run_hours` DECIMAL(12,4) NOT NULL DEFAULT 0 COMMENT '標準加工工時（整批）',
  `plan_start` DATETIME COMMENT '排程開始',
  `plan_finish` DATETIME COMMENT '排程結束',
  `good_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '良品累計',
  `scrap_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '不良累計',
  `actual_hours` DECIMAL(12,4) NOT NULL DEFAULT 0 COMMENT '實際工時累計',
  `status` CHAR(1) NOT NULL DEFAULT 'W' COMMENT 'W 待開工、S 進行中、F 完成',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sfc_wo_operation_1` (`wo_id`, `op_seq`),
  CONSTRAINT `fk_sfc_wo_operation_wo_id` FOREIGN KEY (`wo_id`) REFERENCES `sfc_work_order` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sfc_wo_operation_wc_id` FOREIGN KEY (`wc_id`) REFERENCES `rou_work_center` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_sfc_wo_operation_1` CHECK (status IN ('W','S','F'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工單工序';

-- 請料單頭：現場向倉庫申請物料（REA：請料）
CREATE TABLE IF NOT EXISTS `sfc_request_h` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `req_no` VARCHAR(20) NOT NULL COMMENT '請料單號',
  `req_date` DATETIME NOT NULL COMMENT '請料時間',
  `wo_id` INT NOT NULL COMMENT '工單',
  `requester_id` INT COMMENT '請料人（主管）',
  `status` CHAR(1) NOT NULL DEFAULT 'D' COMMENT 'D 草稿、A 待發、P 部分發料、C 已發完、X 作廢',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sfc_request_h_req_no` (`req_no`),
  CONSTRAINT `fk_sfc_request_h_wo_id` FOREIGN KEY (`wo_id`) REFERENCES `sfc_work_order` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_request_h_requester_id` FOREIGN KEY (`requester_id`) REFERENCES `bas_employee` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_request_h_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_request_h_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_sfc_request_h_1` CHECK (status IN ('D','A','P','C','X'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='請料單頭';

-- 請料單身：請料料件、數量（REA：保留）
CREATE TABLE IF NOT EXISTS `sfc_request_d` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `req_id` INT NOT NULL COMMENT '請料單頭',
  `line_no` SMALLINT NOT NULL COMMENT '項次',
  `wo_material_id` BIGINT COMMENT '工單用料',
  `item_id` INT NOT NULL COMMENT '料件',
  `rev_id` INT COMMENT '請料版本',
  `qty` DECIMAL(18,4) NOT NULL COMMENT '請料量',
  `issued_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '已發量',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sfc_request_d_1` (`req_id`, `line_no`),
  KEY `ix_sfc_request_d_1` (`item_id`, `rev_id`),
  CONSTRAINT `fk_sfc_request_d_req_id` FOREIGN KEY (`req_id`) REFERENCES `sfc_request_h` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sfc_request_d_wo_material_id` FOREIGN KEY (`wo_material_id`) REFERENCES `sfc_wo_material` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_request_d_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_request_d_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='請料單身';

-- 領退料單頭：倉庫發料/現場退料（REA：發料）
CREATE TABLE IF NOT EXISTS `sfc_issue_h` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `issue_no` VARCHAR(20) NOT NULL COMMENT '領料單號',
  `issue_date` DATETIME NOT NULL COMMENT '發料時間',
  `issue_type` CHAR(1) NOT NULL DEFAULT 'I' COMMENT 'I 領料、R 退料、O 超領、B 倒扣',
  `wo_id` INT NOT NULL COMMENT '工單',
  `req_id` INT COMMENT '依據請料單（REA：履行）',
  `warehouse_id` INT NOT NULL COMMENT '倉庫',
  `keeper_id` INT COMMENT '倉管人員',
  `status` CHAR(1) NOT NULL DEFAULT 'D' COMMENT 'D 草稿、A 已過帳、X 作廢',
  `note` VARCHAR(500) COMMENT '備註',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sfc_issue_h_issue_no` (`issue_no`),
  CONSTRAINT `fk_sfc_issue_h_wo_id` FOREIGN KEY (`wo_id`) REFERENCES `sfc_work_order` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_issue_h_req_id` FOREIGN KEY (`req_id`) REFERENCES `sfc_request_h` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_issue_h_warehouse_id` FOREIGN KEY (`warehouse_id`) REFERENCES `bas_warehouse` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_issue_h_keeper_id` FOREIGN KEY (`keeper_id`) REFERENCES `bas_employee` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_issue_h_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_issue_h_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_sfc_issue_h_1` CHECK (issue_type IN ('I','R','O','B')),
  CONSTRAINT `ck_sfc_issue_h_2` CHECK (status IN ('D','A','X'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='領退料單頭';

-- 領退料單身：實發料件、批號、數量
CREATE TABLE IF NOT EXISTS `sfc_issue_d` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `issue_id` INT NOT NULL COMMENT '領料單頭',
  `line_no` SMALLINT NOT NULL COMMENT '項次',
  `wo_material_id` BIGINT COMMENT '工單用料',
  `req_line_id` BIGINT COMMENT '請料明細',
  `item_id` INT NOT NULL COMMENT '料件',
  `rev_id` INT COMMENT '實發版本',
  `lot_no` VARCHAR(30) COMMENT '批號',
  `location_id` INT COMMENT '儲位',
  `qty` DECIMAL(18,4) NOT NULL COMMENT '數量',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sfc_issue_d_1` (`issue_id`, `line_no`),
  KEY `ix_sfc_issue_d_1` (`item_id`, `rev_id`),
  CONSTRAINT `fk_sfc_issue_d_issue_id` FOREIGN KEY (`issue_id`) REFERENCES `sfc_issue_h` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sfc_issue_d_wo_material_id` FOREIGN KEY (`wo_material_id`) REFERENCES `sfc_wo_material` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_issue_d_req_line_id` FOREIGN KEY (`req_line_id`) REFERENCES `sfc_request_d` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_issue_d_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_issue_d_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_issue_d_location_id` FOREIGN KEY (`location_id`) REFERENCES `bas_location` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='領退料單身';

-- 報工（計工單）：人工/機器操作實績：工時、良品、不良（REA：人力操作、機器操作）
CREATE TABLE IF NOT EXISTS `sfc_report` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `report_no` VARCHAR(20) NOT NULL COMMENT '報工單號',
  `report_type` CHAR(1) NOT NULL DEFAULT 'L' COMMENT 'L 人工、M 機器',
  `wo_op_id` BIGINT NOT NULL COMMENT '工單工序',
  `employee_id` INT COMMENT '作業員',
  `machine_id` INT COMMENT '機器',
  `wc_id` INT NOT NULL COMMENT '工作中心',
  `start_time` DATETIME NOT NULL COMMENT '開始',
  `end_time` DATETIME COMMENT '結束',
  `setup_hours` DECIMAL(10,4) NOT NULL DEFAULT 0 COMMENT '整備工時',
  `run_hours` DECIMAL(10,4) NOT NULL DEFAULT 0 COMMENT '加工工時',
  `good_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '良品',
  `scrap_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '不良',
  `scrap_reason` VARCHAR(100) COMMENT '不良原因',
  `gl_batch_id` INT COMMENT '會計拋轉批次（空白＝尚未拋轉）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sfc_report_report_no` (`report_no`),
  KEY `ix_sfc_report_1` (`start_time`),
  KEY `ix_sfc_report_2` (`gl_batch_id`),
  CONSTRAINT `fk_sfc_report_wo_op_id` FOREIGN KEY (`wo_op_id`) REFERENCES `sfc_wo_operation` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_report_employee_id` FOREIGN KEY (`employee_id`) REFERENCES `bas_employee` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_report_machine_id` FOREIGN KEY (`machine_id`) REFERENCES `rou_machine` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_report_wc_id` FOREIGN KEY (`wc_id`) REFERENCES `rou_work_center` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_sfc_report_1` CHECK (report_type IN ('L','M')),
  CONSTRAINT `ck_sfc_report_2` CHECK (end_time IS NULL OR end_time >= start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='報工（計工單）';

-- 移轉單：在製品從前一工序移到下一工序
CREATE TABLE IF NOT EXISTS `sfc_move` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `move_no` VARCHAR(20) NOT NULL COMMENT '移轉單號',
  `move_time` DATETIME NOT NULL COMMENT '移轉時間',
  `wo_id` INT NOT NULL COMMENT '工單',
  `from_op_seq` SMALLINT NOT NULL COMMENT '自工序',
  `to_op_seq` SMALLINT COMMENT '至工序（空白=完工）',
  `qty` DECIMAL(18,4) NOT NULL COMMENT '數量',
  `mover_id` INT COMMENT '移轉人',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sfc_move_move_no` (`move_no`),
  CONSTRAINT `fk_sfc_move_wo_id` FOREIGN KEY (`wo_id`) REFERENCES `sfc_work_order` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_move_mover_id` FOREIGN KEY (`mover_id`) REFERENCES `bas_employee` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='移轉單';

-- 完工入庫：成品/半成品生產入庫（REA：生產運轉產出）
CREATE TABLE IF NOT EXISTS `sfc_complete` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `complete_no` VARCHAR(20) NOT NULL COMMENT '入庫單號',
  `complete_date` DATETIME NOT NULL COMMENT '入庫時間',
  `wo_id` INT NOT NULL COMMENT '工單',
  `rev_id` INT COMMENT '入庫版本',
  `warehouse_id` INT NOT NULL COMMENT '入庫倉',
  `location_id` INT COMMENT '儲位',
  `lot_no` VARCHAR(30) COMMENT '生產批號',
  `qty` DECIMAL(18,4) NOT NULL COMMENT '入庫量',
  `qc_result` CHAR(1) NOT NULL DEFAULT 'W' COMMENT 'P 合格、F 不合格、W 免驗',
  `status` CHAR(1) NOT NULL DEFAULT 'D' COMMENT 'D 草稿、A 已過帳、X 作廢',
  `note` VARCHAR(500) COMMENT '備註',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sfc_complete_complete_no` (`complete_no`),
  CONSTRAINT `fk_sfc_complete_wo_id` FOREIGN KEY (`wo_id`) REFERENCES `sfc_work_order` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_complete_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_complete_warehouse_id` FOREIGN KEY (`warehouse_id`) REFERENCES `bas_warehouse` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_complete_location_id` FOREIGN KEY (`location_id`) REFERENCES `bas_location` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_complete_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_sfc_complete_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_sfc_complete_1` CHECK (qc_result IN ('P','F','W')),
  CONSTRAINT `ck_sfc_complete_2` CHECK (status IN ('D','A','X'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='完工入庫';

-- ─────────────── INV 存貨控制（11 張）───────────────
-- 批號：批號主檔（料件 1:N 批號）
CREATE TABLE IF NOT EXISTS `inv_lot` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `item_id` INT NOT NULL COMMENT '料件',
  `rev_id` INT COMMENT '批號所屬版本',
  `mfr_part_id` INT COMMENT '製造商料號',
  `origin_country` CHAR(2) COMMENT '原產國',
  `date_code` VARCHAR(10) COMMENT '生產週別 Date Code',
  `lot_no` VARCHAR(30) NOT NULL COMMENT '批號',
  `received_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '首次入庫時間（先進先出排序依據）',
  `mfg_date` DATE COMMENT '製造日',
  `exp_date` DATE COMMENT '有效日（先到期先出依據）',
  `supplier_id` INT COMMENT '供應商',
  `source_doc_no` VARCHAR(20) COMMENT '來源單號',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_inv_lot_1` (`item_id`, `lot_no`),
  KEY `ix_inv_lot_1` (`item_id`, `rev_id`),
  KEY `ix_inv_lot_2` (`item_id`, `origin_country`),
  CONSTRAINT `fk_inv_lot_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_lot_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_lot_mfr_part_id` FOREIGN KEY (`mfr_part_id`) REFERENCES `itm_mfr_part` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_lot_origin_country` FOREIGN KEY (`origin_country`) REFERENCES `bas_country` (`country_code`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_lot_supplier_id` FOREIGN KEY (`supplier_id`) REFERENCES `pur_supplier` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_lot_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_lot_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='批號';

-- 庫存餘額：料件 × 倉庫 × 儲位 × 批號的現有量與保留量（Inventory Status）
CREATE TABLE IF NOT EXISTS `inv_balance` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `item_id` INT NOT NULL COMMENT '料件',
  `warehouse_id` INT NOT NULL COMMENT '倉庫',
  `location_id` INT COMMENT '儲位',
  `lot_id` INT COMMENT '批號',
  `loc_key` INT AS (IFNULL(location_id,0)) PERSISTENT COMMENT '唯一鍵輔助（自動）',
  `lot_key` INT AS (IFNULL(lot_id,0)) PERSISTENT COMMENT '唯一鍵輔助（自動）',
  `rev_id` INT COMMENT '版本',
  `rev_key` INT AS (IFNULL(rev_id,0)) PERSISTENT COMMENT '唯一鍵輔助（自動）',
  `on_hand_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '現有量',
  `allocated_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '已保留（分配）量',
  `last_txn_at` DATETIME COMMENT '最後異動',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_inv_balance_1` (`item_id`, `warehouse_id`, `loc_key`, `lot_key`, `rev_key`),
  KEY `ix_inv_balance_1` (`item_id`, `rev_id`),
  CONSTRAINT `fk_inv_balance_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_balance_warehouse_id` FOREIGN KEY (`warehouse_id`) REFERENCES `bas_warehouse` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_balance_location_id` FOREIGN KEY (`location_id`) REFERENCES `bas_location` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_balance_lot_id` FOREIGN KEY (`lot_id`) REFERENCES `inv_lot` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_balance_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='庫存餘額';

-- 存貨異動帳：所有入出庫的流水帳（單一真相，餘額可由此重建）
CREATE TABLE IF NOT EXISTS `inv_txn` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `txn_time` DATETIME NOT NULL COMMENT '異動時間',
  `doc_type` VARCHAR(10) NOT NULL COMMENT '單別',
  `doc_no` VARCHAR(20) NOT NULL COMMENT '單號',
  `doc_line_no` SMALLINT COMMENT '項次',
  `item_id` INT NOT NULL COMMENT '料件',
  `rev_id` INT COMMENT '異動版本',
  `warehouse_id` INT NOT NULL COMMENT '倉庫',
  `location_id` INT COMMENT '儲位',
  `lot_id` INT COMMENT '批號',
  `qty` DECIMAL(18,4) NOT NULL COMMENT '數量（入正出負）',
  `unit_cost` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '單位成本',
  `amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '金額',
  `wo_id` INT COMMENT '相關工單',
  `gl_batch_id` INT COMMENT '會計拋轉批次（空白＝尚未拋轉）',
  `created_by` INT COMMENT '建立者',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  PRIMARY KEY (`id`),
  KEY `ix_inv_txn_1` (`item_id`, `txn_time`),
  KEY `ix_inv_txn_2` (`doc_type`, `doc_no`),
  KEY `ix_inv_txn_3` (`item_id`, `rev_id`),
  KEY `ix_inv_txn_4` (`gl_batch_id`),
  CONSTRAINT `fk_inv_txn_doc_type` FOREIGN KEY (`doc_type`) REFERENCES `sys_doc_type` (`doc_type`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_txn_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_txn_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_txn_warehouse_id` FOREIGN KEY (`warehouse_id`) REFERENCES `bas_warehouse` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_txn_location_id` FOREIGN KEY (`location_id`) REFERENCES `bas_location` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_txn_lot_id` FOREIGN KEY (`lot_id`) REFERENCES `inv_lot` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_txn_wo_id` FOREIGN KEY (`wo_id`) REFERENCES `sfc_work_order` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_txn_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='存貨異動帳';

-- 先進先出成本層：每次入庫產生一層；出庫依入庫時間由舊到新扣減剩餘量
CREATE TABLE IF NOT EXISTS `inv_layer` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `item_id` INT NOT NULL COMMENT '料件',
  `warehouse_id` INT NOT NULL COMMENT '倉庫',
  `lot_id` INT COMMENT '批號',
  `rev_id` INT COMMENT '版本',
  `in_txn_id` BIGINT NOT NULL COMMENT '產生此層的入庫異動',
  `received_at` DATETIME NOT NULL COMMENT '入庫時間（先進先出排序）',
  `in_qty` DECIMAL(18,4) NOT NULL COMMENT '入庫量',
  `remaining_qty` DECIMAL(18,4) NOT NULL COMMENT '剩餘量',
  `unit_cost` DECIMAL(18,6) NOT NULL COMMENT '本位幣單位成本（含匯率換算、運費分攤）',
  `is_closed` TINYINT(1) AS (IF(remaining_qty <= 0, 1, 0)) PERSISTENT COMMENT '已耗盡（自動）',
  PRIMARY KEY (`id`),
  KEY `ix_inv_layer_1` (`item_id`, `warehouse_id`, `is_closed`, `received_at`),
  KEY `ix_inv_layer_2` (`item_id`, `rev_id`),
  CONSTRAINT `fk_inv_layer_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_layer_warehouse_id` FOREIGN KEY (`warehouse_id`) REFERENCES `bas_warehouse` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_layer_lot_id` FOREIGN KEY (`lot_id`) REFERENCES `inv_lot` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_layer_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_layer_in_txn_id` FOREIGN KEY (`in_txn_id`) REFERENCES `inv_txn` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_inv_layer_1` CHECK (remaining_qty >= 0),
  CONSTRAINT `ck_inv_layer_2` CHECK (remaining_qty <= in_qty)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='先進先出成本層';

-- 成本層耗用明細：出庫異動 × 成本層（多對多）：每筆出庫吃掉哪些層、各多少
CREATE TABLE IF NOT EXISTS `inv_layer_consume` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `out_txn_id` BIGINT NOT NULL COMMENT '出庫異動',
  `layer_id` BIGINT NOT NULL COMMENT '被耗用的成本層',
  `qty` DECIMAL(18,4) NOT NULL COMMENT '耗用量',
  `unit_cost` DECIMAL(18,6) NOT NULL COMMENT '單位成本',
  `amount` DECIMAL(18,2) NOT NULL COMMENT '成本金額',
  PRIMARY KEY (`id`),
  KEY `ix_inv_layer_consume_1` (`layer_id`),
  CONSTRAINT `fk_inv_layer_consume_out_txn_id` FOREIGN KEY (`out_txn_id`) REFERENCES `inv_txn` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_layer_consume_layer_id` FOREIGN KEY (`layer_id`) REFERENCES `inv_layer` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='成本層耗用明細';

-- 調撥單頭：倉庫間移轉
CREATE TABLE IF NOT EXISTS `inv_transfer_h` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `trf_no` VARCHAR(20) NOT NULL COMMENT '調撥單號',
  `trf_date` DATE NOT NULL COMMENT '調撥日',
  `from_wh_id` INT NOT NULL COMMENT '撥出倉',
  `to_wh_id` INT NOT NULL COMMENT '撥入倉',
  `status` CHAR(1) NOT NULL DEFAULT 'D' COMMENT 'D 草稿、A 已過帳、X 作廢',
  `note` VARCHAR(500) COMMENT '備註',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_inv_transfer_h_trf_no` (`trf_no`),
  CONSTRAINT `fk_inv_transfer_h_from_wh_id` FOREIGN KEY (`from_wh_id`) REFERENCES `bas_warehouse` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_transfer_h_to_wh_id` FOREIGN KEY (`to_wh_id`) REFERENCES `bas_warehouse` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_transfer_h_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_transfer_h_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_inv_transfer_h_1` CHECK (from_wh_id <> to_wh_id),
  CONSTRAINT `ck_inv_transfer_h_2` CHECK (status IN ('D','A','X'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='調撥單頭';

-- 調撥單身：調撥料件與數量
CREATE TABLE IF NOT EXISTS `inv_transfer_d` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `trf_id` INT NOT NULL COMMENT '調撥單頭',
  `line_no` SMALLINT NOT NULL COMMENT '項次',
  `item_id` INT NOT NULL COMMENT '料件',
  `rev_id` INT COMMENT '調撥版本',
  `lot_no` VARCHAR(30) COMMENT '批號',
  `qty` DECIMAL(18,4) NOT NULL COMMENT '數量',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_inv_transfer_d_1` (`trf_id`, `line_no`),
  KEY `ix_inv_transfer_d_1` (`item_id`, `rev_id`),
  CONSTRAINT `fk_inv_transfer_d_trf_id` FOREIGN KEY (`trf_id`) REFERENCES `inv_transfer_h` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_inv_transfer_d_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_transfer_d_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='調撥單身';

-- 庫存調整單頭：報廢、盤盈虧、其他調整
CREATE TABLE IF NOT EXISTS `inv_adjust_h` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `adj_no` VARCHAR(20) NOT NULL COMMENT '調整單號',
  `adj_date` DATE NOT NULL COMMENT '調整日',
  `warehouse_id` INT NOT NULL COMMENT '倉庫',
  `reason` CHAR(1) NOT NULL DEFAULT 'O' COMMENT 'C 盤點差異、S 報廢、O 其他',
  `count_id` INT COMMENT '來源盤點單',
  `status` CHAR(1) NOT NULL DEFAULT 'D' COMMENT 'D 草稿、A 已過帳、X 作廢',
  `note` VARCHAR(500) COMMENT '備註',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_inv_adjust_h_adj_no` (`adj_no`),
  CONSTRAINT `fk_inv_adjust_h_warehouse_id` FOREIGN KEY (`warehouse_id`) REFERENCES `bas_warehouse` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_adjust_h_count_id` FOREIGN KEY (`count_id`) REFERENCES `inv_count_h` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_adjust_h_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_adjust_h_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_inv_adjust_h_1` CHECK (reason IN ('C','S','O')),
  CONSTRAINT `ck_inv_adjust_h_2` CHECK (status IN ('D','A','X'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='庫存調整單頭';

-- 庫存調整單身：調整料件與數量（正增負減）
CREATE TABLE IF NOT EXISTS `inv_adjust_d` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `adj_id` INT NOT NULL COMMENT '調整單頭',
  `line_no` SMALLINT NOT NULL COMMENT '項次',
  `item_id` INT NOT NULL COMMENT '料件',
  `rev_id` INT COMMENT '調整版本',
  `lot_no` VARCHAR(30) COMMENT '批號',
  `qty` DECIMAL(18,4) NOT NULL COMMENT '調整量（正增負減）',
  `unit_cost` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '單位成本',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_inv_adjust_d_1` (`adj_id`, `line_no`),
  KEY `ix_inv_adjust_d_1` (`item_id`, `rev_id`),
  CONSTRAINT `fk_inv_adjust_d_adj_id` FOREIGN KEY (`adj_id`) REFERENCES `inv_adjust_h` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_inv_adjust_d_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_adjust_d_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='庫存調整單身';

-- 盤點單頭：定期/循環盤點
CREATE TABLE IF NOT EXISTS `inv_count_h` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `count_no` VARCHAR(20) NOT NULL COMMENT '盤點單號',
  `count_date` DATE NOT NULL COMMENT '盤點日',
  `warehouse_id` INT NOT NULL COMMENT '倉庫',
  `count_type` CHAR(1) NOT NULL DEFAULT 'P' COMMENT 'P 全面盤點、C 循環盤點',
  `status` CHAR(1) NOT NULL DEFAULT 'D' COMMENT 'D 盤點中、F 已完成、A 已調整、X 作廢',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_inv_count_h_count_no` (`count_no`),
  CONSTRAINT `fk_inv_count_h_warehouse_id` FOREIGN KEY (`warehouse_id`) REFERENCES `bas_warehouse` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_count_h_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_count_h_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_inv_count_h_1` CHECK (count_type IN ('P','C')),
  CONSTRAINT `ck_inv_count_h_2` CHECK (status IN ('D','F','A','X'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='盤點單頭';

-- 盤點單身：帳面量 vs 實盤量
CREATE TABLE IF NOT EXISTS `inv_count_d` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `count_id` INT NOT NULL COMMENT '盤點單頭',
  `line_no` SMALLINT NOT NULL COMMENT '項次',
  `item_id` INT NOT NULL COMMENT '料件',
  `rev_id` INT COMMENT '盤點版本',
  `location_id` INT COMMENT '儲位',
  `lot_no` VARCHAR(30) COMMENT '批號',
  `book_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '帳面量',
  `count_qty` DECIMAL(18,4) COMMENT '實盤量',
  `diff_qty` DECIMAL(18,4) AS (count_qty - book_qty) PERSISTENT COMMENT '差異（自動）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_inv_count_d_1` (`count_id`, `line_no`),
  KEY `ix_inv_count_d_1` (`item_id`, `rev_id`),
  CONSTRAINT `fk_inv_count_d_count_id` FOREIGN KEY (`count_id`) REFERENCES `inv_count_h` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_inv_count_d_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_count_d_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_inv_count_d_location_id` FOREIGN KEY (`location_id`) REFERENCES `bas_location` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='盤點單身';

-- ─────────────── ACC 會計與財務分析（10 張）───────────────
-- 會計期間：月結與關帳（關帳後不可再異動）
CREATE TABLE IF NOT EXISTS `acc_period` (
  `period` CHAR(6) NOT NULL COMMENT '期別 yyyymm',
  `start_date` DATE NOT NULL COMMENT '起日',
  `end_date` DATE NOT NULL COMMENT '迄日',
  `is_closed` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '已關帳',
  `closed_at` DATETIME COMMENT '關帳時間',
  `closed_by` INT COMMENT '關帳人',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`period`),
  CONSTRAINT `fk_acc_period_closed_by` FOREIGN KEY (`closed_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_period_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_period_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='會計期間';

-- 會計科目對應：拋轉傳票時，各成本項目對應到一般公司會計的科目
CREATE TABLE IF NOT EXISTS `acc_account_map` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `map_code` VARCHAR(20) NOT NULL COMMENT '對應代碼，如 INV_RAW、WIP、FG、COGS、AP、PPV',
  `map_name` VARCHAR(50) NOT NULL COMMENT '說明',
  `account_no` VARCHAR(20) NOT NULL COMMENT '會計科目代號',
  `account_name` VARCHAR(50) NOT NULL COMMENT '會計科目名稱',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_acc_account_map_map_code` (`map_code`),
  CONSTRAINT `fk_acc_account_map_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_account_map_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='會計科目對應';

-- 工作中心費率：每工時的直接人工與製造費用分攤率
CREATE TABLE IF NOT EXISTS `acc_wc_rate` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `wc_id` INT NOT NULL COMMENT '工作中心',
  `period` CHAR(6) NOT NULL COMMENT '期別',
  `labor_rate` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '人工費率（元/時）',
  `overhead_rate` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '製費率（元/時）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_acc_wc_rate_1` (`wc_id`, `period`),
  CONSTRAINT `fk_acc_wc_rate_wc_id` FOREIGN KEY (`wc_id`) REFERENCES `rou_work_center` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_wc_rate_period` FOREIGN KEY (`period`) REFERENCES `acc_period` (`period`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_wc_rate_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_wc_rate_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作中心費率';

-- 料件成本：標準成本（BOM＋途程累算）或月加權實際成本
CREATE TABLE IF NOT EXISTS `acc_item_cost` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `item_id` INT NOT NULL COMMENT '料件',
  `rev_id` INT COMMENT '成本版本（空白=料件通用）',
  `rev_key` INT AS (IFNULL(rev_id,0)) PERSISTENT COMMENT '唯一鍵輔助（自動）',
  `cost_type` CHAR(1) NOT NULL COMMENT 'S 標準、A 實際',
  `period` CHAR(6) NOT NULL COMMENT '期別',
  `material_cost` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '材料',
  `labor_cost` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '人工',
  `overhead_cost` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '製費',
  `outsource_cost` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '委外',
  `total_cost` DECIMAL(18,6) AS (material_cost + labor_cost + overhead_cost + outsource_cost) PERSISTENT COMMENT '合計（自動）',
  `rolled_at` DATETIME COMMENT '成本累算時間',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_acc_item_cost_1` (`item_id`, `cost_type`, `period`, `rev_key`),
  KEY `ix_acc_item_cost_1` (`item_id`, `rev_id`),
  CONSTRAINT `fk_acc_item_cost_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_item_cost_rev_id` FOREIGN KEY (`rev_id`) REFERENCES `itm_revision` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_item_cost_period` FOREIGN KEY (`period`) REFERENCES `acc_period` (`period`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_item_cost_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_item_cost_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_acc_item_cost_1` CHECK (cost_type IN ('S','A'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='料件成本';

-- 存貨月結：料件 × 倉庫 × 期別：期初、入、出、期末數量金額（存貨週轉分析）
CREATE TABLE IF NOT EXISTS `acc_inv_month` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `period` CHAR(6) NOT NULL COMMENT '期別',
  `item_id` INT NOT NULL COMMENT '料件',
  `warehouse_id` INT NOT NULL COMMENT '倉庫',
  `begin_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '期初量',
  `begin_amt` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '期初金額',
  `in_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '本期入',
  `in_amt` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '入金額',
  `out_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '本期出',
  `out_amt` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '出金額',
  `end_qty` DECIMAL(18,4) NOT NULL DEFAULT 0 COMMENT '期末量',
  `end_amt` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '期末金額',
  `unit_cost` DECIMAL(18,6) NOT NULL DEFAULT 0 COMMENT '月加權單位成本',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_acc_inv_month_1` (`period`, `item_id`, `warehouse_id`),
  CONSTRAINT `fk_acc_inv_month_period` FOREIGN KEY (`period`) REFERENCES `acc_period` (`period`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_inv_month_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_inv_month_warehouse_id` FOREIGN KEY (`warehouse_id`) REFERENCES `bas_warehouse` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='存貨月結';

-- 工單成本：工單 × 期別：投入材料、人工、製費、轉出完工、期末在製、差異
CREATE TABLE IF NOT EXISTS `acc_wo_cost` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `wo_id` INT NOT NULL COMMENT '工單',
  `period` CHAR(6) NOT NULL COMMENT '期別',
  `material_amt` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '材料投入',
  `labor_amt` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '人工投入',
  `overhead_amt` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '製費投入',
  `outsource_amt` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '委外投入',
  `completed_amt` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '轉出完工',
  `wip_end_amt` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '期末在製',
  `standard_amt` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '標準成本',
  `variance_amt` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '差異',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_acc_wo_cost_1` (`wo_id`, `period`),
  CONSTRAINT `fk_acc_wo_cost_wo_id` FOREIGN KEY (`wo_id`) REFERENCES `sfc_work_order` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_wo_cost_period` FOREIGN KEY (`period`) REFERENCES `acc_period` (`period`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工單成本';

-- 成本差異：採購價差、用料差異、人工效率差異、製費差異、良率差異
CREATE TABLE IF NOT EXISTS `acc_variance` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `period` CHAR(6) NOT NULL COMMENT '期別',
  `variance_type` CHAR(3) NOT NULL COMMENT 'PPV 採購價差、MUV 用料差、LEV 人工效率、OHV 製費、YLD 良率、FXV 匯兌差異',
  `item_id` INT COMMENT '料件',
  `wo_id` INT COMMENT '工單',
  `ref_doc_no` VARCHAR(20) COMMENT '相關單號',
  `amount` DECIMAL(18,2) NOT NULL COMMENT '差異金額（正=不利）',
  `note` VARCHAR(500) COMMENT '備註',
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_acc_variance_period` FOREIGN KEY (`period`) REFERENCES `acc_period` (`period`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_variance_item_id` FOREIGN KEY (`item_id`) REFERENCES `itm_item` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_variance_wo_id` FOREIGN KEY (`wo_id`) REFERENCES `sfc_work_order` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_acc_variance_1` CHECK (variance_type IN ('PPV','MUV','LEV','OHV','YLD','FXV'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='成本差異';

-- 會計拋轉批次：一次拋轉產生的傳票批次（zms-gl 格式）；可匯出拋轉檔或直接傳送到會計系統
CREATE TABLE IF NOT EXISTS `acc_gl_batch` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `batch_no` VARCHAR(20) NOT NULL COMMENT '批次號碼',
  `batch_uid` VARCHAR(80) NOT NULL COMMENT '批次代碼（會計系統用來防止重複匯入）',
  `date_from` DATE NOT NULL COMMENT '拋轉期間起',
  `date_to` DATE NOT NULL COMMENT '拋轉期間迄',
  `scope` VARCHAR(60) NOT NULL COMMENT '拋轉類別（逗號分隔）',
  `voucher_count` INT NOT NULL DEFAULT 0 COMMENT '傳票張數',
  `total` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '借方合計',
  `payload` LONGTEXT COMMENT '拋轉內容 JSON',
  `method` CHAR(1) COMMENT 'F 匯出檔案、A 直接傳送',
  `status` CHAR(1) NOT NULL DEFAULT 'N' COMMENT 'N 已產生、E 已匯出、S 已傳送、X 已取消',
  `result` VARCHAR(500) COMMENT '結果說明',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_acc_gl_batch_batch_no` (`batch_no`),
  UNIQUE KEY `uk_acc_gl_batch_batch_uid` (`batch_uid`),
  CONSTRAINT `fk_acc_gl_batch_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_gl_batch_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_acc_gl_batch_1` CHECK (status IN ('N','E','S','X')),
  CONSTRAINT `ck_acc_gl_batch_2` CHECK (payload IS NULL OR JSON_VALID(payload))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='會計拋轉批次';

-- 拋轉傳票單頭：由進貨/領料/完工/出貨/差異彙總，拋轉到「資料助秘之一般公司會計」
CREATE TABLE IF NOT EXISTS `acc_voucher_h` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `voucher_no` VARCHAR(30) NOT NULL COMMENT '傳票參考號（來源單號）',
  `batch_id` INT COMMENT '所屬拋轉批次',
  `voucher_date` DATE NOT NULL COMMENT '傳票日期',
  `period` CHAR(6) NOT NULL COMMENT '期別',
  `source_type` CHAR(3) NOT NULL COMMENT 'PUR 進貨、ISS 領料、CMP 完工、RPT 報工、SHP 出貨、VAR 差異、ADJ 調整',
  `status` CHAR(1) NOT NULL DEFAULT 'N' COMMENT 'N 未拋轉、E 已匯出檔案、S 已傳送 API',
  `exported_at` DATETIME COMMENT '拋轉時間',
  `summary` VARCHAR(200) COMMENT '摘要',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `created_by` INT COMMENT '建立者',
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '修改時間',
  `updated_by` INT COMMENT '修改者',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_acc_voucher_h_voucher_no` (`voucher_no`),
  CONSTRAINT `fk_acc_voucher_h_batch_id` FOREIGN KEY (`batch_id`) REFERENCES `acc_gl_batch` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_voucher_h_period` FOREIGN KEY (`period`) REFERENCES `acc_period` (`period`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_voucher_h_created_by` FOREIGN KEY (`created_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_acc_voucher_h_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `sys_user` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_acc_voucher_h_1` CHECK (source_type IN ('PUR','ISS','CMP','RPT','SHP','VAR','ADJ')),
  CONSTRAINT `ck_acc_voucher_h_2` CHECK (status IN ('N','E','S'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='拋轉傳票單頭';

-- 拋轉傳票單身：借貸分錄
CREATE TABLE IF NOT EXISTS `acc_voucher_d` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `voucher_id` INT NOT NULL COMMENT '傳票單頭',
  `line_no` SMALLINT NOT NULL COMMENT '項次',
  `account_no` VARCHAR(20) NOT NULL COMMENT '科目代號',
  `dr_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '借方',
  `cr_amount` DECIMAL(18,2) NOT NULL DEFAULT 0 COMMENT '貸方',
  `summary` VARCHAR(200) COMMENT '摘要',
  `dept_id` INT COMMENT '部門',
  `ref_doc_no` VARCHAR(20) COMMENT '來源單號',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_acc_voucher_d_1` (`voucher_id`, `line_no`),
  CONSTRAINT `fk_acc_voucher_d_voucher_id` FOREIGN KEY (`voucher_id`) REFERENCES `acc_voucher_h` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_acc_voucher_d_dept_id` FOREIGN KEY (`dept_id`) REFERENCES `bas_dept` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `ck_acc_voucher_d_1` CHECK (dr_amount >= 0 AND cr_amount >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='拋轉傳票單身';

SET FOREIGN_KEY_CHECKS = 1;
INSERT IGNORE INTO sys_schema_version (version, app_version, note) VALUES ('1.0.0', '1.0.0', '初始建立');
