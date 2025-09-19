"""
資料庫模組
提供 Supabase 資料庫連接和查詢功能
"""

from .alert_queries import create_alert_record, get_active_alert_rules
from .asin_status_queries import (
    bulk_update_asin_status,
    get_asins_to_scrape,
    get_pending_asins,
)
from .snapshots_queries import get_latest_snapshot, get_previous_snapshot
from .supabase_client import get_supabase_client

__all__ = [
    "get_supabase_client",
    "get_asins_to_scrape",
    "get_pending_asins",
    "bulk_update_asin_status",
    "get_latest_snapshot",
    "get_previous_snapshot",
    "get_active_alert_rules",
    "create_alert_record",
]
