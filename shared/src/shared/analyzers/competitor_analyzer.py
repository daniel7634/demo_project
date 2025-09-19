"""
競品分析器模組
提供競品分析的核心邏輯和資料收集功能
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from shared.analyzers.analyzer_types import (
    BasicComparison,
    CompetitorAnalysisData,
    CompetitorAnalysisMetadata,
    CompetitorAnalysisResult,
    DataAvailability,
    ExtractedProductData,
    PriceComparison,
    ProductAnalysisData,
    ProductBasicInfo,
    ProductCurrentData,
    RatingComparison,
    ReviewComparison,
)
from shared.database.model_types import Product, ProductSnapshotDict
from shared.database.products_queries import get_products_by_asins
from shared.database.snapshots_queries import (
    get_latest_snapshot,
    get_snapshots_by_date_range,
)

# 設定 logger
logger = logging.getLogger(__name__)


class CompetitorAnalyzer:
    """
    競品分析器
    負責收集產品資料、分析競品關係、生成分析結果
    """

    def __init__(self):
        """初始化競品分析器"""
        self.analysis_cache = {}
        self.alert_rules = None

    async def collect_product_data(self, asin: str) -> ProductAnalysisData:
        """
        收集單個產品的資料

        Args:
            asin: 產品 ASIN

        Returns:
            ProductAnalysisData: 收集到的產品資料
        """
        try:
            logger.info(f"開始收集產品資料: {asin}")

            if not asin:
                raise ValueError("缺少產品 ASIN")

            # 獲取產品基本資訊
            products_info = await self._get_products_info([asin])
            logger.debug(f"獲取到產品基本資訊: {products_info}")

            # 獲取最新快照資料
            latest_snapshots = await self._get_latest_snapshots([asin])
            logger.debug(f"獲取到最新快照: {latest_snapshots}")

            # 獲取歷史快照資料（使用預設的 7 天窗口）
            historical_snapshots = await self._get_historical_snapshots([asin], 7)
            logger.debug(f"獲取到歷史快照: {historical_snapshots}")

            # 組織單個產品的資料結構
            product_data = ProductAnalysisData(
                asin=asin,
                info=products_info.get(asin, Product(asin=asin)),
                latest_snapshot=latest_snapshots.get(asin),
                historical_snapshots=historical_snapshots.get(asin, []),
                collected_at=datetime.now().isoformat(),
            )

            logger.info(f"產品資料收集完成: {asin}")
            return product_data

        except Exception as e:
            logger.error(f"收集產品資料失敗: {str(e)}", exc_info=True)
            raise

    async def collect_competitors_data(
        self, main_asin: str, competitor_asins: List[str], window_size: int = 7
    ) -> CompetitorAnalysisData:
        """
        收集競品分析的完整資料

        Args:
            main_asin: 主產品 ASIN
            competitor_asins: 競品 ASIN 列表
            window_size: 分析時間窗口（天數）

        Returns:
            CompetitorAnalysisData: 收集到的完整分析資料
        """
        try:
            logger.info(
                f"開始收集競品分析資料: 主產品 {main_asin}, 競品 {len(competitor_asins)} 個"
            )

            # 收集所有相關 ASIN
            all_asins = [main_asin] + competitor_asins
            logger.debug(f"分析 ASIN 列表: {all_asins}")

            # 獲取產品基本資訊
            products_info = await self._get_products_info(all_asins)
            logger.debug(f"獲取到 {len(products_info)} 個產品基本資訊")

            # 獲取最新快照資料
            latest_snapshots = await self._get_latest_snapshots(all_asins)
            logger.debug(f"獲取到 {len(latest_snapshots)} 個最新快照")

            # 獲取歷史快照資料
            historical_snapshots = await self._get_historical_snapshots(
                all_asins, window_size
            )
            logger.debug(f"獲取到 {len(historical_snapshots)} 個歷史快照")

            # 組織資料結構
            main_product = ProductAnalysisData(
                asin=main_asin,
                info=products_info.get(main_asin, Product(asin=main_asin)),
                latest_snapshot=latest_snapshots.get(main_asin),
                historical_snapshots=historical_snapshots.get(main_asin, []),
            )

            # 處理競品資料
            competitors = []
            for asin in competitor_asins:
                competitor_data = ProductAnalysisData(
                    asin=asin,
                    info=products_info.get(asin, Product(asin=asin)),
                    latest_snapshot=latest_snapshots.get(asin),
                    historical_snapshots=historical_snapshots.get(asin, []),
                )
                competitors.append(competitor_data)

            analysis_metadata = CompetitorAnalysisMetadata(
                window_size=window_size,
                analysis_date=datetime.now().isoformat(),
                total_products=len(all_asins),
                competitor_count=len(competitor_asins),
            )

            product_data = CompetitorAnalysisData(
                main_product=main_product,
                competitors=competitors,
                analysis_metadata=analysis_metadata,
            )

            logger.info("競品分析資料收集完成")
            logger.debug(f"競品分析資料: {product_data}")
            return product_data

        except Exception as e:
            logger.error(f"收集競品分析資料失敗: {str(e)}", exc_info=True)
            raise

    async def analyze_competitors(
        self, main_asin: str, competitor_asins: List[str], window_size: int = 7
    ) -> CompetitorAnalysisResult:
        """
        分析競品關係

        Args:
            main_asin: 主產品 ASIN
            competitor_asins: 競品 ASIN 列表
            window_size: 分析時間窗口（天數）

        Returns:
            CompetitorAnalysisResult: 分析結果
        """
        try:
            logger.info(
                f"開始競品分析: 主產品 {main_asin}, 競品 {len(competitor_asins)} 個"
            )

            # 收集完整的競品分析資料
            product_data = await self.collect_competitors_data(
                main_asin, competitor_asins, window_size
            )
            if not product_data:
                raise ValueError("無法獲取競品分析資料")

            logger.info("成功收集競品分析資料")

            # 提取主產品數據
            main_product_data = self._extract_product_data(product_data.main_product)

            # 提取競品數據
            competitor_data = []
            for competitor in product_data.competitors:
                competitor_info = self._extract_product_data(competitor)
                competitor_data.append(competitor_info)

            # 基本數值比較
            basic_comparison = self._perform_basic_comparison(
                main_product_data, competitor_data
            )

            analysis_result = CompetitorAnalysisResult(
                main_product_data=main_product_data,
                competitor_data=competitor_data,
                basic_comparison=basic_comparison,
            )
            logger.debug(f"分析結果: {analysis_result}")

            logger.info("競品分析完成")
            return analysis_result

        except Exception as e:
            logger.error(f"競品分析失敗: {str(e)}", exc_info=True)
            raise

    def _extract_product_data(
        self, product_data: ProductAnalysisData
    ) -> ExtractedProductData:
        """
        提取產品基本數據

        Args:
            product_data: 產品分析資料

        Returns:
            ExtractedProductData: 提取的產品數據
        """
        asin = product_data.asin
        info: Product = product_data.info
        latest: Optional[ProductSnapshotDict] = product_data.latest_snapshot

        product_info = ProductBasicInfo(
            asin=asin, title=info.title, categories=info.categories
        )

        # 提取當前快照數據
        if latest:
            logger.debug(f"產品 {asin} 有快照數據")
            # 處理 BSR 資料
            bsr_data = latest.bsr_data or []
            bsr_info = self._extract_bsr_info(bsr_data)

            current_data = ProductCurrentData(
                price=latest.price,
                rating=latest.rating,
                review_count=latest.review_count,
                bsr=bsr_info["overall_rank"],
                bsr_details=bsr_info["details"],
                snapshot_date=latest.snapshot_date,
            )
        else:
            logger.warning(f"產品 {asin} 沒有快照數據")
            current_data = ProductCurrentData()

        return ExtractedProductData(basic_info=product_info, current_data=current_data)

    def _extract_bsr_info(self, bsr_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        從 BSR 資料列表中提取排名資訊

        Args:
            bsr_data: BSR 資料列表

        Returns:
            Dict[str, Any]: 包含整體排名和詳細資訊的字典
        """
        if not bsr_data:
            return {"overall_rank": None, "details": []}

        # 提取所有排名資訊
        details = []
        overall_rank = None

        for bsr_item in bsr_data:
            rank = bsr_item.get("rank")
            category = bsr_item.get("category", "未知類別")
            raw_value = bsr_item.get("raw_value", "")

            details.append({"rank": rank, "category": category, "raw_value": raw_value})

            # 使用第一個排名作為整體排名（通常是主要類別）
            if overall_rank is None and rank is not None:
                overall_rank = rank

        return {"overall_rank": overall_rank, "details": details}

    def _perform_basic_comparison(
        self,
        main_data: ExtractedProductData,
        competitor_data: List[ExtractedProductData],
    ) -> BasicComparison:
        """
        執行基本數值比較

        Args:
            main_data: 主產品數據
            competitor_data: 競品數據列表

        Returns:
            BasicComparison: 基本比較結果
        """
        if not competitor_data:
            # 返回空的比較結果
            return BasicComparison(
                price_comparison=PriceComparison(),
                rating_comparison=RatingComparison(),
                review_comparison=ReviewComparison(),
                total_competitors=0,
                data_availability=DataAvailability(
                    main_has_data=False, competitors_with_data=0
                ),
            )

        main_current = main_data.current_data

        # 收集所有競品的有效數據
        valid_competitors = [
            c
            for c in competitor_data
            if c.current_data
            and (
                c.current_data.price is not None
                or c.current_data.rating is not None
                or c.current_data.review_count is not None
            )
        ]

        if not valid_competitors:
            return BasicComparison(
                price_comparison=PriceComparison(),
                rating_comparison=RatingComparison(),
                review_comparison=ReviewComparison(),
                total_competitors=0,
                data_availability=DataAvailability(
                    main_has_data=bool(main_current), competitors_with_data=0
                ),
            )

        # 價格比較
        main_price = main_current.price if main_current else None
        competitor_prices = [
            c.current_data.price
            for c in valid_competitors
            if c.current_data.price is not None
        ]

        price_comparison = PriceComparison(
            main_price=main_price,
            competitor_prices=competitor_prices,
            min_competitor_price=min(competitor_prices) if competitor_prices else None,
            max_competitor_price=max(competitor_prices) if competitor_prices else None,
            avg_competitor_price=(
                sum(competitor_prices) / len(competitor_prices)
                if competitor_prices
                else None
            ),
        )

        # 評分比較
        main_rating = main_current.rating if main_current else None
        competitor_ratings = [
            c.current_data.rating
            for c in valid_competitors
            if c.current_data.rating is not None
        ]

        rating_comparison = RatingComparison(
            main_rating=main_rating,
            competitor_ratings=competitor_ratings,
            min_competitor_rating=(
                min(competitor_ratings) if competitor_ratings else None
            ),
            max_competitor_rating=(
                max(competitor_ratings) if competitor_ratings else None
            ),
            avg_competitor_rating=(
                sum(competitor_ratings) / len(competitor_ratings)
                if competitor_ratings
                else None
            ),
        )

        # 評論數比較
        main_reviews = main_current.review_count if main_current else None
        competitor_reviews = [
            c.current_data.review_count
            for c in valid_competitors
            if c.current_data.review_count is not None
        ]

        review_comparison = ReviewComparison(
            main_review_count=main_reviews,
            competitor_review_counts=competitor_reviews,
            min_competitor_reviews=(
                min(competitor_reviews) if competitor_reviews else None
            ),
            max_competitor_reviews=(
                max(competitor_reviews) if competitor_reviews else None
            ),
            avg_competitor_reviews=(
                sum(competitor_reviews) / len(competitor_reviews)
                if competitor_reviews
                else None
            ),
        )

        return BasicComparison(
            price_comparison=price_comparison,
            rating_comparison=rating_comparison,
            review_comparison=review_comparison,
            total_competitors=len(valid_competitors),
            data_availability=DataAvailability(
                main_has_data=bool(main_current),
                competitors_with_data=len(valid_competitors),
            ),
        )

    async def _get_products_info(self, asins: List[str]) -> Dict[str, Product]:
        """獲取產品基本資訊"""
        try:
            products = get_products_by_asins(asins)
            return {product.asin: product for product in products}
        except Exception as e:
            logger.warning(f"獲取產品資訊失敗: {str(e)}", exc_info=True)
            return {}

    async def _get_latest_snapshots(
        self, asins: List[str]
    ) -> Dict[str, ProductSnapshotDict]:
        """獲取最新快照"""
        try:
            snapshots = {}
            for asin in asins:
                snapshot = get_latest_snapshot(asin)
                if snapshot:
                    snapshots[asin] = snapshot
            return snapshots
        except Exception as e:
            logger.warning(f"獲取最新快照失敗: {str(e)}", exc_info=True)
            return {}

    async def _get_historical_snapshots(
        self, asins: List[str], window_size: int
    ) -> Dict[str, List[ProductSnapshotDict]]:
        """獲取歷史快照"""
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=window_size)

            # 按 ASIN 分組獲取歷史快照
            grouped_snapshots = {}
            for asin in asins:
                snapshots = get_snapshots_by_date_range(asin, start_date, end_date)
                if snapshots:
                    grouped_snapshots[asin] = snapshots

            return grouped_snapshots
        except Exception as e:
            logger.warning(f"獲取歷史快照失敗: {str(e)}", exc_info=True)
            return {}


# 測試函數
def test_competitor_analyzer():
    """測試競品分析器功能 - 簡化版本"""
    logger.info("開始測試競品分析器...")

    try:
        analyzer = CompetitorAnalyzer()

        # 測試參數
        test_parameters = {
            "main_asin": "B01LP0U5X0",
            "competitor_asins": ["B092XTMNCC", "B0DG3X1D7B"],
            "window_size": 7,
        }

        # 測試資料收集
        logger.info("測試資料收集...")
        product_data = asyncio.run(analyzer.collect_product_data(test_parameters))
        logger.info(f"資料收集完成，主產品: {product_data['main_product']['asin']}")
        logger.info(f"競品數量: {len(product_data['competitors'])}")

        # 測試競品分析
        logger.info("測試競品分析...")
        analysis_result = asyncio.run(
            analyzer.analyze_competitors(
                product_data["main_product"], product_data["competitors"]
            )
        )

        logger.info("分析結果:")
        logger.info(
            f"- 主產品: {analysis_result['main_product_data']['basic_info']['title']}"
        )
        logger.info(f"- 競品數量: {len(analysis_result['competitor_data'])}")
        logger.info(
            f"- 有效競品: {analysis_result['basic_comparison'].get('total_competitors', 0)}"
        )

        # 顯示基本比較數據
        price_comp = analysis_result["basic_comparison"].get("price_comparison", {})
        if price_comp.get("main_price"):
            logger.info(f"- 主產品價格: ${price_comp['main_price']}")
            if price_comp.get("avg_competitor_price"):
                logger.info(
                    f"- 競品平均價格: ${price_comp['avg_competitor_price']:.2f}"
                )

        logger.info("競品分析器測試完成！")

    except Exception as e:
        logger.error(f"測試失敗: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    test_competitor_analyzer()
