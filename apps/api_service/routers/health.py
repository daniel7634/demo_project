"""
健康檢查和系統相關 API 路由
"""

from datetime import datetime

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/")
async def root():
    """
    根路徑 - 歡迎訊息
    """
    return {
        "message": "歡迎使用 Amazon Product Monitor API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs",
    }


@router.get("/health")
async def health_check():
    """
    健康檢查端點
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "api_service",
    }
