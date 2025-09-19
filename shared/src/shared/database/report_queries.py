"""
報告相關資料庫查詢模組
提供報告任務狀態管理和結果存儲的完整功能
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from shared.database.supabase_client import get_supabase_client


def create_report_job(
    job_type: str,
    parameters: Dict[str, Any],
    parameters_hash: str,
    status: str = "pending",
) -> str:
    """
    創建報告任務記錄

    Args:
        job_type: 任務類型（如 'competitor_analysis'）
        parameters: 請求參數（JSON 格式）
        parameters_hash: 參數雜湊值（用於冪等性檢查）
        status: 初始狀態（預設 'pending'）

    Returns:
        str: 創建的任務 ID

    Raises:
        Exception: 資料庫操作失敗時拋出異常
    """
    try:
        supabase = get_supabase_client()

        # 準備插入資料
        job_data = {
            "job_type": job_type,
            "parameters": parameters,
            "parameters_hash": parameters_hash,
            "status": status,
            "created_at": datetime.now().isoformat(),
        }

        # 插入資料庫
        result = supabase.table("report_jobs").insert(job_data).execute()

        if result.data:
            job_id = result.data[0]["id"]
            print(f"✅ 成功創建報告任務: {job_id}")
            return job_id
        else:
            raise Exception("創建報告任務失敗：沒有返回任務 ID")

    except Exception as e:
        print(f"❌ 創建報告任務失敗: {str(e)}")
        raise


def update_report_job_status(
    job_id: str,
    status: str,
    result_url: Optional[str] = None,
    error_message: Optional[str] = None,
) -> bool:
    """
    更新報告任務狀態

    Args:
        job_id: 任務 ID
        status: 新狀態（pending, running, completed, failed）
        result_url: 結果下載 URL（可選）
        error_message: 錯誤訊息（可選）

    Returns:
        bool: 更新是否成功

    Raises:
        Exception: 資料庫操作失敗時拋出異常
    """
    try:
        supabase = get_supabase_client()

        # 準備更新資料
        update_data = {"status": status}

        # 根據狀態添加相應欄位
        if status == "running":
            update_data["started_at"] = datetime.now().isoformat()
        elif status in ["completed", "failed"]:
            update_data["completed_at"] = datetime.now().isoformat()

        if result_url:
            update_data["result_url"] = result_url

        if error_message:
            update_data["error_message"] = error_message

        # 更新資料庫
        result = (
            supabase.table("report_jobs").update(update_data).eq("id", job_id).execute()
        )

        if result.data:
            print(f"✅ 成功更新報告任務狀態: {job_id} -> {status}")
            return True
        else:
            print(f"⚠️ 報告任務不存在或更新失敗: {job_id}")
            return False

    except Exception as e:
        print(f"❌ 更新報告任務狀態失敗: {str(e)}")
        raise


def get_report_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    獲取報告任務狀態

    Args:
        job_id: 任務 ID

    Returns:
        Optional[Dict[str, Any]]: 任務狀態資訊，如果不存在則返回 None

    Raises:
        Exception: 資料庫操作失敗時拋出異常
    """
    try:
        supabase = get_supabase_client()

        # 查詢任務狀態
        result = supabase.table("report_jobs").select("*").eq("id", job_id).execute()

        if result.data:
            job_info = result.data[0]
            print(f"✅ 成功獲取報告任務狀態: {job_id} -> {job_info['status']}")
            return job_info
        else:
            print(f"⚠️ 報告任務不存在: {job_id}")
            return None

    except Exception as e:
        print(f"❌ 獲取報告任務狀態失敗: {str(e)}")
        raise


def save_report_result(
    job_id: str,
    content: str,
    report_type: str = "competitor_analysis",
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    保存報告結果

    Args:
        job_id: 任務 ID
        content: 報告內容（Markdown 格式）
        report_type: 報告類型（預設 'competitor_analysis'）
        metadata: 報告元資料（可選）

    Returns:
        str: 創建的結果記錄 ID

    Raises:
        Exception: 資料庫操作失敗時拋出異常
    """
    try:
        supabase = get_supabase_client()

        # 準備插入資料
        result_data = {
            "job_id": job_id,
            "report_type": report_type,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
        }

        # 插入資料庫
        result = supabase.table("report_results").insert(result_data).execute()

        if result.data:
            result_id = result.data[0]["id"]
            print(f"✅ 成功保存報告結果: {result_id}")
            return result_id
        else:
            raise Exception("保存報告結果失敗：沒有返回結果 ID")

    except Exception as e:
        print(f"❌ 保存報告結果失敗: {str(e)}")
        raise


def get_report_result(job_id: str) -> Optional[Dict[str, Any]]:
    """
    獲取報告結果

    Args:
        job_id: 任務 ID

    Returns:
        Optional[Dict[str, Any]]: 報告結果資訊，如果不存在則返回 None

    Raises:
        Exception: 資料庫操作失敗時拋出異常
    """
    try:
        supabase = get_supabase_client()

        # 查詢報告結果
        result = (
            supabase.table("report_results").select("*").eq("job_id", job_id).execute()
        )

        if result.data:
            report_info = result.data[0]
            print(f"✅ 成功獲取報告結果: {job_id}")
            return report_info
        else:
            print(f"⚠️ 報告結果不存在: {job_id}")
            return None

    except Exception as e:
        print(f"❌ 獲取報告結果失敗: {str(e)}")
        raise


def check_existing_report(
    parameters_hash: str, date: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    檢查是否存在相同參數的報告（冪等性檢查）

    Args:
        parameters_hash: 參數雜湊值
        date: 檢查日期（預設為今天）

    Returns:
        Optional[Dict[str, Any]]: 已存在的報告資訊，如果不存在則返回 None

    Raises:
        Exception: 資料庫操作失敗時拋出異常
    """
    try:
        supabase = get_supabase_client()

        # 設定查詢條件
        query = supabase.table("report_jobs").select("*")
        query = query.eq("parameters_hash", parameters_hash)
        query = query.eq("status", "completed")

        if date:
            # 按指定日期查詢
            query = query.gte("created_at", f"{date} 00:00:00")
            query = query.lt("created_at", f"{date} 23:59:59")
        else:
            # 按今天查詢
            today = datetime.now().strftime("%Y-%m-%d")
            query = query.gte("created_at", f"{today} 00:00:00")
            query = query.lt("created_at", f"{today} 23:59:59")

        result = query.execute()

        if result.data:
            existing_report = result.data[0]
            print(f"✅ 找到已存在的報告: {existing_report['id']}")
            return existing_report
        else:
            print("ℹ️ 沒有找到已存在的報告")
            return None

    except Exception as e:
        print(f"❌ 檢查已存在報告失敗: {str(e)}")
        raise


def get_report_jobs_by_status(status: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    根據狀態獲取報告任務列表

    Args:
        status: 任務狀態
        limit: 限制數量（預設 100）

    Returns:
        List[Dict[str, Any]]: 任務列表

    Raises:
        Exception: 資料庫操作失敗時拋出異常
    """
    try:
        supabase = get_supabase_client()

        # 查詢指定狀態的任務
        result = (
            supabase.table("report_jobs")
            .select("*")
            .eq("status", status)
            .limit(limit)
            .execute()
        )

        if result.data:
            print(f"✅ 成功獲取 {len(result.data)} 個 {status} 狀態的報告任務")
            return result.data
        else:
            print(f"ℹ️ 沒有找到 {status} 狀態的報告任務")
            return []

    except Exception as e:
        print(f"❌ 獲取報告任務列表失敗: {str(e)}")
        raise


def delete_report_job(job_id: str) -> bool:
    """
    刪除報告任務（包括相關的結果記錄）

    Args:
        job_id: 任務 ID

    Returns:
        bool: 刪除是否成功

    Raises:
        Exception: 資料庫操作失敗時拋出異常
    """
    try:
        supabase = get_supabase_client()

        # 先刪除相關的結果記錄
        supabase.table("report_results").delete().eq("job_id", job_id).execute()

        # 再刪除任務記錄
        result = supabase.table("report_jobs").delete().eq("id", job_id).execute()

        if result.data:
            print(f"✅ 成功刪除報告任務: {job_id}")
            return True
        else:
            print(f"⚠️ 報告任務不存在: {job_id}")
            return False

    except Exception as e:
        print(f"❌ 刪除報告任務失敗: {str(e)}")
        raise


def generate_parameters_hash(parameters: Dict[str, Any]) -> str:
    """
    生成參數雜湊值（用於冪等性檢查）

    Args:
        parameters: 參數字典

    Returns:
        str: 參數雜湊值
    """
    # 將參數轉換為 JSON 字串並排序
    sorted_params = json.dumps(parameters, sort_keys=True, ensure_ascii=False)

    # 生成 SHA-256 雜湊值
    hash_object = hashlib.sha256(sorted_params.encode("utf-8"))
    return hash_object.hexdigest()


# 測試函數
def test_report_queries():
    """測試報告查詢模組功能"""
    print("🧪 開始測試報告查詢模組...")

    try:
        # 測試參數
        test_parameters = {
            "main_asin": "B0DG3X1D7B",
            "competitor_asins": ["B08XYZ1234", "B09ABC5678"],
            "window_size": 7,
        }

        # 生成參數雜湊值
        params_hash = generate_parameters_hash(test_parameters)
        print(f"📝 參數雜湊值: {params_hash}")

        # 測試創建任務
        job_id = create_report_job(
            job_type="competitor_analysis",
            parameters=test_parameters,
            parameters_hash=params_hash,
        )
        print(f"✅ 創建任務成功: {job_id}")

        # 測試更新狀態
        update_report_job_status(job_id, "running")
        update_report_job_status(
            job_id, "completed", result_url=f"/api/v1/reports/{job_id}/download"
        )

        # 測試保存結果
        test_content = "# 競品分析報告\n\n## 主產品分析\n測試內容..."
        result_id = save_report_result(job_id, test_content)
        print(f"✅ 保存結果成功: {result_id}")

        # 測試查詢狀態
        job_status = get_report_job_status(job_id)
        print(f"📊 任務狀態: {job_status['status'] if job_status else 'Not Found'}")

        # 測試查詢結果
        report_result = get_report_result(job_id)
        print(f"📄 報告結果: {'Found' if report_result else 'Not Found'}")

        # 測試冪等性檢查
        existing_report = check_existing_report(params_hash)
        print(f"🔄 冪等性檢查: {'Found' if existing_report else 'Not Found'}")

        # 清理測試資料
        delete_report_job(job_id)
        print("🧹 清理測試資料完成")

        print("✅ 報告查詢模組測試完成！")

    except Exception as e:
        print(f"❌ 測試失敗: {str(e)}")
        raise


if __name__ == "__main__":
    test_report_queries()
