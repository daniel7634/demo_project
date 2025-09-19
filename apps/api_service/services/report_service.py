"""
報告服務模組

提供競品分析報告的創建、狀態查詢和下載功能。
支援非同步報告生成和冪等性控制。
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from shared.analyzers.competitor_analyzer import CompetitorAnalyzer
from shared.analyzers.llm_report_generator import LLMReportGenerator
from shared.analyzers.prompt_templates import PromptTemplate
from shared.celery.celery_config import get_celery_app
from shared.database.report_queries import (
    check_existing_report,
    create_report_job,
    generate_parameters_hash,
    get_report_job_status,
    get_report_result,
)

# 設定 logger
logger = logging.getLogger(__name__)


class ReportService:
    """報告服務類別"""

    def __init__(self):
        """初始化報告服務"""
        self.competitor_analyzer = CompetitorAnalyzer()
        self.llm_generator = LLMReportGenerator()
        self.prompt_templates = PromptTemplate()

    async def create_competitor_report(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        創建競品分析報告

        Args:
            request: 報告請求參數
                - main_asin: 主產品 ASIN
                - competitor_asins: 競品 ASIN 列表
                - window_size: 分析時間窗口（天數，預設 7）
                - report_type: 報告類型（預設 "competitor_analysis"）

        Returns:
            Dict[str, Any]: 報告創建結果
                - job_id: 任務 ID
                - status: 任務狀態
                - message: 狀態訊息
        """
        try:
            logger.info("🔍 開始創建競品分析報告...")

            # 提取請求參數
            main_asin = request.get("main_asin")
            competitor_asins = request.get("competitor_asins", [])
            window_size = request.get("window_size", 7)
            report_type = request.get("report_type", "competitor_analysis")

            # 驗證必要參數
            if not main_asin:
                return {"error": "缺少必要參數: main_asin", "status": "failed"}

            if not competitor_asins:
                return {"error": "缺少必要參數: competitor_asins", "status": "failed"}

            # 準備參數
            parameters = {
                "main_asin": main_asin,
                "competitor_asins": competitor_asins,
                "window_size": window_size,
                "report_type": report_type,
            }

            # 生成參數雜湊
            parameters_hash = generate_parameters_hash(parameters)

            # 檢查冪等性
            existing_job = await self._check_idempotency(parameters_hash)
            if existing_job:
                logger.info(f"✅ 找到現有報告任務: {existing_job['id']}")
                return {
                    "job_id": existing_job["id"],
                    "status": existing_job["status"],
                    "message": "報告任務已存在",
                    "existing": True,
                }

            # 創建報告任務
            job_id = create_report_job(
                job_type="competitor_analysis",
                parameters=parameters,
                parameters_hash=parameters_hash,
            )

            if not job_id:
                return {"error": "創建報告任務失敗", "status": "failed"}

            logger.info(f"✅ 成功創建報告任務: {job_id}")

            # 通過 Celery 發送報告生成任務
            try:
                # 獲取 Celery 應用程式實例
                celery_app = get_celery_app("api_service")

                # 發送任務到 Celery
                task_result = celery_app.send_task(
                    "tasks.report_tasks.generate_competitor_report",
                    args=[job_id, parameters],
                    queue="report_queue",
                )

                logger.info(
                    f"🚀 報告任務已發送到 Celery: {job_id} (Task ID: {task_result.id})"
                )

                return {
                    "job_id": job_id,
                    "status": "pending",
                    "message": "報告任務已創建並提交到隊列，正在處理中",
                    "existing": False,
                    "celery_task_id": task_result.id,
                }

            except Exception as celery_error:
                logger.warning(f"⚠️ Celery 任務提交失敗: {celery_error}")
                # 即使 Celery 失敗，也返回任務 ID，可以手動重試
                return {
                    "job_id": job_id,
                    "status": "pending",
                    "message": "報告任務已創建，但 Celery 任務提交失敗，請稍後重試",
                    "existing": False,
                    "warning": f"Celery 錯誤: {str(celery_error)}",
                }

        except Exception as e:
            logger.error(f"❌ 創建競品分析報告失敗: {e}")
            return {"error": f"創建報告失敗: {str(e)}", "status": "failed"}

    async def get_report_status(self, job_id: str) -> Dict[str, Any]:
        """
        獲取報告任務狀態

        Args:
            job_id: 任務 ID

        Returns:
            Dict[str, Any]: 任務狀態資訊
                - job_id: 任務 ID
                - status: 任務狀態 (pending, running, completed, failed)
                - created_at: 創建時間
                - started_at: 開始時間
                - completed_at: 完成時間
                - error_message: 錯誤訊息（如果有）
                - result_url: 結果 URL（如果完成）
        """
        try:
            logger.info(f"🔍 查詢報告任務狀態: {job_id}")

            job_status = get_report_job_status(job_id)

            if not job_status:
                return {"error": "找不到指定的報告任務", "status": "not_found"}

            logger.info(f"✅ 任務狀態: {job_status['status']}")
            return job_status

        except Exception as e:
            logger.error(f"❌ 查詢報告任務狀態失敗: {e}")
            return {"error": f"查詢狀態失敗: {str(e)}", "status": "error"}

    async def download_report(self, job_id: str) -> Dict[str, Any]:
        """
        下載報告結果

        Args:
            job_id: 任務 ID

        Returns:
            Dict[str, Any]: 報告結果
                - content: 報告內容
                - metadata: 報告元數據
                - report_type: 報告類型
                - created_at: 創建時間
        """
        try:
            logger.info(f"🔍 下載報告結果: {job_id}")

            # 先檢查任務狀態
            job_status = get_report_job_status(job_id)
            if not job_status:
                return {"error": "找不到指定的報告任務", "status": "not_found"}

            if job_status["status"] != "completed":
                return {
                    "error": f"報告尚未完成，當前狀態: {job_status['status']}",
                    "status": job_status["status"],
                }

            # 獲取報告結果
            report_result = get_report_result(job_id)

            if not report_result:
                return {"error": "找不到報告結果", "status": "not_found"}

            logger.info("✅ 成功獲取報告結果")
            return report_result

        except Exception as e:
            logger.error(f"❌ 下載報告結果失敗: {e}")
            return {"error": f"下載報告失敗: {str(e)}", "status": "error"}

    async def _check_idempotency(
        self, parameters_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        檢查冪等性，避免重複創建相同參數的報告

        Args:
            parameters_hash: 參數雜湊值

        Returns:
            Optional[Dict[str, Any]]: 如果找到現有任務則返回任務資訊，否則返回 None
        """
        try:
            logger.info("🔍 檢查冪等性...")

            # 檢查是否有相同參數的任務（今天內）
            today = datetime.now().date().isoformat()
            existing_job = check_existing_report(
                parameters_hash=parameters_hash, date=today
            )

            if existing_job:
                logger.info(
                    f"✅ 找到現有任務: {existing_job['id']} (狀態: {existing_job['status']})"
                )
                return existing_job

            logger.info("✅ 沒有找到重複任務，可以創建新任務")
            return None

        except Exception as e:
            logger.error(f"❌ 檢查冪等性失敗: {e}")
            return None


# 測試函數
async def test_report_service():
    """測試報告服務"""
    logger.info("🧪 測試報告服務")
    logger.info("=" * 50)

    # 創建服務實例
    report_service = ReportService()

    # 測試創建報告
    logger.info("\n1. 測試創建競品分析報告:")
    test_request = {
        "main_asin": "B01LP0U5X0",
        "competitor_asins": ["B092XTMNCC", "B0DG3X1D7B"],
        "window_size": 7,
        "report_type": "competitor_analysis",
    }

    result = await report_service.create_competitor_report(test_request)
    logger.info(f"   創建結果: {result}")

    if result.get("job_id"):
        job_id = result["job_id"]

        # 測試查詢狀態
        logger.info("\n2. 測試查詢任務狀態:")
        status = await report_service.get_report_status(job_id)
        logger.info(f"   狀態: {status}")

        # 測試下載報告（如果完成）
        if status.get("status") == "completed":
            logger.info("\n3. 測試下載報告:")
            download_result = await report_service.download_report(job_id)
            logger.info(f"   下載結果: {len(download_result.get('content', ''))} 字元")

    logger.info("\n✅ 報告服務測試完成")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_report_service())
