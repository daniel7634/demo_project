#!/usr/bin/env python3
"""
Celery Worker 啟動腳本
用於啟動簡單的 Celery Worker 來處理任務
"""

import logging
import os
import sys

from celery_app import app

# 設定 logger
logger = logging.getLogger(__name__)


def start_worker():
    """啟動 Celery Worker"""
    logger.info("=" * 50)
    logger.info("啟動 Celery Worker")
    logger.info("=" * 50)
    logger.info(f"工作目錄: {os.getcwd()}")
    logger.info(f"Redis URL: {os.getenv('REDIS_URL', 'redis://localhost:6379/0')}")
    logger.info("監聽佇列: amazon_queue, report_queue")
    logger.info("=" * 50)
    logger.info("按 Ctrl+C 停止 Worker")
    logger.info("=" * 50)

    # 啟動 worker
    app.worker_main(
        [
            "worker",
            "--loglevel=info",
            "--queues=amazon_queue,report_queue",  # 監聽佇列
            "--concurrency=1",  # 簡單起見，只用一個 worker
            "--hostname=amazon-worker@%h",
        ]
    )


if __name__ == "__main__":
    try:
        start_worker()
    except KeyboardInterrupt:
        logger.info("Worker 已停止")
    except Exception as e:
        logger.error(f"Worker 啟動失敗: {e}", exc_info=True)
        sys.exit(1)
