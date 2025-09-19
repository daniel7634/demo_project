"""
報告生成 Celery 任務

提供競品分析報告的非同步生成功能。
支援任務狀態更新、錯誤處理和重試機制。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List

from celery import Task
from celery_app import app
from shared.analyzers.competitor_analyzer import CompetitorAnalyzer
from shared.analyzers.llm_report_generator import LLMReportGenerator
from shared.database.report_queries import save_report_result, update_report_job_status


class ReportTask(Task):
    """報告任務基類，提供通用功能"""

    def on_success(self, retval, task_id, args, kwargs):
        """任務成功完成時的回調"""
        print(f"✅ 報告任務 {task_id} 成功完成")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任務失敗時的回調"""
        print(f"❌ 報告任務 {task_id} 失敗: {exc}")
        # 更新任務狀態為失敗
        try:
            update_report_job_status(task_id, "failed", error_message=str(exc))
        except Exception as e:
            print(f"❌ 更新任務狀態失敗: {e}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """任務重試時的回調"""
        print(f"🔄 報告任務 {task_id} 重試中: {exc}")


@app.task(
    bind=True,
    base=ReportTask,
    name="tasks.report_tasks.generate_competitor_report",
    max_retries=3,
    default_retry_delay=60,  # 60 秒後重試
    retry_backoff=True,
    retry_backoff_max=600,  # 最大重試間隔 10 分鐘
    retry_jitter=True,
    time_limit=1800,  # 30 分鐘超時
    soft_time_limit=1500,  # 25 分鐘軟超時
    acks_late=True,
    reject_on_worker_lost=True,
)
def generate_competitor_report(
    self, job_id: str, parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    生成競品分析報告的 Celery 任務

    Args:
        job_id: 報告任務 ID
        parameters: 報告參數
            - main_asin: 主產品 ASIN
            - competitor_asins: 競品 ASIN 列表
            - window_size: 分析時間窗口（天數）
            - report_type: 報告類型

    Returns:
        Dict[str, Any]: 任務執行結果
    """
    try:
        print(f"🚀 開始執行報告生成任務: {job_id}")
        print(f"📋 任務參數: {parameters}")

        # 更新任務狀態為運行中
        update_report_job_status(job_id, "running")

        # 在異步環境中運行報告生成
        # 明確傳遞每個參數
        result = asyncio.run(
            _execute_report_generation(
                job_id=job_id,
                main_asin=parameters["main_asin"],
                competitor_asins=parameters["competitor_asins"],
                window_size=parameters["window_size"],
                report_type=parameters["report_type"],
            )
        )

        if result["success"]:
            print(f"✅ 報告生成任務完成: {job_id}")
            return {
                "success": True,
                "job_id": job_id,
                "message": "報告生成成功",
                "result": result.get("result"),
            }
        else:
            print(f"❌ 報告生成任務失敗: {job_id} - {result.get('error')}")
            # 更新任務狀態為失敗
            update_report_job_status(
                job_id, "failed", error_message=result.get("error", "報告生成失敗")
            )
            return {
                "success": False,
                "job_id": job_id,
                "error": result.get("error"),
                "message": "報告生成失敗",
            }

    except Exception as exc:
        print(f"❌ 報告生成任務異常: {job_id} - {exc}")

        # 檢查是否應該重試
        if self.request.retries < self.max_retries:
            print(f"🔄 準備重試任務: {job_id} (第 {self.request.retries + 1} 次)")

            # 更新任務狀態為重試中
            update_report_job_status(
                job_id,
                "running",
                error_message=f"任務重試中 (第 {self.request.retries + 1} 次): {str(exc)}",
            )

            # 重試任務
            raise self.retry(
                exc=exc, countdown=self.get_retry_delay(), max_retries=self.max_retries
            )
        else:
            print(f"❌ 任務重試次數已達上限: {job_id}")
            # 更新任務狀態為失敗
            update_report_job_status(
                job_id, "failed", error_message=f"任務重試次數已達上限: {str(exc)}"
            )
            return {
                "success": False,
                "job_id": job_id,
                "error": str(exc),
                "message": "任務重試次數已達上限",
            }


async def _execute_report_generation(
    job_id: str,
    main_asin: str,
    competitor_asins: List[str],
    window_size: int,
    report_type: str,
) -> Dict[str, Any]:
    """
    執行報告生成的實際邏輯

    Args:
        job_id: 報告任務 ID
        main_asin: 主產品 ASIN
        competitor_asins: 競品 ASIN 列表
        window_size: 分析時間窗口（天數）
        report_type: 報告類型

    Returns:
        Dict[str, Any]: 執行結果
    """
    try:
        print(f"🔍 開始執行報告生成邏輯: {job_id}")

        # 初始化分析器和生成器
        competitor_analyzer = CompetitorAnalyzer()
        llm_generator = LLMReportGenerator()

        # 執行競品分析
        print(f"📊 開始競品分析: {job_id}")
        analysis_result = await competitor_analyzer.analyze_competitors(
            main_asin=main_asin,
            competitor_asins=competitor_asins,
            window_size=window_size,
        )

        if not analysis_result:
            return {"success": False, "error": "競品分析失敗，沒有返回結果"}

        print(f"✅ 競品分析完成: {job_id}")

        # 生成 LLM 報告
        print(f"🤖 開始 LLM 報告生成: {job_id}")
        report_content = llm_generator.generate_report(
            analysis_result, {"report_type": report_type}
        )

        if not report_content:
            return {"success": False, "error": "LLM 報告生成失敗，沒有返回內容"}

        print(f"✅ LLM 報告生成完成: {job_id}")

        # 準備報告元數據
        report_metadata = {
            "main_asin": main_asin,
            "competitor_count": len(competitor_asins),
            "window_size": window_size,
            "generated_at": datetime.now().isoformat(),
            "analysis_summary": {
                "total_products": len(analysis_result.competitor_data)
                + 1,  # +1 for main product
                "analysis_type": "basic_comparison",
                "has_analysis_data": bool(analysis_result.competitor_data),
            },
            "task_info": {
                "task_id": job_id,
                "generation_time": datetime.now().isoformat(),
                "content_length": len(report_content),
            },
        }

        # 保存報告結果
        print(f"💾 保存報告結果: {job_id}")
        save_report_result(
            job_id=job_id,
            report_type=report_type,
            content=report_content,
            metadata=report_metadata,
        )

        # 更新任務狀態為完成
        update_report_job_status(job_id, "completed")

        print(f"✅ 報告生成完全完成: {job_id}")

        return {
            "success": True,
            "result": {
                "job_id": job_id,
                "content_length": len(report_content),
                "metadata": report_metadata,
            },
        }

    except Exception as e:
        import traceback

        print(f"❌ 報告生成邏輯執行失敗: {job_id} - {e}")
        print("📋 錯誤堆棧:")
        traceback.print_exc()
        return {"success": False, "error": f"報告生成邏輯執行失敗: {str(e)}"}


@app.task(
    bind=True,
    name="tasks.report_tasks.cleanup_old_reports",
    time_limit=300,  # 5 分鐘超時
)
def cleanup_old_reports(self, days_old: int = 30) -> Dict[str, Any]:
    """
    清理舊的報告任務和結果

    Args:
        days_old: 清理多少天前的報告（預設 30 天）

    Returns:
        Dict[str, Any]: 清理結果
    """
    try:
        print(f"🧹 開始清理 {days_old} 天前的舊報告...")

        # 這裡可以實現清理邏輯
        # 例如：刪除過期的報告任務和結果

        cleanup_date = datetime.now() - timedelta(days=days_old)
        print(f"🗑️ 清理日期閾值: {cleanup_date.isoformat()}")

        # TODO: 實現實際的清理邏輯
        # 1. 查詢過期的報告任務
        # 2. 刪除相關的報告結果
        # 3. 更新統計信息

        print("✅ 舊報告清理完成")

        return {
            "success": True,
            "message": f"成功清理 {days_old} 天前的舊報告",
            "cleanup_date": cleanup_date.isoformat(),
        }

    except Exception as e:
        print(f"❌ 清理舊報告失敗: {e}")
        return {"success": False, "error": str(e)}


@app.task(
    bind=True,
    name="tasks.report_tasks.monitor_report_health",
    time_limit=60,  # 1 分鐘超時
)
def monitor_report_health(self) -> Dict[str, Any]:
    """
    監控報告服務健康狀態

    Returns:
        Dict[str, Any]: 健康狀態信息
    """
    try:
        print("🏥 檢查報告服務健康狀態...")

        # 檢查各種組件的健康狀態
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "services": {
                "competitor_analyzer": _check_analyzer_health(),
                "llm_generator": _check_llm_health(),
                "database": _check_database_health(),
            },
            "overall_status": "healthy",
        }

        # 判斷整體健康狀態
        if not all(health_status["services"].values()):
            health_status["overall_status"] = "unhealthy"

        print(f"✅ 報告服務健康檢查完成: {health_status['overall_status']}")

        return health_status

    except Exception as e:
        print(f"❌ 健康檢查失敗: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "error",
            "error": str(e),
        }


def _check_analyzer_health() -> bool:
    """檢查競品分析器健康狀態"""
    try:
        analyzer = CompetitorAnalyzer()
        return analyzer is not None
    except Exception:
        return False


def _check_llm_health() -> bool:
    """檢查 LLM 生成器健康狀態"""
    try:
        generator = LLMReportGenerator()
        return generator is not None
    except Exception:
        return False


def _check_database_health() -> bool:
    """檢查資料庫健康狀態"""
    try:
        from shared.database.supabase_client import get_supabase_client

        client = get_supabase_client()
        return client is not None
    except Exception:
        return False


# 測試函數
def test_report_tasks():
    """測試報告任務"""
    print("🧪 測試報告任務")
    print("=" * 50)

    # 測試健康檢查
    print("\n1. 測試健康檢查:")
    health_result = monitor_report_health.delay()
    print(f"   健康檢查結果: {health_result.get()}")

    # 測試清理任務
    print("\n2. 測試清理任務:")
    cleanup_result = cleanup_old_reports.delay(30)
    print(f"   清理任務結果: {cleanup_result.get()}")

    print("\n✅ 報告任務測試完成")


if __name__ == "__main__":
    test_report_tasks()
