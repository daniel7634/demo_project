"""
Celery 配置模組
使用單例模式提供統一的 Celery 配置和實例管理
"""

import os
from typing import Any, Dict, Optional

from celery import Celery
from celery.schedules import crontab


class CelerySingleton:
    """Celery 單例類別"""

    _instance: Optional["CelerySingleton"] = None
    _app: Optional[Celery] = None

    def __new__(cls) -> "CelerySingleton":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_app(self, app_name: str = "default", **overrides) -> Celery:
        """
        獲取 Celery 應用程式實例

        Args:
            app_name: 應用程式名稱
            **overrides: 覆蓋的配置選項

        Returns:
            Celery 應用程式實例
        """
        if self._app is None:
            self._app = self._create_app(app_name, **overrides)
        return self._app

    def _create_app(self, app_name: str, **overrides) -> Celery:
        """創建 Celery 應用程式"""
        # 從環境變數獲取 Redis URL，預設為本地 Redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # 創建 Celery 應用程式
        app = Celery(app_name, broker=redis_url, backend=redis_url)

        # 基礎配置
        base_config = {
            # 任務序列化
            "task_serializer": "json",
            "accept_content": ["json"],
            "result_serializer": "json",
            # 時區設定
            "timezone": "UTC",
            "enable_utc": True,
        }

        # 應用程式特定配置
        app_specific_config = self._get_app_specific_config(app_name)

        # 合併配置
        final_config = {**base_config, **app_specific_config, **overrides}
        app.conf.update(final_config)

        return app

    def _get_app_specific_config(self, app_name: str) -> Dict[str, Any]:
        """獲取應用程式特定配置"""
        if app_name == "api_service":
            return {
                # API 服務不需要包含任務模組
                "include": [],
            }
        elif app_name == "celery_service":
            return {
                # Celery 服務包含所有任務模組
                "include": ["tasks.amazon_tasks", "tasks.report_tasks"],
                # 任務路由
                "task_routes": {
                    "tasks.amazon_tasks.*": {"queue": "amazon_queue"},
                    "tasks.report_tasks.*": {"queue": "report_queue"},
                },
                # Beat 排程設定
                "beat_schedule": {
                    "schedule-amazon-scraping": {
                        "task": "tasks.amazon_tasks.schedule_amazon_scraping",
                        "schedule": crontab(minute="*/2"),  # 每2分鐘執行一次
                    },
                    "cleanup-old-reports": {
                        "task": "tasks.report_tasks.cleanup_old_reports",
                        "schedule": crontab(hour=2, minute=0),  # 每天凌晨2點執行
                    },
                    "monitor-report-health": {
                        "task": "tasks.report_tasks.monitor_report_health",
                        "schedule": crontab(minute="*/10"),  # 每10分鐘執行一次
                    },
                },
            }
        else:
            return {}

    def reset(self) -> None:
        """重置單例狀態（主要用於測試）"""
        self._instance = None
        self._app = None

    @classmethod
    def get_instance(cls) -> "CelerySingleton":
        """獲取單例實例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


# 全域單例實例
celery_singleton = CelerySingleton()


def get_celery_app(app_name: str = "default", **overrides) -> Celery:
    """
    便捷函數：獲取 Celery 應用程式實例

    Args:
        app_name: 應用程式名稱
        **overrides: 覆蓋的配置選項

    Returns:
        Celery 應用程式實例
    """
    return celery_singleton.get_app(app_name, **overrides)


def reset_celery_singleton() -> None:
    """重置 Celery 單例（主要用於測試）"""
    celery_singleton.reset()


# 測試函數
def test_celery_config():
    """測試 Celery 配置"""
    print("🧪 測試 Celery 配置")
    print("=" * 50)

    try:
        # 測試 API 服務配置
        api_app = get_celery_app("api_service")
        print(f"✅ API 服務 Celery 應用程式創建成功: {api_app.main}")

        # 測試 Celery 服務配置
        celery_app = get_celery_app("celery_service")
        print(f"✅ Celery 服務應用程式創建成功: {celery_app.main}")

        # 測試單例行為
        api_app2 = get_celery_app("api_service")
        print(f"✅ 單例測試: {api_app is api_app2}")

        # 測試配置
        print(f"✅ API 服務配置: {api_app.conf.broker_url}")
        print(f"✅ Celery 服務配置: {celery_app.conf.broker_url}")

        return True

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False


if __name__ == "__main__":
    test_celery_config()
