import asyncio
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId
from pymongo.errors import AutoReconnect, PyMongoError
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

    net_show = sum(aggregates[f"{prefix}_show"] for prefix in day_prefixes)
    net_adm = sum(aggregates[f"{prefix}_admits"] for prefix in day_prefixes)

    aggregates["net_show"] = net_show
    aggregates["net_adm"] = net_adm
    aggregates["total_shows"] = net_show
    aggregates["total_admits"] = net_adm
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

    for attempt in range(3):
        try:
            result = await db.dcr_reports.insert_one(doc)
            return str(result.inserted_id)
        except AutoReconnect as e:
            if attempt < 2:
                logger.warning("MongoDB AutoReconnect on insert (attempt %d/3), retrying in 0.5s...", attempt + 1)
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            logger.error("MongoDB insert failed after retries: %s", str(e))
            raise

async def fetchrecords(sql_string: Optional[Any] = None, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Fetches all DCR reports from MongoDB 'dcr_reports' collection.
    Maintains compatibility with existing templates and Excel exports.
    """
    for attempt in range(3):
        try:
            cursor = db.dcr_reports.find({}).sort("_id", 1)
            reports: List[Dict[str, Any]] = []
            async for doc in cursor:
                doc["id"] = str(doc.get("_id", ""))
                doc["_id"] = str(doc.get("_id", ""))
                if isinstance(doc.get("created_at"), datetime):
                    doc["created_at"] = doc["created_at"].isoformat()

                day_prefixes = ["fri", "sat", "sun", "mon", "tue", "wed", "thu"]
                if "net_show" not in doc:
                    doc["net_show"] = sum(int(doc.get(f"{p}_show", 0) or 0) for p in day_prefixes)
                if "net_adm" not in doc:
                    doc["net_adm"] = sum(int(doc.get(f"{p}_admits", 0) or 0) for p in day_prefixes)

                reports.append(doc)
            return reports
        except AutoReconnect as e:
            if attempt < 2:
                logger.warning("MongoDB AutoReconnect on fetch (attempt %d/3), retrying...", attempt + 1)
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            logger.error("MongoDB fetch failed after retries: %s", str(e))
            return []
        except Exception as e:
            logger.error("Failed to fetch records from MongoDB: %s", str(e))
            return []

async def init_db_indexes():
    """Ensures performance indexes exist on dcr_reports collection."""
    try:
        await db.dcr_reports.create_index([("created_at", -1)], background=True)
        await db.dcr_reports.create_index([("report_date", -1)], background=True)
        await db.dcr_reports.create_index([("file_name", 1)], background=True)
    except (AutoReconnect, PyMongoError) as e:
        logger.warning("Index creation notice: %s", str(e))

async def delete_dcr_report(report_id: str) -> bool:
    """Deletes a single DCR report document by ID."""
    try:
        res = await db.dcr_reports.delete_one({"_id": ObjectId(report_id)})
        return res.deleted_count > 0
    except Exception as e:
        logger.error("Failed to delete report %s: %s", report_id, str(e))
        return False

async def clear_all_dcr_reports() -> int:
    """Deletes all documents from dcr_reports collection."""
    try:
        res = await db.dcr_reports.delete_many({})
        return res.deleted_count
    except Exception as e:
        logger.error("Failed to clear reports: %s", str(e))
        return 0

def get_dcr_summary(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculates KPI summary totals across all fetched DCR reports."""
    days = ['fri', 'sat', 'sun', 'mon', 'tue', 'wed', 'thu']
    total_net = 0.0
    total_admits = 0
    total_shows = 0

    for r in reports:
        try:
            total_net += float(r.get("grand_total", 0) or 0)
        except (ValueError, TypeError):
            pass
        for day in days:
            try:
                total_shows += int(r.get(f"{day}_show", 0) or 0)
            except (ValueError, TypeError):
                pass
            try:
                total_admits += int(r.get(f"{day}_admits", 0) or 0)
            except (ValueError, TypeError):
                pass

    return {
        "total_reports": len(reports),
        "total_net": round(total_net, 2),
        "total_admits": total_admits,
        "total_shows": total_shows,
    }

def main_query():
    """Placeholder kept for compatibility with existing route handlers."""
    return None

# Backward compatibility wrappers
async def createrecords(sql_string: str, params: Optional[Dict[str, Any]] = None) -> int:
    return 1

async def bulk_createrecords(sql_string: str, params_list: List[Dict[str, Any]]) -> None:
    pass