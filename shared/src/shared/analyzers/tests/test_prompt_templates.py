#!/usr/bin/env python3
"""
prompt_templates.py 的基本測試
測試 PromptTemplate 類別的基本功能
"""

from shared.analyzers.prompt_templates import PromptTemplate


def test_prompt_template_initialization():
    """測試 PromptTemplate 初始化"""
    template = PromptTemplate()

    assert template is not None
    assert hasattr(template, "templates")
    assert isinstance(template.templates, dict)
    assert "competitor_analysis" in template.templates
    assert "market_analysis" in template.templates


def test_build_competitor_analysis_prompt_basic():
    """測試構建競品分析提示詞 - 基本情況"""
    template = PromptTemplate()

    # 基本測試資料
    analysis_data = {
        "main_product": {
            "asin": "B08N5WRWNW",
            "title": "Test Main Product",
            "price": 29.99,
            "rating": 4.5,
            "review_count": 150,
        },
        "competitors": [
            {
                "asin": "B08N5WRWNW2",
                "title": "Competitor 1",
                "price": 25.99,
                "rating": 4.2,
                "review_count": 120,
            }
        ],
        "comparison_metrics": {
            "price_comparison": {
                "main_price": 29.99,
                "avg_competitor_price": 25.99,
                "min_competitor_price": 20.99,
                "max_competitor_price": 30.99,
                "price_position": "higher",
            },
            "rating_comparison": {
                "main_rating": 4.5,
                "avg_competitor_rating": 4.2,
                "min_competitor_rating": 4.0,
                "max_competitor_rating": 4.7,
                "rating_position": "above_average",
            },
            "total_competitors": 1,
        },
        "analysis_parameters": {"window_size": 7, "focus_areas": ["price", "rating"]},
    }

    prompt = template.build_competitor_analysis_prompt(analysis_data)

    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "B08N5WRWNW" in prompt  # 主產品 ASIN
    assert "Test Main Product" in prompt  # 主產品標題
    assert "B08N5WRWNW2" in prompt  # 競品 ASIN
    assert "Competitor 1" in prompt  # 競品標題


def test_build_competitor_analysis_prompt_empty_data():
    """測試構建競品分析提示詞 - 空資料"""
    template = PromptTemplate()

    # 空資料測試
    analysis_data = {}

    prompt = template.build_competitor_analysis_prompt(analysis_data)

    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_build_competitor_analysis_prompt_missing_competitors():
    """測試構建競品分析提示詞 - 缺少競品資料"""
    template = PromptTemplate()

    analysis_data = {
        "main_product": {"asin": "B08N5WRWNW", "title": "Test Main Product"},
        "competitors": [],
        "comparison_metrics": {},
        "analysis_parameters": {},
    }

    prompt = template.build_competitor_analysis_prompt(analysis_data)

    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "B08N5WRWNW" in prompt


def test_format_product_info():
    """測試格式化產品資訊"""
    template = PromptTemplate()

    product_data = {
        "asin": "B08N5WRWNW",
        "title": "Test Product",
        "price": 29.99,
        "rating": 4.5,
        "review_count": 150,
    }

    formatted_info = template._format_product_info(product_data, "主產品")

    assert isinstance(formatted_info, str)
    assert "主產品" in formatted_info
    assert "B08N5WRWNW" in formatted_info
    assert "Test Product" in formatted_info


def test_format_competitors_info():
    """測試格式化競品資訊"""
    template = PromptTemplate()

    competitors_data = [
        {"asin": "B08N5WRWNW2", "title": "Competitor 1", "price": 25.99, "rating": 4.2},
        {"asin": "B08N5WRWNW3", "title": "Competitor 2", "price": 32.99, "rating": 4.7},
    ]

    formatted_info = template._format_competitors_info(competitors_data)

    assert isinstance(formatted_info, str)
    assert "B08N5WRWNW2" in formatted_info
    assert "Competitor 1" in formatted_info
    assert "B08N5WRWNW3" in formatted_info
    assert "Competitor 2" in formatted_info


def test_format_competitors_info_empty():
    """測試格式化競品資訊 - 空列表"""
    template = PromptTemplate()

    competitors_data = []

    formatted_info = template._format_competitors_info(competitors_data)

    assert isinstance(formatted_info, str)
    assert len(formatted_info) > 0


def test_format_comparison_info():
    """測試格式化比較資訊"""
    template = PromptTemplate()

    comparison_metrics = {
        "price_comparison": {
            "main_price": 29.99,
            "avg_competitor_price": 25.99,
            "min_competitor_price": 20.99,
            "max_competitor_price": 30.99,
            "price_position": "higher",
        },
        "rating_comparison": {
            "main_rating": 4.5,
            "avg_competitor_rating": 4.2,
            "min_competitor_rating": 4.0,
            "max_competitor_rating": 4.7,
            "rating_position": "above_average",
        },
        "review_comparison": {
            "main_reviews": 150,
            "avg_competitor_reviews": 120,
            "min_competitor_reviews": 80,
            "max_competitor_reviews": 200,
            "review_position": "moderate",
        },
        "total_competitors": 3,
    }

    formatted_info = template._format_comparison_info(comparison_metrics)

    assert isinstance(formatted_info, str)
    assert "29.99" in formatted_info
    assert "4.5" in formatted_info
    assert "150" in formatted_info


def test_format_parameters_info():
    """測試格式化參數資訊"""
    template = PromptTemplate()

    parameters = {
        "window_size": 7,
        "analysis_date": "2024-01-01",
        "total_products": 5,
        "competitor_count": 4,
    }

    formatted_info = template._format_parameters_info(parameters)

    assert isinstance(formatted_info, str)
    assert "7" in formatted_info  # window_size
    assert "2024-01-01" in formatted_info  # analysis_date
    assert "5" in formatted_info  # total_products
    assert "4" in formatted_info  # competitor_count


def test_get_competitor_analysis_template():
    """測試獲取競品分析模板"""
    template = PromptTemplate()

    competitor_template = template._get_competitor_analysis_template()

    assert isinstance(competitor_template, str)
    assert len(competitor_template) > 0
    assert (
        "競品分析" in competitor_template or "competitor" in competitor_template.lower()
    )


def test_get_market_analysis_template():
    """測試獲取市場分析模板"""
    template = PromptTemplate()

    market_template = template._get_market_analysis_template()

    assert isinstance(market_template, str)
    assert len(market_template) > 0
    assert "市場分析" in market_template or "market" in market_template.lower()
