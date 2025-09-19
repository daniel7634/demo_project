"""
競品分析器模組
提供競品分析、LLM 報告生成和提示詞模板功能
"""

from .analyzer_types import (
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
from .competitor_analyzer import CompetitorAnalyzer
from .llm_report_generator import LLMReportGenerator
from .prompt_templates import PromptTemplate

__all__ = [
    "CompetitorAnalyzer",
    "LLMReportGenerator",
    "PromptTemplate",
    "ProductAnalysisData",
    "CompetitorAnalysisData",
    "CompetitorAnalysisMetadata",
    "ProductBasicInfo",
    "ProductCurrentData",
    "ExtractedProductData",
    "PriceComparison",
    "RatingComparison",
    "ReviewComparison",
    "DataAvailability",
    "BasicComparison",
    "CompetitorAnalysisResult",
]
