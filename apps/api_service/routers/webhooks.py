"""
Webhook 相關 API 路由
"""

import json
import logging
import traceback
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from services.alert_cache_service import AlertCacheService
from services.alert_check_service import AlertCheckService
from services.webhook_service import WebhookService

# 配置日誌
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhooks"])

# 初始化服務（需要從 main.py 獲取）
webhook_service = None
alert_check_service = None


def get_webhook_service():
    """獲取 Webhook 服務實例"""
    global webhook_service, alert_check_service

    if webhook_service is None:
        # 創建告警快取服務
        try:
            import os

            import redis

            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            redis_client = redis.from_url(redis_url, decode_responses=True)
            alert_cache_service = AlertCacheService(redis_client)
            alert_check_service = AlertCheckService(alert_cache_service)
            webhook_service = WebhookService(alert_check_service)
            logger.info("✅ Webhook 服務已初始化（包含告警檢查）")
        except Exception as e:
            logger.warning(f"⚠️ 告警服務初始化失敗，使用基本 Webhook 服務: {e}")
            logger.warning(f"📍 Traceback: {traceback.format_exc()}")
            logger.warning(f"告警服務初始化失敗: {e}")
            logger.warning(f"Traceback: {traceback.format_exc()}")
            webhook_service = WebhookService()

    return webhook_service


@router.post("/amazon-products")
async def webhook_amazon_products(request: Request):
    """
    Apify Amazon 產品抓取 Webhook 接收端點

    接收 Apify Actor 執行完成後的回調通知
    """
    try:
        # 獲取請求資料
        body = await request.body()

        # 嘗試解析 JSON
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            # 如果不是 JSON，嘗試解析為字串
            data = {"raw_body": body.decode("utf-8")}

        # 獲取請求標頭
        headers = dict(request.headers)

        # 獲取查詢參數
        query_params = dict(request.query_params)

        # 記錄接收到的資料
        logger.info("=" * 80)
        logger.info(f"🔔 收到 Apify Webhook 通知 - {datetime.now().isoformat()}")
        logger.info("=" * 80)
        logger.info(f"📋 請求方法: {request.method}")
        logger.info(f"🌐 請求 URL: {request.url}")
        logger.info(f"📊 查詢參數: {query_params}")
        logger.info("📝 請求標頭:")
        for key, value in headers.items():
            logger.info(f"   {key}: {value}")
        logger.info("📦 請求內容:")
        logger.info(json.dumps(data, ensure_ascii=False, indent=2))
        logger.info("=" * 80)

        # 使用 Webhook 服務處理資料
        webhook_service = get_webhook_service()
        result = await webhook_service.process_amazon_webhook(data)

        return result

    except Exception as e:
        logger.error(f"❌ Webhook 處理錯誤: {str(e)}")
        logger.error(f"📍 Traceback: {traceback.format_exc()}")

        logger.error(f"Webhook 處理錯誤: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        raise HTTPException(status_code=500, detail=f"Webhook 處理失敗: {str(e)}")


@router.get("/amazon-products")
async def webhook_amazon_products_get():
    """
    Webhook 端點的 GET 方法（用於測試）
    """
    return {
        "message": "Amazon Products Webhook 端點已就緒",
        "method": "GET",
        "timestamp": datetime.now().isoformat(),
        "note": "請使用 POST 方法發送 webhook 資料",
    }
