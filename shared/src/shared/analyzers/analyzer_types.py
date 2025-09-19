"""
分析器相關的 Type Classes 定義
提供所有分析器操作中使用的類型定義
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from shared.database.model_types import Product, ProductSnapshotDict


@dataclass
class ProductAnalysisData:
    """產品分析資料"""

    asin: str
    info: Product
    latest_snapshot: Optional[ProductSnapshotDict] = None
    historical_snapshots: List[ProductSnapshotDict] = None
    collected_at: Optional[str] = None

    def __post_init__(self):
        if self.historical_snapshots is None:
            self.historical_snapshots = []


@dataclass
class CompetitorAnalysisMetadata:
    """競品分析元資料"""

    window_size: int
    analysis_date: str
    total_products: int
    competitor_count: int


@dataclass
class CompetitorAnalysisData:
    """競品分析資料"""

    main_product: ProductAnalysisData
    competitors: List[ProductAnalysisData]
    analysis_metadata: CompetitorAnalysisMetadata


@dataclass
class ProductBasicInfo:
    """產品基本資訊（用於分析）"""

    asin: str
    title: Optional[str] = None
    categories: List[str] = None

    def __post_init__(self):
        if self.categories is None:
            self.categories = []


@dataclass
class ProductCurrentData:
    """產品當前數據（用於分析）"""

    price: Optional[float] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    bsr: Optional[int] = None
    bsr_details: List[Dict[str, Any]] = None
    snapshot_date: Optional[str] = None

    def __post_init__(self):
        if self.bsr_details is None:
            self.bsr_details = []


@dataclass
class ExtractedProductData:
    """提取的產品數據"""

    basic_info: ProductBasicInfo
    current_data: ProductCurrentData


@dataclass
class PriceComparison:
    """價格比較數據"""

    main_price: Optional[float] = None
    competitor_prices: List[Optional[float]] = None
    min_competitor_price: Optional[float] = None
    max_competitor_price: Optional[float] = None
    avg_competitor_price: Optional[float] = None

    def __post_init__(self):
        if self.competitor_prices is None:
            self.competitor_prices = []


@dataclass
class RatingComparison:
    """評分比較數據"""

    main_rating: Optional[float] = None
    competitor_ratings: List[Optional[float]] = None
    min_competitor_rating: Optional[float] = None
    max_competitor_rating: Optional[float] = None
    avg_competitor_rating: Optional[float] = None

    def __post_init__(self):
        if self.competitor_ratings is None:
            self.competitor_ratings = []


@dataclass
class ReviewComparison:
    """評論數比較數據"""

    main_review_count: Optional[int] = None
    competitor_review_counts: List[Optional[int]] = None
    min_competitor_reviews: Optional[int] = None
    max_competitor_reviews: Optional[int] = None
    avg_competitor_reviews: Optional[float] = None

    def __post_init__(self):
        if self.competitor_review_counts is None:
            self.competitor_review_counts = []


@dataclass
class DataAvailability:
    """數據可用性"""

    main_has_data: bool
    competitors_with_data: int


@dataclass
class BasicComparison:
    """基本比較結果"""

    price_comparison: PriceComparison
    rating_comparison: RatingComparison
    review_comparison: ReviewComparison
    total_competitors: int
    data_availability: DataAvailability


@dataclass
class CompetitorAnalysisResult:
    """競品分析結果"""

    main_product_data: ExtractedProductData
    competitor_data: List[ExtractedProductData]
    basic_comparison: BasicComparison


# 類型別名
ProductAnalysisDataList = List[ProductAnalysisData]
ExtractedProductDataList = List[ExtractedProductData]
