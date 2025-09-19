"""
Supabase 客戶端測試
"""

import unittest
from unittest.mock import MagicMock, patch

from shared.database.supabase_client import (
    SupabaseConfig,
    get_supabase_client,
    test_connection,
)


class TestSupabaseClient(unittest.TestCase):
    """Supabase 客戶端測試類"""

    def setUp(self):
        """測試前準備"""
        self.original_url = SupabaseConfig.SUPABASE_URL
        self.original_key = SupabaseConfig.SUPABASE_KEY

    def tearDown(self):
        """測試後清理"""
        SupabaseConfig.SUPABASE_URL = self.original_url
        SupabaseConfig.SUPABASE_KEY = self.original_key

    def test_validate_config_success(self):
        """測試配置驗證成功"""
        SupabaseConfig.SUPABASE_URL = "https://test.supabase.co"
        SupabaseConfig.SUPABASE_KEY = "test_key"

        self.assertTrue(SupabaseConfig.validate_config())

    def test_validate_config_missing_url(self):
        """測試配置驗證失敗 - 缺少 URL"""
        SupabaseConfig.SUPABASE_URL = None
        SupabaseConfig.SUPABASE_KEY = "test_key"

        self.assertFalse(SupabaseConfig.validate_config())

    def test_validate_config_missing_key(self):
        """測試配置驗證失敗 - 缺少 KEY"""
        SupabaseConfig.SUPABASE_URL = "https://test.supabase.co"
        SupabaseConfig.SUPABASE_KEY = None

        self.assertFalse(SupabaseConfig.validate_config())

    @patch("shared.database.supabase_client.create_client")
    def test_get_supabase_client_success(self, mock_create_client):
        """測試獲取 Supabase 客戶端成功"""
        SupabaseConfig.SUPABASE_URL = "https://test.supabase.co"
        SupabaseConfig.SUPABASE_KEY = "test_key"

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        client = get_supabase_client()

        self.assertIsNotNone(client)
        mock_create_client.assert_called_once_with(
            "https://test.supabase.co", "test_key"
        )

    def test_get_supabase_client_config_invalid(self):
        """測試獲取 Supabase 客戶端失敗 - 配置無效"""
        SupabaseConfig.SUPABASE_URL = None
        SupabaseConfig.SUPABASE_KEY = None

        client = get_supabase_client()

        self.assertIsNone(client)

    @patch("shared.database.supabase_client.get_supabase_client")
    def test_test_connection_success(self, mock_get_client):
        """測試連接測試成功"""
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": 1}]
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = (
            mock_result
        )
        mock_get_client.return_value = mock_client

        result = test_connection()

        self.assertTrue(result)

    @patch("shared.database.supabase_client.get_supabase_client")
    def test_test_connection_failure(self, mock_get_client):
        """測試連接測試失敗"""
        mock_get_client.return_value = None

        result = test_connection()

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
