"""
Webhook 業務邏輯服務
處理 Amazon 產品抓取 Webhook 的複雜業務邏輯
"""

import logging
from datetime import date, datetime
from typing import Any, Dict

from shared.collectors.amazon_data_collector import AmazonDataCollector
from shared.database.asin_status_queries import bulk_update_asin_status
from shared.database.model_types import ProductSnapshotDict
from shared.database.products_queries import bulk_update_products
from shared.database.snapshots_queries import bulk_create_snapshots

from .alert_check_service import AlertCheckService

# 設定 logger
logger = logging.getLogger(__name__)


class WebhookService:
    """Webhook 業務邏輯服務類"""

    def __init__(self, alert_check_service: AlertCheckService = None):
        """
        初始化服務

        Args:
            alert_check_service (AlertCheckService, optional): 告警檢查服務實例
        """
        # 初始化 Amazon 資料收集器
        try:
            self.amazon_collector = AmazonDataCollector()
            logger.info("✅ Amazon 資料收集器初始化成功")
        except Exception as e:
            logger.error(f"❌ Amazon 資料收集器初始化失敗: {e}")
            self.amazon_collector = None

        # 初始化告警檢查服務
        self.alert_check_service = alert_check_service
        if self.alert_check_service:
            logger.info("✅ 告警檢查服務已初始化")
        else:
            logger.warning("⚠️ 告警檢查服務未初始化")

    async def process_amazon_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        處理 Amazon 產品抓取 Webhook

        Args:
            data: Webhook 資料

        Returns:
            處理結果
        """
        # 初始化響應資料
        response_data = {
            "status": "success",
            "message": "Webhook 接收成功",
            "timestamp": datetime.now().isoformat(),
            "event_type": None,
            "processed": False,
        }

        try:
            # 檢查是否包含 Apify 特定的資料
            if isinstance(data, dict):
                event_type = data.get("eventType")
                logger.info(f"🎭 Event Type: {event_type}")

                # 更新響應資料中的事件類型
                response_data["event_type"] = event_type
                response_data["processed"] = event_type == "ACTOR.RUN.SUCCEEDED"

                if "eventData" in data:
                    event_data = data.get("eventData")
                    logger.info(f"🏃 Actor Run ID: {event_data.get('actorRunId')}")
                    logger.info(f"🎭 Actor ID: {event_data.get('actorId')}")

                if "resource" in data:
                    resource = data.get("resource")
                    logger.info(f"📊 狀態: {resource.get('status')}")
                    logger.info(f"💾 Dataset ID: {resource.get('defaultDatasetId')}")
                    logger.info(f"⏰ 開始時間: {resource.get('startedAt')}")
                    logger.info(f"⏰ 結束時間: {resource.get('finishedAt')}")

                    # 處理 ACTOR.RUN.SUCCEEDED 事件
                    if (
                        event_type == "ACTOR.RUN.SUCCEEDED"
                        and resource.get("status") == "SUCCEEDED"
                    ):
                        result = await self._process_successful_webhook(resource)
                        response_data.update(result)

                    # 處理非 SUCCEEDED 事件
                    elif (
                        event_type != "ACTOR.RUN.SUCCEEDED"
                        or resource.get("status") != "SUCCEEDED"
                    ):
                        logger.warning(
                            f"⚠️ 收到非成功事件: {event_type}, 狀態: {resource.get('status')}"
                        )
                        logger.warning(
                            "🔄 需要更新相關 ASIN 狀態為 failed，但無法從當前 webhook 資料中獲取 ASIN 列表"
                        )
                        logger.warning(
                            "   建議：在 Celery 任務中記錄 run_id 與 ASIN 的對應關係，以便在此處查詢"
                        )

            return response_data

        except Exception as e:
            logger.error(f"❌ Webhook 處理錯誤: {str(e)}")
            response_data.update(
                {"status": "error", "message": f"Webhook 處理失敗: {str(e)}"}
            )
            return response_data

    async def _process_successful_webhook(
        self, resource: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        處理成功的 Webhook 事件

        Args:
            resource: 資源資料

        Returns:
            處理結果
        """
        dataset_id = resource.get("defaultDatasetId")
        if not dataset_id or not self.amazon_collector:
            logger.warning(
                f"⚠️ 無法抓取資料: Dataset ID={dataset_id}, Collector={self.amazon_collector is not None}"
            )
            return {}

        logger.info(f"🔄 開始從 Dataset {dataset_id} 抓取資料...")
        try:
            # 使用 Amazon 資料收集器抓取資料
            dataset_items = await self.amazon_collector.get_parsed_dataset_items(
                dataset_id
            )
            logger.info(f"✅ 成功抓取 {len(dataset_items)} 筆產品資料")

            if not dataset_items:
                logger.warning("⚠️ 沒有抓取到任何產品資料")
                return {}

            # 準備批量更新 products 和創建 snapshots 的資料
            products_data = []
            snapshots_data = []
            current_date = date.today()

            for i, item in enumerate(dataset_items, 1):
                logger.info(
                    f"   處理產品 {i}/{len(dataset_items)}: {item.get('asin', 'Unknown')}"
                )

                # 準備 products 資料
                product_data = {
                    "asin": item.get("asin"),
                    "title": item.get("title"),
                    "categories": item.get("categories", []),
                }
                products_data.append(product_data)

                # 準備 snapshots 資料
                snapshot_data = ProductSnapshotDict(
                    asin=item.get("asin"),
                    snapshot_date=current_date,
                    price=item.get("price"),
                    rating=item.get("rating"),
                    review_count=item.get("review_count"),
                    bsr_data=item.get("bsr", []),
                    raw_data=item,  # 儲存完整的解析後資料
                )
                snapshots_data.append(snapshot_data)

            # 批量更新 products 表
            logger.info(f"🔄 開始批量更新 {len(products_data)} 筆產品資料...")
            products_success = bulk_update_products(products_data)
            if products_success:
                logger.info(f"✅ 成功更新 {len(products_data)} 筆產品資料")
            else:
                logger.error("❌ 更新產品資料失敗")

            # 批量創建 snapshots
            logger.info(f"🔄 開始批量創建 {len(snapshots_data)} 筆快照資料...")
            snapshots_success = bulk_create_snapshots(snapshots_data)
            if snapshots_success:
                logger.info(f"✅ 成功創建 {len(snapshots_data)} 筆快照資料")
            else:
                logger.error("❌ 創建快照資料失敗")

            # 總結處理結果並更新 ASIN 狀態
            if products_success and snapshots_success:
                logger.info(f"🎉 成功處理 {len(dataset_items)} 筆產品資料")

                # 獲取所有處理成功的 ASIN
                successful_asins = [
                    item.get("asin") for item in dataset_items if item.get("asin")
                ]

                # 更新 ASIN 狀態為 completed
                logger.info(
                    f"🔄 更新 {len(successful_asins)} 個 ASIN 狀態為 completed..."
                )
                status_update_result = bulk_update_asin_status(
                    successful_asins, "completed"
                )

                if status_update_result["success"]:
                    logger.info(
                        f"✅ 成功更新 {status_update_result['success_count']} 個 ASIN 狀態為 completed"
                    )
                    if status_update_result["failed_asins"]:
                        logger.warning(
                            f"⚠️ 有 {len(status_update_result['failed_asins'])} 個 ASIN 狀態更新失敗: {status_update_result['failed_asins']}"
                        )
                else:
                    logger.error(
                        f"❌ ASIN 狀態更新失敗: {status_update_result['message']}"
                    )

                # 檢查告警（如果告警檢查服務可用）
                alert_results = {}
                if self.alert_check_service:
                    logger.info(
                        f"🔍 開始檢查 {len(successful_asins)} 個 ASIN 的告警..."
                    )
                    try:
                        alert_results = (
                            await self.alert_check_service.check_alerts_for_asins(
                                successful_asins
                            )
                        )
                        total_alerts = sum(
                            len(alerts) for alerts in alert_results.values()
                        )
                        logger.info(f"✅ 告警檢查完成，總共觸發 {total_alerts} 個告警")
                    except Exception as e:
                        logger.error(f"❌ 告警檢查失敗: {e}")
                        alert_results = {}
                else:
                    logger.warning("⚠️ 告警檢查服務不可用，跳過告警檢查")

                return {
                    "products_updated": len(products_data),
                    "snapshots_created": len(snapshots_data),
                    "total_processed": len(dataset_items),
                    "asin_status_update": status_update_result,
                    "alerts_triggered": alert_results,
                }
            else:
                logger.warning("⚠️ 部分資料處理失敗")

                # 獲取所有 ASIN（即使處理失敗也要更新狀態）
                all_asins = [
                    item.get("asin") for item in dataset_items if item.get("asin")
                ]

                # 更新 ASIN 狀態為 failed
                logger.info(f"🔄 更新 {len(all_asins)} 個 ASIN 狀態為 failed...")
                status_update_result = bulk_update_asin_status(all_asins, "failed")

                if status_update_result["success"]:
                    logger.info(
                        f"✅ 成功更新 {status_update_result['success_count']} 個 ASIN 狀態為 failed"
                    )
                else:
                    logger.error(
                        f"❌ ASIN 狀態更新失敗: {status_update_result['message']}"
                    )

                return {
                    "products_updated": len(products_data) if products_success else 0,
                    "snapshots_created": (
                        len(snapshots_data) if snapshots_success else 0
                    ),
                    "total_processed": len(dataset_items),
                    "asin_status_update": status_update_result,
                }

        except Exception as e:
            logger.error(f"❌ 從 Dataset 抓取資料失敗: {e}")
            return {}
