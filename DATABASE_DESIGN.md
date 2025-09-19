# 資料庫設計文件

## 1. 資料庫概述

### 1.1 技術選型
- **主要資料庫：** Supabase (PostgreSQL 15+)
- **時間序列擴展：** TimescaleDB
- **快取資料庫：** Redis 7+
- **AI 服務：** OpenAI GPT-4/3.5-turbo

### 1.2 設計原則
- **簡化設計：** 專注於核心功能，避免過度設計
- **效能優化：** 針對查詢模式設計索引
- **擴展性：** 支援水平分區和垂直分區
- **一致性：** 確保資料完整性和一致性

## 2. 核心資料表設計

### 2.1 產品主表 (products)

```sql
CREATE TABLE products (
    asin VARCHAR(10) PRIMARY KEY,
    title VARCHAR(500),
    categories JSONB DEFAULT '[]'::jsonb,  -- 產品分類陣列
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**欄位說明：**
- `asin`: Amazon 產品識別碼，主鍵
- `title`: 產品標題
- `categories`: 產品分類陣列
- `created_at`: 創建時間

### 2.2 產品快照表 (product_snapshots)

```sql
-- 使用 TimescaleDB 建立時間序列表
CREATE TABLE product_snapshots (
    asin VARCHAR(10) NOT NULL REFERENCES products(asin) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,

    -- 核心追蹤指標
    price DECIMAL(10,2),
    rating DECIMAL(3,2) CHECK (rating >= 0 AND rating <= 5),
    review_count INTEGER CHECK (review_count >= 0),
    bsr_data JSONB DEFAULT '[]'::jsonb,
    raw_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 複合主鍵包含分區鍵（解決 TimescaleDB 唯一索引限制）
    PRIMARY KEY (asin, snapshot_date, created_at)
);

-- 轉換為 TimescaleDB 超表
SELECT create_hypertable('product_snapshots', 'created_at');

-- 其他索引
CREATE INDEX idx_snapshots_asin_date ON product_snapshots(asin, snapshot_date);
CREATE INDEX idx_snapshots_created_at ON product_snapshots(created_at);
```

**欄位說明：**
- `asin`: 產品識別碼，外鍵，複合主鍵的一部分
- `snapshot_date`: 快照日期，複合主鍵的一部分
- `created_at`: 創建時間戳記，複合主鍵的一部分（分區鍵）
- `price`: 當前價格
- `rating`: 評分
- `review_count`: 評論數量
- `bsr_data`: 多個 BSR 排名資料（JSON 格式）
- `raw_data`: 原始抓取資料

### 2.3 ASIN 狀態表 (asin_status)

```sql
CREATE TABLE asin_status (
    id BIGSERIAL PRIMARY KEY,
    asin VARCHAR(10) UNIQUE NOT NULL REFERENCES products(asin) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, running, completed, failed
    task_timestamp TIMESTAMP WITH TIME ZONE,  -- 任務啟動時間
    retry_count INTEGER DEFAULT 0,  -- 重試次數
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_asin_status_asin ON asin_status(asin);
CREATE INDEX idx_asin_status_status ON asin_status(status);
CREATE INDEX idx_asin_status_task_timestamp ON asin_status(task_timestamp);
```

**欄位說明：**
- `id`: 自增主鍵
- `asin`: Amazon 產品識別碼，外鍵引用 products(asin)，唯一約束
- `status`: 抓取狀態（pending, running, completed, failed）
- `task_timestamp`: 任務啟動時間戳記（用於超時檢測和重新抓取判斷）
- `retry_count`: 重試次數（防止無限重試）
- `created_at`: 創建時間

### 2.4 告警規則表 (alert_rules)

```sql
CREATE TABLE alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL, -- 'price_change', 'bsr_change', 'rating_change'
    change_direction VARCHAR(20) NOT NULL, -- 'increase', 'decrease', 'any'
    threshold DECIMAL(10,4) NOT NULL, -- 觸發閾值
    threshold_type VARCHAR(20) NOT NULL, -- 'percentage', 'absolute'
    is_active BOOLEAN DEFAULT TRUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_alert_rules_type ON alert_rules(rule_type);
CREATE INDEX idx_alert_rules_direction ON alert_rules(change_direction);
CREATE INDEX idx_alert_rules_active ON alert_rules(is_active);
```

**欄位說明：**
- `id`: 告警規則 ID
- `rule_name`: 規則名稱
- `rule_type`: 規則類型（價格變化、BSR 變化、評分變化）
- `change_direction`: 變化方向（上升、下降、任何方向）
- `threshold`: 觸發閾值
- `threshold_type`: 閾值類型（百分比、絕對值）
- `is_active`: 是否啟用
- `description`: 規則描述
- `created_at`: 創建時間
- `updated_at`: 更新時間

### 2.5 告警記錄表 (alerts)

```sql
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asin VARCHAR(10) NOT NULL REFERENCES products(asin) ON DELETE CASCADE,
    rule_id UUID NOT NULL REFERENCES alert_rules(id),
    message TEXT NOT NULL,
    previous_value DECIMAL(15,4),
    current_value DECIMAL(15,4),
    change_percent DECIMAL(10,4),
    snapshot_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_alerts_asin ON alerts(asin);
CREATE INDEX idx_alerts_rule_id ON alerts(rule_id);
CREATE INDEX idx_alerts_created_at ON alerts(created_at);
```

**欄位說明：**
- `id`: 告警記錄 ID
- `asin`: 產品識別碼，外鍵
- `rule_id`: 告警規則 ID，外鍵
- `message`: 告警訊息
- `previous_value`: 前一個值
- `current_value`: 當前值
- `change_percent`: 變化百分比
- `snapshot_date`: 觸發告警的快照日期
- `created_at`: 創建時間

### 2.6 報告任務表 (report_jobs)

```sql
CREATE TABLE report_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(50) NOT NULL DEFAULT 'competitor_analysis',
    parameters JSONB NOT NULL, -- 請求參數
    parameters_hash VARCHAR(64) NOT NULL, -- 參數雜湊值（用於冪等性檢查）
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed
    result_url TEXT, -- 報告結果 URL
    error_message TEXT, -- 錯誤訊息
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 索引
CREATE INDEX idx_report_jobs_status ON report_jobs(status);
CREATE INDEX idx_report_jobs_type ON report_jobs(job_type);
CREATE INDEX idx_report_jobs_hash ON report_jobs(parameters_hash);
CREATE INDEX idx_report_jobs_created_at ON report_jobs(created_at);
```

**欄位說明：**
- `id`: 報告任務 ID
- `job_type`: 任務類型（目前支援 competitor_analysis）
- `parameters`: 請求參數（JSON 格式）
- `parameters_hash`: 參數雜湊值，用於冪等性檢查
- `status`: 任務狀態（pending, running, completed, failed）
- `result_url`: 報告結果下載 URL
- `error_message`: 錯誤訊息（任務失敗時）
- `created_at`: 創建時間
- `started_at`: 開始執行時間
- `completed_at`: 完成時間

### 2.7 報告結果表 (report_results)

```sql
CREATE TABLE report_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES report_jobs(id) ON DELETE CASCADE,
    report_type VARCHAR(50) NOT NULL DEFAULT 'competitor_analysis',
    content TEXT NOT NULL, -- Markdown 格式的報告內容
    metadata JSONB DEFAULT '{}'::jsonb, -- 報告元資料
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_report_results_job_id ON report_results(job_id);
CREATE INDEX idx_report_results_type ON report_results(report_type);
CREATE INDEX idx_report_results_created_at ON report_results(created_at);
```

**欄位說明：**
- `id`: 報告結果 ID
- `job_id`: 關聯的報告任務 ID，外鍵
- `report_type`: 報告類型（目前支援 competitor_analysis）
- `content`: Markdown 格式的報告內容
- `metadata`: 報告元資料（JSON 格式）
- `created_at`: 創建時間

## 3. 核心查詢範例

```sql
-- 1. 獲取產品最新快照（用於異常檢測）
SELECT DISTINCT ON (asin)
    asin, snapshot_date, price, rating, review_count, bsr_data
FROM product_snapshots
WHERE asin = 'B0DG3X1D7B'
ORDER BY asin, created_at DESC;

-- 2. 獲取產品歷史快照（用於趨勢分析）
SELECT asin, snapshot_date, price, rating, review_count, bsr_data
FROM product_snapshots
WHERE asin = 'B0DG3X1D7B'
  AND snapshot_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY created_at DESC;

-- 3. 獲取多個競品的當前狀態（競品分析）
SELECT DISTINCT ON (asin)
    asin, snapshot_date, price, rating, review_count, bsr_data
FROM product_snapshots
WHERE asin IN ('B0DG3X1D7B', 'B08XYZ1234', 'B09ABC5678')
ORDER BY asin, created_at DESC;

-- 4. 計算價格變化（異常檢測）
SELECT
    asin,
    snapshot_date,
    price,
    LAG(price) OVER (PARTITION BY asin ORDER BY created_at) as previous_price,
    ROUND((price - LAG(price) OVER (PARTITION BY asin ORDER BY created_at)) /
          LAG(price) OVER (PARTITION BY asin ORDER BY created_at) * 100, 2) as price_change_percent
FROM product_snapshots
WHERE asin = 'B0DG3X1D7B'
ORDER BY created_at;

-- 5. 獲取需要抓取的 ASIN（支援超時檢測）
SELECT asin FROM asin_status
WHERE (
    status = 'pending'
    OR (status = 'completed' AND task_timestamp < NOW() - INTERVAL '1 day')
    OR (status = 'running' AND task_timestamp < NOW() - INTERVAL '5 minutes')
    OR (status = 'failed' AND retry_count < 3)
)
ORDER BY task_timestamp ASC
LIMIT 100;

-- 6. 查詢異常告警
SELECT a.asin, ar.rule_type, a.message, a.change_percent, a.created_at
FROM alerts a
JOIN alert_rules ar ON a.rule_id = ar.id
WHERE a.created_at >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY a.created_at DESC;

-- 7. 獲取啟用的告警規則
SELECT * FROM alert_rules
WHERE is_active = TRUE
ORDER BY rule_type, change_direction, threshold;

-- 8. 查詢特定規則的告警記錄
SELECT a.*, ar.rule_name, ar.description
FROM alerts a
JOIN alert_rules ar ON a.rule_id = ar.id
WHERE ar.rule_type = 'price_change'
  AND a.created_at >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY a.created_at DESC;

-- 9. 查詢特定方向的告警規則
SELECT * FROM alert_rules
WHERE rule_type = 'price_change'
  AND change_direction = 'decrease'
  AND is_active = TRUE;

-- 10. 創建報告任務
INSERT INTO report_jobs (job_type, parameters, parameters_hash, status)
VALUES (
    'competitor_analysis',
    '{"main_asin": "B0DG3X1D7B", "competitor_asins": ["B08XYZ1234", "B09ABC5678"], "window_size": 7}',
    'hash_of_parameters',
    'pending'
);

-- 11. 查詢報告任務狀態
SELECT id, job_type, status, created_at, started_at, completed_at, error_message
FROM report_jobs
WHERE id = 'job_uuid_here';

-- 12. 更新報告任務狀態
UPDATE report_jobs
SET status = 'running', started_at = NOW()
WHERE id = 'job_uuid_here';

-- 13. 完成報告任務
UPDATE report_jobs
SET status = 'completed', completed_at = NOW(), result_url = '/api/v1/reports/job_uuid/download'
WHERE id = 'job_uuid_here';

-- 14. 保存報告結果
INSERT INTO report_results (job_id, report_type, content, metadata)
VALUES (
    'job_uuid_here',
    'competitor_analysis',
    '# 競品分析報告\n\n## 主產品 vs 競品比較...',
    '{"main_asin": "B0DG3X1D7B", "competitor_count": 2, "analysis_date": "2025-01-11"}'
);

-- 15. 查詢報告結果
SELECT rr.content, rr.metadata, rj.status, rj.created_at
FROM report_results rr
JOIN report_jobs rj ON rr.job_id = rj.id
WHERE rj.id = 'job_uuid_here';

-- 16. 冪等性檢查（查詢相同參數的報告）
SELECT rj.id, rj.status, rr.content
FROM report_jobs rj
LEFT JOIN report_results rr ON rj.id = rr.job_id
WHERE rj.parameters_hash = 'hash_of_parameters'
  AND rj.status = 'completed'
  AND DATE(rj.created_at) = CURRENT_DATE;

-- 17. 查詢失敗的報告任務
SELECT id, job_type, error_message, created_at
FROM report_jobs
WHERE status = 'failed'
  AND created_at >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY created_at DESC;

-- 18. 查詢進行中的報告任務
SELECT id, job_type, created_at, started_at
FROM report_jobs
WHERE status IN ('pending', 'running')
ORDER BY created_at ASC;
```

## 3. 預設告警規則

### 3.1 插入預設規則

```sql
-- 價格變化告警
INSERT INTO alert_rules (rule_name, rule_type, change_direction, threshold, threshold_type, description) VALUES
('價格大幅下降', 'price_change', 'decrease', 10.0, 'percentage', '價格下降超過 10% 時告警'),
('價格大幅上升', 'price_change', 'increase', 15.0, 'percentage', '價格上升超過 15% 時告警');

-- BSR 變化告警
INSERT INTO alert_rules (rule_name, rule_type, change_direction, threshold, threshold_type, description) VALUES
('BSR 大幅下降', 'bsr_change', 'decrease', 30.0, 'percentage', 'BSR 下降超過 30% 時告警'),
('BSR 大幅上升', 'bsr_change', 'increase', 50.0, 'percentage', 'BSR 上升超過 50% 時告警');

-- 評分變化告警
INSERT INTO alert_rules (rule_name, rule_type, change_direction, threshold, threshold_type, description) VALUES
('評分下降', 'rating_change', 'decrease', 0.5, 'absolute', '評分下降超過 0.5 時告警');
```

## 4. ASIN 狀態管理設計

### 4.1 狀態轉換邏輯

```
pending → running (任務啟動時，記錄 task_timestamp)
running → completed (收到成功 Webhook 時，保持 task_timestamp)
running → failed (收到失敗 Webhook 時，保持 task_timestamp)
running → pending (超時時，重新抓取，更新 task_timestamp)
completed → pending (隔天重新抓取時，基於 task_timestamp 日期)
failed → pending (重試時，更新 task_timestamp)
```

### 4.2 超時檢測機制

- **閾值設定**：5 分鐘（可調整）
- **檢測方式**：查詢時自動檢測 `running` 狀態且 `task_timestamp` 超過閾值的 ASIN
- **處理方式**：自動將超時的 ASIN 重新加入抓取佇列

### 4.3 重試策略

- **重試限制**：最多重試 3 次
- **重試條件**：`failed` 狀態且 `retry_count < 3`
- **重試間隔**：立即重試（在下次查詢時）

### 4.4 查詢策略

- **時間優先**：按 `task_timestamp` 升序排序，先到先處理
- **公平處理**：所有需要抓取的 ASIN 都按時間順序處理
- **簡潔邏輯**：避免複雜的優先級排序

## 5. 告警系統設計

### 5.1 告警檢查時機

- **觸發時機**：每日抓取完成後，在 Webhook 處理過程中同步檢查
- **檢查範圍**：所有成功處理的 ASIN
- **檢查方式**：載入啟用的告警規則，逐一檢查每個 ASIN

### 5.2 告警規則管理

- **動態配置**：告警規則存儲在資料庫中，可動態調整
- **規則類型**：支援價格變化、BSR 變化、評分變化等（通過 `rule_type` 欄位定義）
- **變化方向**：支援上升、下降、任何方向三種變化方向（通過 `change_direction` 欄位定義）
- **閾值設定**：支援百分比和絕對值兩種閾值類型
- **啟用控制**：可動態啟用/停用特定規則

### 5.3 告警記錄管理

- **記錄創建**：觸發告警時自動創建記錄
- **關聯追蹤**：記錄與告警規則的關聯關係
- **歷史查詢**：支援按時間、類型、ASIN 等條件查詢

## 6. 資料表總結

### 核心資料表（7個）

1. **products** - 產品基本資訊
2. **product_snapshots** - 時間序列快照資料
3. **asin_status** - ASIN 抓取狀態管理
4. **report_jobs** - 報告任務狀態管理
5. **report_results** - 報告結果存儲
6. **alert_rules** - 告警規則配置
7. **alerts** - 異常告警記錄

### 支援功能
- TimescaleDB 時間序列優化
- 複合主鍵設計（解決 TimescaleDB 唯一索引限制）
- ASIN 狀態管理（支援超時檢測和重試機制）
- 報告任務管理（支援非同步報告生成和狀態追蹤）
- 冪等性控制（基於參數雜湊值的重複檢查）
- 動態告警規則配置
- 告警記錄追蹤和管理
- 最小化索引設計（只保留實際需要的索引）
- 專注於產品追蹤和競品分析需求
- 外鍵約束保證資料完整性
- 每日抓取任務的狀態追蹤和錯誤恢復

## 7. 實際實現對照

### 7.1 資料庫模組架構

實際實現包含以下模組：

- **`supabase_client.py`** - Supabase 客戶端（單例模式）
- **`asin_status_queries.py`** - ASIN 狀態查詢與任務分發
- **`products_queries.py`** - 產品資料 CRUD 操作
- **`snapshots_queries.py`** - 產品快照時間序列資料
- **`alert_queries.py`** - 告警規則和記錄管理
- **`report_queries.py`** - 報告任務和結果管理
- **`model_types.py`** - 資料類型定義

### 7.2 類型定義系統

實際實現包含完整的類型定義：

- **`BSRData`** - BSR 排名資料
- **`ProductSnapshot`** - 產品快照資料
- **`ProductSnapshotDict`** - 產品快照字典格式
- **`Product`** - 產品基本資訊
- **`ASINStatus`** - ASIN 狀態
- **`AlertRule`** - 告警規則
- **`Alert`** - 告警記錄
- **`ReportJob`** - 報告任務
- **`ReportResult`** - 報告結果

### 7.3 查詢功能實現

實際實現包含以下核心查詢功能：

**ASIN 狀態管理：**
- `get_asins_to_scrape()` - 獲取需要抓取的 ASIN（支援超時檢測）
- `bulk_update_asin_status()` - 批量更新 ASIN 狀態
- `get_pending_asins()` - 獲取待處理的 ASIN

**產品資料管理：**
- `get_product()` - 獲取單一產品資料
- `get_products_by_asins()` - 根據 ASIN 列表獲取產品資料
- `bulk_create_products()` - 批量創建產品資料
- `bulk_update_products()` - 批量更新產品資料
- `upsert_product()` - 創建或更新產品資料

**快照資料追蹤：**
- `get_latest_snapshot()` - 獲取產品最新快照
- `get_previous_snapshot()` - 獲取前一個快照
- `get_snapshots_by_date_range()` - 按日期範圍獲取快照
- `bulk_create_snapshots()` - 批量創建快照
- `bulk_update_snapshots()` - 批量更新快照
- `create_snapshot()` - 創建單個快照
- `get_snapshots_by_asins()` - 根據 ASIN 列表獲取快照

**告警系統管理：**
- `get_active_alert_rules()` - 獲取啟用的告警規則
- `create_alert_record()` - 創建告警記錄

**報告任務管理：**
- `create_report_job()` - 創建報告任務
- `update_report_job_status()` - 更新任務狀態
- `get_report_job_status()` - 獲取任務狀態
- `save_report_result()` - 保存報告結果
- `get_report_result()` - 獲取報告結果
- `check_existing_report()` - 檢查現有報告（冪等性）
- `get_report_jobs_by_status()` - 根據狀態獲取任務
- `delete_report_job()` - 刪除報告任務
- `generate_parameters_hash()` - 生成參數雜湊值
