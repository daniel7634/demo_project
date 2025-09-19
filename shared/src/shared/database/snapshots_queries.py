"""
Product Snapshots 相關查詢功能
提供 product_snapshots 表的查詢、創建和更新操作
"""

import logging
from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from shared.database.model_types import ProductSnapshotDict
from shared.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def get_latest_snapshot(asin: str) -> Optional[ProductSnapshotDict]:
    """
    獲取產品最新快照

    Args:
        asin: 產品 ASIN

    Returns:
        最新快照資料，如果不存在則返回 None
    """
    client = get_supabase_client()
    if not client:
        logger.error("無法獲取 Supabase 客戶端")
        return None

    try:
        # 使用 DISTINCT ON 邏輯獲取最新快照
        # 對於 TimescaleDB，先按 snapshot_date 排序，再按 created_at 排序
        # 明確指定需要的欄位，排除 created_at
        result = (
            client.table("product_snapshots")
            .select(
                "asin, snapshot_date, price, rating, review_count, bsr_data, raw_data"
            )
            .eq("asin", asin)
            .order("snapshot_date", desc=True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if result.data:
            logger.info(f"成功獲取產品 {asin} 的最新快照")
            try:
                return ProductSnapshotDict(**result.data[0])
            except Exception as conversion_error:
                logger.error(f"轉換快照資料失敗: {conversion_error}")
                return None
        else:
            logger.info(f"產品 {asin} 沒有快照資料")
            return None
    except Exception as e:
        logger.error(f"獲取產品 {asin} 最新快照失敗: {e}")
        return None


def get_previous_snapshot(
    asin: str, current_date: str
) -> Optional[ProductSnapshotDict]:
    """
    獲取產品前一個快照

    Args:
        asin: 產品 ASIN
        current_date: 當前快照日期 (YYYY-MM-DD)

    Returns:
        前一個快照資料，如果不存在則返回 None
    """
    client = get_supabase_client()
    if not client:
        logger.error("無法獲取 Supabase 客戶端")
        return None

    try:
        result = (
            client.table("product_snapshots")
            .select(
                "asin, snapshot_date, price, rating, review_count, bsr_data, raw_data"
            )
            .eq("asin", asin)
            .lt("snapshot_date", current_date)
            .order("snapshot_date", desc=True)
            .limit(1)
            .execute()
        )

        if result.data:
            logger.info(
                f"成功獲取產品 {asin} 的前一個快照: {result.data[0].get('snapshot_date')}"
            )
            try:
                return ProductSnapshotDict(**result.data[0])
            except Exception as conversion_error:
                logger.error(f"轉換前一個快照資料失敗: {conversion_error}")
                return None
        else:
            logger.info(f"產品 {asin} 沒有前一個快照")
            return None
    except Exception as e:
        logger.error(f"獲取產品 {asin} 前一個快照失敗: {e}")
        return None


def get_snapshots_by_date_range(
    asin: str, start_date: date, end_date: date
) -> List[ProductSnapshotDict]:
    """
    獲取產品在指定日期範圍內的快照

    Args:
        asin: 產品 ASIN
        start_date: 開始日期
        end_date: 結束日期

    Returns:
        快照資料列表
    """
    client = get_supabase_client()
    if not client:
        logger.error("無法獲取 Supabase 客戶端")
        return []

    try:
        # 對於 TimescaleDB，優先使用 snapshot_date 進行分區裁剪
        result = (
            client.table("product_snapshots")
            .select(
                "asin, snapshot_date, price, rating, review_count, bsr_data, raw_data"
            )
            .eq("asin", asin)
            .gte("snapshot_date", start_date.isoformat())
            .lte("snapshot_date", end_date.isoformat())
            .order("snapshot_date", desc=True)
            .order("created_at", desc=True)
            .execute()
        )

        logger.info(
            f"成功獲取產品 {asin} 在 {start_date} 到 {end_date} 的 {len(result.data)} 筆快照"
        )

        # 轉換所有快照資料為 dataclass
        converted_snapshots = []
        for snapshot_data in result.data:
            try:
                converted_snapshots.append(ProductSnapshotDict(**snapshot_data))
            except Exception as conversion_error:
                logger.warning(f"跳過無效快照資料: {conversion_error}")
                continue

        return converted_snapshots
    except Exception as e:
        logger.error(f"獲取產品 {asin} 快照失敗: {e}")
        return []


def bulk_create_snapshots(snapshots: List[ProductSnapshotDict]) -> bool:
    """
    批量創建產品快照

    Args:
        snapshots: 快照資料列表，每個字典應包含必要欄位

    Returns:
        創建是否成功
    """
    if not snapshots:
        logger.warning("沒有快照資料需要創建")
        return True

    client = get_supabase_client()
    if not client:
        logger.error("無法獲取 Supabase 客戶端")
        return False

    try:
        prepared_snapshots = []
        for snapshot in snapshots:
            # 轉換 ProductSnapshotDict 為字典
            prepared_snapshot = asdict(snapshot)

            # 驗證必要欄位
            if not prepared_snapshot["asin"] or not prepared_snapshot["snapshot_date"]:
                logger.warning(f"跳過無效快照資料（缺少必要欄位）: {snapshot}")
                continue

            # 確保 snapshot_date 是字串格式
            if isinstance(prepared_snapshot["snapshot_date"], date):
                prepared_snapshot["snapshot_date"] = prepared_snapshot[
                    "snapshot_date"
                ].isoformat()
            elif isinstance(prepared_snapshot["snapshot_date"], str):
                # 已經是字串格式，不需要轉換
                pass

            # 自動添加 created_at 欄位（TimescaleDB 分區需要）
            if (
                "created_at" not in prepared_snapshot
                or prepared_snapshot["created_at"] is None
            ):
                prepared_snapshot["created_at"] = datetime.now().isoformat()

            prepared_snapshots.append(prepared_snapshot)

        if not prepared_snapshots:
            logger.warning("沒有有效的快照資料需要創建")
            return True

        print(prepared_snapshots)

        result = client.table("product_snapshots").insert(prepared_snapshots).execute()
        logger.info(f"成功創建 {len(result.data)} 筆快照資料")
        return True
    except Exception as e:
        logger.error(f"批量創建快照失敗: {e}")
        return False


def bulk_update_snapshots(snapshots: List[ProductSnapshotDict]) -> bool:
    """
    批量更新產品快照（使用 upsert）

    Args:
        snapshots: 快照資料列表，每個字典應包含 asin, snapshot_date, created_at

    Returns:
        更新是否成功
    """
    if not snapshots:
        logger.warning("沒有快照資料需要更新")
        return True

    client = get_supabase_client()
    if not client:
        logger.error("無法獲取 Supabase 客戶端")
        return False

    try:
        prepared_snapshots = []
        for snapshot in snapshots:
            if not snapshot.asin or not snapshot.snapshot_date:
                logger.warning(f"跳過無效快照資料（缺少主鍵欄位）: {snapshot}")
                continue

            # 使用 asdict 轉換為字典格式
            snapshot_dict = asdict(snapshot)

            # 確保 snapshot_date 是字串格式
            if isinstance(snapshot_dict["snapshot_date"], date):
                snapshot_dict["snapshot_date"] = snapshot_dict[
                    "snapshot_date"
                ].isoformat()
            elif isinstance(snapshot_dict["snapshot_date"], str):
                # 已經是字串格式，不需要轉換
                pass

            # 自動添加 created_at 欄位（TimescaleDB 分區需要）
            if "created_at" not in snapshot_dict or snapshot_dict["created_at"] is None:
                snapshot_dict["created_at"] = datetime.now().isoformat()

            prepared_snapshots.append(snapshot_dict)

        if not prepared_snapshots:
            logger.warning("沒有有效的快照資料需要更新")
            return True

        result = client.table("product_snapshots").upsert(prepared_snapshots).execute()
        logger.info(f"成功更新 {len(result.data)} 筆快照資料")
        return True
    except Exception as e:
        logger.error(f"批量更新快照失敗: {e}")
        return False


def create_snapshot(
    asin: str,
    snapshot_date: date,
    price: Optional[float] = None,
    rating: Optional[float] = None,
    review_count: Optional[int] = None,
    bsr_data: Optional[List[Dict[str, Any]]] = None,
    raw_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    創建單一產品快照

    Args:
        asin: 產品 ASIN
        snapshot_date: 快照日期
        price: 價格
        rating: 評分
        review_count: 評論數量
        bsr_data: BSR 資料
        raw_data: 原始資料

    Returns:
        創建是否成功
    """
    snapshot_data = ProductSnapshotDict(
        asin=asin,
        snapshot_date=snapshot_date.isoformat(),
        price=price,
        rating=rating,
        review_count=review_count,
        bsr_data=bsr_data or [],
        raw_data=raw_data or {},
    )

    return bulk_create_snapshots([snapshot_data])


def get_snapshots_by_asins(
    asins: List[str], limit: int = 100
) -> List[ProductSnapshotDict]:
    """
    獲取多個產品的最新快照

    Args:
        asins: ASIN 列表
        limit: 限制返回筆數

    Returns:
        快照資料列表
    """
    client = get_supabase_client()
    if not client:
        logger.error("無法獲取 Supabase 客戶端")
        return []

    try:
        result = (
            client.table("product_snapshots")
            .select(
                "asin, snapshot_date, price, rating, review_count, bsr_data, raw_data"
            )
            .in_("asin", asins)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        logger.info(f"成功獲取 {len(result.data)} 筆快照資料")

        # 轉換所有快照資料為 dataclass
        converted_snapshots = []
        for snapshot_data in result.data:
            try:
                converted_snapshots.append(ProductSnapshotDict(**snapshot_data))
            except Exception as conversion_error:
                logger.warning(f"跳過無效快照資料: {conversion_error}")
                continue

        return converted_snapshots
    except Exception as e:
        logger.error(f"獲取快照資料失敗: {e}")
        return []


# 使用範例
if __name__ == "__main__":
    from datetime import date

    # 測試獲取最新快照
    print("=== 測試獲取最新快照 ===")
    snapshot = get_latest_snapshot("B01LP0U5X0")
    print(f"最新快照: {snapshot}")

    # 測試批量創建快照
    # print("\n=== 測試批量創建快照 ===")
    # test_snapshots = [
    #     ProductSnapshotDict(
    #         asin='B0DG3X1D7B',
    #         snapshot_date=date.today().isoformat(),
    #         price=17.67,
    #         rating=4.6,
    #         review_count=2512,
    #         bsr_data=[
    #             {'rank': 475, 'category': 'Sports & Outdoors'},
    #             {'rank': 8, 'category': 'Yoga Mats'}
    #         ],
    #         raw_data={'test': 'data'}
    #     )
    # ]
    # success = bulk_create_snapshots(test_snapshots)
    # print(f"批量創建結果: {success}")

    # 測試獲取日期範圍快照
    print("\n=== 測試獲取日期範圍快照 ===")
    start_date = date.today() - timedelta(days=2)
    end_date = date.today()
    snapshots = get_snapshots_by_date_range("B01LP0U5X0", start_date, end_date)
    print(f"日期範圍快照: {len(snapshots)} 筆")

# 導出函數
__all__ = [
    "get_latest_snapshot",
    "get_previous_snapshot",
    "get_snapshots_by_date_range",
    "get_snapshots_by_asins",
    "bulk_create_snapshots",
    "bulk_update_snapshots",
    "create_snapshot",
]
