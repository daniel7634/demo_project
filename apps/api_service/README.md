# API 服務

Amazon 產品監控工具的 FastAPI 服務，提供產品數據查詢、Webhook 處理和競品分析報告生成功能。

## 快速開始

```bash
# 安裝依賴（使用 Poetry）
poetry install

# 配置環境變數
cp .env.example .env
# 編輯 .env 文件，設定必要的 API 金鑰

# 啟動 Redis（必需）
docker run -d --name redis -p 6379:6379 redis:latest

# 啟動服務
python main.py
# 或
python start.py
# 或使用 shell 腳本
./start.sh

# API 文檔：http://localhost:8000/docs
```

## 專案結構

```
api_service/
├── main.py                    # FastAPI 應用程式主入口
├── start.py                  # 服務啟動腳本
├── routers/                  # API 路由
│   ├── __init__.py          # 路由註冊
│   ├── health.py            # 健康檢查與系統狀態
│   ├── webhooks.py          # Webhook 處理
│   └── reports.py           # 競品分析報告 API
├── services/                 # 業務邏輯
│   ├── webhook_service.py   # Webhook 資料處理
│   ├── alert_cache_service.py  # 告警快取服務
│   ├── alert_check_service.py  # 告警檢查服務
│   └── report_service.py    # 報告生成服務
├── test_api.py              # API 測試腳本
├── test_webhook.py          # Webhook 測試腳本
├── pyproject.toml           # Poetry 依賴配置
└── .env                     # 環境變數配置
```

## API 端點

### 系統端點
- `GET /` - 服務歡迎頁
- `GET /health` - 健康檢查

### Webhook 端點
- `GET /webhook/amazon-products` - 檢查 Webhook 狀態
- `POST /webhook/amazon-products` - 接收 Apify 抓取結果

### 報告 API (`/api/v1/reports`)
- `POST /competitors` - 創建競品分析報告
- `GET /jobs/{job_id}` - 查詢報告任務狀態
- `GET /{job_id}/download` - 下載報告結果
- `GET /jobs` - 獲取所有報告任務（管理端）
- `GET /health` - 報告服務健康檢查

### 文檔端點
- `/docs` - Swagger UI 互動式文檔
- `/redoc` - ReDoc 美觀文檔

## 主要功能

### 1. Webhook 處理流程
1. 接收 Apify 的 `ACTOR.RUN.SUCCEEDED` 事件
2. 從 Dataset 抓取產品資料
3. 批量更新產品資料表
4. 創建產品快照
5. 更新 ASIN 狀態
6. 觸發告警檢查

### 2. 競品分析報告
- 支援非同步報告生成
- 提供冪等性控制（避免重複創建）
- 支援最多 10 個競品 ASIN 比較
- 可自訂分析時間窗口（1-30 天）
- 提供任務狀態查詢和結果下載

### 3. 告警快取系統
- 使用 Redis 快取告警規則
- 啟動時自動載入規則到快取
- 提供高效能的告警檢查

## 測試

```bash
# 測試 API 基本功能
python test_api.py

# 測試 Webhook 功能
python test_webhook.py
```

## 環境需求

### 必需依賴
- Python 3.12+
- FastAPI
- Uvicorn
- Redis（本地或遠端）

### 必需環境變數
- `SUPABASE_URL` - Supabase 項目 URL
- `SUPABASE_KEY` - Supabase 匿名金鑰
- `APIFY_API_TOKEN` - Apify API 令牌
- `OPENAI_API_KEY` - OpenAI API Key（用於報告生成）
- `REDIS_URL` - Redis 連接 URL（默認：redis://localhost:6379）

### 可選環境變數
- `API_PORT` - API 服務埠號（默認：8000）

## 部署注意事項

1. 確保 Redis 服務正在運行
2. 配置正確的環境變數
3. 在生產環境中限制 CORS 域名
4. 建議使用反向代理（如 Nginx）
5. 監控服務健康狀態和告警快取

## 錯誤處理

API 使用標準 HTTP 狀態碼：
- `200 OK` - 請求成功
- `202 Accepted` - 已接受請求（非同步處理）
- `400 Bad Request` - 請求參數錯誤
- `404 Not Found` - 資源不存在
- `500 Internal Server Error` - 伺服器內部錯誤

錯誤響應格式：
```json
{
  "detail": "具體的錯誤訊息"
}
```
