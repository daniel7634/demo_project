"""
FastAPI 主應用程式
提供基本的 API 服務
"""

import logging
import os
from contextlib import asynccontextmanager

import redis
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import health_router, reports, webhook_router
from services.alert_cache_service import AlertCacheService

# 設定 logger
logger = logging.getLogger(__name__)

# 全域變數
alert_cache_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    global alert_cache_service

    # 啟動時執行
    try:
        logger.info("API Service 啟動中...")

        # 初始化 Redis 客戶端
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_client = redis.from_url(redis_url, decode_responses=True)

        # 測試 Redis 連接
        redis_client.ping()
        logger.info("Redis 連接成功")

        # 初始化告警快取服務
        alert_cache_service = AlertCacheService(redis_client)

        # 載入告警規則到快取
        success = await alert_cache_service.load_rules_to_cache()
        if success:
            logger.info("告警規則已載入到 Redis 快取")
        else:
            logger.warning("告警規則載入失敗，將在需要時從資料庫載入")

        logger.info("API Service 啟動完成")

    except Exception as e:
        logger.error(f"API Service 啟動失敗: {e}", exc_info=True)
        # 不讓啟動失敗，但記錄錯誤
        alert_cache_service = None

    yield  # 應用程式運行期間

    # 關閉時執行
    logger.info("API Service 正在關閉...")
    logger.info("API Service 已關閉")


# 創建 FastAPI 應用程式
app = FastAPI(
    title="Amazon Product Monitor API",
    description="Amazon 產品監控與優化工具 API 服務",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 添加 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生產環境中應該限制具體的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(health_router)
app.include_router(webhook_router)
app.include_router(reports.router)

if __name__ == "__main__":
    # 開發環境啟動
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
