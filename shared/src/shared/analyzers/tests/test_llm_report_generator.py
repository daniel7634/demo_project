#!/usr/bin/env python3
"""
llm_report_generator.py 的基本測試
測試 LLMReportGenerator 類別的基本功能
"""

import os
from unittest.mock import Mock, patch

import pytest
from shared.analyzers.llm_report_generator import LLMReportGenerator


def test_llm_report_generator_initialization():
    """測試 LLMReportGenerator 初始化"""
    # 設定測試環境變數
    os.environ["OPENAI_API_KEY"] = "test_api_key_12345"

    generator = LLMReportGenerator()

    assert generator is not None
    assert generator.api_key == "test_api_key_12345"
    assert generator.model == "gpt-3.5-turbo"
    assert generator.max_tokens == 4000
    assert generator.temperature == 0.7
    assert generator.prompt_template is not None


def test_llm_report_generator_initialization_with_custom_params():
    """測試 LLMReportGenerator 自定義參數初始化"""
    generator = LLMReportGenerator(api_key="custom_api_key", model="gpt-4")

    assert generator.api_key == "custom_api_key"
    assert generator.model == "gpt-4"


def test_llm_report_generator_initialization_no_api_key():
    """測試 LLMReportGenerator 沒有 API 金鑰時拋出異常"""
    # 清除環境變數
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]

    with pytest.raises(ValueError, match="未提供 OpenAI API 金鑰"):
        LLMReportGenerator()


def test_llm_report_generator_initialization_no_openai():
    """測試 LLMReportGenerator 沒有 OpenAI 套件時拋出異常"""
    with patch("shared.analyzers.llm_report_generator.openai", None):
        with pytest.raises(ImportError, match="OpenAI 套件未安裝"):
            LLMReportGenerator(api_key="test_key")


@pytest.fixture
def mock_generator():
    """創建模擬的 LLMReportGenerator 實例"""
    os.environ["OPENAI_API_KEY"] = "test_api_key_12345"
    return LLMReportGenerator()


def test_generate_report_success(mock_generator):
    """測試成功生成報告"""
    # 創建測試用的分析結果
    from shared.analyzers.analyzer_types import (
        BasicComparison,
        CompetitorAnalysisResult,
        DataAvailability,
        ExtractedProductData,
        PriceComparison,
        ProductBasicInfo,
        ProductCurrentData,
        RatingComparison,
        ReviewComparison,
    )

    # 創建主產品資料
    main_basic_info = ProductBasicInfo(
        asin="B08N5WRWNW", title="Test Main Product", categories=["Sports"]
    )

    main_current_data = ProductCurrentData(
        price=29.99, rating=4.5, review_count=150, bsr=1000
    )

    main_product_data = ExtractedProductData(
        basic_info=main_basic_info, current_data=main_current_data
    )

    # 創建競品資料
    competitor_basic_info = ProductBasicInfo(
        asin="B08N5WRWNW2", title="Competitor 1", categories=["Sports"]
    )

    competitor_current_data = ProductCurrentData(
        price=25.99, rating=4.2, review_count=120, bsr=1500
    )

    competitor_product_data = ExtractedProductData(
        basic_info=competitor_basic_info, current_data=competitor_current_data
    )

    # 創建比較資料
    price_comp = PriceComparison(
        main_price=29.99,
        competitor_prices=[25.99],
        min_competitor_price=25.99,
        max_competitor_price=25.99,
        avg_competitor_price=25.99,
    )

    rating_comp = RatingComparison(
        main_rating=4.5,
        competitor_ratings=[4.2],
        min_competitor_rating=4.2,
        max_competitor_rating=4.2,
        avg_competitor_rating=4.2,
    )

    review_comp = ReviewComparison(
        main_review_count=150,
        competitor_review_counts=[120],
        min_competitor_reviews=120,
        max_competitor_reviews=120,
        avg_competitor_reviews=120.0,
    )

    data_avail = DataAvailability(main_has_data=True, competitors_with_data=1)

    basic_comp = BasicComparison(
        price_comparison=price_comp,
        rating_comparison=rating_comp,
        review_comparison=review_comp,
        total_competitors=1,
        data_availability=data_avail,
    )

    analysis_result = CompetitorAnalysisResult(
        main_product_data=main_product_data,
        competitor_data=[competitor_product_data],
        basic_comparison=basic_comp,
    )

    parameters = {"window_size": "7", "focus_areas": "price,rating"}

    # 模擬 OpenAI 回應
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "這是一個測試的競品分析報告內容。"
    mock_response.usage = Mock()
    mock_response.usage.total_tokens = 1000

    with patch.object(
        mock_generator.client.chat.completions, "create", return_value=mock_response
    ):
        result = mock_generator.generate_report(analysis_result, parameters)

        assert result is not None
        assert isinstance(result, str)
        assert "這是一個測試的競品分析報告內容。" in result


def test_generate_report_openai_error(mock_generator):
    """測試 OpenAI API 錯誤處理"""
    from shared.analyzers.analyzer_types import (
        BasicComparison,
        CompetitorAnalysisResult,
        DataAvailability,
        ExtractedProductData,
        PriceComparison,
        ProductBasicInfo,
        ProductCurrentData,
        RatingComparison,
        ReviewComparison,
    )

    # 創建有效的測試資料
    main_basic_info = ProductBasicInfo(
        asin="B08N5WRWNW", title="Test Product", categories=["Sports"]
    )

    main_current_data = ProductCurrentData(price=29.99, rating=4.5, review_count=150)

    main_product_data = ExtractedProductData(
        basic_info=main_basic_info, current_data=main_current_data
    )

    # 創建比較資料
    price_comp = PriceComparison()
    rating_comp = RatingComparison()
    review_comp = ReviewComparison()
    data_avail = DataAvailability(main_has_data=True, competitors_with_data=0)

    basic_comp = BasicComparison(
        price_comparison=price_comp,
        rating_comparison=rating_comp,
        review_comparison=review_comp,
        total_competitors=0,
        data_availability=data_avail,
    )

    analysis_result = CompetitorAnalysisResult(
        main_product_data=main_product_data,
        competitor_data=[],
        basic_comparison=basic_comp,
    )

    parameters = {}

    # 模擬 OpenAI API 錯誤
    with patch.object(
        mock_generator.client.chat.completions,
        "create",
        side_effect=Exception("API 錯誤"),
    ):
        with pytest.raises(Exception, match="API 錯誤"):
            mock_generator.generate_report(analysis_result, parameters)
