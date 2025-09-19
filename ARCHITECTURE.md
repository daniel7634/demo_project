# 系統架構設計

## 1. 系統概述

### 1.1 目標與範圍
本系統專為 Amazon 賣家設計，提供產品監控與資料管理功能。核心目標是：
- 自動化抓取 Amazon 產品資料（價格、BSR、評分、評論數等）
- 建立完整的產品資料庫和時間序列快照
- 提供 RESTful API 接口供前端和第三方系統使用
- 支援大規模產品資料的批量處理和狀態管理

### 1.2 核心功能
- **自動化資料抓取：** 使用 Apify Actor 定期抓取 Amazon 產品資料
- **資料處理與存儲：** 清洗、標準化並存儲到 Supabase 資料庫
- **任務狀態管理：** 完整的 ASIN 任務生命週期管理（pending → running → completed/failed）
- **異常變化通知：** 基於規則的產品價格、BSR、評分變化告警系統
- **競品分析報告：** 非同步生成競品分析報告，支援多維度比較分析
- **API 服務：** 提供產品查詢、健康檢查、Webhook 處理、報告生成等接口
- **監控與日誌：** 任務執行監控、錯誤處理和詳細日誌記錄

## 2. 整體架構

### 2.1 架構原則
- **模組化設計：** 清晰的職責分離，易於維護和擴展
- **事件驅動：** 基於 Webhook 的異步處理機制
- **資料一致性：** 使用 Supabase 確保資料完整性和一致性
- **容錯設計：** 完整的錯誤處理和重試機制

### 2.2 系統分層

```
┌─────────────────────────────────────────────────────────────┐
│                    外部服務層 (External Services)            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Apify     │  │  Supabase   │  │    Redis    │        │
│  │ (Data Scraping)│ (Database)  │  │ (Task Queue)│        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    應用服務層 (Application Services)         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  API 服務   │  │ Celery 服務 │  │ 共享模組    │        │
│  │ (FastAPI)   │  │ (Worker)    │  │ (Shared)    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    資料處理層 (Data Processing)              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ 資料收集器  │  │ 資料處理器  │  │ 資料庫模組  │        │
│  │ (Collectors)│  │ (Processors)│  │ (Database)  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## 3. 核心組件設計

### 3.1 應用服務層 (Application Services)

#### 3.1.1 API 服務 (FastAPI)
**位置：** `services/api_service/`

**功能：**
- 提供 RESTful API 接口
- 處理 Apify Webhook 通知
- 系統健康檢查和狀態監控
- 自動生成 API 文檔 (Swagger/ReDoc)

**模組結構：**
```
api_service/
├── main.py                 # FastAPI 應用程式主入口
├── routers/               # API 路由層
│   ├── health.py         # 健康檢查與系統狀態
│   ├── hello.py          # 測試用 API
│   ├── webhooks.py       # Webhook 處理
│   ├── reports.py        # 競品分析報告 API
│   └── alert_rules.py    # 告警規則管理 API（規劃中）
└── services/              # 業務邏輯層
    ├── webhook_service.py # Webhook 資料處理
    ├── report_service.py  # 報告生成服務
    └── alert_cache_service.py # 告警規則快取服務（規劃中）
```

**核心功能：**
- **Webhook 處理：** 接收 Apify 的 `ACTOR.RUN.SUCCEEDED` 事件
- **資料處理：** 從 Apify Dataset 抓取產品資料並批量更新資料庫
- **狀態管理：** 更新 ASIN 任務狀態（completed/failed）
- **報告生成：** 非同步生成競品分析報告，支援多維度比較分析
- **報告管理：** 報告任務狀態追蹤、結果存儲和快取管理
- **告警系統：** 基於規則的產品變化告警檢測（規劃中）
- **快取管理：** 告警規則 Redis 快取管理（規劃中）
- **錯誤處理：** 完整的異常處理和日誌記錄

#### 3.1.2 Celery 服務 (Background Tasks)
**位置：** `services/celery_service/`

**功能：**
- 處理 Amazon 產品資料抓取任務
- 自動排程系統（每5分鐘觸發）
- 批次處理（每次100筆ASIN）
- 任務監控和管理

**模組結構：**
```
celery_service/
├── celery_app.py          # Celery 應用配置
├── worker.py              # Worker 啟動腳本
├── flower_monitor.py      # Flower 監控界面
├── tasks/
│   ├── amazon_tasks.py    # Amazon 抓取任務
│   └── report_tasks.py    # 報告生成任務
└── README.md              # 服務說明
```

**核心任務：**
- **`schedule_amazon_scraping`：** 排程任務，每5分鐘自動觸發
- **`fetch_amazon_products`：** 執行 Amazon 產品抓取
- **`generate_competitor_report`：** 生成競品分析報告
- **狀態更新：** 任務啟動時更新 ASIN 狀態為 `running`
- **錯誤處理：** 任務失敗時更新 ASIN 狀態為 `failed`

#### 3.1.3 共享模組 (Shared Modules)
**位置：** `shared/`

**功能：**
- 提供跨服務的通用功能
- 資料庫連接和查詢管理
- 資料收集和處理邏輯
- 配置管理和環境變數處理

**模組結構：**
```
shared/
├── database/              # 資料庫模組
│   ├── supabase_client.py    # Supabase 客戶端
│   ├── asin_status_queries.py # ASIN 狀態管理
│   ├── products_queries.py    # 產品資料 CRUD
│   ├── snapshots_queries.py   # 快照時間序列
│   └── report_queries.py      # 報告相關查詢
├── collectors/            # 資料收集器
│   └── amazon_data_collector.py # Amazon 資料收集
├── analyzers/             # 分析模組
│   └── competitor_analyzer.py  # 競品分析器
└── config/                # 配置管理
    └── settings.py            # 環境變數配置
```

### 3.2 資料處理層 (Data Processing)

#### 3.2.1 資料庫模組 (Database Module)
**位置：** `shared/database/`

**核心功能：**
- **Supabase 客戶端：** 單例模式管理資料庫連接
- **ASIN 狀態管理：** 完整的任務生命週期管理
- **產品資料 CRUD：** 產品基本資訊的增刪改查
- **快照時間序列：** 產品歷史資料的存儲和查詢
- **報告管理：** 報告任務狀態管理和結果存儲
- **告警系統管理：** 動態告警規則配置和異常變化檢測（規劃中）

**主要函數：**
- `get_asins_to_scrape(limit)`: 獲取需要抓取的 ASIN 列表
- `bulk_update_asin_status(asins, status, task_timestamp)`: 批量更新 ASIN 狀態
- `bulk_update_products(products_data)`: 批量更新產品資料
- `bulk_create_snapshots(snapshots_data)`: 批量創建產品快照
- `create_report_job(parameters)`: 創建報告任務
- `update_report_job_status(job_id, status, result_url)`: 更新報告任務狀態
- `get_report_job_status(job_id)`: 獲取報告任務狀態
- `save_report_result(job_id, content)`: 保存報告結果

**告警系統函數（規劃中）：**
- `get_active_alert_rules()`: 獲取啟用的告警規則（從資料庫）
- `create_alert_record(alert_data)`: 創建告警記錄
- `get_latest_snapshot(asin)`: 獲取產品最新快照
- `get_previous_snapshot(asin, current_date)`: 獲取產品前一個快照
- `check_price_alerts(asin, latest, previous)`: 檢查價格變化告警
- `check_bsr_alerts(asin, latest, previous)`: 檢查 BSR 變化告警
- `check_rating_alerts(asin, latest, previous)`: 檢查評分變化告警

**告警快取服務（規劃中）：**
- `AlertCacheService`: 告警規則 Redis 快取管理
- `load_rules_to_cache()`: 載入規則到 Redis 快取
- `get_cached_rules()`: 從 Redis 獲取快取的規則
- `refresh_cache()`: 刷新快取

**狀態管理流程：**
```
pending → running → completed/failed
   ↓         ↓           ↓
新任務    任務啟動    Webhook 處理結果
```

#### 3.2.2 資料收集器 (Data Collectors)
**位置：** `shared/collectors/`

**核心功能：**
- **Amazon 資料收集：** 使用 Apify Actor 抓取產品資料
- **資料解析：** 標準化 Amazon 產品資料格式
- **錯誤處理：** 完整的重試和異常處理機制

**主要類別：**
- `AmazonDataCollector`: 主要的資料收集器
- `AmazonDataParser`: 資料解析和標準化

#### 3.2.3 競品分析器 (Competitor Analyzer)
**位置：** `shared/analyzers/`

**核心功能：**
- **多維度比較：** 價格、BSR、評分、評論數等多維度分析
- **趨勢分析：** 基於歷史資料的趨勢分析
- **LLM 報告生成：** 使用 OpenAI LLM 生成 Markdown 格式的競品分析報告
- **資料標準化：** 統一不同產品的資料格式
- **提示工程：** 設計有效的 LLM 提示詞模板

**主要類別：**
- `CompetitorAnalyzer`: 主要的競品分析器
- `LLMReportGenerator`: 基於 OpenAI LLM 的報告生成器
- `PromptTemplate`: 報告生成提示詞模板管理


#### 3.2.4 配置管理 (Configuration)
**位置：** `shared/config/`

**核心功能：**
- **環境變數管理：** 統一管理所有配置參數
- **API Token 管理：** 安全地管理外部服務 Token
- **預設值設定：** 提供合理的預設配置

**主要配置：**
- Apify API Token
- Supabase 連接資訊
- Redis 連接設定
- OpenAI API Key
- 抓取參數配置

### 3.3 外部服務層 (External Services)

#### 3.3.1 Apify 平台
**功能：** Amazon 產品資料抓取
- **Actor 執行：** 使用 Apify Actor 抓取 Amazon 產品資料
- **Dataset 存儲：** 將抓取結果存儲到 Apify Dataset
- **Webhook 通知：** 任務完成後發送 Webhook 通知
- **排程管理：** 支援定時任務和手動觸發

#### 3.3.2 Supabase 資料庫
**功能：** 主要資料存儲
- **PostgreSQL：** 使用 Supabase 提供的 PostgreSQL 服務
- **即時功能：** 支援即時資料同步
- **API 自動生成：** 自動生成 RESTful API
- **認證管理：** 內建用戶認證和授權

**資料表結構：**
- `asin_status`: ASIN 任務狀態管理
- `products`: 產品基本資訊
- `product_snapshots`: 產品時間序列快照
- `report_jobs`: 報告任務狀態管理
- `report_results`: 報告結果存儲
- `alert_rules`: 告警規則配置
- `alerts`: 異常告警記錄

#### 3.3.3 Redis 快取
**功能：** 任務佇列和快取
- **Celery Broker：** 作為 Celery 的訊息代理
- **任務佇列：** 管理背景任務的執行佇列
- **結果存儲：** 存儲任務執行結果
- **狀態管理：** 追蹤任務執行狀態

#### 3.3.4 OpenAI 平台
**功能：** 競品分析報告生成
- **GPT 模型：** 使用 GPT-4 或 GPT-3.5-turbo 生成報告
- **提示工程：** 設計專門的提示詞模板
- **內容生成：** 基於產品資料生成結構化報告
- **格式控制：** 確保輸出符合 Markdown 格式要求

## 4. 資料流設計

### 4.1 自動化資料抓取流程
```
1. Celery Beat 排程觸發 (每5分鐘)
   ↓
2. 查詢需要抓取的 ASIN (get_asins_to_scrape)
   ↓
3. 發送任務到 Celery 佇列 (fetch_amazon_products)
   ↓
4. Celery Worker 執行任務
   ↓
5. 調用 Apify Actor 抓取資料
   ↓
6. 更新 ASIN 狀態為 'running'
   ↓
7. Apify 完成抓取，存儲到 Dataset
   ↓
8. Apify 發送 Webhook 通知
   ↓
9. API 服務接收 Webhook
   ↓
10. 從 Apify Dataset 抓取資料
    ↓
11. 批量更新產品資料庫
    ↓
12. 創建產品快照記錄
    ↓
13. 更新 ASIN 狀態為 'completed' 或 'failed'
```

### 4.2 ASIN 狀態管理流程
```
新 ASIN 加入系統
   ↓
狀態: pending
   ↓
Celery 任務啟動
   ↓
狀態: running (更新 task_timestamp)
   ↓
Webhook 處理結果
   ↓
成功: completed | 失敗: failed (增加 retry_count)
   ↓
失敗且 retry_count < 3: 重新排入佇列
```

### 4.3 Webhook 處理流程
```
Apify 發送 ACTOR.RUN.SUCCEEDED 事件
   ↓
API 服務接收 Webhook
   ↓
驗證事件類型和狀態
   ↓
從 Apify Dataset 抓取產品資料
   ↓
資料清洗和標準化
   ↓
批量更新 products 表
   ↓
批量創建 product_snapshots 表
   ↓
從 Redis 快取載入啟用的告警規則
   ↓
檢查每個 ASIN 的告警條件
   ↓
創建告警記錄（如有觸發）
   ↓
更新 ASIN 狀態為 completed
   ↓
記錄處理結果和日誌
```

### 4.4 錯誤處理流程
```
任務執行失敗
   ↓
Celery 捕獲異常
   ↓
更新 ASIN 狀態為 failed
   ↓
增加 retry_count
   ↓
retry_count < 3: 重新排入佇列
   ↓
retry_count >= 3: 標記為永久失敗
   ↓
記錄錯誤日誌
```

### 4.5 告警系統流程
```
每日抓取完成後
   ↓
從 Redis 快取載入啟用的告警規則
   ↓
對每個成功處理的 ASIN：
   ↓
獲取最新快照資料
   ↓
獲取前一個快照資料
   ↓
根據規則檢查變化：
   - 價格變化（price_change）：上升/下降 ≥ 閾值
   - BSR 變化（bsr_change）：上升/下降 ≥ 閾值
   - 評分變化（rating_change）：上升/下降 ≥ 閾值
   ↓
觸發告警條件時：
   ↓
創建告警記錄
   ↓
發送通知（可選）
   ↓
記錄告警日誌
```

### 4.6 告警快取管理流程
```
API Service 啟動
   ↓
載入告警規則到 Redis 快取
   ↓
Webhook 處理時從 Redis 獲取規則
   ↓
規則更新時同步更新 Redis 快取
   ↓
快取過期時自動重新載入
```

### 4.7 競品分析報告生成流程
```
客戶端發起報告請求
   ↓
POST /api/v1/reports/competitors
   ↓
檢查冪等性（相同參數 + 同一天）
   ↓
存在快取報告：直接返回 200 + 報告內容
   ↓
不存在：創建報告任務記錄
   ↓
返回 202 Accepted + job_id
   ↓
發送任務到 Celery 佇列
   ↓
Celery Worker 執行報告生成
   ↓
獲取主產品和競品的最新快照資料
   ↓
執行多維度比較分析
   ↓
準備 LLM 提示詞和產品資料
   ↓
調用 OpenAI API 生成報告
   ↓
驗證和格式化 Markdown 報告
   ↓
保存報告結果到資料庫
   ↓
更新任務狀態為 completed
   ↓
客戶端輪詢 GET /api/v1/reports/jobs/{job_id}
   ↓
返回報告狀態和結果 URL
```

## 5. 系統特性

### 5.1 可靠性設計
- **任務重試機制：** ASIN 任務失敗時自動重試（最多3次）
- **狀態追蹤：** 完整的任務狀態管理，避免重複處理
- **錯誤處理：** 每個模組都有完整的異常處理和日誌記錄
- **資料一致性：** 使用 Supabase 事務確保資料完整性

### 5.2 效能優化
- **批量處理：** 使用批量操作減少資料庫查詢次數
- **異步處理：** Celery 背景任務避免阻塞主服務
- **連接池：** Supabase 客戶端使用單例模式管理連接
- **索引優化：** 針對查詢模式設計資料庫索引

### 5.3 監控與日誌
- **Flower 監控：** 提供 Web UI 監控 Celery 任務執行狀態
- **詳細日誌：** 每個關鍵步驟都有詳細的日誌記錄
- **健康檢查：** API 服務提供健康檢查端點
- **錯誤追蹤：** 完整的錯誤堆疊和上下文資訊

### 5.4 配置管理
- **環境變數：** 所有配置都通過環境變數管理
- **預設值：** 提供合理的預設配置
- **模組化配置：** 每個服務都有獨立的配置管理
- **安全考量：** 敏感資訊（如 API Token）通過環境變數管理

## 6. 部署與運維

### 6.1 服務啟動
**API 服務：**
```bash
cd services/api_service
python main.py
```

**Celery 服務：**
```bash
# 啟動 Worker
cd services/celery_service
python worker.py

# 啟動 Beat 排程器
celery -A celery_app beat --loglevel=info

# 啟動 Flower 監控
python flower_monitor.py
```

### 6.2 依賴服務
- **Redis：** 必須先啟動 Redis 服務
- **Supabase：** 需要有效的 Supabase 專案和 API Key
- **Apify：** 需要有效的 Apify API Token

### 6.3 環境變數配置
```bash
# Supabase 配置
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Apify 配置
APIFY_API_TOKEN=your_apify_token

# Redis 配置
REDIS_URL=redis://localhost:6379
```

### 6.4 故障排除
- **服務無法啟動：** 檢查依賴服務和環境變數
- **任務執行失敗：** 查看 Celery 日誌和 Flower 監控
- **資料庫連接失敗：** 檢查 Supabase 配置和網路連接
- **Webhook 處理失敗：** 查看 API 服務日誌

---

## 附錄

### A. 技術選型理由
- **FastAPI：** 高效能的 Python Web 框架，自動生成 API 文檔，支援異步處理
- **Celery：** 成熟的 Python 分散式任務佇列，支援定時任務和監控
- **Supabase：** 提供完整的 PostgreSQL 服務，內建 API 和認證功能
- **Redis：** 高效能記憶體資料庫，適合作為 Celery 的訊息代理
- **Apify：** 專業的網頁抓取平台，提供穩定的 Amazon 資料擷取服務

### B. 架構決策記錄
- **模組化設計：** 選擇清晰的職責分離，便於維護和測試
- **事件驅動：** 使用 Webhook 機制實現異步處理，提高系統響應性
- **共享模組：** 將通用功能提取到 shared 模組，避免重複代碼
- **批量處理：** 使用批量操作提高資料庫操作效率

### C. 專案結構
```
demo_project/
├── services/                    # 應用服務
│   ├── api_service/            # FastAPI 服務
│   │   ├── routers/           # API 路由
│   │   │   ├── health.py
│   │   │   ├── hello.py
│   │   │   ├── webhooks.py
│   │   │   └── reports.py     # 競品分析報告 API
│   │   └── services/          # 業務邏輯
│   │       ├── webhook_service.py
│   │       └── report_service.py  # 報告生成服務
│   └── celery_service/         # Celery 背景任務
│       └── tasks/             # 任務定義
│           ├── amazon_tasks.py
│           └── report_tasks.py    # 報告生成任務
├── shared/                     # 共享模組
│   ├── database/              # 資料庫操作
│   │   ├── asin_status_queries.py
│   │   ├── products_queries.py
│   │   ├── snapshots_queries.py
│   │   ├── report_queries.py      # 報告相關查詢
│   │   └── alert_queries.py   # 告警相關查詢（規劃中）
│   ├── collectors/            # 資料收集器
│   │   └── amazon_data_collector.py
│   ├── analyzers/             # 分析模組
│   │   └── competitor_analyzer.py  # 競品分析器
│   └── config/                # 配置管理
│       └── settings.py
└── 文檔和配置文件
```
