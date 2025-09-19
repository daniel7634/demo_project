"""
Supabase 客戶端
提供資料庫連接和基本操作
"""

import logging
import os
from typing import Optional

from supabase import Client, create_client

logger = logging.getLogger(__name__)

# 全域變數儲存客戶端實例
_supabase_client: Optional[Client] = None


class SupabaseConfig:
    """Supabase 配置類"""

    # Supabase 配置
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    @classmethod
    def validate_config(cls) -> bool:
        """驗證 Supabase 配置是否完整"""
        if not cls.SUPABASE_URL:
            logger.error("SUPABASE_URL 環境變量未設定")
            return False
        if not cls.SUPABASE_KEY:
            logger.error("SUPABASE_KEY 環境變量未設定")
            return False
        return True


def get_supabase_client() -> Optional[Client]:
    """
    獲取 Supabase 客戶端實例（單例模式）

    Returns:
        Supabase 客戶端實例，如果配置無效則返回 None
    """
    global _supabase_client

    # 如果已經有客戶端實例，直接返回
    if _supabase_client is not None:
        return _supabase_client

    # 驗證配置
    if not SupabaseConfig.validate_config():
        logger.error("Supabase 配置驗證失敗")
        return None

    try:
        # 創建新的客戶端實例
        _supabase_client = create_client(
            SupabaseConfig.SUPABASE_URL, SupabaseConfig.SUPABASE_KEY
        )
        logger.info("Supabase 客戶端初始化成功")
        return _supabase_client
    except Exception as e:
        logger.error(f"Supabase 客戶端初始化失敗: {e}")
        return None


def test_connection() -> bool:
    """
    測試 Supabase 連接

    Returns:
        連接是否成功
    """
    client = get_supabase_client()
    if not client:
        return False

    try:
        # 簡單的查詢測試
        client.table("asin_status").select("id").limit(1).execute()
        logger.info("Supabase 連接測試成功")
        return True
    except Exception as e:
        logger.error(f"Supabase 連接測試失敗: {e}")
        return False


# 使用範例
if __name__ == "__main__":
    # 測試連接
    if test_connection():
        print("✅ Supabase 連接成功")
    else:
        print("❌ Supabase 連接失敗")
