"""第一次建立資料庫時寫入的預設資料：功能、角色權限、單別、幣別、國家、單位、倉庫、行事曆、科目對應、參數。"""
import datetime as dt

# 權限以模組為單位（等級：0 無、1 查詢、2 維護）
FUNCS = [
    ("BAS", "基本資料", "BAS"), ("ITM", "料件與版本", "ITM"), ("BOM", "物料清單與工程變更", "BOM"),
    ("ROU", "途程與工作中心", "ROU"), ("FCT", "需求預測", "FCT"), ("SAL", "客戶訂單與出貨", "SAL"),
    ("MPS", "主生產排程", "MPS"), ("MRP", "物料需求規劃", "MRP"), ("CRP", "產能需求規劃", "CRP"),
    ("PUR", "採購與進貨", "PUR"), ("SFC", "現場控制（工單）", "SFC"), ("INV", "存貨控制", "INV"),
    ("ACC", "成本與會計", "ACC"), ("SYS", "系統管理", "SYS"),
]
FUNC_NAMES = {k: n for k, n, _ in FUNCS}

# 角色範本：代碼, 名稱, {功能: 等級}；未列出的功能 = 查詢
ROLES = [
    ("ADMIN", "系統管理員", {k: 2 for k, *_ in FUNCS}),
    ("PLANNER", "生管人員", {"ITM": 2, "BOM": 2, "ROU": 2, "FCT": 2, "MPS": 2, "MRP": 2, "CRP": 2, "SFC": 2,
                           "SYS": 0, "ACC": 0}),
    ("BUYER", "採購人員", {"PUR": 2, "ITM": 1, "SYS": 0, "ACC": 0}),
    ("SHOP", "現場人員", {"SFC": 2, "SYS": 0, "ACC": 0, "PUR": 0, "SAL": 0}),
    ("WH", "倉管人員", {"INV": 2, "PUR": 1, "SYS": 0, "ACC": 0}),
    ("SALES", "業務人員", {"SAL": 2, "FCT": 2, "SYS": 0, "ACC": 0, "PUR": 0}),
    ("ACCT", "會計人員", {"ACC": 2, "SYS": 0}),
    ("VIEW", "查詢人員", {"SYS": 0, "ACC": 0}),
]

DOC_TYPES = [  # 單別, 名稱, 模組, 前綴, 存貨方向
    ("FC", "需求預測", "FCT", "FC", 0), ("SO", "客戶訂單", "SAL", "SO", 0), ("SHP", "出貨單", "SAL", "SH", -1),
    ("MPS", "主生產排程", "MPS", "MPS", 0), ("MRP", "MRP 執行", "MRP", "MRP", 0), ("CRP", "產能運算", "CRP", "CRP", 0),
    ("ECN", "工程變更", "BOM", "ECN", 0), ("PR", "請購單", "PUR", "PR", 0), ("PO", "採購單", "PUR", "PO", 0),
    ("RCV", "進貨驗收", "PUR", "RC", 1), ("WO", "工單", "SFC", "WO", 0), ("REQ", "請料單", "SFC", "RQ", 0),
    ("ISS", "領料單", "SFC", "IS", -1), ("RTN", "退料單", "SFC", "RT", 1), ("RPT", "報工單", "SFC", "RP", 0),
    ("MOV", "移轉單", "SFC", "MV", 0), ("CMP", "完工入庫", "SFC", "CP", 1), ("TRF", "調撥單", "INV", "TF", 0),
    ("ADJ", "庫存調整", "INV", "AJ", 0), ("CNT", "盤點單", "INV", "CT", 0), ("BEG", "期初開帳", "INV", "BG", 1),
    ("JV", "拋轉傳票", "ACC", "JV", 0),
]

CURRENCIES = [  # 代碼, 名稱, 符號, 本位幣, 金額小數, 匯率
    ("TWD", "新台幣", "NT$", 1, 0, 1), ("USD", "美元", "US$", 0, 2, 32.10), ("JPY", "日圓", "¥", 0, 0, 0.2120),
    ("KRW", "韓元", "₩", 0, 0, 0.02350), ("CNY", "人民幣", "CN¥", 0, 2, 4.420), ("EUR", "歐元", "€", 0, 2, 34.80),
]

COUNTRIES = [
    ("TW", "台灣", "Taiwan", "台製"), ("JP", "日本", "Japan", "日製"), ("US", "美國", "United States", "美製"),
    ("KR", "韓國", "Korea", "韓製"), ("CN", "中國", "China", "陸製"), ("MY", "馬來西亞", "Malaysia", "馬製"),
    ("VN", "越南", "Vietnam", "越製"), ("TH", "泰國", "Thailand", "泰製"), ("DE", "德國", "Germany", "德製"),
    ("PH", "菲律賓", "Philippines", "菲製"), ("SG", "新加坡", "Singapore", "星製"), ("MX", "墨西哥", "Mexico", "墨製"),
]

UNITS = [("PCS", "個"), ("PNL", "片"), ("SET", "台"), ("KIT", "組"), ("M", "公尺"), ("KG", "公斤"), ("PC", "條"),
         ("CPY", "份"), ("REEL", "捲"), ("BAG", "包"), ("BOX", "箱")]

WAREHOUSES = [("RM", "原料倉", "R", 1), ("FG", "成品倉", "F", 1), ("WIP", "在製倉", "W", 1),
              ("QC", "IQC 待驗倉", "Q", 0), ("SC", "報廢倉", "S", 0)]

ACCOUNT_MAP = [  # 對應代碼, 說明, 科目代號, 科目名稱
    ("INV_RAW", "原料存貨", "1231", "原料"), ("INV_WIP", "在製品存貨", "1232", "在製品"),
    ("INV_FG", "製成品存貨", "1233", "製成品"), ("VAT_IN", "進項稅額", "1268", "進項稅額"),
    ("AP", "應付帳款", "2171", "應付帳款"), ("AR", "應收帳款", "1191", "應收帳款"),
    ("SALES", "銷貨收入", "4111", "銷貨收入"), ("VAT_OUT", "銷項稅額", "2204", "銷項稅額"),
    ("COGS", "銷貨成本", "5111", "銷貨成本"), ("LABOR_APPLIED", "已分攤直接人工", "5121", "直接人工"),
    ("OH_APPLIED", "已分攤製造費用", "5131", "製造費用"), ("PPV", "採購價格差異", "5141", "採購價格差異"),
    ("MUV", "用料差異", "5142", "材料用量差異"), ("SCRAP", "存貨報廢損失", "5143", "存貨報廢損失"),
    ("INV_ADJ", "存貨盤盈虧", "5144", "存貨盤盈虧"), ("FXV", "匯兌損益", "7151", "兌換損益"),
]

PARAMS = [
    ("mrp_horizon_days", "120", "MRP 計畫天數"), ("mrp_use_safety", "1", "MRP 考慮安全存量"),
    ("mrp_use_scrap", "1", "MRP 考慮損耗率"), ("crp_horizon_days", "60", "CRP 計畫天數"),
    ("default_tax_rate", "0.05", "預設營業稅率"), ("api_port", "8795", "手機連線埠"),
]


def seed_all(db):
    db.exec("INSERT IGNORE INTO sys_company (id, company_name) VALUES (1, '（請到「公司設定」輸入公司名稱）')")
    db.exec_many("INSERT IGNORE INTO sys_function (func_code, func_name, module, sort_no) VALUES (%s,%s,%s,%s)",
                 [(k, n, m, i) for i, (k, n, m) in enumerate(FUNCS)])
    for code, name, perms in ROLES:
        db.exec("INSERT IGNORE INTO sys_role (role_code, role_name) VALUES (%s,%s)", (code, name))
        rid = db.value("SELECT id FROM sys_role WHERE role_code=%s", (code,))
        for f, *_ in FUNCS:
            lvl = perms.get(f, 1)
            db.exec("INSERT IGNORE INTO sys_role_perm (role_id, func_code, can_view, can_add, can_edit, can_delete, "
                    "can_approve, can_print) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (rid, f, int(lvl >= 1), int(lvl >= 2), int(lvl >= 2), int(lvl >= 2), int(lvl >= 2), int(lvl >= 1)))
    db.exec_many("INSERT IGNORE INTO sys_doc_type (doc_type, doc_name, module, prefix, inv_effect) VALUES (%s,%s,%s,%s,%s)",
                 DOC_TYPES)
    db.exec_many("INSERT IGNORE INTO bas_currency (currency_code, currency_name, symbol, is_base, amount_decimals, "
                 "exchange_rate) VALUES (%s,%s,%s,%s,%s,%s)", CURRENCIES)
    today = dt.date.today()
    db.exec_many("INSERT IGNORE INTO bas_exchange_rate (currency_code, rate_date, rate_type, rate, source) "
                 "VALUES (%s,%s,'A',%s,'系統預設')", [(c[0], today, c[5]) for c in CURRENCIES if not c[3]])
    db.exec_many("INSERT IGNORE INTO bas_country (country_code, country_name, country_name_en, origin_label) "
                 "VALUES (%s,%s,%s,%s)", COUNTRIES)
    db.exec_many("INSERT IGNORE INTO bas_unit (unit_code, unit_name) VALUES (%s,%s)", UNITS)
    db.exec_many("INSERT IGNORE INTO bas_warehouse (wh_code, wh_name, wh_type, is_nettable) VALUES (%s,%s,%s,%s)",
                 WAREHOUSES)
    db.exec_many("INSERT IGNORE INTO acc_account_map (map_code, map_name, account_no, account_name) VALUES (%s,%s,%s,%s)",
                 ACCOUNT_MAP)
    db.exec_many("INSERT IGNORE INTO sys_param (param_key, param_value, description) VALUES (%s,%s,%s)", PARAMS)
    extend_calendar(db, dt.date(today.year - 1, 1, 1), dt.date(today.year + 2, 12, 31))
    for y in (today.year - 1, today.year, today.year + 1):
        for m in range(1, 13):
            start = dt.date(y, m, 1)
            end = (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1))
            db.exec("INSERT IGNORE INTO acc_period (period, start_date, end_date) VALUES (%s,%s,%s)",
                    ("%04d%02d" % (y, m), start, end))
    from .help_text import GUIDE
    if not db.value("SELECT COUNT(*) FROM sys_help_topic"):
        db.exec_many("INSERT INTO sys_help_topic (func_code, title, content, voice_script, sort_no) "
                     "VALUES (NULL,%s,%s,%s,%s)", [(t, x, x, i) for i, (k, t, x) in enumerate(GUIDE)])


def extend_calendar(db, start, end):
    """建立工廠行事曆（週六日休），並重排工作天序號。已存在的日期不覆蓋（保留使用者調整的假日）。"""
    rows, d = [], start
    while d <= end:
        wk = d.weekday() < 5
        rows.append((d, int(wk), 8 if wk else 0))
        d += dt.timedelta(days=1)
    db.exec_many("INSERT IGNORE INTO bas_calendar (cal_date, is_workday, work_hours) VALUES (%s,%s,%s)", rows)
    renumber_calendar(db)


def renumber_calendar(db):
    db.exec("UPDATE bas_calendar SET workday_seq = NULL")
    db.exec("UPDATE bas_calendar c JOIN (SELECT cal_date, ROW_NUMBER() OVER (ORDER BY cal_date) AS seq "
            "FROM bas_calendar WHERE is_workday = 1) w ON w.cal_date = c.cal_date SET c.workday_seq = w.seq")
