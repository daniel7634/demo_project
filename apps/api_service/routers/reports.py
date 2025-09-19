"""
報告相關 API 路由

提供競品分析報告的創建、狀態查詢和下載功能。
支援非同步報告生成和冪等性控制。
"""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from services.report_service import ReportService

# 配置日誌
logger = logging.getLogger(__name__)

# 創建路由器
router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

# 創建報告服務實例
report_service = ReportService()


# Pydantic 模型定義
class CompetitorReportRequest(BaseModel):
    """競品分析報告請求模型"""

    main_asin: str = Field(..., description="主產品 ASIN", example="B01LP0U5X0")
    competitor_asins: List[str] = Field(
        ..., description="競品 ASIN 列表", example=["B092XTMNCC", "B0DG3X1D7B"]
    )
    window_size: int = Field(default=7, description="分析時間窗口（天數）", ge=1, le=30)
    report_type: str = Field(default="competitor_analysis", description="報告類型")

    @field_validator("competitor_asins")
    @classmethod
    def validate_competitor_asins(cls, v):
        if not v:
            raise ValueError("競品 ASIN 列表不能為空")
        if len(v) > 10:
            raise ValueError("競品 ASIN 數量不能超過 10 個")
        return v

    @field_validator("main_asin")
    @classmethod
    def validate_main_asin(cls, v):
        if not v or len(v) != 10:
            raise ValueError("主產品 ASIN 必須是 10 位字符")
        return v


class ReportCreateResponse(BaseModel):
    """報告創建響應模型"""

    job_id: str = Field(..., description="任務 ID")
    status: str = Field(..., description="任務狀態")
    message: str = Field(..., description="狀態訊息")
    existing: bool = Field(default=False, description="是否為現有任務")


class ReportStatusResponse(BaseModel):
    """報告狀態響應模型"""

    job_id: str = Field(..., description="任務 ID")
    status: str = Field(..., description="任務狀態")
    created_at: str = Field(..., description="創建時間")
    started_at: Optional[str] = Field(None, description="開始時間")
    completed_at: Optional[str] = Field(None, description="完成時間")
    error_message: Optional[str] = Field(None, description="錯誤訊息")
    result_url: Optional[str] = Field(None, description="結果 URL")


class ReportDownloadResponse(BaseModel):
    """報告下載響應模型"""

    content: str = Field(..., description="報告內容")
    metadata: Dict[str, Any] = Field(..., description="報告元數據")
    report_type: str = Field(..., description="報告類型")
    created_at: str = Field(..., description="創建時間")


# API 端點
@router.post(
    "/competitors",
    response_model=ReportCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="創建競品分析報告",
    description="創建競品分析報告任務，返回 202 Accepted 和任務 ID",
)
async def create_competitor_report(
    request: CompetitorReportRequest,
) -> ReportCreateResponse:
    """
    創建競品分析報告

    這個端點會：
    1. 驗證請求參數
    2. 檢查冪等性（避免重複創建）
    3. 創建報告任務
    4. 返回 202 Accepted 和任務 ID

    客戶端可以使用返回的 job_id 來查詢任務狀態和下載報告。
    """
    try:
        # 轉換為字典格式
        request_dict = request.model_dump()

        # 創建報告任務
        result = await report_service.create_competitor_report(request_dict)

        # 檢查是否有錯誤
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"]
            )

        # 返回成功響應
        return ReportCreateResponse(
            job_id=result["job_id"],
            status=result["status"],
            message=result["message"],
            existing=result.get("existing", False),
        )

    except HTTPException:
        raise
    except Exception as e:
        # 打印完整的 traceback 到控制台
        logger.error(f"❌ 創建報告失敗: {str(e)}")
        logger.error(f"📍 Traceback: {traceback.format_exc()}")

        # 記錄到日誌
        logger.error(f"創建報告失敗: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"創建報告失敗: {str(e)}",
        )


@router.get(
    "/jobs/{job_id}",
    response_model=ReportStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="查詢報告任務狀態",
    description="根據任務 ID 查詢報告生成狀態",
)
async def get_report_status(job_id: str) -> ReportStatusResponse:
    """
    查詢報告任務狀態

    返回任務的詳細狀態資訊，包括：
    - 任務狀態（pending, running, completed, failed）
    - 創建時間、開始時間、完成時間
    - 錯誤訊息（如果有）
    - 結果 URL（如果完成）
    """
    try:
        # 查詢任務狀態
        result = await report_service.get_report_status(job_id)

        # 檢查是否有錯誤
        if "error" in result:
            if result["status"] == "not_found":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=result["error"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["error"],
                )

        # 返回狀態響應
        return ReportStatusResponse(
            job_id=result["id"],
            status=result["status"],
            created_at=result["created_at"],
            started_at=result.get("started_at"),
            completed_at=result.get("completed_at"),
            error_message=result.get("error_message"),
            result_url=result.get("result_url"),
        )

    except HTTPException:
        raise
    except Exception as e:
        # 打印完整的 traceback 到控制台
        logger.error(f"❌ 查詢報告狀態失敗: {str(e)}")
        logger.error(f"📍 Traceback: {traceback.format_exc()}")

        # 記錄到日誌
        logger.error(f"查詢報告狀態失敗: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢狀態失敗: {str(e)}",
        )


@router.get(
    "/{job_id}/download",
    response_model=ReportDownloadResponse,
    status_code=status.HTTP_200_OK,
    summary="下載報告結果",
    description="下載已完成的報告內容",
)
async def download_report(job_id: str) -> ReportDownloadResponse:
    """
    下載報告結果

    只有狀態為 "completed" 的報告才能下載。
    返回完整的報告內容和元數據。
    """
    try:
        # 下載報告結果
        result = await report_service.download_report(job_id)

        # 檢查是否有錯誤
        if "error" in result:
            if result["status"] == "not_found":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=result["error"]
                )
            elif result["status"] in ["pending", "running"]:
                raise HTTPException(
                    status_code=status.HTTP_202_ACCEPTED, detail=result["error"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result["error"],
                )

        # 返回報告內容
        return ReportDownloadResponse(
            content=result["content"],
            metadata=result["metadata"],
            report_type=result["report_type"],
            created_at=result["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        # 打印完整的 traceback 到控制台
        logger.error(f"❌ 下載報告失敗: {str(e)}")
        logger.error(f"📍 Traceback: {traceback.format_exc()}")

        # 記錄到日誌
        logger.error(f"下載報告失敗: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下載報告失敗: {str(e)}",
        )


# 健康檢查端點
@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="報告服務健康檢查",
    description="檢查報告服務是否正常運行",
)
async def health_check() -> Dict[str, Any]:
    """報告服務健康檢查"""
    return {
        "status": "healthy",
        "service": "reports",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }


# 獲取所有報告任務（管理端）
@router.get(
    "/jobs",
    status_code=status.HTTP_200_OK,
    summary="獲取所有報告任務",
    description="獲取所有報告任務列表（管理端功能）",
)
async def list_reports(
    status: str = None, limit: int = 50, offset: int = 0
) -> Dict[str, Any]:
    """
    獲取所有報告任務列表

    支援按狀態篩選和分頁。
    """
    try:
        # 這裡可以實現獲取所有任務的邏輯
        # 暫時返回示例響應
        return {
            "reports": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "status": status,
        }

    except Exception as e:
        # 打印完整的 traceback 到控制台
        logger.error(f"❌ 獲取報告列表失敗: {str(e)}")
        logger.error(f"📍 Traceback: {traceback.format_exc()}")

        # 記錄到日誌
        logger.error(f"獲取報告列表失敗: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取報告列表失敗: {str(e)}",
        )
