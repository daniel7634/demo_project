"""
簡化的 Amazon 資料收集器
專注於單一產品詳細資料抓取，批次處理和重試由 Celery 處理
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from apify_client import ApifyClientAsync
from shared.config.settings import get_apify_token

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AmazonDataParser:
    """Amazon 產品資料解析器 - 處理從 Apify Dataset 抓取的原始資料"""

    def __init__(self):
        """初始化解析器"""
        self.logger = logging.getLogger(__name__)

    def parse_product_data(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析單一產品資料

        Args:
            raw_item: 從 Apify Dataset 抓取的原始資料

        Returns:
            解析後的標準化產品資料
        """
        try:
            parsed_data = {
                "asin": self._extract_asin(raw_item),
                "title": self._extract_title(raw_item),
                "price": self._extract_price(raw_item),
                "rating": self._extract_rating(raw_item),
                "review_count": self._extract_review_count(raw_item),
                "bsr": self._extract_bsr(raw_item),
                "categories": self._extract_categories(raw_item),
                # "raw_data": raw_item,  # 保留原始資料供除錯用
            }

            self.logger.info(f"✅ 成功解析產品資料: ASIN={parsed_data.get('asin')}")
            return parsed_data

        except Exception as e:
            self.logger.error(f"❌ 解析產品資料失敗: {e}")
            return {
                "error": str(e),
                "raw_data": raw_item,
                "parsed_at": self._get_current_timestamp(),
            }

    def parse_batch_data(self, raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批次解析產品資料

        Args:
            raw_items: 從 Apify Dataset 抓取的原始資料列表

        Returns:
            解析後的標準化產品資料列表
        """
        self.logger.info(f"開始批次解析 {len(raw_items)} 筆產品資料")

        parsed_items = []
        success_count = 0
        error_count = 0

        for i, raw_item in enumerate(raw_items, 1):
            try:
                parsed_item = self.parse_product_data(raw_item)
                parsed_items.append(parsed_item)

                if "error" not in parsed_item:
                    success_count += 1
                else:
                    error_count += 1

            except Exception as e:
                self.logger.error(f"❌ 批次解析第 {i} 筆資料失敗: {e}")
                error_count += 1
                parsed_items.append(
                    {
                        "error": str(e),
                        "raw_data": raw_item,
                        "parsed_at": self._get_current_timestamp(),
                    }
                )

        self.logger.info(
            f"✅ 批次解析完成: 成功 {success_count} 筆, 失敗 {error_count} 筆"
        )
        return parsed_items

    def _extract_asin(self, raw_item: Dict[str, Any]) -> Optional[str]:
        """提取 ASIN"""
        return raw_item.get("asin")

    def _extract_title(self, raw_item: Dict[str, Any]) -> Optional[str]:
        """提取產品標題"""
        return raw_item.get("title")

    def _extract_price(self, raw_item: Dict[str, Any]) -> Optional[str]:
        """提取價格資訊"""
        return raw_item.get("price")

    def _extract_rating(self, raw_item: Dict[str, Any]) -> Optional[float]:
        """提取評分資訊 - 轉換為數值"""
        try:
            rating = raw_item.get("productRating")
            if rating is None:
                return None

            # 如果是字串，嘗試提取數值
            if isinstance(rating, str):
                # 處理 "4.5 out of 5 stars" 格式
                import re

                match = re.search(r"(\d+\.?\d*)", rating)
                if match:
                    return float(match.group(1))
                return None

            # 如果已經是數值，直接返回
            if isinstance(rating, (int, float)):
                return float(rating)

            return None
        except Exception as e:
            self.logger.error(f"提取評分資訊失敗: {e}")
            return None

    def _extract_review_count(self, raw_item: Dict[str, Any]) -> Optional[int]:
        """提取評論數量"""
        return raw_item.get("countReview")

    def _extract_bsr(self, raw_item: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """提取BSR資訊 - 從 productDetails 中尋找所有 Best Sellers Rank"""
        try:
            product_details = raw_item.get("productDetails", [])
            if not isinstance(product_details, list):
                return None

            bsr_list = []
            # 在 productDetails 列表中尋找所有 "Best Sellers Rank"
            for detail in product_details:
                if (
                    isinstance(detail, dict)
                    and detail.get("name") == "Best Sellers Rank"
                ):
                    value = detail.get("value", "")
                    if value:
                        # 解析 BSR 資料，可能包含多個排名
                        parsed_bsr = self._parse_bsr_value(value)
                        if parsed_bsr:
                            bsr_list.extend(parsed_bsr)

            return bsr_list if bsr_list else None
        except Exception as e:
            self.logger.error(f"提取 BSR 資訊失敗: {e}")
            return None

    def _parse_bsr_value(self, bsr_value: str) -> Optional[List[Dict[str, Any]]]:
        """解析 BSR 值，支援多個排名格式"""
        try:
            import re

            bsr_list = []

            # 移除括號內容，例如 "(See Top 100 in Sports & Outdoors)"
            cleaned_value = re.sub(r"\([^)]*\)", "", bsr_value)

            # 匹配多個 "#數字 in 類別" 格式
            # 例如: "#10 in Sports & Outdoors #1 in Yoga Mats"
            pattern = r"#(\d+)\s+in\s+([^#]+?)(?=#|$)"
            matches = re.findall(pattern, cleaned_value)

            for match in matches:
                rank = int(match[0])
                category = match[1].strip()
                bsr_list.append(
                    {"rank": rank, "category": category, "raw_value": bsr_value}
                )

            return bsr_list if bsr_list else None
        except Exception as e:
            self.logger.error(f"解析 BSR 值失敗: {e}")
            return None

    def _extract_categories(self, raw_item: Dict[str, Any]) -> Optional[List[str]]:
        """提取分類資訊 - 從 categoriesExtended 中提取 name 欄位"""
        try:
            categories_extended = raw_item.get("categoriesExtended", [])
            if not isinstance(categories_extended, list):
                return None

            # 提取所有分類的 name 欄位
            categories = []
            for category in categories_extended:
                if isinstance(category, dict) and "name" in category:
                    categories.append(category["name"])

            return categories if categories else None
        except Exception as e:
            self.logger.error(f"提取分類資訊失敗: {e}")
            return None


class AmazonDataCollector:
    """簡化的 Amazon 資料收集器 - 專注於單一產品資料抓取"""

    def __init__(self, api_token: str = None):
        """
        初始化 Amazon 資料收集器

        Args:
            api_token: Apify API Token，如果未提供則從環境變量讀取
        """
        if api_token is None:
            api_token = get_apify_token()

        self.client = ApifyClientAsync(api_token)
        self.api_token = api_token

        # Amazon 產品抓取 Actor ID
        self.PRODUCT_DETAILS_ACTOR = "axesso_data/amazon-product-details-scraper"

        # 初始化資料解析器
        self.parser = AmazonDataParser()

    async def get_product_details(self, asins: List[str]) -> Dict[str, Any]:
        """
        啟動 Amazon 產品抓取任務 - 純 webhook 模式

        Args:
            asins: 產品 ASIN 列表

        Returns:
            包含任務資訊的字典，結果將通過 webhook 接收
        """
        if not asins:
            logger.warning("ASIN 列表為空")
            return {"status": "error", "message": "ASIN 列表為空"}

        try:
            logger.info(f"啟動 Amazon 產品抓取任務: {asins}")

            # 設定產品詳情抓取參數
            run_input = {
                "urls": [f"https://www.amazon.com/dp/{asin}" for asin in asins],
                "language": "zh-TW",
                "proxy": {
                    "useApifyProxy": True,
                    "apifyProxyGroups": ["RESIDENTIAL"],
                    "apifyProxyCountry": "TW",
                },
            }

            # 設定 webhook URL
            webhook_domain = os.getenv("WEBHOOK_DOMAIN", "https://localhost:8000")
            webhook_url = f"{webhook_domain}/webhook/amazon-products"

            # 啟動 Actor 並設定 webhook
            run = await self.client.actor(self.PRODUCT_DETAILS_ACTOR).start(
                run_input=run_input,
                webhooks=[
                    {
                        "event_types": [
                            "ACTOR.RUN.SUCCEEDED",
                            "ACTOR.RUN.FAILED",
                            "ACTOR.RUN.TIMED_OUT",
                            "ACTOR.RUN.ABORTED",
                        ],
                        "request_url": webhook_url,
                    }
                ],
            )

            logger.info("✅ Actor 任務已啟動")
            logger.info(f"   Run ID: {run.get('id')}")
            logger.info(f"   Status: {run.get('status')}")
            logger.info(f"   Webhook URL: {webhook_url}")

            return {
                "status": "started",
                "message": "Amazon 產品抓取任務已啟動，結果將通過 webhook 接收",
                "run_id": run.get("id"),
                "actor_id": self.PRODUCT_DETAILS_ACTOR,
                "asins": asins,
                "webhook_url": webhook_url,
                "started_at": run.get("startedAt"),
            }

        except Exception as e:
            logger.error(f"啟動 Amazon 產品抓取任務時發生錯誤: {str(e)}")
            return {
                "status": "error",
                "message": f"啟動任務失敗: {str(e)}",
                "asins": asins,
            }

    async def get_dataset_items(self, dataset_id: str) -> List[Dict[str, Any]]:
        """
        從 Apify Dataset 抓取資料

        Args:
            dataset_id: Apify Dataset ID

        Returns:
            抓取到的資料列表
        """
        try:
            logger.info(f"從 Dataset {dataset_id} 抓取資料...")
            dataset_items = await self.client.dataset(dataset_id).list_items()
            logger.info(f"✅ 成功抓取 {len(dataset_items.items)} 筆資料")
            return dataset_items.items
        except Exception as e:
            logger.error(f"從 Dataset {dataset_id} 抓取資料失敗: {e}")
            return []

    async def get_parsed_dataset_items(self, dataset_id: str) -> List[Dict[str, Any]]:
        """
        從 Apify Dataset 抓取並解析資料

        Args:
            dataset_id: Apify Dataset ID

        Returns:
            解析後的標準化產品資料列表
        """
        try:
            logger.info(f"從 Dataset {dataset_id} 抓取並解析資料...")

            # 1. 抓取原始資料
            raw_items = await self.get_dataset_items(dataset_id)

            if not raw_items:
                logger.warning(f"Dataset {dataset_id} 沒有資料")
                return []

            # 2. 使用 parser 解析資料
            parsed_items = self.parser.parse_batch_data(raw_items)

            logger.info(f"✅ 成功抓取並解析 {len(parsed_items)} 筆產品資料")
            return parsed_items

        except Exception as e:
            logger.error(f"從 Dataset {dataset_id} 抓取並解析資料失敗: {e}")
            return []


# 使用範例
async def main():
    """主函數範例"""
    # 創建 Amazon 資料收集器 (會自動從環境變量讀取 API Token)
    amazon_collector = AmazonDataCollector()

    # 測試多個產品資料抓取
    test_asins = ["B01LP0U5X0", "B0DG3X1D7B", "B092XTMNCC"]

    print(f"🚀 啟動 Amazon 產品抓取任務: {test_asins}")
    result = await amazon_collector.get_product_details(test_asins)

    if result["status"] == "started":
        print("✅ 任務啟動成功:")
        print(f"   Run ID: {result.get('run_id')}")
        print(f"   Actor ID: {result.get('actor_id')}")
        print(f"   Webhook URL: {result.get('webhook_url')}")
        print(f"   開始時間: {result.get('started_at')}")
        print(f"   訊息: {result.get('message')}")
        print(f"\n📡 結果將通過 webhook 發送到: {result.get('webhook_url')}")
    else:
        print(f"❌ 任務啟動失敗: {result.get('message')}")


async def test_parser():
    """測試 Parser 功能"""
    print("\n" + "=" * 50)
    print("🧪 測試 AmazonDataParser")
    print("=" * 50)

    # 創建解析器
    parser = AmazonDataParser()

    # 模擬原始資料
    mock_raw_data = [
        {
            "asin": "B01LP0U5X0",
            "title": "測試產品標題",
            "price": "$29.99",
            "productRating": "4.5 out of 5 stars",  # 測試字串格式
            "countReview": 1234,
            "productDetails": [
                {
                    "name": "Best Sellers Rank",
                    "value": "#10 in Sports & Outdoors (See Top 100 in Sports & Outdoors) #1 in Yoga Mats",
                },
                {"name": "Color", "value": "Red"},
            ],
            "categoriesExtended": [
                {
                    "name": "Electronics",
                    "url": "/electronics-store/b/ref=dp_bc_1?ie=UTF8&node=172282",
                    "node": "172282",
                },
                {
                    "name": "Computers & Accessories",
                    "url": "/computer-pc-hardware-accessories-add-ons/b/ref=dp_bc_2?ie=UTF8&node=541966",
                    "node": "541966",
                },
                {
                    "name": "Data Storage",
                    "url": "/Memory-Cards-External-Storage/b/ref=dp_bc_3?ie=UTF8&node=1292110011",
                    "node": "1292110011",
                },
                {
                    "name": "USB Flash Drives",
                    "url": "/USB-Flash-Drives-Storage-Add-Ons/b/ref=dp_bc_4?ie=UTF8&node=3151491",
                    "node": "3151491",
                },
            ],
        }
    ]

    # 測試單一產品解析
    print("📝 測試單一產品解析:")
    parsed_item = parser.parse_product_data(mock_raw_data[0])
    print(f"   解析結果: {parsed_item}")

    # 測試批次解析
    print("\n📝 測試批次解析:")
    parsed_items = parser.parse_batch_data(mock_raw_data)
    print(f"   批次解析結果: {len(parsed_items)} 筆")
    for i, item in enumerate(parsed_items, 1):
        print(f"   產品 {i}: ASIN={item.get('asin')}, 標題={item.get('title')}")
        print(f"   評分: {item.get('rating')}")
        print(f"   BSR: {item.get('bsr')}")
        print(f"   分類: {item.get('categories')}")


if __name__ == "__main__":
    # 測試基本功能
    asyncio.run(main())

    # 測試 Parser 功能
    asyncio.run(test_parser())
