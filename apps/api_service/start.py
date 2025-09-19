#!/usr/bin/env python3
"""
API 服務啟動腳本
"""

import logging

import uvicorn

# 設定 logger
logger = logging.getLogger(__name__)


def start_api_server():
    """啟動 API 服務器"""
    logger.info("啟動 FastAPI 服務器...")
    logger.info("API 文檔: http://localhost:8000/docs")
    logger.info("ReDoc 文檔: http://localhost:8000/redoc")
    logger.info("健康檢查: http://localhost:8000/health")
    logger.info("=" * 50)

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")


if __name__ == "__main__":
    start_api_server()
