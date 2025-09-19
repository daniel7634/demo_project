#!/usr/bin/env python3
"""
competitor_analyzer.py 的基本測試
測試 CompetitorAnalyzer 類別的基本功能
"""

from unittest.mock import patch

import pytest
from shared.analyzers.analyzer_types import (
    CompetitorAnalysisData,
    CompetitorAnalysisMetadata,
    CompetitorAnalysisResult,
    ExtractedProductData,
    ProductAnalysisData,
    ProductBasicInfo,
    ProductCurrentData,
)
from shared.analyzers.competitor_analyzer import CompetitorAnalyzer
from shared.database.model_types import Product, ProductSnapshotDict


@pytest.fixture
def mock_analyzer():
    """創建模擬的 CompetitorAnalyzer 實例"""
    return CompetitorAnalyzer()


def test_competitor_analyzer_initialization(mock_analyzer):
    """測試 CompetitorAnalyzer 初始化"""
    assert mock_analyzer is not None
    assert hasattr(mock_analyzer, "analysis_cache")
    assert hasattr(mock_analyzer, "alert_rules")
    assert mock_analyzer.analysis_cache == {}
    assert mock_analyzer.alert_rules is None


@pytest.mark.asyncio
async def test_collect_product_data_success(mock_analyzer):
    """測試成功收集產品資料"""
    asin = "B08N5WRWNW"

    # 模擬產品資料
    mock_product = Product(
        asin=asin, title="Test Product", categories=["Sports", "Fitness"]
    )

    mock_snapshot = ProductSnapshotDict(
        asin=asin, snapshot_date="2024-01-01", price=29.99, rating=4.5, review_count=150
    )

    # 模擬資料庫查詢
    with patch.object(
        mock_analyzer, "_get_products_info", return_value={asin: mock_product}
    ) as mock_get_products:
        with patch.object(
            mock_analyzer, "_get_latest_snapshots", return_value={asin: mock_snapshot}
        ) as mock_get_snapshot:
            with patch.object(
                mock_analyzer,
                "_get_historical_snapshots",
                return_value={asin: [mock_snapshot]},
            ) as mock_get_historical:

                result = await mock_analyzer.collect_product_data(asin)

                assert isinstance(result, ProductAnalysisData)
                assert result.asin == asin
                assert result.info == mock_product
                assert result.latest_snapshot == mock_snapshot
                assert len(result.historical_snapshots) == 1

                mock_get_products.assert_called_once_with([asin])
                mock_get_snapshot.assert_called_once_with([asin])
                mock_get_historical.assert_called_once_with([asin], 7)


@pytest.mark.asyncio
async def test_collect_product_data_empty_asin(mock_analyzer):
    """測試空 ASIN 的處理"""
    with pytest.raises(ValueError, match="缺少產品 ASIN"):
        await mock_analyzer.collect_product_data("")


@pytest.mark.asyncio
async def test_collect_product_data_none_asin(mock_analyzer):
    """測試 None ASIN 的處理"""
    with pytest.raises(ValueError, match="缺少產品 ASIN"):
        await mock_analyzer.collect_product_data(None)


@pytest.mark.asyncio
async def test_collect_competitor_data_success(mock_analyzer):
    """測試成功收集競品資料"""
    main_asin = "B08N5WRWNW"
    competitor_asins = ["B08N5WRWNW2", "B08N5WRWNW3"]

    # 模擬主產品資料
    mock_main_product = Product(
        asin=main_asin, title="Main Product", categories=["Sports"]
    )

    # 模擬競品資料
    mock_competitor_products = [
        Product(asin=competitor_asins[0], title="Competitor 1", categories=["Sports"]),
        Product(asin=competitor_asins[1], title="Competitor 2", categories=["Sports"]),
    ]

    # 模擬資料庫查詢
    with (
        patch.object(
            mock_analyzer,
            "_get_products_info",
            return_value={
                main_asin: mock_main_product,
                competitor_asins[0]: mock_competitor_products[0],
                competitor_asins[1]: mock_competitor_products[1],
            },
        ),
        patch.object(mock_analyzer, "_get_latest_snapshots", return_value={}),
        patch.object(mock_analyzer, "_get_historical_snapshots", return_value={}),
    ):

        result = await mock_analyzer.collect_competitors_data(
            main_asin, competitor_asins
        )

        assert isinstance(result, CompetitorAnalysisData)
        assert result.main_product.asin == main_asin
        assert len(result.competitors) == 2
        assert result.competitors[0].asin == competitor_asins[0]
        assert result.competitors[1].asin == competitor_asins[1]
        assert isinstance(result.analysis_metadata, CompetitorAnalysisMetadata)
        assert result.analysis_metadata.total_products == 3
        assert result.analysis_metadata.competitor_count == 2


@pytest.mark.asyncio
async def test_collect_competitor_data_empty_competitors(mock_analyzer):
    """測試空競品列表的處理"""
    main_asin = "B08N5WRWNW"
    competitor_asins = []

    mock_main_product = Product(
        asin=main_asin, title="Main Product", categories=["Sports"]
    )

    with (
        patch.object(
            mock_analyzer,
            "_get_products_info",
            return_value={main_asin: mock_main_product},
        ),
        patch.object(mock_analyzer, "_get_latest_snapshots", return_value={}),
        patch.object(mock_analyzer, "_get_historical_snapshots", return_value={}),
    ):

        result = await mock_analyzer.collect_competitors_data(
            main_asin, competitor_asins
        )

        assert isinstance(result, CompetitorAnalysisData)
        assert result.main_product.asin == main_asin
        assert len(result.competitors) == 0
        assert result.analysis_metadata.competitor_count == 0


@pytest.mark.asyncio
async def test_analyze_competitors_success(mock_analyzer):
    """測試成功分析競品"""
    # 創建測試資料
    basic_info = ProductBasicInfo(
        asin="B08N5WRWNW", title="Main Product", categories=["Sports"]
    )

    current_data = ProductCurrentData(
        price=29.99, rating=4.5, review_count=150, bsr=1000
    )

    extracted_data = ExtractedProductData(
        basic_info=basic_info, current_data=current_data
    )

    with patch.object(
        mock_analyzer, "_extract_product_data", return_value=extracted_data
    ):

        result = await mock_analyzer.analyze_competitors("B08N5WRWNW", ["B08N5WRWNW2"])

        assert result is not None
        assert isinstance(result, CompetitorAnalysisResult)
        assert result.main_product_data is not None
        assert len(result.competitor_data) >= 0
        assert result.basic_comparison is not None


def test_extract_product_data_with_snapshot(mock_analyzer):
    """測試從快照提取產品資料"""
    asin = "B08N5WRWNW"
    product = Product(asin=asin, title="Test Product", categories=["Sports", "Fitness"])

    snapshot = ProductSnapshotDict(
        asin=asin, snapshot_date="2024-01-01", price=29.99, rating=4.5, review_count=150
    )

    analysis_data = ProductAnalysisData(
        asin=asin, info=product, latest_snapshot=snapshot
    )

    result = mock_analyzer._extract_product_data(analysis_data)

    assert isinstance(result, ExtractedProductData)
    assert result.basic_info.asin == asin
    assert result.basic_info.title == "Test Product"
    assert result.current_data.price == 29.99
    assert result.current_data.rating == 4.5
    assert result.current_data.review_count == 150
    assert result.basic_info.categories == ["Sports", "Fitness"]


def test_extract_product_data_without_snapshot(mock_analyzer):
    """測試沒有快照時提取產品資料"""
    asin = "B08N5WRWNW"
    product = Product(asin=asin, title="Test Product", categories=["Sports", "Fitness"])

    analysis_data = ProductAnalysisData(asin=asin, info=product, latest_snapshot=None)

    result = mock_analyzer._extract_product_data(analysis_data)

    assert isinstance(result, ExtractedProductData)
    assert result.basic_info.asin == asin
    assert result.basic_info.title == "Test Product"
    assert result.current_data.price is None
    assert result.current_data.rating is None
    assert result.current_data.review_count is None
    assert result.current_data.bsr is None
    assert result.basic_info.categories == ["Sports", "Fitness"]


def test_competitor_analyzer_basic_functionality(mock_analyzer):
    """測試 CompetitorAnalyzer 基本功能"""
    # 測試初始化
    assert mock_analyzer is not None
    assert hasattr(mock_analyzer, "collect_product_data")
    assert hasattr(mock_analyzer, "collect_competitors_data")
    assert hasattr(mock_analyzer, "analyze_competitors")
