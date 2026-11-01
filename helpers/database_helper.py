import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from pymongo.errors import AutoReconnect, PyMongoError
from database import db

logger = logging.getLogger(__name__)

def sanitize_mongo_doc(obj: Any) -> Any:
    """Recursively converts ObjectId and datetime objects into JSON-serializable types."""
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: sanitize_mongo_doc(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_mongo_doc(item) for item in obj]
    return obj

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

async def find_cinema_master_match(cinema_name: str, file_name: str = "") -> Optional[Dict[str, Any]]:
    """
    Matches a DCR report against cinema_master collection using either:
    1. Extracted cinema_name (exact case-insensitive match)
    2. DCR file_name (cleaned of .pdf, underscores to spaces, exact case-insensitive match)
    3. Flexible substring / containment matching across registered cinema names
    Returns the matched cinema document (with _id, cinema_name, etc.), or None if no match.
    Does NOT create a new cinema record (Cinemas are only created via Excel Bulk Upload).
    """
    c_clean = (cinema_name or "").strip()
    f_clean = re.sub(r'\.pdf$', '', (file_name or "").strip(), flags=re.IGNORECASE).strip()
    f_spaces = f_clean.replace('_', ' ').strip()
    f_spaces_clean = re.sub(r'\s+', ' ', f_spaces)

    # 1. Exact case-insensitive matching against cinema_name
    if c_clean and c_clean.lower() not in ("unknown cinema", "unknown", "cinema", "n/a", "-"):
        doc = await db.cinema_master.find_one({
            "cinema_name": {"$regex": f"^{re.escape(c_clean)}$", "$options": "i"}
        })
        if doc:
            return doc

    # 2. Exact case-insensitive matching against file_name
    for cand in (f_clean, f_spaces, f_spaces_clean):
        if cand and cand.lower() not in ("unknown", "dcr", "report", "n/a", "-"):
            doc = await db.cinema_master.find_one({
                "cinema_name": {"$regex": f"^{re.escape(cand)}$", "$options": "i"}
            })
            if doc:
                return doc

    # 3. Flexible containment / substring match across registered cinemas in cinema_master
    try:
        cursor = db.cinema_master.find({}, {"cinema_name": 1})
        all_cinemas = await cursor.to_list(length=5000)
    except Exception as e:
        logger.error("Error querying cinema_master in find_cinema_master_match: %s", e)
        return None

    if not all_cinemas:
        return None

    target_tokens = set()
    for s in (c_clean, f_clean, f_spaces, f_spaces_clean):
        if s and s.lower() not in ("unknown cinema", "unknown", "cinema", "dcr", "report", "n/a", "-"):
            target_tokens.add(s.lower())

    candidates = []
    for c in all_cinemas:
        m_name = (c.get("cinema_name") or "").strip()
        m_lower = m_name.lower()
        if not m_lower or len(m_lower) < 3:
            continue

        for token in target_tokens:
            if m_lower == token:
                return c
            # Cinema name contained within filename or extracted cinema text
            if len(m_lower) >= 4 and m_lower in token:
                candidates.append((len(m_lower), c))
            # Or token contained in cinema name (only if token is specific, >= 5 chars)
            elif len(token) >= 5 and token in m_lower:
                candidates.append((len(token), c))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    return None

async def get_or_create_cinema_master(cinema_name: str, file_name: str = "") -> Optional[ObjectId]:
    """
    Finds a cinema record in MongoDB 'cinema_master' collection matching cinema_name or file_name.
    Does NOT create a new cinema (Cinemas are strictly created via Excel Bulk Upload).
    Returns the ObjectId of the cinema record if matched, else None.
    """
    matched = await find_cinema_master_match(cinema_name, file_name)
    return matched["_id"] if matched else None

async def migrate_existing_cinemas_to_master():
    """
    Backfills cinema_id into dcr_reports documents by matching either
    cinema_name OR file_name with cinema_master.
    Does NOT create new cinemas (Cinemas are only created via Excel Bulk Upload).
    """
    try:
        cursor = db.dcr_reports.find({
            "$or": [
                {"cinema_id": {"$exists": False}},
                {"cinema_id": None}
            ]
        })
        migrated_count = 0
        async for r in cursor:
            raw_name = (r.get("cinema_name") or "").strip()
            raw_file = (r.get("file_name") or "").strip()
            matched = await find_cinema_master_match(raw_name, raw_file)
            if matched:
                await db.dcr_reports.update_one(
                    {"_id": r["_id"]},
                    {"$set": {
                        "cinema_id": matched["_id"],
                        "cinema_name": matched["cinema_name"]
                    }}
                )
                migrated_count += 1
        if migrated_count > 0:
            logger.info("Migrated/linked %d dcr_reports with cinema_master.", migrated_count)
    except Exception as e:
        logger.warning("Notice on cinema migration: %s", str(e))

async def insert_dcr_report(report_payload: Dict[str, Any]) -> str:
    """
    Inserts a DCR report document with computed aggregates into MongoDB 'dcr_reports' collection.
    Matches either cinema_name OR file_name with 'cinema_master'.
    If matched, stores the cinema_master ObjectId as 'cinema_id' and the official cinema_name.
    If not matched, leaves 'cinema_id' as None and retains the extracted cinema name.
    Does NOT create new records in cinema_master (Cinemas can only be created via Excel Bulk Upload).
    """
    raw_cinema_name = (report_payload.get("cinema_name") or "").strip()
    raw_file_name = (report_payload.get("file_name") or "").strip()

    matched_cinema = await find_cinema_master_match(raw_cinema_name, raw_file_name)
    if matched_cinema:
        cinema_id = matched_cinema["_id"]
        final_cinema_name = matched_cinema.get("cinema_name") or raw_cinema_name
    else:
        cinema_id = None
        clean_fallback = re.sub(r'\.pdf$', '', raw_file_name, flags=re.IGNORECASE).strip()
        final_cinema_name = raw_cinema_name or clean_fallback or "Unknown Cinema"

    details = report_payload.get("details", [])
    aggregates = compute_report_aggregates(details)

    doc = {
        "file_name": raw_file_name,
        "cinema_id": cinema_id,
        "cinema_name": final_cinema_name,
        "movie_name": report_payload.get("movie_name", ""),
        "distributor_address": report_payload.get("distributor_address", ""),
        "report_date": report_payload.get("report_date", 0),
        "total_deduction": float(report_payload.get("total_deduction", 0.0) or 0.0),
        "created_at": datetime.now(timezone.utc),
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
    Fetches DCR reports from MongoDB 'dcr_reports' collection.
    Maps cinema_id to 'cinema_master' collection dynamically to fetch updated cinema details.
    Supports an optional MongoDB filter query dictionary for movie filtering.
    """
    query = sql_string if isinstance(sql_string, dict) else {}
    for attempt in range(3):
        try:
            pipeline: List[Dict[str, Any]] = []
            if query:
                pipeline.append({"$match": query})
            pipeline.append({"$sort": {"_id": 1}})
            pipeline.append({
                "$lookup": {
                    "from": "cinema_master",
                    "localField": "cinema_id",
                    "foreignField": "_id",
                    "as": "cinema_master_data"
                }
            })

            cursor = db.dcr_reports.aggregate(pipeline)
            reports: List[Dict[str, Any]] = []
            async for doc in cursor:
                doc["id"] = str(doc.get("_id", ""))
                doc["_id"] = str(doc.get("_id", ""))

                # Dynamic ID mapping from cinema_master
                c_data = doc.pop("cinema_master_data", None) or []
                c_info = c_data[0] if (c_data and len(c_data) > 0 and isinstance(c_data[0], dict)) else None

                # Fallback dynamic match if cinema_id was not previously linked
                if not c_info and (doc.get("cinema_name") or doc.get("file_name")):
                    c_info = await find_cinema_master_match(doc.get("cinema_name", ""), doc.get("file_name", ""))
                    if c_info:
                        doc["cinema_id"] = str(c_info["_id"])
                        try:
                            raw_id = ObjectId(doc["id"]) if ObjectId.is_valid(doc["id"]) else doc["_id"]
                            await db.dcr_reports.update_one(
                                {"_id": raw_id},
                                {"$set": {"cinema_id": c_info["_id"], "cinema_name": c_info.get("cinema_name", doc.get("cinema_name"))}}
                            )
                        except Exception:
                            pass

                if c_info:
                    if c_info.get("cinema_name"):
                        doc["cinema_name"] = c_info["cinema_name"]
                    doc["location"] = c_info.get("location") or ""
                    doc["state"] = c_info.get("state") or ""
                    doc["sircuit"] = c_info.get("sircuit") or ""
                    doc["controller"] = c_info.get("controller") or ""
                    doc["gst"] = c_info.get("gst") or ""
                    doc["pan_number"] = c_info.get("pan_number") or ""
                    doc["address"] = c_info.get("address") or ""
                else:
                    if not doc.get("cinema_name"):
                        doc["cinema_name"] = "Unknown Cinema"
                    doc["location"] = ""
                    doc["state"] = ""
                    doc["sircuit"] = ""
                    doc["controller"] = ""
                    doc["gst"] = ""
                    doc["pan_number"] = ""
                    doc["address"] = ""

                if doc.get("cinema_id"):
                    doc["cinema_id"] = str(doc["cinema_id"])

                doc["movie_name"] = doc.get("movie_name", "") or ""
                if isinstance(doc.get("created_at"), datetime):
                    doc["created_at"] = doc["created_at"].isoformat()

                day_prefixes = ["fri", "sat", "sun", "mon", "tue", "wed", "thu"]
                if "net_show" not in doc:
                    doc["net_show"] = sum(int(doc.get(f"{p}_show", 0) or 0) for p in day_prefixes)
                if "net_adm" not in doc:
                    doc["net_adm"] = sum(int(doc.get(f"{p}_admits", 0) or 0) for p in day_prefixes)

                doc["total_deduction"] = float(doc.get("total_deduction", 0.0) or 0.0)
                reports.append(sanitize_mongo_doc(doc))
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

async def get_dcr_report_by_id(report_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single DCR report document by ID, mapping cinema_id with cinema_master."""
    try:
        doc = await db.dcr_reports.find_one({"_id": ObjectId(report_id)})
        if doc:
            doc["id"] = str(doc["_id"])
            doc["_id"] = str(doc["_id"])
            c_master = None
            if doc.get("cinema_id"):
                try:
                    c_id = ObjectId(doc["cinema_id"]) if isinstance(doc["cinema_id"], str) else doc["cinema_id"]
                    c_master = await db.cinema_master.find_one({"_id": c_id})
                    doc["cinema_id"] = str(c_id)
                except Exception:
                    pass
            if not c_master and (doc.get("cinema_name") or doc.get("file_name")):
                c_master = await find_cinema_master_match(doc.get("cinema_name", ""), doc.get("file_name", ""))

            if c_master:
                if c_master.get("cinema_name"):
                    doc["cinema_name"] = c_master["cinema_name"]
                doc["location"] = c_master.get("location") or ""
                doc["state"] = c_master.get("state") or ""
                doc["sircuit"] = c_master.get("sircuit") or ""
                doc["controller"] = c_master.get("controller") or ""
                doc["gst"] = c_master.get("gst") or ""
                doc["pan_number"] = c_master.get("pan_number") or ""
                doc["address"] = c_master.get("address") or ""
            else:
                doc["location"] = ""
                doc["state"] = ""
                doc["sircuit"] = ""
                doc["controller"] = ""
                doc["gst"] = ""
                doc["pan_number"] = ""
                doc["address"] = ""
            doc["movie_name"] = doc.get("movie_name", "") or ""
            doc["total_deduction"] = float(doc.get("total_deduction", 0.0) or 0.0)
            if isinstance(doc.get("created_at"), datetime):
                doc["created_at"] = doc["created_at"].isoformat()
            return sanitize_mongo_doc(doc)
        return None
    except Exception as e:
        logger.error("Failed to fetch report %s: %s", report_id, str(e))
        return None

async def init_db_indexes():
    """Ensures performance indexes exist on dcr_reports and cinema_master collections."""
    try:
        await db.dcr_reports.create_index([("created_at", -1)], background=True)
        await db.dcr_reports.create_index([("report_date", -1)], background=True)
        await db.dcr_reports.create_index([("file_name", 1)], background=True)
        await db.dcr_reports.create_index([("cinema_id", 1)], background=True)
        await db.cinema_master.create_index([("cinema_name", 1)], background=True)
        await migrate_existing_cinemas_to_master()
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

# -------------------------------------------------------------
# Cinema Master CRUD & Bulk Functions
# -------------------------------------------------------------

async def list_all_cinemas() -> List[Dict[str, Any]]:
    """
    Lists all cinemas in cinema_master sorted alphabetically,
    with count of linked DCR reports and full metadata.
    """
    try:
        pipeline = [
            {"$sort": {"cinema_name": 1}},
            {
                "$lookup": {
                    "from": "dcr_reports",
                    "localField": "_id",
                    "foreignField": "cinema_id",
                    "as": "linked_reports"
                }
            },
            {
                "$addFields": {
                    "report_count": {"$size": "$linked_reports"}
                }
            },
            {
                "$project": {
                    "linked_reports": 0
                }
            }
        ]
        cursor = db.cinema_master.aggregate(pipeline)
        cinemas: List[Dict[str, Any]] = []
        async for doc in cursor:
            doc["id"] = str(doc["_id"])
            doc["_id"] = str(doc["_id"])
            doc["cinema_name"] = doc.get("cinema_name") or ""
            doc["address"] = doc.get("address") or ""
            doc["location"] = doc.get("location") or ""
            doc["state"] = doc.get("state") or ""
            doc["sircuit"] = doc.get("sircuit") or ""
            doc["controller"] = doc.get("controller") or ""
            doc["gst"] = doc.get("gst") or ""
            doc["pan_number"] = doc.get("pan_number") or ""
            doc["digital_format"] = doc.get("digital_format") or ""
            charges_val = doc.get("digital_charges") or doc.get("digital_charges_per_show") or ""
            doc["digital_charges"] = charges_val
            doc["digital_charges_per_show"] = charges_val
            doc["cdc_charges"] = doc.get("cdc_charges") or ""

            created_at = doc.get("created_at")
            if isinstance(created_at, datetime):
                doc["created_at_formatted"] = created_at.strftime("%d %b %Y, %I:%M %p")
            else:
                doc["created_at_formatted"] = "N/A"

            updated_at = doc.get("updated_at")
            if isinstance(updated_at, datetime):
                doc["updated_at_formatted"] = updated_at.strftime("%d %b %Y, %I:%M %p")
            else:
                doc["updated_at_formatted"] = doc["created_at_formatted"]

            cinemas.append(sanitize_mongo_doc(doc))
        return cinemas
    except Exception as e:
        logger.error("Failed to list cinemas: %s", str(e))
        return []

async def get_cinema_by_id(cinema_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single cinema from cinema_master with all fields."""
    try:
        doc = await db.cinema_master.find_one({"_id": ObjectId(cinema_id)})
        if doc:
            doc["id"] = str(doc["_id"])
            doc["_id"] = str(doc["_id"])
            doc["cinema_name"] = doc.get("cinema_name") or ""
            doc["address"] = doc.get("address") or ""
            doc["location"] = doc.get("location") or ""
            doc["state"] = doc.get("state") or ""
            doc["sircuit"] = doc.get("sircuit") or ""
            doc["controller"] = doc.get("controller") or ""
            doc["gst"] = doc.get("gst") or ""
            doc["pan_number"] = doc.get("pan_number") or ""
            doc["digital_format"] = doc.get("digital_format") or ""
            charges_val = doc.get("digital_charges") or doc.get("digital_charges_per_show") or ""
            doc["digital_charges"] = charges_val
            doc["digital_charges_per_show"] = charges_val
            doc["cdc_charges"] = doc.get("cdc_charges") or ""
            doc["report_count"] = await db.dcr_reports.count_documents({"cinema_id": ObjectId(cinema_id)})
            return sanitize_mongo_doc(doc)
        return None
    except Exception as e:
        logger.error("Failed to get cinema %s: %s", cinema_id, str(e))
        return None

async def create_cinema_master_record(
    cinema_name: str,
    address: str = "",
    location: str = "",
    state: str = "",
    sircuit: str = "",
    controller: str = "",
    gst: str = "",
    pan_number: str = "",
    digital_format: str = "",
    digital_charges: str = "",
    cdc_charges: str = "",
    digital_charges_per_show: str = ""
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Manually creates a new cinema in cinema_master with address, location, tax, digital format, and charges."""
    cleaned = (cinema_name or "").strip()
    if not cleaned:
        return False, "Cinema name cannot be empty.", None

    try:
        existing = await db.cinema_master.find_one({
            "cinema_name": {"$regex": f"^{re.escape(cleaned)}$", "$options": "i"}
        })
        if existing:
            return False, f"Cinema '{cleaned}' already exists in Cinema Master.", None

        now = datetime.now(timezone.utc)
        resolved_charges = (digital_charges or digital_charges_per_show or "").strip()
        doc = {
            "cinema_name": cleaned,
            "address": (address or "").strip(),
            "location": (location or "").strip(),
            "state": (state or "").strip(),
            "sircuit": (sircuit or "").strip(),
            "controller": (controller or "").strip(),
            "gst": (gst or "").strip(),
            "pan_number": (pan_number or "").strip(),
            "digital_format": (digital_format or "").strip(),
            "digital_charges": resolved_charges,
            "digital_charges_per_show": resolved_charges,
            "cdc_charges": (cdc_charges or "").strip(),
            "created_at": now,
            "updated_at": now
        }
        res = await db.cinema_master.insert_one(doc)
        doc["id"] = str(res.inserted_id)
        doc["_id"] = str(res.inserted_id)
        doc["report_count"] = 0
        doc["created_at_formatted"] = now.strftime("%d %b %Y, %I:%M %p")
        doc["updated_at_formatted"] = doc["created_at_formatted"]
        return True, f"Cinema '{cleaned}' added successfully.", sanitize_mongo_doc(doc)
    except Exception as e:
        logger.error("Error creating cinema: %s", str(e))
        return False, f"Database error: {str(e)}", None

async def update_cinema_record(
    cinema_id: str,
    new_name: str,
    address: str = "",
    location: str = "",
    state: str = "",
    sircuit: str = "",
    controller: str = "",
    gst: str = "",
    pan_number: str = "",
    digital_format: str = "",
    digital_charges: str = "",
    cdc_charges: str = "",
    digital_charges_per_show: str = ""
) -> Tuple[bool, str]:
    """
    Updates cinema details in cinema_master and synchronizes the
    denormalized cinema_name in all associated dcr_reports.
    """
    cleaned = (new_name or "").strip()
    if not cleaned:
        return False, "Cinema name cannot be empty."

    try:
        obj_id = ObjectId(cinema_id)
    except Exception:
        return False, "Invalid cinema ID format."

    try:
        # Check if another cinema already uses this name
        existing = await db.cinema_master.find_one({
            "_id": {"$ne": obj_id},
            "cinema_name": {"$regex": f"^{re.escape(cleaned)}$", "$options": "i"}
        })
        if existing:
            return False, f"Another cinema with the name '{cleaned}' already exists."

        now = datetime.now(timezone.utc)
        resolved_charges = (digital_charges or digital_charges_per_show or "").strip()
        update_data = {
            "cinema_name": cleaned,
            "address": (address or "").strip(),
            "location": (location or "").strip(),
            "state": (state or "").strip(),
            "sircuit": (sircuit or "").strip(),
            "controller": (controller or "").strip(),
            "gst": (gst or "").strip(),
            "pan_number": (pan_number or "").strip(),
            "digital_format": (digital_format or "").strip(),
            "digital_charges": resolved_charges,
            "digital_charges_per_show": resolved_charges,
            "cdc_charges": (cdc_charges or "").strip(),
            "updated_at": now
        }
        res = await db.cinema_master.update_one(
            {"_id": obj_id},
            {"$set": update_data}
        )
        if res.matched_count == 0:
            return False, "Cinema record not found."

        # Keep denormalized field in dcr_reports in sync as well
        await db.dcr_reports.update_many(
            {"cinema_id": obj_id},
            {"$set": {"cinema_name": cleaned}}
        )
        return True, f"Cinema '{cleaned}' successfully updated."
    except Exception as e:
        logger.error("Error updating cinema %s: %s", cinema_id, str(e))
        return False, f"Database error: {str(e)}"

# Alias for backwards compatibility
update_cinema_name = update_cinema_record

async def bulk_create_cinemas(cinemas_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Processes a list of cinema dictionaries for bulk upload.
    Skips cinemas whose name already exists in cinema_master (case-insensitive).
    Creates only new cinemas in a single batch operation.
    """
    try:
        existing_names = await db.cinema_master.distinct("cinema_name")
        existing_set = {str(n).strip().lower() for n in existing_names if n and str(n).strip()}

        seen_in_batch = set()
        to_insert: List[Dict[str, Any]] = []
        created_cinemas: List[str] = []
        skipped_cinemas: List[str] = []

        now = datetime.now(timezone.utc)

        for item in cinemas_list:
            raw_name = str(item.get("cinema_name") or "").strip()
            if not raw_name:
                continue

            name_key = raw_name.lower()
            if name_key in existing_set or name_key in seen_in_batch:
                skipped_cinemas.append(raw_name)
                continue

            seen_in_batch.add(name_key)
            resolved_charges = str(item.get("digital_charges") or item.get("digital_charges_per_show") or "").strip()
            doc = {
                "cinema_name": raw_name,
                "address": str(item.get("address") or "").strip(),
                "location": str(item.get("location") or "").strip(),
                "state": str(item.get("state") or "").strip(),
                "sircuit": str(item.get("sircuit") or "").strip(),
                "controller": str(item.get("controller") or "").strip(),
                "gst": str(item.get("gst") or "").strip(),
                "pan_number": str(item.get("pan_number") or "").strip(),
                "digital_format": str(item.get("digital_format") or "").strip(),
                "digital_charges": resolved_charges,
                "digital_charges_per_show": resolved_charges,
                "cdc_charges": str(item.get("cdc_charges") or "").strip(),
                "created_at": now,
                "updated_at": now
            }
            to_insert.append(doc)
            created_cinemas.append(raw_name)

        if to_insert:
            await db.cinema_master.insert_many(to_insert)

        return {
            "status": True,
            "created_count": len(created_cinemas),
            "skipped_count": len(skipped_cinemas),
            "created_cinemas": created_cinemas,
            "skipped_cinemas": skipped_cinemas
        }
    except Exception as e:
        logger.error("Error in bulk_create_cinemas: %s", str(e))
        return {
            "status": False,
            "message": f"Database error: {str(e)}",
            "created_count": 0,
            "skipped_count": 0,
            "created_cinemas": [],
            "skipped_cinemas": []
        }

async def delete_cinema_master_record(cinema_id: str) -> Tuple[bool, str]:
    """Deletes a cinema from cinema_master if no DCR reports are linked."""
    try:
        obj_id = ObjectId(cinema_id)
    except Exception:
        return False, "Invalid cinema ID format."

    try:
        count = await db.dcr_reports.count_documents({"cinema_id": obj_id})
        if count > 0:
            return False, f"Cannot delete cinema. {count} DCR report(s) are linked to this cinema."

        res = await db.cinema_master.delete_one({"_id": obj_id})
        if res.deleted_count > 0:
            return True, "Cinema deleted successfully."
        return False, "Cinema not found."
    except Exception as e:
        logger.error("Error deleting cinema %s: %s", cinema_id, str(e))
        return False, f"Database error: {str(e)}"

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
