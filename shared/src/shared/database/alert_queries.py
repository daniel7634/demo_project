"""
告警規則和記錄的資料庫查詢函數

提供告警規則的 CRUD 操作和告警記錄的創建功能。
支援動態告警規則配置和異常變化檢測。
"""

from datetime import date
from typing import Any, Dict, List

from shared.database.snapshots_queries import get_previous_snapshot
from shared.database.supabase_client import get_supabase_client


def get_active_alert_rules() -> List[Dict[str, Any]]:
    """
    獲取所有啟用的告警規則

    Returns:
        List[Dict[str, Any]]: 啟用的告警規則列表
    """
    try:
        client = get_supabase_client()
        result = client.table("alert_rules").select("*").eq("is_active", True).execute()

        if result.data:
            print(f"✅ 成功獲取 {len(result.data)} 個啟用的告警規則")
            return result.data
        else:
            print("⚠️ 沒有找到啟用的告警規則")
            return []

    except Exception as e:
        print(f"❌ 獲取告警規則失敗: {e}")
        return []


def create_alert_record(alert_data: Dict[str, Any]) -> bool:
    """
    創建告警記錄

    Args:
        alert_data (Dict[str, Any]): 告警記錄資料
            - asin (str): 產品 ASIN
            - rule_id (str): 告警規則 ID
            - message (str): 告警訊息
            - previous_value (float): 前一個值
            - current_value (float): 當前值
            - change_percent (float): 變化百分比
            - snapshot_date (str): 快照日期 (YYYY-MM-DD)

    Returns:
        bool: 創建是否成功
    """
    try:
        client = get_supabase_client()

        # 確保 snapshot_date 是正確的格式
        if isinstance(alert_data.get("snapshot_date"), date):
            alert_data["snapshot_date"] = alert_data["snapshot_date"].isoformat()

        result = client.table("alerts").insert(alert_data).execute()

        if result.data:
            print(
                f"✅ 成功創建告警記錄: {alert_data.get('asin')} - {alert_data.get('message')}"
            )
            return True
        else:
            print(f"❌ 創建告警記錄失敗: {result}")
            return False

    except Exception as e:
        print(f"❌ 創建告警記錄失敗: {e}")
        return False


# 測試函數
if __name__ == "__main__":
    print("🧪 測試告警查詢函數")
    print("=" * 50)

    # 測試獲取啟用的告警規則
    print("\n1. 測試獲取啟用的告警規則:")
    rules = get_active_alert_rules()
    for rule in rules:
        print(
            f"   - {rule.get('rule_name')}: {rule.get('rule_type')} {rule.get('change_direction')} {rule.get('threshold')}"
        )

    # 測試創建告警記錄
    print("\n2. 測試創建告警記錄:")
    if rules:
        sample_alert = {
            "asin": "TEST123",
            "rule_id": rules[0]["id"],
            "message": "測試告警",
            "previous_value": 100.0,
            "current_value": 90.0,
            "change_percent": -10.0,
            "snapshot_date": "2024-01-01",
        }
        success = create_alert_record(sample_alert)
        print(f"   創建結果: {'成功' if success else '失敗'}")
    else:
        print("   沒有規則可用於測試")

    print("\n✅ 告警查詢函數測試完成")

# 導出函數
__all__ = [
    "get_active_alert_rules",
    "create_alert_record",
    "get_previous_snapshot",  # 從 snapshots_queries 重新導出
]
