#!/usr/bin/env python3
"""
Amazon 資料收集器測試腳本
使用 pytest 測試 AmazonDataCollector 的 get_product_details 方法
"""

import os
from unittest.mock import AsyncMock, patch

import pytest

# 設定測試環境變量
os.environ["APIFY_API_TOKEN"] = "test_token_12345"


def test_apify_client_import():
    """測試 apify-client 包導入"""
    from apify_client import ApifyClient

    assert ApifyClient is not None


def test_amazon_data_collector_import():
    """測試 AmazonDataCollector 導入"""
    from shared.collectors.amazon_data_collector import AmazonDataCollector

    assert AmazonDataCollector is not None


def test_amazon_data_collector_init():
    """測試 AmazonDataCollector 初始化"""
    from shared.collectors.amazon_data_collector import AmazonDataCollector

    collector = AmazonDataCollector()
    assert collector is not None
    assert len(collector.api_token) > 0
    assert collector.PRODUCT_DETAILS_ACTOR is not None


@pytest.fixture
def collector():
    """創建 AmazonDataCollector 實例"""
    from shared.collectors.amazon_data_collector import AmazonDataCollector

    return AmazonDataCollector()


@pytest.mark.asyncio
async def test_get_product_details_success(collector):
    """測試成功啟動產品抓取任務"""
    mock_run_result = {
        "id": "test_run_123",
        "status": "RUNNING",
        "startedAt": "2024-01-01T00:00:00Z",
    }

    with patch.object(collector.client, "actor") as mock_actor:
        # 配置異步 mock
        mock_actor_instance = AsyncMock()
        mock_actor_instance.start = AsyncMock(return_value=mock_run_result)
        mock_actor.return_value = mock_actor_instance

        result = await collector.get_product_details(["B08N5WRWNW", "B08N5WRWNW2"])

        # 驗證返回結果
        assert result["status"] == "started"
        assert result["message"] == "Amazon 產品抓取任務已啟動，結果將通過 webhook 接收"
        assert result["run_id"] == "test_run_123"
        assert result["asins"] == ["B08N5WRWNW", "B08N5WRWNW2"]
        assert "webhook_url" in result
        assert "started_at" in result

        # 驗證 Actor 調用參數
        mock_actor_instance.start.assert_called_once()
        call_args = mock_actor_instance.start.call_args[1]
        assert "run_input" in call_args
        assert "webhooks" in call_args
        assert call_args["run_input"]["urls"] == [
            "https://www.amazon.com/dp/B08N5WRWNW",
            "https://www.amazon.com/dp/B08N5WRWNW2",
        ]
        assert call_args["run_input"]["language"] == "zh-TW"


@pytest.mark.asyncio
async def test_get_product_details_actor_failed(collector):
    """測試 Actor 執行失敗的情況"""
    with patch.object(collector.client, "actor") as mock_actor:
        # 配置異步 mock 拋出異常
        mock_actor_instance = AsyncMock()
        mock_actor_instance.start = AsyncMock(side_effect=Exception("Actor 啟動失敗"))
        mock_actor.return_value = mock_actor_instance

        result = await collector.get_product_details(["B08N5WRWNW"])

        # 驗證錯誤返回結果
        assert result["status"] == "error"
        assert "啟動任務失敗" in result["message"]
        assert result["asins"] == ["B08N5WRWNW"]


@pytest.mark.asyncio
async def test_get_product_details_exception(collector):
    """測試異常處理"""
    with patch.object(collector.client, "actor") as mock_actor:
        # 配置異步 mock 拋出異常
        mock_actor_instance = AsyncMock()
        mock_actor_instance.start = AsyncMock(side_effect=Exception("網路連接錯誤"))
        mock_actor.return_value = mock_actor_instance

        result = await collector.get_product_details(["B08N5WRWNW"])

        # 驗證錯誤返回結果
        assert result["status"] == "error"
        assert "網路連接錯誤" in result["message"]
        assert result["asins"] == ["B08N5WRWNW"]


@pytest.mark.asyncio
async def test_get_product_details_success_single_asin(collector):
    """測試成功啟動單一產品抓取任務"""
    mock_run_result = {
        "id": "test_run_456",
        "status": "RUNNING",
        "startedAt": "2024-01-01T00:00:00Z",
    }

    with patch.object(collector.client, "actor") as mock_actor:
        # 配置異步 mock
        mock_actor_instance = AsyncMock()
        mock_actor_instance.start = AsyncMock(return_value=mock_run_result)
        mock_actor.return_value = mock_actor_instance

        result = await collector.get_product_details(["B08N5WRWNW"])

        # 驗證返回結果
        assert result["status"] == "started"
        assert result["run_id"] == "test_run_456"
        assert result["asins"] == ["B08N5WRWNW"]
        assert "webhook_url" in result


@pytest.mark.asyncio
async def test_get_product_details_empty_asin_list(collector):
    """測試空 ASIN 列表的情況"""
    result = await collector.get_product_details([])

    # 驗證空 ASIN 列表的錯誤返回結果
    assert result["status"] == "error"
    assert result["message"] == "ASIN 列表為空"
