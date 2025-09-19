"""
Celery 應用程式配置
使用共享的 Celery 配置模組
"""

from shared.celery.celery_config import get_celery_app

# 獲取 Celery 應用程式實例
app = get_celery_app("celery_service")

# 定義佇列
app.conf.task_default_queue = "amazon_queue"

if __name__ == "__main__":
    app.start()
