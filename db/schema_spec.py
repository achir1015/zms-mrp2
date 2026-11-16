"""資料助秘之物料需求II生產製造系統 — 資料庫規格（唯一真相來源）

執行  py db/schema_spec.py  會產生：
  db/schema.sql                 MariaDB 建表腳本
  docs/資料表欄位明細.md         每張表的欄位、型別、關聯說明

命名規則
  * 表名 = 三碼模組前綴 + 底線 + 名稱，一律小寫（Windows/Mac 的 MariaDB 大小寫設定不同，小寫最安全）
  * 主鍵一律 id（代理鍵）；業務編號（料號、單號）另設 UNIQUE
  * 外鍵欄位以 _id 結尾；單頭 _h、單身 _d
"""
from __future__ import annotations

import os
import re

# 欄位：(名稱, 型別, 旗標, 說明, 參照表, 預設值)
#   旗標：P=主鍵 A=自動編號 N=NOT NULL U=單欄唯一
MODULES = [
    ("SYS", "系統管理", "公司、使用者、權限、單據編號、系統更新、語音教學"),
    ("BAS", "基本資料", "單位、幣別、部門、員工、倉庫、工廠行事曆"),
    ("ITM", "料件主檔", "成品/半成品/原物料主檔與計畫參數"),
    ("FCT", "需求預測", "產銷計畫、需求預測"),
    ("SAL", "客戶訂單", "客戶、訂單、出貨"),
    ("ROU", "途程與工作中心", "工作中心、機器設備、標準途程（MRP II 產能基礎）"),
    ("BOM", "物料清單", "產品結構、替代料、工程變更"),
    ("MPS", "主生產排程", "MPS 版本、時距排程、需求對應"),
    ("MRP", "物料需求規劃", "執行批次、時距表、計畫訂單、需求追溯、例外訊息"),
    ("CRP", "產能需求規劃", "粗略產能 RCCP、細部產能 CRP 負荷"),
    ("PUR", "採購管理", "供應商、料件供應來源、請購、採購、進貨驗收"),
    ("SFC", "現場控制", "工單、請料、發料、報工、移轉、完工入庫"),
    ("INV", "存貨控制", "批號、庫存餘額、異動帳、調撥、調整、盤點"),
    ("ACC", "會計與財務分析", "會計期間、標準成本、工單成本、差異、拋轉傳票"),
]

TABLES: list[dict] = []


def T(name, title, desc, cols, uniq=(), checks=(), index=(), audit=True, note=""):
    TABLES.append(dict(name=name, title=title, desc=desc, cols=cols, uniq=list(uniq),
                       checks=list(checks), index=list(index), audit=audit, note=note))


def C(name, typ, flags="", desc="", ref=None, default=None):
    assert desc.strip(), f"欄位 {name} 缺少繁體中文說明（會寫入資料庫 COMMENT）"
    assert "'" not in desc, f"欄位 {name} 的說明不可含單引號"
    return dict(name=name, typ=typ, flags=flags, desc=desc, ref=ref, default=default)


ID = lambda d="流水號": C("id", "INT", "PAN", d)
BID = lambda d="流水號": C("id", "BIGINT", "PAN", d)
QTY = "DECIMAL(18,4)"
PRICE = "DECIMAL(18,6)"
AMT = "DECIMAL(18,2)"
NOTE = lambda: C("note", "VARCHAR(500)", "", "備註")
ACTIVE = lambda: C("is_active", "TINYINT(1)", "N", "啟用 1/停用 0", default="1")
LINE = lambda: C("line_no", "SMALLINT", "N", "項次")

# ───────────────────────── SYS 系統管理 ─────────────────────────
T("sys_company", "公司基本資料", "單一公司設定（固定 1 筆）", [
    C("id", "TINYINT", "PN", "固定 1", default="1"),
    C("company_name", "VARCHAR(100)", "N", "公司名稱"),
    C("tax_id", "CHAR(8)", "", "統一編號"),
    C("owner_name", "VARCHAR(50)", "", "負責人"),
    C("phone", "VARCHAR(30)", "", "電話"),
    C("address", "VARCHAR(200)", "", "地址"),
    C("base_currency", "CHAR(3)", "N", "本位幣", default="'TWD'"),
    C("fiscal_start_month", "TINYINT", "N", "會計年度起始月", default="1"),
], checks=["id = 1"])

T("sys_param", "系統參數", "鍵值式參數（MRP 時距、預設倉、API 埠等）", [
    C("param_key", "VARCHAR(60)", "PN", "參數鍵"),
    C("param_value", "VARCHAR(500)", "", "參數值"),
    C("description", "VARCHAR(200)", "", "說明"),
])

T("sys_schema_version", "資料庫版本", "系統更新時逐版套用資料庫升級腳本的紀錄", [
    C("version", "VARCHAR(20)", "PN", "版本號，如 1.0.0"),
    C("applied_at", "DATETIME", "N", "套用時間", default="CURRENT_TIMESTAMP"),
    C("app_version", "VARCHAR(20)", "", "套用時的程式版本"),
    NOTE(),
], audit=False)

T("sys_function", "功能清單", "選單上的每個作業（權限與說明文件的依據）", [
    C("func_code", "VARCHAR(30)", "PN", "功能代碼，如 MRP010"),
    C("func_name", "VARCHAR(60)", "N", "功能名稱"),
    C("module", "CHAR(3)", "N", "所屬模組前綴"),
    C("sort_no", "SMALLINT", "N", "排序", default="0"),
], audit=False)

T("sys_role", "角色", "權限群組", [
    ID(), C("role_code", "VARCHAR(20)", "NU", "角色代碼"),
    C("role_name", "VARCHAR(50)", "N", "角色名稱"),
])

T("sys_role_perm", "角色權限", "角色 × 功能（多對多）的權限明細", [
    C("role_id", "INT", "PN", "角色", ref="sys_role"),
    C("func_code", "VARCHAR(30)", "PN", "功能", ref="sys_function.func_code"),
    C("can_view", "TINYINT(1)", "N", "查詢", default="1"),
    C("can_add", "TINYINT(1)", "N", "新增", default="0"),
    C("can_edit", "TINYINT(1)", "N", "修改", default="0"),
    C("can_delete", "TINYINT(1)", "N", "刪除", default="0"),
    C("can_approve", "TINYINT(1)", "N", "核准", default="0"),
    C("can_print", "TINYINT(1)", "N", "列印/匯出", default="0"),
], audit=False)

T("sys_user", "使用者", "登入帳號；可對應一位員工（一對一）", [
    ID(), C("user_code", "VARCHAR(30)", "NU", "帳號"),
    C("user_name", "VARCHAR(50)", "N", "姓名"),
    C("password_hash", "VARCHAR(255)", "N", "密碼雜湊（PBKDF2）"),
    C("employee_id", "INT", "U", "對應員工（1:1）", ref="bas_employee"),
    C("last_login_at", "DATETIME", "", "最後登入"),
    ACTIVE(),
])

T("sys_user_role", "使用者角色", "使用者 × 角色（多對多橋接表）", [
    C("user_id", "INT", "PN", "使用者", ref="sys_user"),
    C("role_id", "INT", "PN", "角色", ref="sys_role"),
], audit=False)

T("sys_doc_type", "單據類別", "統一表單代碼與編號規則；存貨異動方向", [
    C("doc_type", "VARCHAR(10)", "PN", "單別，如 PO、WO、ISS"),
    C("doc_name", "VARCHAR(40)", "N", "單據名稱"),
    C("module", "CHAR(3)", "N", "所屬模組"),
    C("prefix", "VARCHAR(10)", "N", "編號前綴"),
    C("no_format", "VARCHAR(30)", "N", "編號格式，如 {prefix}{yyyymm}{seq:4}", default="'{prefix}{yyyymm}{seq:4}'"),
    C("inv_effect", "TINYINT", "N", "存貨影響：1 入庫、-1 出庫、0 不影響", default="0"),
], checks=["inv_effect IN (-1,0,1)"], audit=False)

T("sys_doc_seq", "單據流水號", "各單別每期最後號碼", [
    C("doc_type", "VARCHAR(10)", "PN", "單別", ref="sys_doc_type.doc_type"),
    C("period", "CHAR(6)", "PN", "期別 yyyymm"),
    C("last_no", "INT", "N", "最後流水號", default="0"),
], audit=False)

T("sys_audit_log", "操作紀錄", "新增/修改/刪除/核准的稽核軌跡", [
    BID(), C("user_id", "INT", "", "使用者", ref="sys_user"),
    C("func_code", "VARCHAR(30)", "", "功能"),
    C("action", "VARCHAR(10)", "N", "ADD/EDIT/DEL/APPROVE/LOGIN"),
    C("table_name", "VARCHAR(40)", "", "資料表"),
    C("record_key", "VARCHAR(60)", "", "主鍵或單號"),
    C("detail", "LONGTEXT", "", "異動內容 JSON"),
    C("created_at", "DATETIME", "N", "時間", default="CURRENT_TIMESTAMP"),
], checks=["detail IS NULL OR JSON_VALID(detail)"], index=[("created_at",)], audit=False)

T("sys_help_topic", "語音教學說明", "每個功能的說明文件與語音朗讀稿", [
    ID(), C("func_code", "VARCHAR(30)", "", "對應功能（可空白=總說明）", ref="sys_function.func_code"),
    C("title", "VARCHAR(100)", "N", "標題"),
    C("content", "TEXT", "N", "說明內容（Markdown）"),
    C("voice_script", "TEXT", "", "語音朗讀稿"),
    C("sort_no", "SMALLINT", "N", "排序", default="0"),
])

# ───────────────────────── BAS 基本資料 ─────────────────────────
T("bas_unit", "計量單位", "個、台、公斤、公尺…", [
    ID(), C("unit_code", "VARCHAR(10)", "NU", "單位代碼"),
    C("unit_name", "VARCHAR(20)", "N", "單位名稱"),
])

T("bas_currency", "幣別", "幣別主檔（ISO 4217）：TWD、USD、JPY、KRW、CNY、EUR…", [
    C("currency_code", "CHAR(3)", "PN", "幣別代碼"),
    C("currency_name", "VARCHAR(20)", "N", "名稱，如 新台幣、美元、日圓"),
    C("symbol", "VARCHAR(5)", "", "符號，如 NT$、US$、¥、₩"),
    C("is_base", "TINYINT(1)", "N", "是否本位幣（僅一個）", default="0"),
    C("amount_decimals", "TINYINT", "N", "金額小數位（日圓、韓元為 0）", default="2"),
    C("price_decimals", "TINYINT", "N", "單價小數位", default="4"),
    C("exchange_rate", PRICE, "N", "最新記帳匯率（1 外幣 = ? 本位幣）", default="1"),
    C("rate_updated_at", "DATETIME", "", "最新匯率更新時間"),
    ACTIVE(),
])

T("bas_exchange_rate", "匯率歷史", "幣別 × 日期 × 匯率類型；單據依單據日期帶入匯率", [
    BID(), C("currency_code", "CHAR(3)", "N", "幣別", ref="bas_currency"),
    C("rate_date", "DATE", "N", "匯率日期"),
    C("rate_type", "CHAR(1)", "N", "B 銀行買入、S 銀行賣出、M 中價、A 記帳匯率", default="'A'"),
    C("rate", PRICE, "N", "匯率（1 外幣 = ? 本位幣）"),
    C("source", "VARCHAR(30)", "", "來源，如 臺灣銀行牌告、人工輸入"),
], uniq=[("currency_code", "rate_date", "rate_type")], checks=["rate > 0", "rate_type IN ('B','S','M','A')"],
   index=[("rate_date",)])

T("bas_country", "國家/產地", "原產國代碼（ISO 3166 兩碼）：TW 台灣、JP 日本、US 美國、KR 韓國…", [
    C("country_code", "CHAR(2)", "PN", "國家代碼"),
    C("country_name", "VARCHAR(30)", "N", "中文名稱"),
    C("country_name_en", "VARCHAR(50)", "", "英文名稱"),
    C("origin_label", "VARCHAR(10)", "", "產地簡稱，如 台製、日製"),
], audit=False)

T("bas_manufacturer", "製造商", "原廠（與供應商不同：供應商可能是代理商）", [
    ID(), C("mfr_code", "VARCHAR(20)", "NU", "製造商代碼"),
    C("mfr_name", "VARCHAR(100)", "N", "製造商名稱"),
    C("country_code", "CHAR(2)", "", "總部所在國", ref="bas_country"),
    C("website", "VARCHAR(200)", "", "網站"),
    ACTIVE(),
])

T("bas_dept", "部門", "組織部門（自我參照形成樹狀）", [
    ID(), C("dept_code", "VARCHAR(10)", "NU", "部門代碼"),
    C("dept_name", "VARCHAR(50)", "N", "部門名稱"),
    C("parent_id", "INT", "", "上層部門（自我參照 N:1）", ref="bas_dept"),
    ACTIVE(),
])

T("bas_employee", "員工", "生管、採購、現場人員等", [
    ID(), C("emp_code", "VARCHAR(20)", "NU", "員工編號"),
    C("emp_name", "VARCHAR(50)", "N", "姓名"),
    C("dept_id", "INT", "", "部門", ref="bas_dept"),
    C("job_title", "VARCHAR(30)", "", "職稱"),
    C("supervisor_id", "INT", "", "直屬主管（自我參照）", ref="bas_employee"),
    C("phone", "VARCHAR(30)", "", "電話"),
    ACTIVE(),
])

T("bas_warehouse", "倉庫", "原料倉、成品倉、在製倉、待驗倉…", [
    ID(), C("wh_code", "VARCHAR(10)", "NU", "倉庫代碼"),
    C("wh_name", "VARCHAR(50)", "N", "倉庫名稱"),
    C("wh_type", "CHAR(1)", "N", "R 原料、F 成品、W 在製、Q 待驗、S 報廢", default="'R'"),
    C("is_nettable", "TINYINT(1)", "N", "MRP 是否計入可用量", default="1"),
    C("keeper_id", "INT", "", "倉管人員", ref="bas_employee"),
    ACTIVE(),
], checks=["wh_type IN ('R','F','W','Q','S')"])

T("bas_location", "儲位", "倉庫內儲位（倉庫 1:N 儲位）", [
    ID(), C("warehouse_id", "INT", "N", "倉庫", ref="bas_warehouse"),
    C("loc_code", "VARCHAR(20)", "N", "儲位代碼"),
    C("loc_name", "VARCHAR(50)", "", "儲位名稱"),
], uniq=[("warehouse_id", "loc_code")])

T("bas_calendar", "工廠行事曆", "每日是否上班與工時；前置時間以工作天位移", [
    C("cal_date", "DATE", "PN", "日期"),
    C("is_workday", "TINYINT(1)", "N", "是否上班", default="1"),
    C("work_hours", "DECIMAL(5,2)", "N", "標準工時", default="8"),
    C("shift_count", "TINYINT", "N", "班次", default="1"),
    C("workday_seq", "INT", "", "工作天序號（位移計算用）"),
    NOTE(),
], index=[("workday_seq",)], audit=False)

# ───────────────────────── ITM 料件主檔 ─────────────────────────
T("itm_category", "料件分類", "分類樹；亦作為產銷計畫的產品族", [
    ID(), C("cat_code", "VARCHAR(20)", "NU", "分類代碼"),
    C("cat_name", "VARCHAR(50)", "N", "分類名稱"),
    C("parent_id", "INT", "", "上層分類", ref="itm_category"),
])

T("itm_item", "料件主檔", "所有成品、半成品、原物料、包材", [
    ID(), C("item_code", "VARCHAR(40)", "NU", "料號"),
    C("item_name", "VARCHAR(100)", "N", "品名"),
    C("spec", "VARCHAR(200)", "", "規格"),
    C("item_type", "CHAR(1)", "N", "F 成品、S 半成品、R 原物料、P 包材、X 虛設件"),
    C("source_type", "CHAR(1)", "N", "M 自製、P 採購、O 委外", default="'P'"),
    C("category_id", "INT", "", "分類", ref="itm_category"),
    C("unit_id", "INT", "N", "庫存單位", ref="bas_unit"),
    C("purchase_unit_id", "INT", "", "採購單位", ref="bas_unit"),
    C("current_rev_id", "INT", "", "目前量產版本", ref="itm_revision"),
    C("low_level_code", "SMALLINT", "N", "低階碼（BOM 最深層級，MRP 由上而下逐階計算用）", default="0"),
    C("is_lot_control", "TINYINT(1)", "N", "批號管理", default="0"),
    C("barcode", "VARCHAR(40)", "", "條碼"),
    C("drawing_no", "VARCHAR(40)", "", "圖號"),
    C("weight_kg", "DECIMAL(12,4)", "", "單位重量"),
    ACTIVE(), NOTE(),
], checks=["item_type IN ('F','S','R','P','X')", "source_type IN ('M','P','O')"],
   index=[("item_type",), ("low_level_code",)])

T("itm_revision", "料件版本", "同一料號的不同版本（PCB Rev A/B、韌體 1.0/1.1）；料件 1:N 版本", [
    ID(), C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("rev_code", "VARCHAR(10)", "N", "版本碼，如 A、B、1.0、1.1"),
    C("rev_desc", "VARCHAR(200)", "", "版本差異說明"),
    C("status", "CHAR(1)", "N", "D 設計中、P 試產、A 量產、H 暫停、O 淘汰（淘汰版庫存不計入 MRP）", default="'A'"),
    C("effective_date", "DATE", "N", "生效日", default="'2000-01-01'"),
    C("obsolete_date", "DATE", "", "失效日"),
    C("is_interchangeable", "TINYINT(1)", "N", "可與前一版互換（MRP 合併計算）", default="1"),
    C("prev_rev_id", "INT", "", "前一版本（自我參照）", ref="itm_revision"),
    C("firmware_ver", "VARCHAR(30)", "", "韌體/BIOS 版本"),
    C("drawing_no", "VARCHAR(40)", "", "圖號"),
    C("gerber_file", "VARCHAR(200)", "", "線路圖/Gerber 檔案路徑"),
    C("ecn_id", "INT", "", "由哪張工程變更產生", ref="bom_ecn"),
    NOTE(),
], uniq=[("item_id", "rev_code")], checks=["status IN ('D','P','A','H','O')"],
   index=[("item_id", "status")])

T("itm_mfr_part", "核可製造商料號 AML", "料件 × 版本 × 製造商：製造商料號與原產地（同料號可有台製、日製、美製、韓製來源）", [
    ID(), C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("rev_id", "INT", "", "適用版本（空白=全部版本）", ref="itm_revision"),
    C("manufacturer_id", "INT", "N", "製造商", ref="bas_manufacturer"),
    C("mfr_part_no", "VARCHAR(60)", "N", "製造商料號 MPN"),
    C("origin_country", "CHAR(2)", "N", "原產國", ref="bas_country"),
    C("approval_status", "CHAR(1)", "N", "A 核可、T 試用、R 不核可", default="'A'"),
    C("priority", "TINYINT", "N", "優先順序（1 最優先）", default="1"),
    C("rohs", "TINYINT(1)", "N", "符合 RoHS", default="1"),
    C("datasheet", "VARCHAR(200)", "", "規格書路徑"),
    NOTE(),
], uniq=[("item_id", "manufacturer_id", "mfr_part_no")],
   checks=["approval_status IN ('A','T','R')"], index=[("origin_country",)])

T("itm_plan", "料件計畫參數", "與料件一對一；MRP 批量法則、前置時間、安全存量、EOQ", [
    C("item_id", "INT", "PN", "料件（1:1）", ref="itm_item"),
    C("planner_id", "INT", "", "生管/採購負責人", ref="bas_employee"),
    C("default_wh_id", "INT", "", "預設倉庫", ref="bas_warehouse"),
    C("lead_time_days", "SMALLINT", "N", "前置時間（工作天）", default="0"),
    C("safety_lead_days", "SMALLINT", "N", "安全前置時間", default="0"),
    C("safety_stock", QTY, "N", "安全存量", default="0"),
    C("reorder_point", QTY, "N", "再訂購點", default="0"),
    C("lot_rule", "CHAR(3)", "N", "批量法則：LFL 逐批、FOQ 固定量、EOQ 經濟批量、POQ 期間訂購", default="'LFL'"),
    C("fixed_lot_qty", QTY, "N", "固定批量（FOQ）", default="0"),
    C("min_order_qty", QTY, "N", "最小訂購量", default="0"),
    C("order_multiple", QTY, "N", "訂購倍數", default="0"),
    C("poq_periods", "SMALLINT", "N", "POQ 合併期數", default="1"),
    C("annual_demand", QTY, "N", "年需求量（EOQ 用）", default="0"),
    C("order_cost", AMT, "N", "每次訂購/整備成本（EOQ 用）", default="0"),
    C("holding_rate", "DECIMAL(6,4)", "N", "年持有成本率（EOQ 用）", default="0.2"),
    C("eoq_qty", QTY, "N", "計算後經濟訂購量", default="0"),
    C("yield_rate", "DECIMAL(6,4)", "N", "良率", default="1"),
    C("issue_rule", "CHAR(1)", "N", "發料原則：F 先進先出、E 先到期先出、M 人工指定", default="'F'"),
    C("cost_method", "CHAR(1)", "N", "成本計價：F 先進先出、W 月加權平均、S 標準成本", default="'F'"),
    C("is_mps_item", "TINYINT(1)", "N", "列入主生產排程", default="0"),
    C("demand_fence_days", "SMALLINT", "N", "需求時柵", default="0"),
    C("planning_fence_days", "SMALLINT", "N", "計畫時柵", default="0"),
], checks=["lot_rule IN ('LFL','FOQ','EOQ','POQ')", "issue_rule IN ('F','E','M')", "cost_method IN ('F','W','S')"])

T("itm_unit_conv", "單位換算", "料件專屬或通用的單位換算", [
    ID(), C("item_id", "INT", "", "料件（空白=通用）", ref="itm_item"),
    C("from_unit_id", "INT", "N", "來源單位", ref="bas_unit"),
    C("to_unit_id", "INT", "N", "目的單位", ref="bas_unit"),
    C("factor", PRICE, "N", "1 來源 = factor 目的"),
], uniq=[("item_id", "from_unit_id", "to_unit_id")])

# ───────────────────────── SAL 客戶（FCT 會用到，先建）─────────────────────────
T("sal_customer", "客戶", "客戶主檔", [
    ID(), C("cust_code", "VARCHAR(20)", "NU", "客戶編號"),
    C("cust_name", "VARCHAR(100)", "N", "客戶名稱"),
    C("short_name", "VARCHAR(30)", "", "簡稱"),
    C("tax_id", "CHAR(8)", "", "統一編號"),
    C("contact", "VARCHAR(50)", "", "聯絡人"),
    C("phone", "VARCHAR(30)", "", "電話"),
    C("email", "VARCHAR(100)", "", "Email"),
    C("address", "VARCHAR(200)", "", "地址"),
    C("currency_code", "CHAR(3)", "N", "交易幣別", ref="bas_currency.currency_code", default="'TWD'"),
    C("payment_terms", "VARCHAR(30)", "", "付款條件"),
    C("credit_limit", AMT, "N", "信用額度", default="0"),
    C("sales_id", "INT", "", "業務", ref="bas_employee"),
    ACTIVE(),
])

# ───────────────────────── FCT 需求預測 ─────────────────────────
T("fct_sop_plan", "產銷計畫", "長期：產品族 × 月份的銷售/生產/庫存目標（S&OP）", [
    ID(), C("plan_year", "SMALLINT", "N", "年度"),
    C("plan_month", "TINYINT", "N", "月份"),
    C("category_id", "INT", "N", "產品族", ref="itm_category"),
    C("sales_plan_qty", QTY, "N", "銷售計畫量", default="0"),
    C("prod_plan_qty", QTY, "N", "生產計畫量", default="0"),
    C("target_inv_qty", QTY, "N", "目標庫存", default="0"),
    C("sales_plan_amt", AMT, "N", "銷售計畫金額", default="0"),
], uniq=[("plan_year", "plan_month", "category_id")], checks=["plan_month BETWEEN 1 AND 12"])

T("fct_forecast_h", "需求預測單頭", "一次預測（版本）", [
    ID(), C("fc_no", "VARCHAR(20)", "NU", "預測單號"),
    C("fc_date", "DATE", "N", "預測日期"),
    C("method", "CHAR(1)", "N", "M 人工、A 移動平均、E 指數平滑、T 趨勢", default="'M'"),
    C("bucket_type", "CHAR(1)", "N", "時距：D 日、W 週、M 月", default="'M'"),
    C("status", "CHAR(1)", "N", "D 草稿、A 核准、X 作廢", default="'D'"),
    NOTE(),
], checks=["method IN ('M','A','E','T')", "bucket_type IN ('D','W','M')", "status IN ('D','A','X')"])

T("fct_forecast_d", "需求預測單身", "料件 × 期間的預測量；被訂單沖銷的量另記", [
    BID(), C("forecast_id", "INT", "N", "預測單頭", ref="fct_forecast_h"),
    C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("customer_id", "INT", "", "客戶（可空白）", ref="sal_customer"),
    C("period_start", "DATE", "N", "期間起日"),
    C("forecast_qty", QTY, "N", "預測量", default="0"),
    C("consumed_qty", QTY, "N", "已被訂單沖銷量", default="0"),
], uniq=[("forecast_id", "item_id", "customer_id", "period_start")], audit=False)

# ───────────────────────── SAL 客戶訂單 ─────────────────────────
T("sal_order_h", "客戶訂單單頭", "接單（獨立需求來源）", [
    ID(), C("so_no", "VARCHAR(20)", "NU", "訂單號"),
    C("order_date", "DATE", "N", "訂單日期"),
    C("customer_id", "INT", "N", "客戶", ref="sal_customer"),
    C("cust_po_no", "VARCHAR(40)", "", "客戶採購單號"),
    C("currency_code", "CHAR(3)", "N", "幣別", ref="bas_currency.currency_code", default="'TWD'"),
    C("exchange_rate", PRICE, "N", "匯率", default="1"),
    C("tax_type", "CHAR(1)", "N", "1 應稅外加、2 應稅內含、3 零稅、4 免稅", default="'1'"),
    C("tax_rate", "DECIMAL(5,4)", "N", "稅率", default="0.05"),
    C("sales_id", "INT", "", "業務", ref="bas_employee"),
    C("untaxed_amount", AMT, "N", "未稅金額", default="0"),
    C("tax_amount", AMT, "N", "稅額", default="0"),
    C("status", "CHAR(1)", "N", "D 草稿、A 核准、P 部分出貨、C 結案、X 作廢", default="'D'"),
    NOTE(),
], checks=["status IN ('D','A','P','C','X')"], index=[("order_date",)])

T("sal_order_d", "客戶訂單單身", "每個料件的訂購量與交期", [
    BID(), C("so_id", "INT", "N", "訂單單頭", ref="sal_order_h"),
    LINE(), C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("qty", QTY, "N", "訂購量"),
    C("unit_price", PRICE, "N", "單價", default="0"),
    C("amount", AMT, "N", "金額", default="0"),
    C("due_date", "DATE", "N", "客戶交期"),
    C("promised_date", "DATE", "", "承諾交期（ATP）"),
    C("shipped_qty", QTY, "N", "已出貨量", default="0"),
    C("status", "CHAR(1)", "N", "O 未結、C 結案、X 取消", default="'O'"),
], uniq=[("so_id", "line_no")], index=[("item_id", "due_date")], audit=False)

# ───────────────────────── ROU 途程與工作中心 ─────────────────────────
T("rou_work_center", "工作中心", "產能計算單位（機台群、產線、人工站）", [
    ID(), C("wc_code", "VARCHAR(20)", "NU", "工作中心代碼"),
    C("wc_name", "VARCHAR(50)", "N", "名稱"),
    C("dept_id", "INT", "", "所屬部門", ref="bas_dept"),
    C("wc_type", "CHAR(1)", "N", "M 機器、L 人工、O 委外", default="'M'"),
    C("resource_count", "SMALLINT", "N", "機台/人數", default="1"),
    C("hours_per_shift", "DECIMAL(5,2)", "N", "每班工時", default="8"),
    C("efficiency", "DECIMAL(6,4)", "N", "效率", default="1"),
    C("utilization", "DECIMAL(6,4)", "N", "利用率", default="1"),
    C("queue_days", "DECIMAL(6,2)", "N", "等候時間（天）", default="0"),
    C("move_days", "DECIMAL(6,2)", "N", "搬運時間（天）", default="0"),
    C("is_bottleneck", "TINYINT(1)", "N", "瓶頸站（RCCP 檢核）", default="0"),
    ACTIVE(),
], checks=["wc_type IN ('M','L','O')"], note="每日可用工時 = 人機數 × 班次 × 每班工時 × 效率 × 利用率")

T("rou_wc_calendar", "工作中心例外產能", "某天加班、停機、保養時覆寫可用工時", [
    C("wc_id", "INT", "PN", "工作中心", ref="rou_work_center"),
    C("cal_date", "DATE", "PN", "日期"),
    C("available_hours", "DECIMAL(8,2)", "N", "當日可用工時"),
    C("reason", "VARCHAR(100)", "", "原因"),
], audit=False)

T("rou_machine", "機器設備", "工作中心內的設備；購置成本與耐用年限供製費分攤", [
    ID(), C("machine_code", "VARCHAR(20)", "NU", "設備編號"),
    C("machine_name", "VARCHAR(50)", "N", "名稱"),
    C("wc_id", "INT", "N", "所屬工作中心", ref="rou_work_center"),
    C("purchase_date", "DATE", "", "購置日期"),
    C("cost", AMT, "N", "取得成本", default="0"),
    C("useful_years", "SMALLINT", "N", "耐用年限", default="5"),
    C("salvage_value", AMT, "N", "估計殘值", default="0"),
    C("status", "CHAR(1)", "N", "A 正常、M 保養中、D 報廢", default="'A'"),
], checks=["status IN ('A','M','D')"])

T("rou_routing_h", "途程單頭", "料件的製造途程版本", [
    ID(), C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("routing_ver", "VARCHAR(10)", "N", "版本", default="'01'"),
    C("is_default", "TINYINT(1)", "N", "預設途程", default="1"),
    C("status", "CHAR(1)", "N", "D 草稿、A 生效、X 失效", default="'D'"),
    NOTE(),
], uniq=[("item_id", "routing_ver")], checks=["status IN ('D','A','X')"])

T("rou_routing_d", "途程工序", "每道工序在哪個工作中心、整備與加工工時", [
    ID(), C("routing_id", "INT", "N", "途程單頭", ref="rou_routing_h"),
    C("op_seq", "SMALLINT", "N", "工序 10、20、30…"),
    C("op_name", "VARCHAR(50)", "N", "工序名稱"),
    C("wc_id", "INT", "N", "工作中心", ref="rou_work_center"),
    C("setup_hours", "DECIMAL(10,4)", "N", "整備工時（每批）", default="0"),
    C("run_hours", "DECIMAL(10,6)", "N", "加工工時（每單位）", default="0"),
    C("is_outsource", "TINYINT(1)", "N", "委外工序", default="0"),
    C("supplier_id", "INT", "", "委外廠商", ref="pur_supplier"),
    C("is_report_point", "TINYINT(1)", "N", "報工點", default="1"),
], uniq=[("routing_id", "op_seq")], audit=False)

# ───────────────────────── PUR 供應商（ROU 會用到）─────────────────────────
T("pur_supplier", "供應商", "供應商與委外廠商", [
    ID(), C("sup_code", "VARCHAR(20)", "NU", "供應商編號"),
    C("sup_name", "VARCHAR(100)", "N", "名稱"),
    C("short_name", "VARCHAR(30)", "", "簡稱"),
    C("tax_id", "CHAR(8)", "", "統一編號"),
    C("contact", "VARCHAR(50)", "", "聯絡人"),
    C("phone", "VARCHAR(30)", "", "電話"),
    C("email", "VARCHAR(100)", "", "Email"),
    C("address", "VARCHAR(200)", "", "地址"),
    C("currency_code", "CHAR(3)", "N", "交易幣別", ref="bas_currency.currency_code", default="'TWD'"),
    C("payment_terms", "VARCHAR(30)", "", "付款條件"),
    C("lead_time_days", "SMALLINT", "N", "一般交期（天）", default="0"),
    ACTIVE(),
])

# ───────────────────────── BOM 物料清單 ─────────────────────────
T("bom_header", "BOM 單頭", "母件的產品結構版本（料件自我多對多關係的單頭）", [
    ID(), C("parent_item_id", "INT", "N", "母件", ref="itm_item"),
    C("bom_ver", "VARCHAR(10)", "N", "版本", default="'01'"),
    C("base_qty", QTY, "N", "基準量（每幾個母件）", default="1"),
    C("is_default", "TINYINT(1)", "N", "預設 BOM", default="1"),
    C("status", "CHAR(1)", "N", "D 草稿、A 核准、X 失效", default="'D'"),
    C("approved_by", "INT", "", "核准人", ref="sys_user"),
    C("approved_at", "DATETIME", "", "核准時間"),
    NOTE(),
], uniq=[("parent_item_id", "bom_ver")], checks=["status IN ('D','A','X')"])

T("bom_detail", "BOM 單身", "元件、用量、損耗率、生效區間（展開 Exploding 的依據）", [
    ID(), C("bom_id", "INT", "N", "BOM 單頭", ref="bom_header"),
    LINE(), C("child_item_id", "INT", "N", "元件", ref="itm_item"),
    C("qty_per", QTY, "N", "組成用量（每基準量）"),
    C("scrap_rate", "DECIMAL(6,4)", "N", "損耗率", default="0"),
    C("op_seq", "SMALLINT", "", "投入工序"),
    C("issue_type", "CHAR(1)", "N", "P 領料、B 倒扣（完工扣料）、N 不發料", default="'P'"),
    C("is_phantom", "TINYINT(1)", "N", "虛設件（展開時穿透）", default="0"),
    C("effective_date", "DATE", "N", "生效日", default="'2000-01-01'"),
    C("obsolete_date", "DATE", "", "失效日"),
    NOTE(),
], uniq=[("bom_id", "line_no")], checks=["qty_per > 0", "issue_type IN ('P','B','N')"],
   index=[("child_item_id",)], audit=False, note="毛需求 = 母件需求 ÷ 基準量 × 組成用量 ÷ (1 − 損耗率)")

T("bom_substitute", "替代料", "BOM 元件可用的替代料（BOM 單身 1:N）", [
    ID(), C("bom_detail_id", "INT", "N", "BOM 單身", ref="bom_detail"),
    C("sub_item_id", "INT", "N", "替代料件", ref="itm_item"),
    C("sub_qty_per", QTY, "N", "替代用量"),
    C("priority", "TINYINT", "N", "優先順序", default="1"),
], uniq=[("bom_detail_id", "sub_item_id")], audit=False)

T("bom_ecn", "工程變更", "ECN：BOM 改版的申請、核准與生效日", [
    ID(), C("ecn_no", "VARCHAR(20)", "NU", "變更單號"),
    C("ecn_date", "DATE", "N", "申請日"),
    C("bom_id", "INT", "N", "變更的 BOM", ref="bom_header"),
    C("new_bom_id", "INT", "", "新版 BOM", ref="bom_header"),
    C("reason", "VARCHAR(200)", "N", "變更原因"),
    C("change_desc", "TEXT", "", "變更內容"),
    C("effective_date", "DATE", "N", "生效日"),
    C("requested_by", "INT", "", "申請人", ref="bas_employee"),
    C("status", "CHAR(1)", "N", "D 草稿、A 核准、E 已生效、X 作廢", default="'D'"),
], checks=["status IN ('D','A','E','X')"])

# ───────────────────────── MPS 主生產排程 ─────────────────────────
T("mps_plan_h", "主生產排程單頭", "MPS 版本：時距、計畫期間、凍結期", [
    ID(), C("mps_no", "VARCHAR(20)", "NU", "排程單號"),
    C("plan_date", "DATE", "N", "編製日"),
    C("bucket_type", "CHAR(1)", "N", "時距 D/W/M", default="'W'"),
    C("horizon_start", "DATE", "N", "計畫起日"),
    C("horizon_end", "DATE", "N", "計畫迄日"),
    C("frozen_until", "DATE", "", "凍結期（之前不可變動）"),
    C("forecast_id", "INT", "", "引用預測", ref="fct_forecast_h"),
    C("status", "CHAR(1)", "N", "D 草稿、C 確認、R 已執行 MRP、X 作廢", default="'D'"),
    NOTE(),
], checks=["bucket_type IN ('D','W','M')", "status IN ('D','C','R','X')", "horizon_end >= horizon_start"])

T("mps_plan_d", "主生產排程明細", "MPS 料件 × 期間：預測、訂單、預計庫存、MPS 量、ATP", [
    BID(), C("mps_id", "INT", "N", "排程單頭", ref="mps_plan_h"),
    C("item_id", "INT", "N", "料件（is_mps_item）", ref="itm_item"),
    C("period_start", "DATE", "N", "期間起日"),
    C("forecast_qty", QTY, "N", "預測需求", default="0"),
    C("order_qty", QTY, "N", "訂單需求", default="0"),
    C("projected_oh", QTY, "N", "預計在庫量", default="0"),
    C("mps_qty", QTY, "N", "主排程量（完工量）", default="0"),
    C("atp_qty", QTY, "N", "可承諾量 ATP", default="0"),
    C("is_firm", "TINYINT(1)", "N", "人工確定（不被重算覆蓋）", default="0"),
], uniq=[("mps_id", "item_id", "period_start")], audit=False,
   note="總需求 = MAX(預測未沖銷, 訂單)（需求時柵內只看訂單）")

T("mps_demand_link", "MPS 需求對應", "MPS 明細 ↔ 訂單/預測明細（多對多橋接表，部分數量）", [
    BID(), C("mps_line_id", "BIGINT", "N", "MPS 明細", ref="mps_plan_d"),
    C("demand_type", "CHAR(1)", "N", "S 訂單、F 預測"),
    C("so_line_id", "BIGINT", "", "訂單明細", ref="sal_order_d"),
    C("fc_line_id", "BIGINT", "", "預測明細", ref="fct_forecast_d"),
    C("linked_qty", QTY, "N", "對應數量"),
], checks=["demand_type IN ('S','F')",
           "(demand_type='S' AND so_line_id IS NOT NULL) OR (demand_type='F' AND fc_line_id IS NOT NULL)"],
   audit=False)

# ───────────────────────── MRP 物料需求規劃 ─────────────────────────
T("mrp_run", "MRP 執行批次", "每次 MRP 運算的參數與結果摘要", [
    ID(), C("run_no", "VARCHAR(20)", "NU", "執行編號"),
    C("mps_id", "INT", "N", "依據 MPS", ref="mps_plan_h"),
    C("run_mode", "CHAR(1)", "N", "R 全部重算（再生法）、N 淨變法", default="'R'"),
    C("plan_start", "DATE", "N", "計畫起日"),
    C("horizon_days", "SMALLINT", "N", "計畫天數", default="90"),
    C("bucket_type", "CHAR(1)", "N", "時距 D/W/M", default="'D'"),
    C("use_safety_stock", "TINYINT(1)", "N", "考慮安全存量", default="1"),
    C("use_scrap", "TINYINT(1)", "N", "考慮損耗率", default="1"),
    C("started_at", "DATETIME", "N", "開始", default="CURRENT_TIMESTAMP"),
    C("finished_at", "DATETIME", "", "結束"),
    C("run_by", "INT", "", "執行人", ref="sys_user"),
    C("item_count", "INT", "N", "計算料件數", default="0"),
    C("planned_count", "INT", "N", "產生計畫訂單數", default="0"),
    C("status", "CHAR(1)", "N", "R 執行中、D 完成、E 錯誤", default="'R'"),
    C("message", "VARCHAR(500)", "", "訊息"),
], checks=["run_mode IN ('R','N')", "status IN ('R','D','E')"], audit=False)

T("mrp_record", "MRP 時距表", "MRP 經典表格：料件 × 期間的毛需求、預定接收、預計在庫、淨需求、計畫接收/發出", [
    BID(), C("run_id", "INT", "N", "執行批次", ref="mrp_run"),
    C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("period_start", "DATE", "N", "期間起日"),
    C("gross_req", QTY, "N", "毛需求（展開 Exploding）", default="0"),
    C("scheduled_receipt", QTY, "N", "預定接收（在途採購/工單）", default="0"),
    C("projected_oh", QTY, "N", "預計在庫量", default="0"),
    C("net_req", QTY, "N", "淨需求（Netting）", default="0"),
    C("planned_receipt", QTY, "N", "計畫訂單接收（批量後）", default="0"),
    C("planned_release", QTY, "N", "計畫訂單發出（前置時間位移 Offsetting）", default="0"),
], uniq=[("run_id", "item_id", "period_start")], audit=False,
   note="淨需求 = MAX(0, 毛需求 + 安全存量 − 前期在庫 − 預定接收)")

T("mrp_planned_order", "MRP 計畫訂單", "建議採購/製造/委外；確認後轉請購單或工單", [
    BID(), C("run_id", "INT", "N", "執行批次", ref="mrp_run"),
    C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("order_type", "CHAR(1)", "N", "P 採購、M 製造、O 委外"),
    C("qty", QTY, "N", "建議量"),
    C("release_date", "DATE", "N", "建議發出日（需求日 − 前置時間）"),
    C("due_date", "DATE", "N", "需求日"),
    C("supplier_id", "INT", "", "建議供應商", ref="pur_supplier"),
    C("status", "CHAR(1)", "N", "N 建議、F 確認、C 已轉單、X 取消", default="'N'"),
    C("converted_doc_no", "VARCHAR(20)", "", "轉出單號（請購/工單）"),
], checks=["order_type IN ('P','M','O')", "status IN ('N','F','C','X')", "due_date >= release_date"],
   index=[("item_id", "due_date")], audit=False)

T("mrp_pegging", "需求追溯", "每筆需求從哪裡來（上階計畫單/MPS/訂單/工單用料），供 pegging 查詢", [
    BID(), C("run_id", "INT", "N", "執行批次", ref="mrp_run"),
    C("item_id", "INT", "N", "需求料件", ref="itm_item"),
    C("need_date", "DATE", "N", "需求日"),
    C("need_qty", QTY, "N", "需求量"),
    C("source_type", "CHAR(1)", "N", "M MPS、P 上階計畫單、W 工單用料、S 安全存量"),
    C("mps_line_id", "BIGINT", "", "來源 MPS 明細", ref="mps_plan_d"),
    C("parent_po_id", "BIGINT", "", "來源上階計畫訂單", ref="mrp_planned_order"),
    C("source_doc_no", "VARCHAR(20)", "", "來源單號（工單等）"),
    C("supply_po_id", "BIGINT", "", "滿足此需求的計畫訂單", ref="mrp_planned_order"),
], checks=["source_type IN ('M','P','W','S')"], index=[("run_id", "item_id")], audit=False)

T("mrp_exception", "MRP 例外訊息", "行動建議：提前、延後、取消、逾期、低於安全存量", [
    BID(), C("run_id", "INT", "N", "執行批次", ref="mrp_run"),
    C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("msg_type", "CHAR(3)", "N", "NEW 新增、EXP 提前、DLY 延後、CAN 取消、PDL 已逾期、SFT 低於安全存量"),
    C("ref_doc_no", "VARCHAR(20)", "", "相關單號"),
    C("ref_date", "DATE", "", "原日期"),
    C("suggest_date", "DATE", "", "建議日期"),
    C("qty", QTY, "N", "數量", default="0"),
    C("message", "VARCHAR(200)", "N", "訊息"),
    C("is_handled", "TINYINT(1)", "N", "已處理", default="0"),
], checks=["msg_type IN ('NEW','EXP','DLY','CAN','PDL','SFT')"], audit=False)

# ───────────────────────── CRP 產能需求規劃 ─────────────────────────
T("crp_bill_resource", "資源清單", "RCCP 用：每單位 MPS 料件約耗用各瓶頸站多少工時", [
    ID(), C("item_id", "INT", "N", "MPS 料件", ref="itm_item"),
    C("wc_id", "INT", "N", "工作中心", ref="rou_work_center"),
    C("hours_per_unit", "DECIMAL(12,6)", "N", "每單位工時"),
    C("offset_days", "SMALLINT", "N", "相對完工日提前天數", default="0"),
], uniq=[("item_id", "wc_id")], audit=False)

T("crp_run", "產能運算批次", "RCCP（依 MPS）或 CRP（依 MRP 計畫單＋已發放工單）", [
    ID(), C("run_no", "VARCHAR(20)", "NU", "執行編號"),
    C("run_type", "CHAR(1)", "N", "R 粗略產能 RCCP、C 細部產能 CRP"),
    C("mps_id", "INT", "", "依據 MPS", ref="mps_plan_h"),
    C("mrp_run_id", "INT", "", "依據 MRP", ref="mrp_run"),
    C("horizon_start", "DATE", "N", "期間起"),
    C("horizon_end", "DATE", "N", "期間迄"),
    C("bucket_type", "CHAR(1)", "N", "時距 D/W/M", default="'D'"),
    C("run_at", "DATETIME", "N", "執行時間", default="CURRENT_TIMESTAMP"),
    C("run_by", "INT", "", "執行人", ref="sys_user"),
], checks=["run_type IN ('R','C')"], audit=False)

T("crp_load", "工作中心負荷", "工作中心 × 期間：需求工時、可用工時、負荷率", [
    BID(), C("run_id", "INT", "N", "產能批次", ref="crp_run"),
    C("wc_id", "INT", "N", "工作中心", ref="rou_work_center"),
    C("period_start", "DATE", "N", "期間起日"),
    C("required_hours", "DECIMAL(12,2)", "N", "需求工時", default="0"),
    C("available_hours", "DECIMAL(12,2)", "N", "可用工時", default="0"),
    C("load_pct", "DECIMAL(8,2)", "N", "負荷率 %", default="0"),
], uniq=[("run_id", "wc_id", "period_start")], audit=False)

T("crp_load_detail", "負荷來源明細", "負荷由哪張計畫單/工單的哪道工序產生", [
    BID(), C("load_id", "BIGINT", "N", "負荷", ref="crp_load"),
    C("source_type", "CHAR(1)", "N", "M MPS、P 計畫訂單、W 工單"),
    C("source_doc_no", "VARCHAR(20)", "N", "來源單號"),
    C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("op_seq", "SMALLINT", "", "工序"),
    C("qty", QTY, "N", "數量"),
    C("setup_hours", "DECIMAL(12,4)", "N", "整備工時", default="0"),
    C("run_hours", "DECIMAL(12,4)", "N", "加工工時", default="0"),
], checks=["source_type IN ('M','P','W')"], audit=False)

# ───────────────────────── PUR 採購 ─────────────────────────
T("pur_item_source", "料件供應來源", "料件 × 供應商（多對多橋接表）：報價、交期、MOQ、優先序", [
    ID(), C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("supplier_id", "INT", "N", "供應商", ref="pur_supplier"),
    C("sup_item_code", "VARCHAR(40)", "", "廠商料號"),
    C("unit_price", PRICE, "N", "單價", default="0"),
    C("currency_code", "CHAR(3)", "N", "幣別", ref="bas_currency.currency_code", default="'TWD'"),
    C("lead_days", "SMALLINT", "N", "交期（天）", default="0"),
    C("moq", QTY, "N", "最小訂購量", default="0"),
    C("priority", "TINYINT", "N", "優先順序（1 最優先）", default="1"),
    C("valid_from", "DATE", "", "報價生效"),
    C("valid_to", "DATE", "", "報價失效"),
], uniq=[("item_id", "supplier_id", "mfr_part_id")])

T("pur_req_h", "請購單頭", "MRP 計畫訂單或人工請購", [
    ID(), C("pr_no", "VARCHAR(20)", "NU", "請購單號"),
    C("pr_date", "DATE", "N", "請購日"),
    C("dept_id", "INT", "", "請購部門", ref="bas_dept"),
    C("requester_id", "INT", "", "請購人", ref="bas_employee"),
    C("source", "CHAR(1)", "N", "M 人工、R MRP 轉入", default="'M'"),
    C("status", "CHAR(1)", "N", "D 草稿、A 核准、P 部分轉採購、C 結案、X 作廢", default="'D'"),
    NOTE(),
], checks=["status IN ('D','A','P','C','X')"])

T("pur_req_d", "請購單身", "請購料件與需求日", [
    BID(), C("pr_id", "INT", "N", "請購單頭", ref="pur_req_h"),
    LINE(), C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("qty", QTY, "N", "請購量"),
    C("need_date", "DATE", "N", "需求日"),
    C("suggest_supplier_id", "INT", "", "建議供應商", ref="pur_supplier"),
    C("planned_order_id", "BIGINT", "", "來源 MRP 計畫訂單", ref="mrp_planned_order"),
    C("ordered_qty", QTY, "N", "已轉採購量", default="0"),
], uniq=[("pr_id", "line_no")], audit=False)

T("pur_order_h", "採購單頭", "對供應商下單；未交量即 MRP 的預定接收", [
    ID(), C("po_no", "VARCHAR(20)", "NU", "採購單號"),
    C("po_date", "DATE", "N", "採購日"),
    C("supplier_id", "INT", "N", "供應商", ref="pur_supplier"),
    C("po_type", "CHAR(1)", "N", "N 一般、O 委外加工", default="'N'"),
    C("currency_code", "CHAR(3)", "N", "幣別", ref="bas_currency.currency_code", default="'TWD'"),
    C("exchange_rate", PRICE, "N", "匯率", default="1"),
    C("tax_type", "CHAR(1)", "N", "1 外加、2 內含、3 零稅、4 免稅", default="'1'"),
    C("tax_rate", "DECIMAL(5,4)", "N", "稅率", default="0.05"),
    C("buyer_id", "INT", "", "採購人員", ref="bas_employee"),
    C("untaxed_amount", AMT, "N", "未稅金額", default="0"),
    C("tax_amount", AMT, "N", "稅額", default="0"),
    C("status", "CHAR(1)", "N", "D 草稿、A 核准、P 部分到貨、C 結案、X 作廢", default="'D'"),
    NOTE(),
], checks=["po_type IN ('N','O')", "status IN ('D','A','P','C','X')"], index=[("po_date",)])

T("pur_order_d", "採購單身", "採購料件、單價、交期、已交量", [
    BID(), C("po_id", "INT", "N", "採購單頭", ref="pur_order_h"),
    LINE(), C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("qty", QTY, "N", "採購量"),
    C("unit_price", PRICE, "N", "單價", default="0"),
    C("amount", AMT, "N", "金額", default="0"),
    C("due_date", "DATE", "N", "預定到貨日"),
    C("received_qty", QTY, "N", "已驗收量", default="0"),
    C("pr_line_id", "BIGINT", "", "來源請購明細", ref="pur_req_d"),
    C("wo_id", "INT", "", "委外對應工單", ref="sfc_work_order"),
    C("status", "CHAR(1)", "N", "O 未結、C 結案、X 取消", default="'O'"),
], uniq=[("po_id", "line_no")], index=[("item_id", "due_date")], audit=False,
   note="預定接收量 = qty − received_qty（status='O'）")

T("pur_receipt_h", "進貨驗收單頭", "到貨、驗收、入庫", [
    ID(), C("rcv_no", "VARCHAR(20)", "NU", "進貨單號"),
    C("rcv_date", "DATE", "N", "進貨日"),
    C("supplier_id", "INT", "N", "供應商", ref="pur_supplier"),
    C("warehouse_id", "INT", "N", "入庫倉", ref="bas_warehouse"),
    C("invoice_no", "VARCHAR(20)", "", "發票號碼"),
    C("untaxed_amount", AMT, "N", "未稅金額", default="0"),
    C("tax_amount", AMT, "N", "稅額", default="0"),
    C("status", "CHAR(1)", "N", "D 草稿、A 已入庫、X 作廢", default="'D'"),
    NOTE(),
], checks=["status IN ('D','A','X')"])

T("pur_receipt_d", "進貨驗收單身", "每項的實收、合格、退回數量", [
    BID(), C("rcv_id", "INT", "N", "進貨單頭", ref="pur_receipt_h"),
    LINE(), C("po_line_id", "BIGINT", "", "採購明細", ref="pur_order_d"),
    C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("lot_no", "VARCHAR(30)", "", "批號"),
    C("location_id", "INT", "", "儲位", ref="bas_location"),
    C("receive_qty", QTY, "N", "實收量"),
    C("accept_qty", QTY, "N", "合格量", default="0"),
    C("reject_qty", QTY, "N", "驗退量", default="0"),
    C("unit_price", PRICE, "N", "單價", default="0"),
    C("amount", AMT, "N", "金額", default="0"),
], uniq=[("rcv_id", "line_no")], audit=False)

# ───────────────────────── SFC 現場控制 ─────────────────────────
T("sfc_work_order", "工單（製令）", "製造命令：生產什麼、多少、何時；未完工量即預定接收", [
    ID(), C("wo_no", "VARCHAR(20)", "NU", "工單號"),
    C("wo_type", "CHAR(1)", "N", "S 一般、R 重工、O 委外", default="'S'"),
    C("item_id", "INT", "N", "生產料件", ref="itm_item"),
    C("bom_id", "INT", "", "使用 BOM", ref="bom_header"),
    C("routing_id", "INT", "", "使用途程", ref="rou_routing_h"),
    C("plan_qty", QTY, "N", "預計產量"),
    C("completed_qty", QTY, "N", "已完工入庫量", default="0"),
    C("scrap_qty", QTY, "N", "報廢量", default="0"),
    C("plan_start", "DATE", "N", "預計開工"),
    C("plan_finish", "DATE", "N", "預計完工"),
    C("actual_start", "DATETIME", "", "實際開工"),
    C("actual_finish", "DATETIME", "", "實際完工"),
    C("so_line_id", "BIGINT", "", "訂單生產對應", ref="sal_order_d"),
    C("planned_order_id", "BIGINT", "", "來源 MRP 計畫訂單", ref="mrp_planned_order"),
    C("parent_wo_id", "INT", "", "上階工單（自我參照）", ref="sfc_work_order"),
    C("warehouse_id", "INT", "", "完工入庫倉", ref="bas_warehouse"),
    C("supervisor_id", "INT", "", "生產線主管", ref="bas_employee"),
    C("priority", "TINYINT", "N", "優先序", default="5"),
    C("status", "CHAR(1)", "N", "P 計畫、R 已發放、S 生產中、F 完工、C 結案、X 作廢", default="'P'"),
    NOTE(),
], checks=["wo_type IN ('S','R','O')", "status IN ('P','R','S','F','C','X')", "plan_finish >= plan_start"],
   index=[("item_id", "plan_finish"), ("status",)])

T("sfc_wo_material", "工單用料", "工單發放時由 BOM 展開；應領量即 MRP 的已分配量", [
    BID(), C("wo_id", "INT", "N", "工單", ref="sfc_work_order"),
    LINE(), C("item_id", "INT", "N", "用料", ref="itm_item"),
    C("required_qty", QTY, "N", "應領量"),
    C("issued_qty", QTY, "N", "已領量", default="0"),
    C("op_seq", "SMALLINT", "", "投入工序"),
    C("issue_type", "CHAR(1)", "N", "P 領料、B 倒扣、N 不發料", default="'P'"),
    C("warehouse_id", "INT", "", "發料倉", ref="bas_warehouse"),
    C("required_date", "DATE", "N", "需用日"),
    C("substitute_for_id", "BIGINT", "", "替代哪一筆用料（自我參照）", ref="sfc_wo_material"),
], uniq=[("wo_id", "line_no")], index=[("item_id",)], audit=False)

T("sfc_wo_operation", "工單工序", "工單發放時由途程複製；排程、實績、狀態", [
    BID(), C("wo_id", "INT", "N", "工單", ref="sfc_work_order"),
    C("op_seq", "SMALLINT", "N", "工序"),
    C("op_name", "VARCHAR(50)", "N", "工序名稱"),
    C("wc_id", "INT", "N", "工作中心", ref="rou_work_center"),
    C("plan_setup_hours", "DECIMAL(12,4)", "N", "標準整備工時", default="0"),
    C("plan_run_hours", "DECIMAL(12,4)", "N", "標準加工工時（整批）", default="0"),
    C("plan_start", "DATETIME", "", "排程開始"),
    C("plan_finish", "DATETIME", "", "排程結束"),
    C("good_qty", QTY, "N", "良品累計", default="0"),
    C("scrap_qty", QTY, "N", "不良累計", default="0"),
    C("actual_hours", "DECIMAL(12,4)", "N", "實際工時累計", default="0"),
    C("status", "CHAR(1)", "N", "W 待開工、S 進行中、F 完成", default="'W'"),
], uniq=[("wo_id", "op_seq")], checks=["status IN ('W','S','F')"], audit=False)

T("sfc_request_h", "請料單頭", "現場向倉庫申請物料（REA：請料）", [
    ID(), C("req_no", "VARCHAR(20)", "NU", "請料單號"),
    C("req_date", "DATETIME", "N", "請料時間"),
    C("wo_id", "INT", "N", "工單", ref="sfc_work_order"),
    C("requester_id", "INT", "", "請料人（主管）", ref="bas_employee"),
    C("status", "CHAR(1)", "N", "D 草稿、A 待發、P 部分發料、C 已發完、X 作廢", default="'D'"),
], checks=["status IN ('D','A','P','C','X')"])

T("sfc_request_d", "請料單身", "請料料件、數量（REA：保留）", [
    BID(), C("req_id", "INT", "N", "請料單頭", ref="sfc_request_h"),
    LINE(), C("wo_material_id", "BIGINT", "", "工單用料", ref="sfc_wo_material"),
    C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("qty", QTY, "N", "請料量"),
    C("issued_qty", QTY, "N", "已發量", default="0"),
], uniq=[("req_id", "line_no")], audit=False)

T("sfc_issue_h", "領退料單頭", "倉庫發料/現場退料（REA：發料）", [
    ID(), C("issue_no", "VARCHAR(20)", "NU", "領料單號"),
    C("issue_date", "DATETIME", "N", "發料時間"),
    C("issue_type", "CHAR(1)", "N", "I 領料、R 退料、O 超領、B 倒扣", default="'I'"),
    C("wo_id", "INT", "N", "工單", ref="sfc_work_order"),
    C("req_id", "INT", "", "依據請料單（REA：履行）", ref="sfc_request_h"),
    C("warehouse_id", "INT", "N", "倉庫", ref="bas_warehouse"),
    C("keeper_id", "INT", "", "倉管人員", ref="bas_employee"),
    C("status", "CHAR(1)", "N", "D 草稿、A 已過帳、X 作廢", default="'D'"),
    NOTE(),
], checks=["issue_type IN ('I','R','O','B')", "status IN ('D','A','X')"])

T("sfc_issue_d", "領退料單身", "實發料件、批號、數量", [
    BID(), C("issue_id", "INT", "N", "領料單頭", ref="sfc_issue_h"),
    LINE(), C("wo_material_id", "BIGINT", "", "工單用料", ref="sfc_wo_material"),
    C("req_line_id", "BIGINT", "", "請料明細", ref="sfc_request_d"),
    C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("lot_no", "VARCHAR(30)", "", "批號"),
    C("location_id", "INT", "", "儲位", ref="bas_location"),
    C("qty", QTY, "N", "數量"),
], uniq=[("issue_id", "line_no")], audit=False)

T("sfc_report", "報工（計工單）", "人工/機器操作實績：工時、良品、不良（REA：人力操作、機器操作）", [
    BID(), C("report_no", "VARCHAR(20)", "NU", "報工單號"),
    C("report_type", "CHAR(1)", "N", "L 人工、M 機器", default="'L'"),
    C("wo_op_id", "BIGINT", "N", "工單工序", ref="sfc_wo_operation"),
    C("employee_id", "INT", "", "作業員", ref="bas_employee"),
    C("machine_id", "INT", "", "機器", ref="rou_machine"),
    C("wc_id", "INT", "N", "工作中心", ref="rou_work_center"),
    C("start_time", "DATETIME", "N", "開始"),
    C("end_time", "DATETIME", "", "結束"),
    C("setup_hours", "DECIMAL(10,4)", "N", "整備工時", default="0"),
    C("run_hours", "DECIMAL(10,4)", "N", "加工工時", default="0"),
    C("good_qty", QTY, "N", "良品", default="0"),
    C("scrap_qty", QTY, "N", "不良", default="0"),
    C("scrap_reason", "VARCHAR(100)", "", "不良原因"),
], checks=["report_type IN ('L','M')", "end_time IS NULL OR end_time >= start_time"],
   index=[("start_time",)], audit=False)

T("sfc_move", "移轉單", "在製品從前一工序移到下一工序", [
    BID(), C("move_no", "VARCHAR(20)", "NU", "移轉單號"),
    C("move_time", "DATETIME", "N", "移轉時間"),
    C("wo_id", "INT", "N", "工單", ref="sfc_work_order"),
    C("from_op_seq", "SMALLINT", "N", "自工序"),
    C("to_op_seq", "SMALLINT", "", "至工序（空白=完工）"),
    C("qty", QTY, "N", "數量"),
    C("mover_id", "INT", "", "移轉人", ref="bas_employee"),
], audit=False)

T("sfc_complete", "完工入庫", "成品/半成品生產入庫（REA：生產運轉產出）", [
    ID(), C("complete_no", "VARCHAR(20)", "NU", "入庫單號"),
    C("complete_date", "DATETIME", "N", "入庫時間"),
    C("wo_id", "INT", "N", "工單", ref="sfc_work_order"),
    C("warehouse_id", "INT", "N", "入庫倉", ref="bas_warehouse"),
    C("location_id", "INT", "", "儲位", ref="bas_location"),
    C("lot_no", "VARCHAR(30)", "", "生產批號"),
    C("qty", QTY, "N", "入庫量"),
    C("qc_result", "CHAR(1)", "N", "P 合格、F 不合格、W 免驗", default="'W'"),
    C("status", "CHAR(1)", "N", "D 草稿、A 已過帳、X 作廢", default="'D'"),
    NOTE(),
], checks=["qc_result IN ('P','F','W')", "status IN ('D','A','X')"])

# ───────────────────────── SAL 出貨（需 INV 前先建無妨）─────────────────────────
T("sal_ship_h", "出貨單頭", "依訂單出貨、扣成品庫存", [
    ID(), C("ship_no", "VARCHAR(20)", "NU", "出貨單號"),
    C("ship_date", "DATE", "N", "出貨日"),
    C("customer_id", "INT", "N", "客戶", ref="sal_customer"),
    C("warehouse_id", "INT", "N", "出貨倉", ref="bas_warehouse"),
    C("invoice_no", "VARCHAR(20)", "", "發票號碼"),
    C("untaxed_amount", AMT, "N", "未稅金額", default="0"),
    C("tax_amount", AMT, "N", "稅額", default="0"),
    C("status", "CHAR(1)", "N", "D 草稿、A 已過帳、X 作廢", default="'D'"),
    NOTE(),
], checks=["status IN ('D','A','X')"])

T("sal_ship_d", "出貨單身", "出貨料件與對應訂單明細", [
    BID(), C("ship_id", "INT", "N", "出貨單頭", ref="sal_ship_h"),
    LINE(), C("so_line_id", "BIGINT", "", "訂單明細", ref="sal_order_d"),
    C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("lot_no", "VARCHAR(30)", "", "批號"),
    C("location_id", "INT", "", "儲位", ref="bas_location"),
    C("qty", QTY, "N", "數量"),
    C("unit_price", PRICE, "N", "單價", default="0"),
    C("amount", AMT, "N", "金額", default="0"),
], uniq=[("ship_id", "line_no")], audit=False)

# ───────────────────────── INV 存貨控制 ─────────────────────────
T("inv_lot", "批號", "批號主檔（料件 1:N 批號）", [
    ID(), C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("lot_no", "VARCHAR(30)", "N", "批號"),
    C("received_at", "DATETIME", "N", "首次入庫時間（先進先出排序依據）", default="CURRENT_TIMESTAMP"),
    C("mfg_date", "DATE", "", "製造日"),
    C("exp_date", "DATE", "", "有效日（先到期先出依據）"),
    C("supplier_id", "INT", "", "供應商", ref="pur_supplier"),
    C("source_doc_no", "VARCHAR(20)", "", "來源單號"),
], uniq=[("item_id", "lot_no")])

T("inv_balance", "庫存餘額", "料件 × 倉庫 × 儲位 × 批號的現有量與保留量（Inventory Status）", [
    BID(), C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("warehouse_id", "INT", "N", "倉庫", ref="bas_warehouse"),
    C("location_id", "INT", "", "儲位", ref="bas_location"),
    C("lot_id", "INT", "", "批號", ref="inv_lot"),
    C("loc_key", "INT", "", "唯一鍵輔助（自動）", default="__GEN__IFNULL(location_id,0)"),
    C("lot_key", "INT", "", "唯一鍵輔助（自動）", default="__GEN__IFNULL(lot_id,0)"),
    C("rev_id", "INT", "", "版本", ref="itm_revision"),
    C("rev_key", "INT", "", "唯一鍵輔助（自動）", default="__GEN__IFNULL(rev_id,0)"),
    C("on_hand_qty", QTY, "N", "現有量", default="0"),
    C("allocated_qty", QTY, "N", "已保留（分配）量", default="0"),
    C("last_txn_at", "DATETIME", "", "最後異動"),
], uniq=[("item_id", "warehouse_id", "loc_key", "lot_key", "rev_key")], audit=False,
   note="可用量 = 現有量 − 保留量（僅 is_nettable 倉庫計入 MRP）")

T("inv_txn", "存貨異動帳", "所有入出庫的流水帳（單一真相，餘額可由此重建）", [
    BID(), C("txn_time", "DATETIME", "N", "異動時間"),
    C("doc_type", "VARCHAR(10)", "N", "單別", ref="sys_doc_type.doc_type"),
    C("doc_no", "VARCHAR(20)", "N", "單號"),
    C("doc_line_no", "SMALLINT", "", "項次"),
    C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("warehouse_id", "INT", "N", "倉庫", ref="bas_warehouse"),
    C("location_id", "INT", "", "儲位", ref="bas_location"),
    C("lot_id", "INT", "", "批號", ref="inv_lot"),
    C("qty", QTY, "N", "數量（入正出負）"),
    C("unit_cost", PRICE, "N", "單位成本", default="0"),
    C("amount", AMT, "N", "金額", default="0"),
    C("wo_id", "INT", "", "相關工單", ref="sfc_work_order"),
    C("created_by", "INT", "", "建立者", ref="sys_user"),
    C("created_at", "DATETIME", "N", "建立時間", default="CURRENT_TIMESTAMP"),
], index=[("item_id", "txn_time"), ("doc_type", "doc_no")], audit=False)

T("inv_layer", "先進先出成本層", "每次入庫產生一層；出庫依入庫時間由舊到新扣減剩餘量", [
    BID(), C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("warehouse_id", "INT", "N", "倉庫", ref="bas_warehouse"),
    C("lot_id", "INT", "", "批號", ref="inv_lot"),
    C("rev_id", "INT", "", "版本", ref="itm_revision"),
    C("in_txn_id", "BIGINT", "N", "產生此層的入庫異動", ref="inv_txn"),
    C("received_at", "DATETIME", "N", "入庫時間（先進先出排序）"),
    C("in_qty", QTY, "N", "入庫量"),
    C("remaining_qty", QTY, "N", "剩餘量"),
    C("unit_cost", PRICE, "N", "本位幣單位成本（含匯率換算、運費分攤）"),
    C("is_closed", "TINYINT(1)", "", "已耗盡（自動）", default="__GEN__IF(remaining_qty <= 0, 1, 0)"),
], checks=["remaining_qty >= 0", "remaining_qty <= in_qty"],
   index=[("item_id", "warehouse_id", "is_closed", "received_at")], audit=False,
   note="出庫成本 = Σ(依 received_at 由舊到新耗用量 × 該層單位成本)")

T("inv_layer_consume", "成本層耗用明細", "出庫異動 × 成本層（多對多）：每筆出庫吃掉哪些層、各多少", [
    BID(), C("out_txn_id", "BIGINT", "N", "出庫異動", ref="inv_txn"),
    C("layer_id", "BIGINT", "N", "被耗用的成本層", ref="inv_layer"),
    C("qty", QTY, "N", "耗用量"),
    C("unit_cost", PRICE, "N", "單位成本"),
    C("amount", AMT, "N", "成本金額"),
], index=[("layer_id",)], audit=False)

T("inv_transfer_h", "調撥單頭", "倉庫間移轉", [
    ID(), C("trf_no", "VARCHAR(20)", "NU", "調撥單號"),
    C("trf_date", "DATE", "N", "調撥日"),
    C("from_wh_id", "INT", "N", "撥出倉", ref="bas_warehouse"),
    C("to_wh_id", "INT", "N", "撥入倉", ref="bas_warehouse"),
    C("status", "CHAR(1)", "N", "D 草稿、A 已過帳、X 作廢", default="'D'"),
    NOTE(),
], checks=["from_wh_id <> to_wh_id", "status IN ('D','A','X')"])

T("inv_transfer_d", "調撥單身", "調撥料件與數量", [
    BID(), C("trf_id", "INT", "N", "調撥單頭", ref="inv_transfer_h"),
    LINE(), C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("lot_no", "VARCHAR(30)", "", "批號"),
    C("qty", QTY, "N", "數量"),
], uniq=[("trf_id", "line_no")], audit=False)

T("inv_adjust_h", "庫存調整單頭", "報廢、盤盈虧、其他調整", [
    ID(), C("adj_no", "VARCHAR(20)", "NU", "調整單號"),
    C("adj_date", "DATE", "N", "調整日"),
    C("warehouse_id", "INT", "N", "倉庫", ref="bas_warehouse"),
    C("reason", "CHAR(1)", "N", "C 盤點差異、S 報廢、O 其他", default="'O'"),
    C("count_id", "INT", "", "來源盤點單", ref="inv_count_h"),
    C("status", "CHAR(1)", "N", "D 草稿、A 已過帳、X 作廢", default="'D'"),
    NOTE(),
], checks=["reason IN ('C','S','O')", "status IN ('D','A','X')"])

T("inv_adjust_d", "庫存調整單身", "調整料件與數量（正增負減）", [
    BID(), C("adj_id", "INT", "N", "調整單頭", ref="inv_adjust_h"),
    LINE(), C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("lot_no", "VARCHAR(30)", "", "批號"),
    C("qty", QTY, "N", "調整量（正增負減）"),
    C("unit_cost", PRICE, "N", "單位成本", default="0"),
], uniq=[("adj_id", "line_no")], audit=False)

T("inv_count_h", "盤點單頭", "定期/循環盤點", [
    ID(), C("count_no", "VARCHAR(20)", "NU", "盤點單號"),
    C("count_date", "DATE", "N", "盤點日"),
    C("warehouse_id", "INT", "N", "倉庫", ref="bas_warehouse"),
    C("count_type", "CHAR(1)", "N", "P 全面盤點、C 循環盤點", default="'P'"),
    C("status", "CHAR(1)", "N", "D 盤點中、F 已完成、A 已調整、X 作廢", default="'D'"),
], checks=["count_type IN ('P','C')", "status IN ('D','F','A','X')"])

T("inv_count_d", "盤點單身", "帳面量 vs 實盤量", [
    BID(), C("count_id", "INT", "N", "盤點單頭", ref="inv_count_h"),
    LINE(), C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("location_id", "INT", "", "儲位", ref="bas_location"),
    C("lot_no", "VARCHAR(30)", "", "批號"),
    C("book_qty", QTY, "N", "帳面量", default="0"),
    C("count_qty", QTY, "", "實盤量"),
    C("diff_qty", QTY, "", "差異（自動）", default="__GEN__count_qty - book_qty"),
], uniq=[("count_id", "line_no")], audit=False)

# ───────────────────────── ACC 會計與財務分析 ─────────────────────────
T("acc_period", "會計期間", "月結與關帳（關帳後不可再異動）", [
    C("period", "CHAR(6)", "PN", "期別 yyyymm"),
    C("start_date", "DATE", "N", "起日"),
    C("end_date", "DATE", "N", "迄日"),
    C("is_closed", "TINYINT(1)", "N", "已關帳", default="0"),
    C("closed_at", "DATETIME", "", "關帳時間"),
    C("closed_by", "INT", "", "關帳人", ref="sys_user"),
])

T("acc_account_map", "會計科目對應", "拋轉傳票時，各成本項目對應到一般公司會計的科目", [
    ID(), C("map_code", "VARCHAR(20)", "NU", "對應代碼，如 INV_RAW、WIP、FG、COGS、AP、PPV"),
    C("map_name", "VARCHAR(50)", "N", "說明"),
    C("account_no", "VARCHAR(20)", "N", "會計科目代號"),
    C("account_name", "VARCHAR(50)", "N", "會計科目名稱"),
])

T("acc_wc_rate", "工作中心費率", "每工時的直接人工與製造費用分攤率", [
    ID(), C("wc_id", "INT", "N", "工作中心", ref="rou_work_center"),
    C("period", "CHAR(6)", "N", "期別", ref="acc_period"),
    C("labor_rate", PRICE, "N", "人工費率（元/時）", default="0"),
    C("overhead_rate", PRICE, "N", "製費率（元/時）", default="0"),
], uniq=[("wc_id", "period")])

T("acc_item_cost", "料件成本", "標準成本（BOM＋途程累算）或月加權實際成本", [
    ID(), C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("cost_type", "CHAR(1)", "N", "S 標準、A 實際"),
    C("period", "CHAR(6)", "N", "期別", ref="acc_period"),
    C("material_cost", PRICE, "N", "材料", default="0"),
    C("labor_cost", PRICE, "N", "人工", default="0"),
    C("overhead_cost", PRICE, "N", "製費", default="0"),
    C("outsource_cost", PRICE, "N", "委外", default="0"),
    C("total_cost", PRICE, "", "合計（自動）", default="__GEN__material_cost + labor_cost + overhead_cost + outsource_cost"),
    C("rolled_at", "DATETIME", "", "成本累算時間"),
], uniq=[("item_id", "cost_type", "period")], checks=["cost_type IN ('S','A')"])

T("acc_inv_month", "存貨月結", "料件 × 倉庫 × 期別：期初、入、出、期末數量金額（存貨週轉分析）", [
    BID(), C("period", "CHAR(6)", "N", "期別", ref="acc_period"),
    C("item_id", "INT", "N", "料件", ref="itm_item"),
    C("warehouse_id", "INT", "N", "倉庫", ref="bas_warehouse"),
    C("begin_qty", QTY, "N", "期初量", default="0"),
    C("begin_amt", AMT, "N", "期初金額", default="0"),
    C("in_qty", QTY, "N", "本期入", default="0"),
    C("in_amt", AMT, "N", "入金額", default="0"),
    C("out_qty", QTY, "N", "本期出", default="0"),
    C("out_amt", AMT, "N", "出金額", default="0"),
    C("end_qty", QTY, "N", "期末量", default="0"),
    C("end_amt", AMT, "N", "期末金額", default="0"),
    C("unit_cost", PRICE, "N", "月加權單位成本", default="0"),
], uniq=[("period", "item_id", "warehouse_id")], audit=False)

T("acc_wo_cost", "工單成本", "工單 × 期別：投入材料、人工、製費、轉出完工、期末在製、差異", [
    BID(), C("wo_id", "INT", "N", "工單", ref="sfc_work_order"),
    C("period", "CHAR(6)", "N", "期別", ref="acc_period"),
    C("material_amt", AMT, "N", "材料投入", default="0"),
    C("labor_amt", AMT, "N", "人工投入", default="0"),
    C("overhead_amt", AMT, "N", "製費投入", default="0"),
    C("outsource_amt", AMT, "N", "委外投入", default="0"),
    C("completed_amt", AMT, "N", "轉出完工", default="0"),
    C("wip_end_amt", AMT, "N", "期末在製", default="0"),
    C("standard_amt", AMT, "N", "標準成本", default="0"),
    C("variance_amt", AMT, "N", "差異", default="0"),
], uniq=[("wo_id", "period")], audit=False)

T("acc_variance", "成本差異", "採購價差、用料差異、人工效率差異、製費差異、良率差異", [
    BID(), C("period", "CHAR(6)", "N", "期別", ref="acc_period"),
    C("variance_type", "CHAR(3)", "N", "PPV 採購價差、MUV 用料差、LEV 人工效率、OHV 製費、YLD 良率、FXV 匯兌差異"),
    C("item_id", "INT", "", "料件", ref="itm_item"),
    C("wo_id", "INT", "", "工單", ref="sfc_work_order"),
    C("ref_doc_no", "VARCHAR(20)", "", "相關單號"),
    C("amount", AMT, "N", "差異金額（正=不利）"),
    NOTE(),
], checks=["variance_type IN ('PPV','MUV','LEV','OHV','YLD','FXV')"], audit=False)

T("acc_voucher_h", "拋轉傳票單頭", "由進貨/領料/完工/出貨/差異彙總，拋轉到「資料助秘之一般公司會計」", [
    ID(), C("voucher_no", "VARCHAR(20)", "NU", "傳票號碼"),
    C("voucher_date", "DATE", "N", "傳票日期"),
    C("period", "CHAR(6)", "N", "期別", ref="acc_period"),
    C("source_type", "CHAR(3)", "N", "PUR 進貨、ISS 領料、CMP 完工、SHP 出貨、VAR 差異、ADJ 調整"),
    C("status", "CHAR(1)", "N", "N 未拋轉、E 已匯出檔案、S 已傳送 API", default="'N'"),
    C("exported_at", "DATETIME", "", "拋轉時間"),
    C("summary", "VARCHAR(200)", "", "摘要"),
], checks=["source_type IN ('PUR','ISS','CMP','SHP','VAR','ADJ')", "status IN ('N','E','S')"])

T("acc_voucher_d", "拋轉傳票單身", "借貸分錄", [
    BID(), C("voucher_id", "INT", "N", "傳票單頭", ref="acc_voucher_h"),
    LINE(), C("account_no", "VARCHAR(20)", "N", "科目代號"),
    C("dr_amount", AMT, "N", "借方", default="0"),
    C("cr_amount", AMT, "N", "貸方", default="0"),
    C("summary", "VARCHAR(200)", "", "摘要"),
    C("dept_id", "INT", "", "部門", ref="bas_dept"),
    C("ref_doc_no", "VARCHAR(20)", "", "來源單號"),
], uniq=[("voucher_id", "line_no")], checks=["dr_amount >= 0 AND cr_amount >= 0"], audit=False)


# ════════════════════════ 版本欄位（插在指定欄位後面）════════════════════════
# 同一電子料件會有不同版本：交易、BOM、庫存都要能指定版本；空白 = 不限版本（用目前量產版）
REV_COLS = {
    "bom_header": [("parent_rev_id", "parent_item_id", "母件版本（此 BOM 適用的版本）")],
    "bom_detail": [("child_rev_id", "child_item_id", "指定元件版本（空白=不限，可互換版本皆可）")],
    "bom_substitute": [("sub_rev_id", "sub_item_id", "替代料版本")],
    "bom_ecn": [("from_rev_id", "new_bom_id", "變更前版本"), ("to_rev_id", "from_rev_id", "變更後版本")],
    "rou_routing_h": [("rev_id", "item_id", "適用版本（空白=全部版本）")],
    "pur_item_source": [("rev_id", "supplier_id", "核可版本（空白=全部版本）")],
    "sal_order_d": [("rev_id", "item_id", "訂購版本（空白=目前量產版）")],
    "sal_ship_d": [("rev_id", "item_id", "出貨版本")],
    "mrp_planned_order": [("rev_id", "item_id", "建議版本")],
    "pur_req_d": [("rev_id", "item_id", "請購版本")],
    "pur_order_d": [("rev_id", "item_id", "採購版本")],
    "pur_receipt_d": [("rev_id", "item_id", "實收版本")],
    "sfc_work_order": [("rev_id", "item_id", "生產版本")],
    "sfc_wo_material": [("rev_id", "item_id", "用料版本")],
    "sfc_request_d": [("rev_id", "item_id", "請料版本")],
    "sfc_issue_d": [("rev_id", "item_id", "實發版本")],
    "sfc_complete": [("rev_id", "wo_id", "入庫版本")],
    "inv_lot": [("rev_id", "item_id", "批號所屬版本")],
    "inv_txn": [("rev_id", "item_id", "異動版本")],
    "inv_transfer_d": [("rev_id", "item_id", "調撥版本")],
    "inv_adjust_d": [("rev_id", "item_id", "調整版本")],
    "inv_count_d": [("rev_id", "item_id", "盤點版本")],
    "acc_item_cost": [("rev_id", "item_id", "成本版本（空白=料件通用）")],
}


def _apply_rev_cols():
    for tname, adds in REV_COLS.items():
        t = next(x for x in TABLES if x["name"] == tname)
        for col, after, desc in adds:
            names = [c["name"] for c in t["cols"]]
            t["cols"].insert(names.index(after) + 1, C(col, "INT", "", desc, ref="itm_revision"))
    # 有料件又有版本的表：自動加 (料件, 版本) 複合索引
    for t in TABLES:
        names = [c["name"] for c in t["cols"]]
        for item_col, rev_col in (("item_id", "rev_id"), ("parent_item_id", "parent_rev_id"),
                                  ("child_item_id", "child_rev_id"), ("sub_item_id", "sub_rev_id")):
            if item_col in names and rev_col in names and (item_col, rev_col) not in t["index"]:
                t["index"].append((item_col, rev_col))


_apply_rev_cols()

# ════════════════════════ 產地欄位（製造商料號＋原產國）════════════════════════
COO_COLS = {
    # 表: [(欄位, 插在哪欄後, 型別, 說明, 參照)]
    "bom_detail": [("required_country", "child_rev_id", "CHAR(2)", "指定產地（空白=不限，如客戶要求日製電容）", "bas_country")],
    "pur_item_source": [("mfr_part_id", "rev_id", "INT", "供應的製造商料號", "itm_mfr_part"),
                        ("origin_country", "mfr_part_id", "CHAR(2)", "原產國", "bas_country")],
    "pur_order_d": [("mfr_part_id", "rev_id", "INT", "指定製造商料號", "itm_mfr_part"),
                    ("origin_country", "mfr_part_id", "CHAR(2)", "指定原產國", "bas_country")],
    "pur_receipt_d": [("mfr_part_id", "rev_id", "INT", "實收製造商料號", "itm_mfr_part"),
                      ("origin_country", "mfr_part_id", "CHAR(2)", "實收原產國", "bas_country"),
                      ("date_code", "origin_country", "VARCHAR(10)", "生產週別 Date Code，如 2645", None),
                      ("coo_cert_no", "date_code", "VARCHAR(40)", "原產地證明書號", None)],
    "inv_lot": [("mfr_part_id", "rev_id", "INT", "製造商料號", "itm_mfr_part"),
                ("origin_country", "mfr_part_id", "CHAR(2)", "原產國", "bas_country"),
                ("date_code", "origin_country", "VARCHAR(10)", "生產週別 Date Code", None)],
    "sfc_wo_material": [("required_country", "rev_id", "CHAR(2)", "指定產地（由 BOM 帶入）", "bas_country")],
}
for _t, _adds in COO_COLS.items():
    _tb = next(x for x in TABLES if x["name"] == _t)
    for _col, _after, _typ, _desc, _ref in _adds:
        _names = [c["name"] for c in _tb["cols"]]
        _tb["cols"].insert(_names.index(_after) + 1, C(_col, _typ, "", _desc, ref=_ref))
        if _col == "origin_country":
            _tb["index"].append(("item_id", "origin_country"))

# ════════════════════════ 幣別、匯率、本位幣金額 ════════════════════════
FX_HEAD = {  # 單頭：插在哪欄後；已有 currency_code/exchange_rate 的只補本位幣金額
    "sal_order_h": "tax_amount", "pur_order_h": "tax_amount",
    "pur_receipt_h": "tax_amount", "sal_ship_h": "tax_amount",
}
for _t, _after in FX_HEAD.items():
    _tb = next(x for x in TABLES if x["name"] == _t)
    _names = [c["name"] for c in _tb["cols"]]
    _new = []
    if "currency_code" not in _names:
        _new += [C("currency_code", "CHAR(3)", "N", "幣別", ref="bas_currency", default="'TWD'"),
                 C("exchange_rate", PRICE, "N", "匯率（1 外幣 = ? 本位幣，依單據日帶入）", default="1")]
    _new += [C("base_untaxed_amount", AMT, "N", "本位幣未稅金額", default="0"),
             C("base_tax_amount", AMT, "N", "本位幣稅額", default="0")]
    _i = _names.index(_after) + 1
    _tb["cols"][_i:_i] = _new
    _tb["index"].append(("currency_code",))
for _t in ("pur_order_d", "pur_receipt_d", "sal_order_d", "sal_ship_d"):
    _tb = next(x for x in TABLES if x["name"] == _t)
    _names = [c["name"] for c in _tb["cols"]]
    _tb["cols"].insert(_names.index("amount") + 1, C("base_amount", AMT, "N", "本位幣金額", default="0"))

# acc_item_cost 唯一鍵需含版本
next(t for t in TABLES if t["name"] == "acc_item_cost")["uniq"] = [("item_id", "cost_type", "period", "rev_key")]
next(t for t in TABLES if t["name"] == "acc_item_cost")["cols"].insert(
    3, C("rev_key", "INT", "", "唯一鍵輔助（自動）", default="__GEN__IFNULL(rev_id,0)"))

# ════════════════════════ 產生器 ════════════════════════
AUDIT_COLS = [
    C("created_at", "DATETIME", "N", "建立時間", default="CURRENT_TIMESTAMP"),
    C("created_by", "INT", "", "建立者", ref="sys_user"),
    C("updated_at", "DATETIME", "", "修改時間", default="__ONUPDATE__"),
    C("updated_by", "INT", "", "修改者", ref="sys_user"),
]

TABLE_MAP = {t["name"]: t for t in TABLES}


def ref_target(ref):
    tbl, _, col = ref.partition(".")
    if not col:  # 未指定欄位 → 目標表的單欄主鍵
        pk = [c["name"] for c in TABLE_MAP[tbl]["cols"] if "P" in c["flags"]]
        assert len(pk) == 1, f"{tbl} 為複合主鍵，參照時須指定欄位"
        col = pk[0]
    return tbl, col


def all_cols(t):
    return t["cols"] + (AUDIT_COLS if t["audit"] else [])


def col_sql(c):
    s = f"  `{c['name']}` {c['typ']}"
    d = c["default"]
    if d and d.startswith("__GEN__"):
        return s + f" AS ({d[7:]}) PERSISTENT COMMENT '{c['desc']}'"
    if "N" in c["flags"] or "P" in c["flags"]:
        s += " NOT NULL"
    if "A" in c["flags"]:
        s += " AUTO_INCREMENT"
    if d == "__ONUPDATE__":
        s += " NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP"
    elif d is not None:
        s += f" DEFAULT {d}"
    return s + f" COMMENT '{c['desc']}'"


def short(name, n=64):
    return name if len(name) <= n else name[:n]


def table_sql(t):
    cols = all_cols(t)
    lines = [col_sql(c) for c in cols]
    pk = [c["name"] for c in cols if "P" in c["flags"]]
    lines.append(f"  PRIMARY KEY ({', '.join(f'`{p}`' for p in pk)})")
    for c in cols:
        if "U" in c["flags"]:
            lines.append(f"  UNIQUE KEY `uk_{t['name']}_{c['name']}` (`{c['name']}`)")
    for i, u in enumerate(t["uniq"], 1):
        lines.append(f"  UNIQUE KEY `uk_{t['name']}_{i}` ({', '.join(f'`{x}`' for x in u)})")
    for i, ix in enumerate(t["index"], 1):
        lines.append(f"  KEY `ix_{t['name']}_{i}` ({', '.join(f'`{x}`' for x in ix)})")
    for c in cols:
        if c["ref"]:
            tbl, rc = ref_target(c["ref"])
            assert tbl in TABLE_MAP, f"{t['name']}.{c['name']} → 未知表 {tbl}"
            on_del = "CASCADE" if is_detail_parent(t, c) else "RESTRICT"
            lines.append(f"  CONSTRAINT `{short('fk_' + t['name'] + '_' + c['name'])}` FOREIGN KEY (`{c['name']}`) "
                         f"REFERENCES `{tbl}` (`{rc}`) ON DELETE {on_del}")
    for i, ck in enumerate(t["checks"], 1):
        lines.append(f"  CONSTRAINT `ck_{t['name']}_{i}` CHECK ({ck})")
    return (f"-- {t['title']}：{t['desc']}\nCREATE TABLE IF NOT EXISTS `{t['name']}` (\n" + ",\n".join(lines) +
            f"\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='{t['title']}';\n")


# 單身刪單頭時一併刪除（CASCADE）的關係：單身/明細指向自己的單頭
CASCADE_PAIRS = {
    ("fct_forecast_d", "forecast_id"), ("sal_order_d", "so_id"), ("sal_ship_d", "ship_id"),
    ("rou_routing_d", "routing_id"), ("bom_detail", "bom_id"), ("bom_substitute", "bom_detail_id"),
    ("mps_plan_d", "mps_id"), ("mps_demand_link", "mps_line_id"),
    ("mrp_record", "run_id"), ("mrp_planned_order", "run_id"), ("mrp_pegging", "run_id"),
    ("mrp_exception", "run_id"), ("crp_load", "run_id"), ("crp_load_detail", "load_id"),
    ("pur_req_d", "pr_id"), ("pur_order_d", "po_id"), ("pur_receipt_d", "rcv_id"),
    ("sfc_wo_material", "wo_id"), ("sfc_wo_operation", "wo_id"), ("sfc_request_d", "req_id"),
    ("sfc_issue_d", "issue_id"), ("inv_transfer_d", "trf_id"), ("inv_adjust_d", "adj_id"),
    ("inv_count_d", "count_id"), ("acc_voucher_d", "voucher_id"), ("sys_user_role", "user_id"),
    ("sys_user_role", "role_id"), ("sys_role_perm", "role_id"), ("rou_wc_calendar", "wc_id"),
    ("itm_plan", "item_id"),
}


def is_detail_parent(t, c):
    return (t["name"], c["name"]) in CASCADE_PAIRS


def relation_kind(t, c):
    """回傳此 FK 欄位代表的關聯種類（從本表角度）。"""
    pk = [x["name"] for x in t["cols"] if "P" in x["flags"]]
    if "U" in c["flags"] or pk == [c["name"]]:
        return "1:1"
    return "N:1"


def gen_sql():
    out = ["-- ============================================================================",
           "-- 資料助秘之物料需求II生產製造系統（ZMS MRP II）— MariaDB 建表腳本",
           "-- 由 db/schema_spec.py 自動產生，請勿手改；修改規格後重新執行產生器",
           f"-- 資料表 {len(TABLES)} 張；字元集 utf8mb4；引擎 InnoDB",
           "-- ============================================================================",
           "SET NAMES utf8mb4;", "SET FOREIGN_KEY_CHECKS = 0;", ""]
    for code, name, _ in MODULES:
        ts = [t for t in TABLES if t["name"].startswith(code.lower() + "_")]
        out.append(f"-- ─────────────── {code} {name}（{len(ts)} 張）───────────────")
        out += [table_sql(t) for t in ts]
    out += ["SET FOREIGN_KEY_CHECKS = 1;",
            "INSERT IGNORE INTO sys_schema_version (version, app_version, note) VALUES ('1.0.0', '1.0.0', '初始建立');", ""]
    return "\n".join(out)


def gen_md():
    out = ["# 資料表欄位明細", "",
           "> 由 `db/schema_spec.py` 自動產生。規劃說明請看 [資料庫規劃.md](資料庫規劃.md)。", "",
           f"共 **{len(TABLES)}** 張表。旗標：🔑 主鍵、🔗 外鍵、★ 唯一、＊ 必填。"
           "標示「共同欄位」的表另有 created_at / created_by / updated_at / updated_by。", ""]
    # 反向參照
    refd: dict[str, list[str]] = {}
    for t in TABLES:
        for c in t["cols"]:
            if c["ref"]:
                tbl, _ = ref_target(c["ref"])
                refd.setdefault(tbl, []).append(f"{t['name']}.{c['name']}")
    for code, name, desc in MODULES:
        ts = [t for t in TABLES if t["name"].startswith(code.lower() + "_")]
        out += [f"## {code} {name}", "", f"{desc}。", ""]
        for t in ts:
            out += [f"### `{t['name']}` {t['title']}", "", t["desc"] + ("（含共同欄位）" if t["audit"] else ""), ""]
            out += ["| 欄位 | 型別 | 旗標 | 說明 | 關聯 |", "|---|---|---|---|---|"]
            for c in t["cols"]:
                fl = ("🔑" if "P" in c["flags"] else "") + ("★" if "U" in c["flags"] else "") + \
                     ("＊" if "N" in c["flags"] else "") + ("🔗" if c["ref"] else "")
                rel = ""
                if c["ref"]:
                    tbl, rc = ref_target(c["ref"])
                    rel = f"{relation_kind(t, c)} → `{tbl}.{rc}`"
                d = c["desc"]
                if c["default"] and c["default"].startswith("__GEN__"):
                    d += f"＝`{c['default'][7:]}`"
                elif c["default"] and c["default"] not in ("__ONUPDATE__",):
                    d += f"（預設 {c['default']}）"
                out.append(f"| `{c['name']}` | {c['typ']} | {fl} | {d} | {rel} |")
            extra = []
            if t["uniq"]:
                extra.append("唯一鍵：" + "；".join("(" + ", ".join(u) + ")" for u in t["uniq"]))
            if t["checks"]:
                extra.append("檢查：" + "；".join(f"`{x}`" for x in t["checks"]))
            if t["name"] in refd:
                extra.append("被參照（1:N）：" + "、".join(f"`{x}`" for x in refd[t["name"]]))
            if t["note"]:
                extra.append("公式：" + t["note"])
            out += [""] + [f"- {x}" for x in extra] + [""]
    return "\n".join(out)


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for p in (os.path.join(root, "db", "schema.sql"), os.path.join(root, "mrp", "schema.sql")):   # mrp/ 隨程式打包
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(gen_sql())
    with open(os.path.join(root, "docs", "資料表欄位明細.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(gen_md())
    counts = {code: sum(t["name"].startswith(code.lower() + "_") for t in TABLES) for code, *_ in MODULES}
    fk = sum(1 for t in TABLES for c in all_cols(t) if c["ref"])
    print(f"tables={len(TABLES)} fks={fk}", counts)
