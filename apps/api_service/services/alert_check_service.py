"""
告警檢查服務

基於告警規則檢查產品變化，創建告警記錄。
支援價格、BSR、評分等多種變化類型的告警檢測。
"""

import logging
import os
from typing import Any, Dict, List

import redis
from shared.database.alert_queries import create_alert_record
from shared.database.model_types import ProductSnapshotDict
from shared.database.snapshots_queries import get_latest_snapshot, get_previous_snapshot

from .alert_cache_service import AlertCacheService

# 設定 logger
logger = logging.getLogger(__name__)


class AlertCheckService:
    """告警檢查服務"""

    def __init__(self, alert_cache_service: AlertCacheService):
        """
        初始化告警檢查服務

        Args:
            alert_cache_service (AlertCacheService): 告警快取服務實例
        """
        self.alert_cache = alert_cache_service

    async def check_alerts_for_asin(self, asin: str) -> List[Dict[str, Any]]:
        """
        檢查單個 ASIN 的告警

        Args:
            asin (str): 產品 ASIN

        Returns:
            List[Dict[str, Any]]: 觸發的告警記錄列表
        """
        try:
            logger.info(f"🔍 開始檢查 {asin} 的告警...")

            # 獲取最新快照
            latest_snapshot = get_latest_snapshot(asin)
            if not latest_snapshot:
                logger.warning(f"⚠️ 沒有找到 {asin} 的最新快照")
                return []

            # 獲取前一個快照
            previous_snapshot = get_previous_snapshot(
                asin, latest_snapshot.snapshot_date
            )
            if not previous_snapshot:
                logger.warning(f"⚠️ 沒有找到 {asin} 的前一個快照")
                return []

            # 獲取告警規則
            rules = await self.alert_cache.get_active_rules()
            if not rules:
                logger.warning("⚠️ 沒有找到啟用的告警規則")
                return []

            # 檢查各種類型的告警
            triggered_alerts = []

            # 檢查價格變化告警
            price_alerts = await self._check_price_alerts(
                asin, latest_snapshot, previous_snapshot, rules
            )
            triggered_alerts.extend(price_alerts)

            # 檢查 BSR 變化告警
            bsr_alerts = await self._check_bsr_alerts(
                asin, latest_snapshot, previous_snapshot, rules
            )
            triggered_alerts.extend(bsr_alerts)

            # 檢查評分變化告警
            rating_alerts = await self._check_rating_alerts(
                asin, latest_snapshot, previous_snapshot, rules
            )
            triggered_alerts.extend(rating_alerts)

            logger.info(f"✅ {asin} 告警檢查完成，觸發 {len(triggered_alerts)} 個告警")
            return triggered_alerts

        except Exception as e:
            logger.error(f"❌ 檢查 {asin} 告警失敗: {e}")
            return []

    async def _check_price_alerts(
        self,
        asin: str,
        latest: ProductSnapshotDict,
        previous: ProductSnapshotDict,
        rules: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """檢查價格變化告警"""
        triggered_alerts = []

        # 獲取價格變化規則
        price_rules = [
            rule for rule in rules if rule.get("rule_type") == "price_change"
        ]

        if not price_rules:
            return triggered_alerts

        # 計算價格變化
        current_price = latest.price
        previous_price = previous.price

        if current_price is None or previous_price is None or previous_price == 0:
            return triggered_alerts

        change_percent = ((current_price - previous_price) / previous_price) * 100

        # 檢查每個規則
        for rule in price_rules:
            if await self._should_trigger_alert(
                rule, change_percent, current_price, previous_price
            ):
                alert_data = {
                    "asin": asin,
                    "rule_id": rule["id"],
                    "message": f"價格從 ${previous_price:.2f} 變為 ${current_price:.2f} ({change_percent:+.2f}%)",
                    "previous_value": previous_price,
                    "current_value": current_price,
                    "change_percent": round(change_percent, 2),
                    "snapshot_date": latest.snapshot_date,
                }

                # 創建告警記錄
                if create_alert_record(alert_data):
                    triggered_alerts.append(alert_data)
                    logger.warning(f"   🚨 觸發價格告警: {alert_data['message']}")

        return triggered_alerts

    async def _check_bsr_alerts(
        self,
        asin: str,
        latest: ProductSnapshotDict,
        previous: ProductSnapshotDict,
        rules: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """檢查 BSR 變化告警"""
        triggered_alerts = []

        # 獲取 BSR 變化規則
        bsr_rules = [rule for rule in rules if rule.get("rule_type") == "bsr_change"]

        if not bsr_rules:
            return triggered_alerts

        # 獲取 BSR 資料
        current_bsr = latest.bsr_data or []
        previous_bsr = previous.bsr_data or []

        if not current_bsr or not previous_bsr:
            return triggered_alerts

        # 比較主要 BSR（假設第一個是最重要的）
        current_main_bsr = current_bsr[0] if current_bsr else {}
        previous_main_bsr = previous_bsr[0] if previous_bsr else {}

        current_rank = current_main_bsr.get("rank")
        previous_rank = previous_main_bsr.get("rank")

        if current_rank is None or previous_rank is None or previous_rank == 0:
            return triggered_alerts

        # 計算 BSR 變化（排名下降表示上升，排名上升表示下降）
        change_percent = ((previous_rank - current_rank) / previous_rank) * 100

        # 檢查每個規則
        for rule in bsr_rules:
            if await self._should_trigger_alert(
                rule, change_percent, current_rank, previous_rank
            ):
                alert_data = {
                    "asin": asin,
                    "rule_id": rule["id"],
                    "message": f"BSR 從 #{previous_rank} 變為 #{current_rank} ({change_percent:+.2f}%)",
                    "previous_value": previous_rank,
                    "current_value": current_rank,
                    "change_percent": round(change_percent, 2),
                    "snapshot_date": latest.snapshot_date,
                }

                # 創建告警記錄
                if create_alert_record(alert_data):
                    triggered_alerts.append(alert_data)
                    logger.warning(f"   🚨 觸發 BSR 告警: {alert_data['message']}")

        return triggered_alerts

    async def _check_rating_alerts(
        self,
        asin: str,
        latest: ProductSnapshotDict,
        previous: ProductSnapshotDict,
        rules: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """檢查評分變化告警"""
        triggered_alerts = []

        # 獲取評分變化規則
        rating_rules = [
            rule for rule in rules if rule.get("rule_type") == "rating_change"
        ]

        if not rating_rules:
            return triggered_alerts

        # 計算評分變化
        current_rating = latest.rating
        previous_rating = previous.rating

        if current_rating is None or previous_rating is None:
            return triggered_alerts

        change_amount = current_rating - previous_rating

        # 檢查每個規則
        for rule in rating_rules:
            if await self._should_trigger_alert(
                rule, change_amount, current_rating, previous_rating
            ):
                alert_data = {
                    "asin": asin,
                    "rule_id": rule["id"],
                    "message": f"評分從 {previous_rating:.2f} 變為 {current_rating:.2f} ({change_amount:+.2f})",
                    "previous_value": previous_rating,
                    "current_value": current_rating,
                    "change_percent": round(change_amount, 2),
                    "snapshot_date": latest.snapshot_date,
                }

                # 創建告警記錄
                if create_alert_record(alert_data):
                    triggered_alerts.append(alert_data)
                    logger.warning(f"   🚨 觸發評分告警: {alert_data['message']}")

        return triggered_alerts

    async def _should_trigger_alert(
        self,
        rule: Dict[str, Any],
        change_value: float,
        current_value: float,
        previous_value: float,
    ) -> bool:
        """
        判斷是否應該觸發告警

        Args:
            rule (Dict[str, Any]): 告警規則
            change_value (float): 變化值（百分比或絕對值）
            current_value (float): 當前值
            previous_value (float): 前一個值

        Returns:
            bool: 是否應該觸發告警
        """
        try:
            threshold = float(rule.get("threshold", 0))
            change_direction = rule.get("change_direction", "any")
            threshold_type = rule.get("threshold_type", "percentage")

            # 根據閾值類型處理
            if threshold_type == "percentage":
                # 百分比閾值
                if change_direction == "increase":
                    return change_value >= threshold
                elif change_direction == "decrease":
                    return change_value <= -threshold
                elif change_direction == "any":
                    return abs(change_value) >= threshold
            else:
                # 絕對值閾值
                if change_direction == "increase":
                    return change_value >= threshold
                elif change_direction == "decrease":
                    return change_value <= -threshold
                elif change_direction == "any":
                    return abs(change_value) >= threshold

            return False

        except Exception as e:
            logger.error(f"❌ 判斷告警觸發條件失敗: {e}")
            return False

    async def check_alerts_for_asins(
        self, asins: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        檢查多個 ASIN 的告警

        Args:
            asins (List[str]): ASIN 列表

        Returns:
            Dict[str, List[Dict[str, Any]]]: 每個 ASIN 的告警記錄
        """
        results = {}

        for asin in asins:
            alerts = await self.check_alerts_for_asin(asin)
            results[asin] = alerts

        total_alerts = sum(len(alerts) for alerts in results.values())
        logger.info(
            f"✅ 完成 {len(asins)} 個 ASIN 的告警檢查，總共觸發 {total_alerts} 個告警"
        )

        return results


# 測試函數
async def test_alert_check_service():
    """測試告警檢查服務"""
    logger.info("🧪 測試告警檢查服務")
    logger.info("=" * 50)

    # 創建 Redis 客戶端
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_client = redis.from_url(redis_url, decode_responses=True)
        redis_client.ping()
        logger.info("✅ Redis 連接成功")
    except Exception as e:
        logger.error(f"❌ Redis 連接失敗: {e}")
        return

    # 創建服務
    cache_service = AlertCacheService(redis_client)
    check_service = AlertCheckService(cache_service)

    # 測試檢查單個 ASIN
    logger.info("\n1. 測試檢查單個 ASIN:")
    test_asin = "B0DG3X1D7B"  # 替換為實際的 ASIN
    alerts = await check_service.check_alerts_for_asin(test_asin)
    logger.info(f"   {test_asin} 觸發 {len(alerts)} 個告警")

    # 測試檢查多個 ASIN
    logger.info("\n2. 測試檢查多個 ASIN:")
    test_asins = ["B0DG3X1D7B", "B08XYZ1234"]  # 替換為實際的 ASIN
    results = await check_service.check_alerts_for_asins(test_asins)
    for asin, asin_alerts in results.items():
        logger.info(f"   {asin}: {len(asin_alerts)} 個告警")

    logger.info("\n✅ 告警檢查服務測試完成")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_alert_check_service())
