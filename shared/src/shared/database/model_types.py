"""
資料庫相關的 Type Classes 定義
提供所有資料庫操作中使用的類型定義
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union


@dataclass
class BSRData:
    """BSR 排名資料"""

    rank: int
    category: str
    raw_value: str


@dataclass
class ProductSnapshot:
    """產品快照資料"""

    asin: str
    snapshot_date: date
    price: Optional[Decimal] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    bsr_data: List[BSRData] = None
    raw_data: Dict[str, Any] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.bsr_data is None:
            self.bsr_data = []
        if self.raw_data is None:
            self.raw_data = {}


@dataclass
class ProductSnapshotDict:
    """產品快照字典格式（用於資料庫操作）"""

    asin: str
    snapshot_date: str  # ISO 格式字串
    price: Optional[float] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    bsr_data: List[Dict[str, Any]] = None
    raw_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.bsr_data is None:
            self.bsr_data = []
        if self.raw_data is None:
            self.raw_data = {}


@dataclass
class Product:
    """產品基本資訊"""

    asin: str
    title: Optional[str] = None
    categories: List[str] = None

    def __post_init__(self):
        if self.categories is None:
            self.categories = []


@dataclass
class ASINStatus:
    """ASIN 狀態"""

    id: Optional[int] = None
    asin: str = ""
    status: str = "pending"  # pending, running, completed, failed
    task_timestamp: Optional[datetime] = None
    retry_count: int = 0
    created_at: Optional[datetime] = None


@dataclass
class AlertRule:
    """告警規則"""

    id: Optional[str] = None
    rule_name: str = ""
    rule_type: str = ""  # price_change, bsr_change, rating_change
    change_direction: str = ""  # increase, decrease, any
    threshold: Optional[Decimal] = None
    threshold_type: str = ""  # percentage, absolute
    is_active: bool = True
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Alert:
    """告警記錄"""

    id: Optional[str] = None
    asin: str = ""
    rule_id: str = ""
    message: str = ""
    previous_value: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    snapshot_date: Optional[date] = None
    created_at: Optional[datetime] = None


@dataclass
class ReportJob:
    """報告任務"""

    id: Optional[str] = None
    job_type: str = "competitor_analysis"
    parameters: Dict[str, Any] = None
    parameters_hash: str = ""
    status: str = "pending"  # pending, running, completed, failed
    result_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class ReportResult:
    """報告結果"""

    id: Optional[str] = None
    job_id: str = ""
    report_type: str = "competitor_analysis"
    content: str = ""
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# 類型別名
SnapshotData = Union[ProductSnapshot, ProductSnapshotDict, Dict[str, Any]]
SnapshotList = List[SnapshotData]
ProductList = List[Product]
ASINList = List[str]
AlertRuleList = List[AlertRule]
AlertList = List[Alert]
ReportJobList = List[ReportJob]
ReportResultList = List[ReportResult]

# 查詢結果類型
QueryResult = Union[
    SnapshotData,
    SnapshotList,
    ProductList,
    ASINList,
    AlertRuleList,
    AlertList,
    ReportJobList,
    ReportResultList,
    bool,
    None,
]
