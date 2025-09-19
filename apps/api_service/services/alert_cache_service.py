"""
告警規則 Redis 快取服務

管理告警規則的 Redis 快取，提供高效的規則查詢和快取管理功能。
在系統啟動時載入規則，在規則變更時更新快取。
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis
from shared.database.alert_queries import get_active_alert_rules

# 設定 logger
logger = logging.getLogger(__name__)


class AlertCacheService:
    """告警規則 Redis 快取服務"""

    def __init__(self, redis_client: redis.Redis):
        """
        初始化告警快取服務

        Args:
            redis_client (redis.Redis): Redis 客戶端實例
        """
        self.redis = redis_client
        self.cache_key = "alert_rules:active"
        self.cache_ttl = 3600  # 1小時過期
        self.last_updated_key = "alert_rules:last_updated"

    async def load_rules_to_cache(self) -> bool:
        """
        從資料庫載入告警規則到 Redis 快取

        Returns:
            bool: 載入是否成功
        """
        try:
            logger.info("🔄 開始載入告警規則到 Redis 快取...")

            # 從資料庫獲取啟用的規則
            rules = get_active_alert_rules()

            if not rules:
                logger.warning("⚠️ 沒有找到啟用的告警規則")
                return False

            # 準備快取資料
            cache_data = {
                "rules": rules,
                "last_updated": datetime.now().isoformat(),
                "count": len(rules),
            }

            # 存儲到 Redis
            self.redis.setex(
                self.cache_key,
                self.cache_ttl,
                json.dumps(cache_data, ensure_ascii=False),
            )

            # 更新最後更新時間
            self.redis.setex(
                self.last_updated_key, self.cache_ttl, datetime.now().isoformat()
            )

            logger.info(f"✅ 成功載入 {len(rules)} 個告警規則到 Redis 快取")
            return True

        except Exception as e:
            logger.error(f"❌ 載入告警規則到快取失敗: {e}")
            return False

    async def get_cached_rules(self) -> Optional[List[Dict[str, Any]]]:
        """
        從 Redis 獲取快取的告警規則

        Returns:
            Optional[List[Dict[str, Any]]]: 快取的規則列表，如果沒有則返回 None
        """
        try:
            cached_data = self.redis.get(self.cache_key)

            if cached_data:
                data = json.loads(cached_data)
                rules = data.get("rules", [])
                logger.info(f"✅ 從 Redis 快取獲取 {len(rules)} 個告警規則")
                return rules
            else:
                logger.warning("⚠️ Redis 快取中沒有告警規則")
                return None

        except Exception as e:
            logger.error(f"❌ 從 Redis 獲取告警規則失敗: {e}")
            return None

    async def get_active_rules(self) -> List[Dict[str, Any]]:
        """
        獲取啟用的告警規則（優先從快取，快取為空時從資料庫載入）

        Returns:
            List[Dict[str, Any]]: 告警規則列表
        """
        # 先嘗試從快取獲取
        rules = await self.get_cached_rules()

        if rules is not None:
            return rules

        # 快取為空，從資料庫載入
        logger.info("🔄 快取為空，從資料庫載入告警規則...")
        success = await self.load_rules_to_cache()

        if success:
            return await self.get_cached_rules() or []
        else:
            # 載入失敗，直接從資料庫獲取
            logger.warning("⚠️ 快取載入失敗，直接從資料庫獲取規則...")
            return get_active_alert_rules()


# 測試函數
async def test_alert_cache_service():
    """測試告警快取服務"""
    logger.info("🧪 測試告警快取服務")
    logger.info("=" * 50)

    # 創建 Redis 客戶端（需要確保 Redis 服務運行）
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_client = redis.from_url(redis_url, decode_responses=True)
        # 測試連接
        redis_client.ping()
        logger.info("✅ Redis 連接成功")
    except Exception as e:
        logger.error(f"❌ Redis 連接失敗: {e}")
        return

    # 創建快取服務
    cache_service = AlertCacheService(redis_client)

    # 測試載入規則到快取
    logger.info("\n1. 測試載入規則到快取:")
    success = await cache_service.load_rules_to_cache()
    logger.info(f"   載入結果: {'成功' if success else '失敗'}")

    # 測試獲取快取規則
    logger.info("\n2. 測試獲取快取規則:")
    rules = await cache_service.get_cached_rules()
    if rules:
        logger.info(f"   獲取到 {len(rules)} 個規則")
        for rule in rules[:3]:  # 只顯示前3個
            logger.info(
                f"   - {rule.get('rule_name')}: {rule.get('rule_type')} {rule.get('change_direction')}"
            )
    else:
        logger.info("   沒有獲取到規則")

    # 測試獲取所有規則
    logger.info("\n3. 測試獲取所有規則:")
    all_rules = await cache_service.get_active_rules()
    logger.info(f"   總規則數: {len(all_rules)}")
    for rule in all_rules[:3]:  # 只顯示前3個
        logger.info(
            f"   - {rule.get('rule_name')}: {rule.get('rule_type')} {rule.get('change_direction')}"
        )

    logger.info("\n✅ 告警快取服務測試完成")


if __name__ == "__main__":
    asyncio.run(test_alert_cache_service())
