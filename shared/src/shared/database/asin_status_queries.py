"""
ASIN 相關查詢功能
提供 ASIN 狀態的查詢和操作
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from shared.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def get_asins_to_scrape(limit: int = 100) -> List[str]:
    """
    獲取需要抓取的 ASIN 列表（支援超時檢測）

    Args:
        limit: 限制返回筆數

    Returns:
        需要抓取的 ASIN 列表
    """
    client = get_supabase_client()
    if not client:
        logger.error("無法獲取 Supabase 客戶端")
        return []

    try:
        # 計算時間閾值
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        one_day_ago = yesterday.replace(
            hour=23, minute=59, second=59, microsecond=999999
        ).isoformat()
        five_minutes_ago = (now - timedelta(minutes=5)).isoformat()

        # 查詢需要抓取的 ASIN
        result = (
            client.table("asin_status")
            .select("asin")
            .or_(
                "status.eq.pending,"
                f"and(status.eq.completed,task_timestamp.lte.{one_day_ago}),"
                f"and(status.eq.running,task_timestamp.lt.{five_minutes_ago}),"
                "and(status.eq.failed,retry_count.lt.3)"
            )
            .order("task_timestamp", desc=False)
            .limit(limit)
            .execute()
        )

        asins = [item["asin"] for item in result.data]
        logger.info(f"找到 {len(asins)} 個 ASIN 需要抓取")
        return asins
    except Exception as e:
        logger.error(f"獲取需要抓取的 ASIN 失敗: {e}")
        return []


def bulk_update_asin_status(
    asins: List[str], status: str, task_timestamp: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    批量更新 ASIN 狀態

    Args:
        asins: 要更新的 ASIN 列表
        status: 目標狀態（pending, running, completed, failed）
        task_timestamp: 任務時間戳記（僅在 status='running' 時使用）

    Returns:
        包含成功和失敗結果的字典
    """
    if not asins:
        return {
            "success": True,
            "successful_asins": [],
            "failed_asins": [],
            "message": "沒有 ASIN 需要更新",
        }

    # 驗證狀態值
    valid_statuses = ["pending", "running", "completed", "failed"]
    if status not in valid_statuses:
        logger.error(f"無效的狀態值: {status}，有效值: {valid_statuses}")
        return {
            "success": False,
            "successful_asins": [],
            "failed_asins": asins,
            "message": f"無效的狀態值: {status}",
        }

    client = get_supabase_client()
    if not client:
        logger.error("無法獲取 Supabase 客戶端")
        return {
            "success": False,
            "successful_asins": [],
            "failed_asins": asins,
            "message": "無法獲取資料庫連接",
        }

    successful_asins = []
    failed_asins = []

    try:

        # 先查詢所有 ASIN 的現有資料
        try:
            logger.info(f"開始查詢 {len(asins)} 個 ASIN 的現有資料...")
            existing_result = (
                client.table("asin_status")
                .select("asin, retry_count")
                .in_("asin", asins)
                .execute()
            )
            existing_asins = {item["asin"]: item for item in existing_result.data}
            logger.info(f"找到 {len(existing_asins)} 個已存在的 ASIN 記錄")

            # 準備批量更新資料
            bulk_update_data = []

            for asin in asins:
                if asin not in existing_asins:
                    logger.warning(f"ASIN {asin} 不存在，跳過更新")
                    failed_asins.append(asin)
                    continue

                # 準備更新資料
                asin_update_data = {"asin": asin, "status": status}

                # 如果是 running 狀態，更新 task_timestamp
                if status == "running" and task_timestamp:
                    asin_update_data["task_timestamp"] = task_timestamp.isoformat()

                # 如果是 failed 狀態，增加 retry_count
                if status == "failed":
                    current_retry_count = existing_asins[asin].get("retry_count", 0)
                    asin_update_data["retry_count"] = current_retry_count + 1

                bulk_update_data.append(asin_update_data)
                successful_asins.append(asin)
                logger.debug(f"準備更新 ASIN {asin}: {asin_update_data}")

            # 執行批量更新
            if bulk_update_data:
                logger.info(f"開始執行批量更新 {len(bulk_update_data)} 個 ASIN...")
                logger.debug(f"批量更新資料: {bulk_update_data}")
                # 使用 asin 欄位作為衝突檢測的依據
                result = (
                    client.table("asin_status")
                    .upsert(bulk_update_data, on_conflict="asin")
                    .execute()
                )
                logger.info(f"成功批量更新 {len(result.data)} 個 ASIN 狀態")
            else:
                logger.warning("沒有資料需要批量更新")

        except Exception as e:
            logger.error(f"批量更新 ASIN 狀態時發生錯誤: {e}")
            # 如果批量更新失敗，回退到逐個更新
            logger.info("回退到逐個更新模式")
            for asin in asins:
                try:
                    # 檢查 ASIN 是否存在
                    check_result = (
                        client.table("asin_status")
                        .select("asin, retry_count")
                        .eq("asin", asin)
                        .execute()
                    )

                    if not check_result.data:
                        logger.warning(f"ASIN {asin} 不存在，跳過更新")
                        failed_asins.append(asin)
                        continue

                    # 準備更新資料
                    asin_update_data = {"status": status}

                    # 如果是 running 狀態，更新 task_timestamp
                    if status == "running" and task_timestamp:
                        asin_update_data["task_timestamp"] = task_timestamp.isoformat()

                    # 如果是 failed 狀態，增加 retry_count
                    if status == "failed":
                        current_retry_count = check_result.data[0].get("retry_count", 0)
                        asin_update_data["retry_count"] = current_retry_count + 1

                    # 執行更新
                    result = (
                        client.table("asin_status")
                        .update(asin_update_data)
                        .eq("asin", asin)
                        .execute()
                    )

                    if result.data:
                        if asin not in successful_asins:
                            successful_asins.append(asin)
                        logger.debug(f"成功更新 ASIN {asin} 狀態為 {status}")
                    else:
                        if asin in successful_asins:
                            successful_asins.remove(asin)
                        failed_asins.append(asin)
                        logger.warning(f"更新 ASIN {asin} 失敗：沒有返回資料")

                except Exception as individual_error:
                    logger.error(f"更新 ASIN {asin} 時發生錯誤: {individual_error}")
                    if asin in successful_asins:
                        successful_asins.remove(asin)
                    failed_asins.append(asin)

        # 準備返回結果
        success = len(failed_asins) == 0
        message = (
            f"成功更新 {len(successful_asins)} 個 ASIN，失敗 {len(failed_asins)} 個"
        )

        logger.info(f"批量更新 ASIN 狀態完成: {message}")

        return {
            "success": success,
            "successful_asins": successful_asins,
            "failed_asins": failed_asins,
            "message": message,
            "total_processed": len(asins),
            "success_count": len(successful_asins),
            "failure_count": len(failed_asins),
        }

    except Exception as e:
        logger.error(f"批量更新 ASIN 狀態時發生錯誤: {e}")
        return {
            "success": False,
            "successful_asins": successful_asins,
            "failed_asins": asins,
            "message": f"批量更新失敗: {str(e)}",
        }


def get_pending_asins(limit: int = 100) -> List[str]:
    """
    獲取待處理的 ASIN 列表（向後兼容）

    Args:
        limit: 限制返回筆數

    Returns:
        待處理的 ASIN 列表
    """
    return get_asins_to_scrape(limit)


# 使用範例
if __name__ == "__main__":
    from datetime import datetime

    # 測試獲取需要抓取的 ASIN
    print("=== 測試獲取需要抓取的 ASIN ===")
    asin_list = get_asins_to_scrape(limit=5)
    print(f"需要抓取的 ASIN 列表: {asin_list}")

    # 測試獲取 ASIN 列表（向後兼容）
    print("\n=== 測試獲取 ASIN 列表（向後兼容）===")
    asin_list = get_pending_asins(limit=3)
    print(f"待處理的 ASIN 列表: {asin_list}")

    # 測試批量更新 ASIN 狀態
    print("\n=== 測試批量更新 ASIN 狀態 ===")
    if asin_list:
        # 測試更新為 running 狀態
        result = bulk_update_asin_status(asin_list[:2], "running", datetime.now())
        print(f"更新為 running 狀態結果: {result}")

        # 測試更新為 completed 狀態
        result = bulk_update_asin_status(asin_list[:2], "completed")
        print(f"更新為 completed 狀態結果: {result}")

        # 測試更新為 failed 狀態
        result = bulk_update_asin_status(asin_list[:2], "failed")
        print(f"更新為 failed 狀態結果: {result}")
    else:
        print("沒有 ASIN 可以測試批量更新功能")
