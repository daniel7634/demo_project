# Amazon 產品監控與優化工具

## 項目概述

這是一個為 Amazon 賣家設計的產品監控與優化工具，主要功能是追蹤產品表現、分析競爭對手，並提供優化建議。本項目專注於系統架構設計，展現可擴展、可維護的系統設計能力。

## 核心功能

### 產品資料追蹤系統 ✅

**功能描述：**
- 追蹤 1000+ 產品（Demo 期先 10-20 個同類別產品）
- 每日更新產品資料快照
- 異常變化自動告警

**追蹤項目：**
- 價格變化
- BSR（Best Sellers Rank）趨勢
- 評分與評論數變化
- Featured Offer（原 Buy Box）價格

**更新頻率：** 每日一次

**異常告警規則：**
- 價格變動 ≥ 10%
- 小類別 BSR 變動 ≥ 30%

### 競品分析引擎 ✅

**功能描述：**
- 非同步生成競品分析報告
- 多維度比較分析（價格、BSR、評分、評論數）
- 支援 3-5 個競品同時分析
- 基於歷史資料的趨勢分析

**分析維度：**
- 價格差異分析
- BSR 排名差距
- 評分優劣勢對比
- 產品特色對比（從 bullet points 提取）
- 歷史趨勢分析

**報告生成：**
- 非同步處理，立即返回 202 Accepted
- 支援任務狀態查詢
- 使用 OpenAI LLM 生成專業報告
- Markdown 格式報告輸出
- 冪等性控制（相同參數 + 同一天直接返回已生成報告）

## 技術架構

### 核心技術棧
- **資料庫：** Supabase（PostgreSQL）
- **快取：** Redis
- **資料擷取：** Apify Actor
- **任務佇列：** Celery
- **後端框架：** FastAPI
- **AI 報告生成：** OpenAI GPT-3.5-turbo
- **監控：** Flower

### 系統特色
- 真實即時資料（透過 Apify 抓取）
- 高可用性設計
- 水平擴展能力
- 完整的監控與告警機制

## 項目結構

```
demo_project/
├── apps/                   # 微服務應用
│   ├── api_service/       # FastAPI 服務
│   │   ├── Dockerfile     # API 服務 Docker 配置
│   │   ├── main.py        # API 服務入口
│   │   ├── start.py       # API 服務啟動腳本
│   │   ├── routers/       # API 路由
│   │   └── services/      # API 業務邏輯
│   └── celery_service/    # Celery 任務服務
│       ├── Dockerfile     # Celery 服務 Docker 配置
│       ├── worker.py      # Celery Worker 入口
│       ├── celery_app.py  # Celery 應用配置
│       ├── flower_monitor.py # Flower 監控啟動腳本
│       ├── start.sh       # Celery 啟動腳本
│       ├── start_flower.sh # Flower 啟動腳本
│       └── tasks/         # 背景任務定義
├── shared/                # 共享模組
│   └── src/shared/       # 共享代碼
│       ├── config/       # 配置管理
│       ├── database/     # 資料庫操作
│       ├── collectors/   # 資料收集器
│       ├── analyzers/    # 資料分析器
│       └── celery/       # Celery 配置
│           └── celery_config.py
├── 架構設計文件/
│   ├── ARCHITECTURE.md   # 系統架構說明
│   ├── API_DESIGN.md     # API 設計文件
│   ├── DATABASE_DESIGN.md # 資料庫設計
│   ├── DESIGN_DECISIONS.md # 設計決策文件
│   └── Requirement.md    # 需求文件
├── docker-compose.yml     # Docker Compose 配置
├── docker-start.sh       # Docker 啟動腳本
├── nginx.conf            # Nginx 配置
├── pyproject.toml        # Poetry 專案配置
├── poetry.lock          # Poetry 鎖定文件
└── README.md
```

## 快速開始

### 環境需求
- Python 3.12+
- Docker & Docker Compose（Docker 方式）
- Apify API Token
- Supabase 項目
- OpenAI API Key
- ngrok（用於 webhook 測試）

### 方式一：Docker 部署（推薦）

1. **clone 項目**
```bash
git clone <repository-url>
cd demo_project
```

2. **配置環境變數**
```bash
# 複製環境變數範例文件
cp .env .env
# 編輯 .env 文件，填入必要的 API Keys
```

3. **啟動 ngrok（用於 webhook）**
```bash
ngrok http 8000
```

4. **一鍵啟動所有服務**
```bash
./docker-start.sh
```

5. **訪問服務**
- **API 服務**: http://localhost:8000
- **API 文檔**: http://localhost:8000/docs
- **Flower 監控**: http://localhost:5555
- **Nginx 代理**: http://localhost

### 方式二：本地開發環境

1. **clone 項目**
```bash
git clone <repository-url>
cd demo_project
```

2. **建立 Python 虛擬環境**
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
```

3. **安裝依賴**
```bash
poetry install
```

4. **配置環境變數**
```bash
# 複製環境變數範例文件
cp .env .env
# 編輯 .env 文件，填入必要的 API Keys

# 載入環境變數
set -a && source .env && set +a
```

5. **啟動 ngrok（用於 webhook）**
```bash
ngrok http 8000
```

6. **啟動 Redis**
```bash
redis-server
```

7. **啟動 Celery Worker**
```bash
cd apps/celery_service
python worker.py
```

8. **啟動 Celery Beat（新終端）**
```bash
cd apps/celery_service
celery -A celery_app beat --loglevel=info
```

9. **啟動 Flower 監控（新終端）**
```bash
cd apps/celery_service
python flower_monitor.py
```

10. **啟動 API 服務（新終端）**
```bash
cd apps/api_service
python start.py
```

### 服務架構

本系統包含以下服務：

1. **Redis** - 訊息代理和快取服務
2. **API Service** - FastAPI 後端服務
3. **Celery Worker** - 背景任務處理服務
4. **Celery Beat** - 定時任務調度服務
5. **Flower** - Celery 監控界面
6. **Nginx** - 反向代理服務（可選）

### 定時任務

系統已配置以下定時任務：

- **Amazon 抓取排程**: 每2分鐘執行一次，自動抓取產品資料
- **報告清理**: 每天凌晨2點執行，清理過期報告
- **健康監控**: 每10分鐘執行一次，監控系統健康狀態
