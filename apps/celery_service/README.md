# Celery 服務

這是一個基於 Celery 的任務佇列服務，專門用於 Amazon 產品資料抓取。

## 功能特色

- ✅ Amazon 產品資料抓取任務
- ✅ 自動排程系統（每5分鐘觸發）
- ✅ 批次處理（每次100筆ASIN）
- ✅ Redis 作為訊息代理
- ✅ Flower 監控界面
- ✅ 簡單的測試任務

## 快速開始

### 1. 安裝依賴

```bash
# 進入 celery_service 目錄
cd services/celery_service

# 安裝依賴
pip install -e .
```

### 2. 啟動 Redis

```bash
# 使用 Docker 啟動 Redis
docker run -d --name redis -p 6379:6379 redis:latest

# 或使用本地 Redis（如果已安裝）
redis-server
```

### 3. 啟動服務

需要同時運行三個服務：

#### 啟動 Worker
```bash
# 終端1：啟動 Worker
python worker.py
```

#### 啟動 Beat 排程器
```bash
# 終端2：啟動 Beat 排程器
celery -A celery_app beat --loglevel=info
```

#### 啟動 Flower 監控（可選）
```bash
# 終端3：啟動 Flower 監控
python flower_monitor.py
# 或使用腳本
./start_flower.sh
```

### 4. 測試服務

```bash
# 在另一個終端視窗中運行測試
python test_celery.py
```

## 服務說明

### Worker 服務
- 執行任務的服務
- 監聽 `amazon_queue` 和 `report_queue`
- 處理 Amazon 產品抓取任務

### Beat 排程器
- 每5分鐘觸發 Amazon 抓取排程
- 每次查詢100筆需要抓取的 ASIN
- 自動發送任務到 Worker

### Flower 監控
- Web UI: http://localhost:5555
- 實時監控任務執行狀態
- 查看 Worker 和佇列狀態

## 可用的任務

### Amazon 相關任務

#### 1. schedule_amazon_scraping
Amazon 抓取排程任務（每5分鐘自動觸發）

```python
from tasks.amazon_tasks import schedule_amazon_scraping

# 手動觸發排程任務
result = schedule_amazon_scraping.delay()
print(result.get())
```

#### 2. fetch_amazon_products
Amazon 產品抓取任務

```python
from tasks.amazon_tasks import fetch_amazon_products

# 抓取指定 ASIN 的產品資料
asins = ["B01LP0U5X0", "B0DG3X1D7B"]
result = fetch_amazon_products.delay(asins)
print(result.get())
```


## 環境變數

| 變數名 | 預設值 | 說明 |
|--------|--------|------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 連接 URL |
| `APIFY_TOKEN` | 無 | Apify API Token（Amazon 抓取需要） |

## 故障排除

### 1. Redis 連接失敗
```
❌ Redis 連接失敗: [Errno 61] Connection refused
```
**解決方案：** 確保 Redis 服務正在運行

### 2. Worker 無法啟動
```
❌ Worker 啟動失敗: No module named 'celery_app'
```
**解決方案：** 確保在正確的目錄中運行腳本

### 3. Beat 無法啟動
```
❌ Beat 啟動失敗: No module named 'celery_app'
```
**解決方案：** 確保在 `services/celery_service` 目錄中運行 Beat

### 4. Amazon 抓取失敗
```
❌ Amazon 抓取失敗: API Token 未設定
```
**解決方案：** 設定 `APIFY_TOKEN` 環境變數

## 監控

### Flower Web UI
- 訪問 http://localhost:5555
- 查看任務執行狀態
- 監控 Worker 狀態
- 查看佇列長度

### 程式化監控
```python
from celery_app import app

# 檢查 Worker 狀態
i = app.control.inspect()
print(i.active())    # 活躍任務
print(i.scheduled()) # 排程任務
print(i.reserved())  # 保留任務
```

### Redis 監控
```bash
# 使用 Redis CLI
redis-cli
> LLEN celery
> LRANGE celery 0 -1
```

## 技術細節

- **Celery 版本：** 5.5.3+
- **Redis 版本：** 6.4.0+
- **Python 版本：** 3.12+
- **佇列：** amazon_queue, report_queue
- **排程：** 每5分鐘觸發
- **批次大小：** 100筆 ASIN

## 檔案結構

```
celery_service/
├── celery_app.py          # Celery 應用配置
├── worker.py              # Worker 啟動腳本
├── flower_monitor.py      # Flower 監控腳本
├── start_flower.sh        # Flower 啟動腳本
├── test_celery.py         # 測試腳本
├── tasks/
│   ├── amazon_tasks.py    # Amazon 抓取任務
│   └── report_tasks.py    # 報告生成任務
└── README.md              # 說明文件
```

## 注意事項

1. **必須同時運行 Worker 和 Beat** - 缺一不可
2. **Redis 必須先啟動** - 所有服務都依賴 Redis
3. **Amazon 抓取需要 API Token** - 設定 `APIFY_TOKEN` 環境變數
4. **Beat 會產生排程檔案** - `celerybeat-schedule.db` 用於持久化排程
