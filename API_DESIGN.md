# API 設計文件

## 1. API 概述

### 1.1 基本資訊
- **Base URL:** `http://localhost:8000` (開發環境)
- **API 版本:** v1.0.0
- **資料格式:** JSON
- **字符編碼:** UTF-8
- **文檔地址:** `http://localhost:8000/docs` (Swagger UI)
- **ReDoc 文檔:** `http://localhost:8000/redoc`

### 1.2 認證機制
目前 API 服務處於開發階段，暫未實施認證機制。所有端點都可以直接訪問。

### 1.3 CORS 支援
API 服務支援跨域請求，配置如下：
- `allow_origins`: `["*"]` (開發環境)
- `allow_credentials`: `True`
- `allow_methods`: `["*"]`
- `allow_headers`: `["*"]`

### 1.4 應用程式生命週期
API 服務在啟動時會：
- 初始化 Redis 連接
- 載入告警規則到快取
- 初始化各項服務（Webhook、報告、告警檢查）

## 2. 通用規範

### 2.1 請求格式
```http
GET / HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Accept: application/json
```

### 2.2 響應格式
API 服務使用統一的 JSON 響應格式：

**成功響應：**
```json
{
  "message": "歡迎使用 Amazon Product Monitor API",
  "version": "1.0.0",
  "timestamp": "2025-01-11T10:30:00.123456",
  "docs": "/docs"
}
```

**報告 API 響應：**
```json
{
  "job_id": "report_20250118_comp_12345",
  "status": "completed",
  "message": "報告生成完成",
  "existing": false
}
```

### 2.3 錯誤處理
統一錯誤響應格式：
```json
{
  "detail": "具體錯誤訊息"
}
```

### 2.4 HTTP 狀態碼
- `200 OK`: 請求成功
- `202 Accepted`: 已接受請求（非同步處理）
- `400 Bad Request`: 請求參數錯誤
- `404 Not Found`: 資源不存在
- `500 Internal Server Error`: 伺服器內部錯誤

## 3. 已實現的 API 端點

### 3.1 系統端點

#### 3.1.1 根路徑
```http
GET /
```

**描述:** 服務歡迎頁面

**響應範例:**
```json
{
  "message": "歡迎使用 Amazon Product Monitor API",
  "version": "1.0.0",
  "timestamp": "2025-01-11T10:30:00.123456",
  "docs": "/docs"
}
```

#### 3.1.2 健康檢查
```http
GET /health
```

**描述:** 系統健康檢查

**響應範例:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-11T10:30:00.123456",
  "service": "api_service"
}
```

### 3.2 Webhook 端點

#### 3.2.1 Webhook 狀態檢查
```http
GET /webhook/amazon-products
```

**描述:** 檢查 Webhook 端點狀態

**響應範例:**
```json
{
  "message": "Amazon Products Webhook 端點已就緒",
  "method": "GET",
  "timestamp": "2025-01-11T10:30:00.123456",
  "note": "請使用 POST 方法發送 webhook 資料"
}
```

#### 3.2.2 接收 Apify Webhook
```http
POST /webhook/amazon-products
```

**描述:** 接收 Apify 產品抓取結果的 Webhook，包含告警檢查功能

**請求體:** JSON 格式的 Apify Webhook 資料

**主要功能:**
- 處理 `ACTOR.RUN.SUCCEEDED` 事件
- 從 Dataset 抓取產品資料
- 批量更新產品資料表
- 創建產品快照
- 更新 ASIN 狀態
- 觸發告警檢查（價格變化 ≥10%，BSR 變化 ≥30%）

**服務架構:**
- 使用 `WebhookService` 處理業務邏輯
- 整合 `AlertCheckService` 進行告警檢查
- 支援 `AmazonDataCollector` 進行資料收集

**響應範例:**
```json
{
  "status": "success",
  "message": "Webhook 接收成功",
  "timestamp": "2025-01-11T10:30:00.123456",
  "event_type": "ACTOR.RUN.SUCCEEDED",
  "processed": true,
  "products_updated": 5,
  "snapshots_created": 5,
  "total_processed": 5,
  "alerts_triggered": 2
}
```

### 3.3 報告 API (`/api/v1/reports`)

#### 3.3.1 創建競品分析報告
```http
POST /api/v1/reports/competitors
```

**描述:** 創建競品分析報告任務（非同步處理）

**請求體:**
```json
{
  "main_asin": "B01LP0U5X0",
  "competitor_asins": ["B092XTMNCC", "B0DG3X1D7B"],
  "window_size": 7,
  "report_type": "competitor_analysis"
}
```

**請求參數驗證:**
- `main_asin`: 必須是 10 位字符
- `competitor_asins`: 不能為空，最多 10 個競品
- `window_size`: 分析時間窗口（1-30 天）

**服務架構:**
- 使用 `ReportService` 處理報告業務邏輯
- 支援 Pydantic 模型驗證
- 整合 Celery 進行非同步任務處理

**響應範例 (202 Accepted):**
```json
{
  "job_id": "report_20250118_comp_12345",
  "status": "pending",
  "message": "報告任務已創建",
  "existing": false
}
```

#### 3.3.2 查詢報告任務狀態
```http
GET /api/v1/reports/jobs/{job_id}
```

**描述:** 根據任務 ID 查詢報告生成狀態

**路徑參數:**
- `job_id`: 報告任務 ID

**響應範例:**
```json
{
  "job_id": "report_20250118_comp_12345",
  "status": "completed",
  "created_at": "2025-01-11T10:30:00.123456",
  "started_at": "2025-01-11T10:30:15.123456",
  "completed_at": "2025-01-11T10:32:30.123456",
  "error_message": null,
  "result_url": "/api/v1/reports/report_20250118_comp_12345/download"
}
```

**任務狀態說明:**
- `pending`: 等待處理
- `running`: 處理中
- `completed`: 已完成
- `failed`: 處理失敗

#### 3.3.3 下載報告結果
```http
GET /api/v1/reports/{job_id}/download
```

**描述:** 下載已完成的報告內容

**路徑參數:**
- `job_id`: 報告任務 ID

**響應條件:**
- 只有狀態為 `completed` 的報告才能下載
- 處理中的任務返回 202 Accepted
- 不存在的任務返回 404 Not Found

**響應範例:**
```json
{
  "content": "# 競品分析報告\n\n...",
  "metadata": {
    "main_asin": "B01LP0U5X0",
    "competitor_count": 2,
    "analysis_period": "7 days"
  },
  "report_type": "competitor_analysis",
  "created_at": "2025-01-11T10:30:00.123456"
}
```

#### 3.3.4 獲取所有報告任務（管理端）
```http
GET /api/v1/reports/jobs
```

**描述:** 獲取所有報告任務列表，支援篩選和分頁

**查詢參數:**
- `status` (可選): 按狀態篩選
- `limit` (默認 50): 每頁數量
- `offset` (默認 0): 偏移量

**響應範例:**
```json
{
  "reports": [],
  "total": 0,
  "limit": 50,
  "offset": 0,
  "status": null
}
```

#### 3.3.5 報告服務健康檢查
```http
GET /api/v1/reports/health
```

**描述:** 檢查報告服務是否正常運行

**響應範例:**
```json
{
  "status": "healthy",
  "service": "reports",
  "timestamp": "2025-01-11T10:30:00.123456",
  "version": "1.0.0"
}
```

### 3.4 文檔端點

#### 3.4.1 Swagger UI
```http
GET /docs
```

**描述:** 互動式 API 文檔 (Swagger UI)

#### 3.4.2 ReDoc 文檔
```http
GET /redoc
```

**描述:** 美觀的 API 文檔 (ReDoc)

## 4. 規劃中的 API 端點

> **注意：** 以下 API 端點目前尚未實現，僅為規劃設計。

### 4.1 產品管理 API (`/api/v1/products`)
- `GET /api/v1/products` - 獲取產品列表
- `GET /api/v1/products/{asin}` - 獲取單一產品詳情
- `POST /api/v1/products` - 添加產品
- `PUT /api/v1/products/{asin}` - 更新產品
- `DELETE /api/v1/products/{asin}` - 刪除產品

### 4.2 產品快照 API (`/api/v1/products/{asin}`)
- `GET /api/v1/products/{asin}/snapshots/latest` - 獲取最新快照
- `GET /api/v1/products/{asin}/snapshots` - 獲取歷史快照
- `GET /api/v1/products/{asin}/trends` - 獲取趨勢資料
- `GET /api/v1/products/{asin}/analytics` - 獲取分析數據

### 4.3 告警管理 API (`/api/v1/alerts`)
- `GET /api/v1/alerts` - 獲取告警列表
- `GET /api/v1/alerts/{alert_id}` - 獲取單一告警詳情
- `POST /api/v1/alerts/{alert_id}/acknowledge` - 確認告警
- `POST /api/v1/alerts/{alert_id}/resolve` - 解決告警
- `GET /api/v1/alerts/rules` - 獲取告警規則
- `POST /api/v1/alerts/rules` - 創建告警規則

### 4.4 系統監控 API (`/api/v1/system`)
- `GET /api/v1/system/metrics` - 獲取系統指標
- `GET /api/v1/system/status` - 獲取服務狀態
- `GET /api/v1/system/cache/stats` - 獲取快取統計

### 4.5 資料擷取 API (`/api/v1/data`)
- `POST /api/v1/data/scrape/trigger` - 觸發資料抓取
- `GET /api/v1/data/scrape/tasks/{task_id}` - 獲取抓取任務狀態
- `GET /api/v1/data/scrape/schedule` - 獲取抓取排程
- `POST /api/v1/data/scrape/schedule` - 設定抓取排程

## 5. 開發與測試

### 5.1 啟動服務
```bash
# 進入 API 服務目錄
cd apps/api_service

# 安裝依賴
poetry install

# 配置環境變數
cp .env .env

# 啟動 Redis
redis-server

# 啟動服務
python start.py
```

### 5.3 查看文檔
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **服務狀態**: http://localhost:8000/health

## 6. 環境需求

### 6.1 必需依賴
- **Python**: 3.12+
- **FastAPI**: 最新版本
- **Uvicorn**: ASGI 伺服器
- **Redis**: 快取和告警規則存储
- **Supabase**: PostgreSQL 資料庫

### 6.2 必需環境變數
- `SUPABASE_URL`: Supabase 項目 URL
- `SUPABASE_KEY`: Supabase 匿名金鑰
- `APIFY_API_TOKEN`: Apify API 令牌
- `OPENAI_API_KEY`: OpenAI API Key（用於報告生成）
- `REDIS_URL`: Redis 連接 URL（默認：redis://localhost:6379）
- `WEBHOOK_DOMAIN`: Webhook 域名（用於 Apify 回調）

### 6.3 可選環境變數
- `API_PORT`: API 服務埠號（默認：8000）

## 7. 特殊功能說明

### 7.1 非同步報告生成
報告 API 採用非同步處理模式：
1. 客戶端提交報告請求，立即返回 202 Accepted 和任務 ID
2. 服務後台處理報告生成
3. 客戶端定期查詢任務狀態
4. 報告完成後下載結果

### 7.2 冪等性控制
報告 API 具備冪等性：
- 相同參數的重複請求會返回現有任務 ID
- 避免重複創建相同的報告任務
- `existing: true` 標識現有任務

### 7.3 告警快取系統
- 使用 Redis 快取告警規則，提高檢查效率
- 支援價格變化 ≥10% 和 BSR 變化 ≥30% 的告警
- 在 Webhook 處理中自動觸發告警檢查
- 服務啟動時自動載入告警規則到快取

### 7.4 服務架構
API 服務採用分層架構：
- **路由層** (`routers/`): 處理 HTTP 請求和響應
- **服務層** (`services/`): 處理業務邏輯
- **共享層** (`shared/`): 共用功能和資料庫操作
- **任務層** (Celery): 處理非同步任務
