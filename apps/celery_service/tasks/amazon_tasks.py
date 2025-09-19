"""
Amazon 產品抓取任務
專門處理 Amazon 產品資料抓取的 Celery 任務
"""

import asyncio
from datetime import datetime

from celery_app import app
from shared.collectors.amazon_data_collector import AmazonDataCollector
from shared.database.asin_status_queries import (
    bulk_update_asin_status,
    get_pending_asins,
)


@app.task(bind=True, name="tasks.amazon_tasks.schedule_amazon_scraping")
def schedule_amazon_scraping(self):
    """
    排程任務：每5分鐘觸發，每次只抓 100 筆 ASIN
    目前先使用模擬數據，等資料庫實作後再替換
    """
    try:
        print(f"[{datetime.now()}] 開始執行 Amazon 抓取排程")
        print(f"[{datetime.now()}] 任務 ID: {self.request.id}")
        print(f"[{datetime.now()}] Worker: {self.request.hostname}")

        # 每次只抓 100 筆 ASIN
        asins_to_scrape = get_pending_asins(limit=100)

        if not asins_to_scrape:
            print(f"[{datetime.now()}] 沒有 ASIN 需要抓取")
            return {
                "status": "no_asins",
                "task_id": self.request.id,
                "timestamp": datetime.now().isoformat(),
                "message": "沒有 ASIN 需要抓取",
            }

        print(f"[{datetime.now()}] 找到 {len(asins_to_scrape)} 個 ASIN 需要抓取")

        # 直接發送一個任務
        task = fetch_amazon_products.delay(asins_to_scrape)

        result = {
            "status": "scheduled",
            "task_id": self.request.id,
            "timestamp": datetime.now().isoformat(),
            "asin_count": len(asins_to_scrape),
            "fetch_task_id": task.id,
            "asins": asins_to_scrape,
        }

        print(f"[{datetime.now()}] Amazon 抓取排程完成: {result}")
        return result

    except Exception as exc:
        print(f"[{datetime.now()}] Amazon 抓取排程執行錯誤: {str(exc)}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@app.task(bind=True, name="tasks.amazon_tasks.fetch_amazon_products")
def fetch_amazon_products(self, asins: list, api_token: str = None):
    """
    啟動 Amazon 產品抓取任務 - Webhook 模式

    Args:
        asins (list): 產品 ASIN 列表
        api_token (str): Apify API Token，如果未提供則從環境變量讀取

    Returns:
        dict: 任務啟動結果，實際產品資料將通過 webhook 接收
    """
    try:
        print(f"[{datetime.now()}] 啟動 Amazon 產品抓取任務: {asins}")
        print(f"[{datetime.now()}] Celery 任務 ID: {self.request.id}")
        print(f"[{datetime.now()}] Worker: {self.request.hostname}")

        # 創建 Amazon 資料收集器
        collector = AmazonDataCollector(api_token=api_token)

        # 使用 asyncio 包裝異步調用
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            task_result = loop.run_until_complete(collector.get_product_details(asins))
        finally:
            loop.close()

        # 檢查任務啟動結果
        if task_result.get("status") == "started":
            print(f"[{datetime.now()}] ✅ Apify 任務啟動成功")
            print(f"[{datetime.now()}]   Run ID: {task_result.get('run_id')}")
            print(f"[{datetime.now()}]   Actor ID: {task_result.get('actor_id')}")
            print(f"[{datetime.now()}]   Webhook URL: {task_result.get('webhook_url')}")

            # 更新 ASIN 狀態為 running
            print(f"[{datetime.now()}] 🔄 更新 ASIN 狀態為 running...")
            status_update_result = bulk_update_asin_status(
                asins, "running", datetime.now()
            )

            if status_update_result["success"]:
                print(
                    f"[{datetime.now()}] ✅ 成功更新 {status_update_result['success_count']} 個 ASIN 狀態為 running"
                )
                if status_update_result["failed_asins"]:
                    print(
                        f"[{datetime.now()}] ⚠️ 有 {len(status_update_result['failed_asins'])} 個 ASIN 狀態更新失敗: {status_update_result['failed_asins']}"
                    )
            else:
                print(
                    f"[{datetime.now()}] ❌ ASIN 狀態更新失敗: {status_update_result['message']}"
                )

            result = {
                "status": "task_started",
                "celery_task_id": self.request.id,
                "worker": self.request.hostname,
                "timestamp": datetime.now().isoformat(),
                "apify_run_id": task_result.get("run_id"),
                "actor_id": task_result.get("actor_id"),
                "webhook_url": task_result.get("webhook_url"),
                "asins": asins,
                "asin_status_update": status_update_result,
                "message": "Amazon 產品抓取任務已啟動，結果將通過 webhook 接收",
            }
        else:
            print(
                f"[{datetime.now()}] ❌ Apify 任務啟動失敗: {task_result.get('message')}"
            )

            # 更新 ASIN 狀態為 failed
            print(f"[{datetime.now()}] 🔄 更新 ASIN 狀態為 failed...")
            status_update_result = bulk_update_asin_status(asins, "failed")

            if status_update_result["success"]:
                print(
                    f"[{datetime.now()}] ✅ 成功更新 {status_update_result['success_count']} 個 ASIN 狀態為 failed"
                )
                if status_update_result["failed_asins"]:
                    print(
                        f"[{datetime.now()}] ⚠️ 有 {len(status_update_result['failed_asins'])} 個 ASIN 狀態更新失敗: {status_update_result['failed_asins']}"
                    )
            else:
                print(
                    f"[{datetime.now()}] ❌ ASIN 狀態更新失敗: {status_update_result['message']}"
                )

            result = {
                "status": "error",
                "celery_task_id": self.request.id,
                "worker": self.request.hostname,
                "timestamp": datetime.now().isoformat(),
                "asins": asins,
                "asin_status_update": status_update_result,
                "message": f"任務啟動失敗: {task_result.get('message')}",
            }

        print(f"[{datetime.now()}] Celery 任務完成: {result}")
        return result

    except Exception as exc:
        print(f"[{datetime.now()}] Celery 任務執行錯誤: {str(exc)}")

        # 更新 ASIN 狀態為 failed
        print(f"[{datetime.now()}] 🔄 更新 ASIN 狀態為 failed...")
        try:
            status_update_result = bulk_update_asin_status(asins, "failed")
            if status_update_result["success"]:
                print(
                    f"[{datetime.now()}] ✅ 成功更新 {status_update_result['success_count']} 個 ASIN 狀態為 failed"
                )
            else:
                print(
                    f"[{datetime.now()}] ❌ ASIN 狀態更新失敗: {status_update_result['message']}"
                )
        except Exception as status_error:
            print(f"[{datetime.now()}] ❌ 更新 ASIN 狀態時發生錯誤: {status_error}")

        # 重新拋出異常讓 Celery 處理
        raise self.retry(exc=exc, countdown=60, max_retries=3)
