#!/usr/bin/env python3
"""
Flower 監控啟動腳本
用於啟動 Celery 任務監控 Web UI
"""

import logging
import os
import sys

# 設定 logger
logger = logging.getLogger(__name__)


def start_flower():
    """啟動 Flower 監控"""
    logger.info("=" * 50)
    logger.info("啟動 Flower 監控")
    logger.info("=" * 50)
    logger.info(f"工作目錄: {os.getcwd()}")
    logger.info(f"Redis URL: {os.getenv('REDIS_URL', 'redis://localhost:6379/0')}")
    logger.info("Web UI: http://localhost:5555")
    logger.info("=" * 50)
    logger.info("按 Ctrl+C 停止監控")
    logger.info("=" * 50)

    # 啟動 Flower - 使用 Celery 子命令
    try:
        import subprocess

        # 構建 Celery Flower 命令
        cmd = [
            "celery",
            "-A",
            "celery_app:app",  # 指定 Celery 應用
            "flower",
            "--port=5555",
            "--address=0.0.0.0",
            "--loglevel=INFO",
            "--db=flower.db",
            "--persistent",
        ]

        logger.info(f"執行命令: {' '.join(cmd)}")

        # 啟動 Flower 進程
        process = subprocess.Popen(cmd, cwd=os.getcwd())

        # 等待進程結束或中斷信號
        try:
            process.wait()
        except KeyboardInterrupt:
            logger.info("正在停止 Flower...")
            process.terminate()
            process.wait()

    except FileNotFoundError:
        logger.error("Celery 或 Flower 未安裝，請先安裝：pip install celery flower")
        return False
    except Exception as e:
        logger.error(f"Flower 啟動失敗: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    try:
        start_flower()
    except KeyboardInterrupt:
        logger.info("Flower 監控已停止")
    except Exception as e:
        logger.error(f"Flower 監控過程中發生錯誤: {e}", exc_info=True)
        sys.exit(1)
