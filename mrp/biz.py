"""業務服務層：組合登入權限、存貨、規劃、單據作業。畫面與日後的手機 API 都只呼叫這一層。"""
import os

from .core import Base, BizError
from .inventory import Inventory
from .ops import Ops
from .planning import Planning


class Biz(Base, Inventory, Planning, Ops):
    def has_business_data(self):
        return bool(self.db.value("SELECT COUNT(*) FROM itm_item"))

    def load_demo(self):
        """載入電子業範例資料（只能在還沒有料件時使用）。"""
        self.need("SYS")
        if self.has_business_data():
            raise BizError("已經有料件資料，不能再載入範例（範例只能載入到空白資料庫）")
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "demo_data.sql"), encoding="utf-8") as f:
            text = f.read()
        for t in ("sys_company", "bas_currency"):
            text = text.replace("INSERT INTO %s " % t, "REPLACE INTO %s " % t)
        for t in ("bas_country", "sys_doc_type", "acc_period", "bas_calendar", "bas_exchange_rate"):
            text = text.replace("INSERT INTO %s " % t, "INSERT IGNORE INTO %s " % t)
        from .database import split_sql
        from .seed import renumber_calendar
        self.db.exec("DELETE FROM bas_exchange_rate")
        self.db.exec("DELETE FROM bas_unit")
        self.db.exec("DELETE FROM bas_warehouse")
        self.db.exec("UPDATE bas_currency SET is_base=0")
        for stmt in split_sql(text):
            if stmt.strip().upper().startswith("SET NAMES"):
                continue
            self.db.exec(stmt)
        renumber_calendar(self.db)
        self.compute_low_level_codes()
        self.log("DEMO", "", "電子業範例", None, "SYS")
