"""
配置模組
負責讀取和管理環境變量配置
"""

import logging
import os

# 設定日誌
logger = logging.getLogger(__name__)


class Config:
    """配置管理類"""

    # Apify 配置
    APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

    # Redis 配置
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Supabase 配置
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def get_apify_token() -> str:
    """
    從環境變量中讀取 Apify API Token

    Returns:
        Apify API Token

    Raises:
        ValueError: 當環境變量未設定時
    """
    token = Config.APIFY_API_TOKEN
    if not token:
        raise ValueError(
            "APIFY_API_TOKEN 環境變量未設定。請在 .env 文件中設定 APIFY_API_TOKEN=your_token_here"
        )
    return token


def validate_required_config() -> bool:
    """
    驗證必要的配置是否已設定

    Returns:
        是否所有必要配置都已設定
    """
    required_configs = [
        ("APIFY_API_TOKEN", Config.APIFY_API_TOKEN),
    ]

    missing_configs = []
    for name, value in required_configs:
        if not value:
            missing_configs.append(name)

    if missing_configs:
        logger.error(f"缺少必要的環境變量配置: {', '.join(missing_configs)}")
        logger.error("請檢查 .env 文件是否正確設定")
        return False

    return True


def print_config_summary():
    """打印配置摘要（隱藏敏感信息）"""
    print("\n" + "=" * 50)
    print("配置摘要")
    print("=" * 50)

    # 顯示配置狀態
    print(f"Apify API Token: {'已設定' if Config.APIFY_API_TOKEN else '未設定'}")
    print(f"Redis URL: {Config.REDIS_URL}")
    print(f"Supabase URL: {'已設定' if Config.SUPABASE_URL else '未設定'}")
    print(f"Supabase Key: {'已設定' if Config.SUPABASE_KEY else '未設定'}")
    print("=" * 50)


# 使用範例
if __name__ == "__main__":
    print_config_summary()

    if validate_required_config():
        print("\n✅ 所有必要配置都已正確設定")
    else:
        print("\n❌ 配置驗證失敗，請檢查環境變量設定")
