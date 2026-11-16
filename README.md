# 資料助秘之物料需求II生產製造系統
<img width="1489" height="921" alt="image" src="https://github.com/user-attachments/assets/74996488-42b7-479a-b20c-c4e4d85a5d93" />
<img width="1486" height="915" alt="image" src="https://github.com/user-attachments/assets/ed90d124-06f8-4e59-8d57-7e998e197dba" />
<img width="1285" height="337" alt="image" src="https://github.com/user-attachments/assets/ea813e8b-064f-4a51-a012-5b3fcd47d15f" />

製造業用的 MRP／MRP II 系統：需求預測、客戶訂單 → 主生產排程 → 物料需求規劃 → 產能需求規劃 → 採購、工單、存貨 → 成本。

- 介面用 Python＋Flet，資料庫用 MariaDB（95 張表，每個欄位都有繁中備註）。
- Windows 版內建資料庫（埠 3398），打開程式自動啟動，關閉程式自動停止。
- 平台：Windows 11、macOS（公證）、Android、iPhone、iPad。手機與平板透過電腦的「手機連線」服務使用，不直接連資料庫。
- 開發者：吳玉柱 先生 與 Claude AI Opus 5.5

## 功能

| 模組 | 功能 |
|---|---|
| 需求與訂單 | 需求預測、客戶訂單（外幣、匯率）、出貨（先進先出扣成品） |
| 主生產排程 MPS | 由未出貨訂單與預測產生；可手動修改；粗略產能 RCCP |
| 物料需求規劃 MRP | 低階碼逐階展開、淨需求、批量法則（逐批／固定／EOQ／POQ、倍數、MOQ）、依工廠行事曆位移前置工作天；例外訊息（逾期、建議提前、延後、取消、低於安全存量）；需求追溯；計畫訂單一鍵轉採購單／工單 |
| 產能需求規劃 CRP | 計畫訂單＋未完工工單排到工作中心每一天，負荷熱度圖 |
| 產品結構 | 料件（版本、核可製造商與產地 AML、計畫參數）、BOM（指定版本、指定產地、損耗、虛設件、多階展開、用在哪裡）、途程、工作中心、機器、ECN |
| 採購 | 請購、採購（外幣）、進貨驗收（批號、Date Code、實際產地、原產地證明；依進貨日匯率換算成本，記匯兌差異） |
| 現場控制 | 工單發放（展開 BOM、複製途程、指定產地先保留）、領料（先進先出）、報工、完工入庫（材料＋工時×費率） |
| 存貨 | 批號 × 版本 × 產地 × 倉庫的庫存、先進先出成本層與耗用明細、異動明細、期初、調整、調撥 |
| 成本 | 標準成本累算、採購價差、匯兌差異、存貨價值 |
| 系統 | 權限（8 種角色 × 14 個模組）、備份還原、版本更新、桌面捷徑、操作紀錄、語音說明（44 段）、電子業範例資料 |

## 安裝（Windows 11）

執行 `ZMSMRP2-Setup-<版本>.exe`，安裝後桌面會出現「資料助秘之物料需求II生產製造系統」捷徑。第一次開啟時建立系統管理員帳號；想先試用可到「系統管理 → 範例資料」載入電子業範例（主機板、電源供應器、USB 集線器）。

- 程式：`%LOCALAPPDATA%\Programs\ZMSMRP2`；資料：`%LOCALAPPDATA%\ZMSMRP2`（更新或解除安裝都不會刪除）。

## 安裝（macOS）

下載 `ZMSMRP2-<版本>-mac.dmg`，把 App 拖到「應用程式」。已通過 Apple 公證；內附 MariaDB 10.11.18，結束 App（含 ⌘Q）自動停止。

## 手機版（Android／iPhone／iPad）

1. 電腦版開啟「系統管理 → 手機連線」，畫面會出現 QR Code。
2. Android 安裝 `ZMSMRP2-<版本>-android.apk`；iPhone／iPad 用 Safari 開 https://achir1015.github.io/zms-mrp2/ios/ 按「安裝」（Ad Hoc，已登記的裝置）。
3. 用手機相機掃 QR Code，App 自動開啟並連線，再用自己的帳號登入；權限與電腦版相同。

- 外出時可開「外出連線」（Cloudflare 加密通道）；也可以用 `ZMSMRP2.exe --server` 不開視窗只提供服務。

## 開發

```
.venv\Scripts\python db\schema_spec.py        # 改資料表規格後重產 schema.sql 與欄位明細
.venv\Scripts\python -m pytest tests           # 引擎測試（自動啟動測試用 MariaDB）
.venv\Scripts\python main.py                   # 桌面版
.venv\Scripts\python tools\build_windows.py    # 建置安裝檔
```

- 資料庫規劃：[docs/資料庫規劃.md](docs/資料庫規劃.md)、[docs/資料表欄位明細.md](docs/資料表欄位明細.md)
