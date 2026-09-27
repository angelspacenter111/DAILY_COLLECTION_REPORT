import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from database import db

logger = logging.getLogger(__name__)

def compute_report_aggregates(details: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes Friday to Thursday aggregated show, admits, and net totals from daily details."""
    day_prefixes = ["fri", "sat", "sun", "mon", "tue", "wed", "thu"]
    aggregates: Dict[str, Any] = {}
    grand_total = 0.0

    for prefix in day_prefixes:
        aggregates[f"{prefix}_show"] = 0
        aggregates[f"{prefix}_admits"] = 0
        aggregates[f"{prefix}_net"] = 0.0

    for item in details:
        day_str = str(item.get("day") or item.get("Day") or "").lower()
        shows = int(item.get("shows", 0) or item.get("Shows", 0) or 0)
        admits = int(item.get("audience", 0) or item.get("Attendance", 0) or 0)
        try:
            net_val = float(str(item.get("final_net", 0) or item.get("Nett", 0)).replace(",", ""))
        except (ValueError, TypeError):
            net_val = 0.0

        grand_total += net_val

        for prefix in day_prefixes:
            if day_str.startswith(prefix):
                aggregates[f"{prefix}_show"] = max(aggregates[f"{prefix}_show"], shows)
                aggregates[f"{prefix}_admits"] = max(aggregates[f"{prefix}_admits"], admits)
                aggregates[f"{prefix}_net"] = round(max(aggregates[f"{prefix}_net"], net_val), 2)
                break

    aggregates["grand_total"] = round(grand_total, 2)
    return aggregates

async def insert_dcr_report(report_payload: Dict[str, Any]) -> str:
    """Inserts a DCR report document with computed aggregates into MongoDB 'dcr_reports' collection."""
    details = report_payload.get("details", [])
    aggregates = compute_report_aggregates(details)

    doc = {
        "file_name": report_payload.get("file_name", ""),
        "cinema_name": report_payload.get("cinema_name", ""),
        "distributor_address": report_payload.get("distributor_address", ""),
        "report_date": report_payload.get("report_date", 0),
        "created_at": datetime.utcnow(),
        "report_data": report_payload.get("report_data", []),
        "details": details,
        **aggregates
    }

    result = await db.dcr_reports.insert_one(doc)
    return str(result.inserted_id)

async def fetchrecords(sql_string: Optional[Any] = None, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Fetches all DCR reports from MongoDB 'dcr_reports' collection.
    Maintains compatibility with existing templates and Excel exports.
    """
    try:
        cursor = db.dcr_reports.find({}).sort("_id", 1)
        reports: List[Dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = str(doc.get("_id", ""))
            reports.append(doc)
        return reports
    except Exception as e:
        logger.error("Failed to fetch records from MongoDB: %s", str(e))
        return []

def main_query():
    """Placeholder kept for compatibility with existing route handlers."""
    return None

# Backward compatibility wrappers
async def createrecords(sql_string: str, params: Optional[Dict[str, Any]] = None) -> int:
    return 1

async def bulk_createrecords(sql_string: str, params_list: List[Dict[str, Any]]) -> None:
    pass