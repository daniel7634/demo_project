"""
Products 相關查詢功能
提供 products 表的查詢、創建和更新操作
"""

import logging
from typing import Any, Dict, List, Optional, Union

from shared.database.model_types import Product
from shared.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def get_product(asin: str) -> Optional[Product]:
    """
    獲取單一產品資料

    Args:
        asin: 產品 ASIN

    Returns:
        產品資料物件，如果不存在則返回 None
    """
    client = get_supabase_client()
    if not client:
        logger.error("無法獲取 Supabase 客戶端")
        return None

    try:
        result = (
            client.table("products")
            .select("asin, title, categories")
            .eq("asin", asin)
            .execute()
        )
        if result.data:
            logger.info(f"成功獲取產品 {asin} 的資料")
            try:
                return Product(**result.data[0])
            except Exception as conversion_error:
                logger.error(f"轉換產品資料失敗: {conversion_error}")
                return None
        else:
            logger.info(f"產品 {asin} 不存在")
            return None
    except Exception as e:
        logger.error(f"獲取產品 {asin} 資料失敗: {e}")
        return None


def get_products_by_asins(asins: List[str]) -> List[Product]:
    """
    根據 ASIN 列表獲取產品資料

    Args:
        asins: ASIN 列表

    Returns:
        產品資料物件列表
    """
    client = get_supabase_client()
    if not client:
        logger.error("無法獲取 Supabase 客戶端")
        return []

    try:
        result = (
            client.table("products")
            .select("asin, title, categories")
            .in_("asin", asins)
            .execute()
        )
        logger.info(f"成功獲取 {len(result.data)} 筆產品資料")

        # 轉換所有產品資料為 Product 物件
        converted_products = []
        for product_data in result.data:
            try:
                converted_products.append(Product(**product_data))
            except Exception as conversion_error:
                logger.warning(f"跳過無效產品資料: {conversion_error}")
                continue

        return converted_products
    except Exception as e:
        logger.error(f"獲取產品資料失敗: {e}")
        return []


def bulk_create_products(products: Union[List[Dict[str, Any]], List[Product]]) -> bool:
    """
    批量創建產品

    Args:
        products: 產品資料列表，可以是字典列表或 Product 物件列表

    Returns:
        創建是否成功
    """
    if not products:
        logger.warning("沒有產品資料需要創建")
        return True

    client = get_supabase_client()
    if not client:
        logger.error("無法獲取 Supabase 客戶端")
        return False

    try:
        # 準備資料，確保必要欄位存在
        prepared_products = []
        for product in products:
            # 處理 Product 物件或字典
            if isinstance(product, Product):
                prepared_product = {
                    "asin": product.asin,
                    "title": product.title,
                    "categories": product.categories or [],
                }
            else:
                prepared_product = {
                    "asin": product.get("asin"),
                    "title": product.get("title"),
                    "categories": product.get("categories", []),
                }

            # 驗證必要欄位
            if not prepared_product["asin"]:
                logger.warning(f"跳過無效產品資料（缺少 ASIN）: {product}")
                continue
            prepared_products.append(prepared_product)

        if not prepared_products:
            logger.warning("沒有有效的產品資料需要創建")
            return True

        result = client.table("products").insert(prepared_products).execute()
        logger.info(f"成功創建 {len(result.data)} 筆產品資料")
        return True
    except Exception as e:
        logger.error(f"批量創建產品失敗: {e}")
        return False


def bulk_update_products(products: Union[List[Dict[str, Any]], List[Product]]) -> bool:
    """
    批量更新產品

    Args:
        products: 產品資料列表，可以是字典列表或 Product 物件列表

    Returns:
        更新是否成功
    """
    if not products:
        logger.warning("沒有產品資料需要更新")
        return True

    client = get_supabase_client()
    if not client:
        logger.error("無法獲取 Supabase 客戶端")
        return False

    try:
        # 準備資料，確保有 ASIN
        prepared_products = []
        for product in products:
            # 處理 Product 物件或字典
            if isinstance(product, Product):
                if not product.asin:
                    logger.warning(f"跳過無效產品資料（缺少 ASIN）: {product}")
                    continue
                # 轉換為字典格式
                prepared_products.append(
                    {
                        "asin": product.asin,
                        "title": product.title,
                        "categories": product.categories or [],
                    }
                )
            else:
                if not product.get("asin"):
                    logger.warning(f"跳過無效產品資料（缺少 ASIN）: {product}")
                    continue
                prepared_products.append(product)

        if not prepared_products:
            logger.warning("沒有有效的產品資料需要更新")
            return True

        result = client.table("products").upsert(prepared_products).execute()
        logger.info(f"成功更新 {len(result.data)} 筆產品資料")
        return True
    except Exception as e:
        logger.error(f"批量更新產品失敗: {e}")
        return False


def upsert_product(
    asin: str, title: Optional[str] = None, categories: Optional[List[str]] = None
) -> bool:
    """
    插入或更新單一產品

    Args:
        asin: 產品 ASIN
        title: 產品標題
        categories: 產品分類列表

    Returns:
        操作是否成功
    """
    product_data = {"asin": asin}
    if title is not None:
        product_data["title"] = title
    if categories is not None:
        product_data["categories"] = categories

    return bulk_update_products([product_data])


# 使用範例
if __name__ == "__main__":
    # 測試獲取單一產品
    print("=== 測試獲取單一產品 ===")
    product = get_product("B0DG3X1D7B")
    print(f"產品資料: {product}")

    # 測試批量創建產品
    print("\n=== 測試批量創建產品 ===")
    test_products = [
        {
            "asin": "B0DG3X1D7B",
            "title": "CAP Barbell 1/2-Inch High Density Exercise Yoga Mat",
            "categories": ["Sports & Outdoors", "Exercise & Fitness", "Yoga", "Mats"],
        },
        {
            "asin": "B08XYZ1234",
            "title": "測試瑜珈墊",
            "categories": ["Sports & Outdoors", "Yoga"],
        },
    ]
    success = bulk_create_products(test_products)
    print(f"批量創建結果: {success}")

    # 測試批量更新產品
    print("\n=== 測試批量更新產品 ===")
    update_products = [
        {
            "asin": "B0DG3X1D7B",
            "title": "更新後的瑜珈墊標題",
            "categories": ["Sports & Outdoors", "Yoga", "Mats", "Fitness"],
        }
    ]
    success = bulk_update_products(update_products)
    print(f"批量更新結果: {success}")

# 導出函數
__all__ = [
    "get_product",
    "get_products_by_asins",
    "bulk_create_products",
    "bulk_update_products",
    "upsert_product",
]
