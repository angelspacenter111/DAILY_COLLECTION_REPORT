import logging
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from bson import ObjectId
from pymongo.errors import AutoReconnect, PyMongoError

from database import db
from helpers.database_helper import sanitize_mongo_doc, find_cinema_master_match

logger = logging.getLogger(__name__)

async def init_release_indexes():
    """Ensures performance indexes exist on release_master collection."""
    try:
        await db.release_master.create_index([("created_at", -1)], background=True)
        await db.release_master.create_index([("movie_name", 1)], background=True)
        await db.release_master.create_index([("cinema_name", 1)], background=True)
        await db.release_master.create_index([("cinema_id", 1)], background=True)
        await db.release_master.create_index([("is_matched", 1)], background=True)
    except (AutoReconnect, PyMongoError) as e:
        logger.warning("Release Master index creation notice: %s", str(e))

def normalize_location_str(s: str) -> str:
    """Normalizes location string: lowercase, replaces punctuation and abbreviations."""
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[\(\)\[\],.\-_/]', ' ', s)
    s = re.sub(r'\b(east|e)\b', 'east', s)
    s = re.sub(r'\b(west|w)\b', 'west', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

CITY_STOP_WORDS = {
    "road", "mall", "street", "near", "opp", "city", "center", "centre", "complex",
    "mumbai", "delhi", "bangalore", "bengaluru", "kolkata", "chennai", "hyderabad",
    "pune", "ahmedabad", "surat", "jaipur", "lucknow", "kanpur", "nagpur", "indore",
    "thane", "bhopal", "patna", "vadodara", "ghaziabad", "ludhiana", "agra", "nashik",
    "india", "maharashtra", "gujarat", "karnataka", "up", "mp"
}

def check_location_match(loc_input: str, loc_master: str, addr_master: str = "") -> bool:
    """
    Checks if the input location matches the Cinema Master location or address.
    """
    if not loc_input or not str(loc_input).strip():
        return False

    norm_in = normalize_location_str(str(loc_input))
    norm_master_loc = normalize_location_str(str(loc_master or ""))
    norm_master_addr = normalize_location_str(str(addr_master or ""))

    if not norm_in:
        return False

    targets = [t for t in (norm_master_loc, norm_master_addr) if t]
    if not targets:
        return False

    for target in targets:
        # If one explicitly says 'east' and the other says 'west', they do not match
        in_east = "east" in norm_in.split()
        in_west = "west" in norm_in.split()
        target_east = "east" in target.split()
        target_west = "west" in target.split()

        if (in_east and target_west) or (in_west and target_east):
            continue

        if norm_in == target:
            return True

        # Check if one contains the other (e.g. "andheri" in "andheri east")
        # Ensure it's not just a stop word like "mumbai"
        if len(norm_in) >= 3 and (norm_in in target or target in norm_in):
            non_stop_in = [w for w in norm_in.split() if w not in CITY_STOP_WORDS]
            non_stop_target = [w for w in target.split() if w not in CITY_STOP_WORDS]
            if non_stop_in and non_stop_target:
                # at least one substantial token must match
                if any(w in target for w in non_stop_in) or any(w in norm_in for w in non_stop_target):
                    return True
            elif not non_stop_in and not non_stop_target:
                return True

        tokens_in = {w for w in norm_in.split() if len(w) >= 3 and w not in CITY_STOP_WORDS}
        tokens_target = {w for w in target.split() if len(w) >= 3 and w not in CITY_STOP_WORDS}
        if tokens_in and tokens_target and (tokens_in & tokens_target):
            return True

    return False

CHAIN_PREFIXES = {
    "pvr", "inox", "cinepolis", "carnival", "wave", "miraj", "movietime",
    "cinemax", "icon", "max", "mukta", "rajhans", "gold", "cinema", "cinemas",
    "theatre", "theaters", "theatres", "multiplex", "hall", "pictures",
    "ltd", "pvt", "limited", "private", "entertainment", "screen", "screens"
}

def compute_cinema_name_score(c_input: str, m_name: str) -> int:
    """
    Computes a matching score between a release cinema name and a cinema_master cinema name.
    Ensures that generic chain prefixes alone (like 'pvr' or 'inox') do not cause a false match.
    """
    c_lower = c_input.strip().lower()
    m_lower = m_name.strip().lower()
    if not c_lower or not m_lower:
        return 0

    if m_lower == c_lower:
        return 100

    # Substring check, but only if length of shorter is > 4 and not just a chain name
    min_str, max_str = (c_lower, m_lower) if len(c_lower) <= len(m_lower) else (m_lower, c_lower)
    if min_str in max_str and len(min_str) > 4 and min_str not in CHAIN_PREFIXES:
        return 85

    c_tokens = set(re.sub(r'[\(\)\[\],.\-_/]', ' ', c_lower).split())
    m_tokens = set(re.sub(r'[\(\)\[\],.\-_/]', ' ', m_lower).split())

    common = c_tokens & m_tokens
    distinct_common = common - CHAIN_PREFIXES

    if distinct_common:
        return 50 + len(distinct_common) * 15 + len(common) * 5

    return 0

async def find_cinema_and_location_match(cinema_name: str, location: str = "") -> Optional[Dict[str, Any]]:
    """
    Finds a cinema in cinema_master where BOTH cinema_name AND location match.
    1. Finds candidate cinemas matching cinema_name.
    2. Filters/selects candidate whose location or address matches the input location.
    """
    c_clean = (cinema_name or "").strip()
    l_clean = (location or "").strip()

    if not c_clean:
        return None

    try:
        cursor = db.cinema_master.find({})
        all_cinemas = await cursor.to_list(length=5000)
    except Exception as e:
        logger.error("Error querying cinema_master in find_cinema_and_location_match: %s", e)
        return None

    if not all_cinemas:
        return None

    candidates = []
    for c in all_cinemas:
        m_name = (c.get("cinema_name") or "").strip()
        if not m_name:
            continue

        m_loc = c.get("location") or ""
        m_addr = c.get("address") or ""

        # If location is provided, it MUST match the cinema's location or address
        loc_matched = False
        if l_clean:
            loc_matched = check_location_match(l_clean, m_loc, m_addr)
            if not loc_matched:
                continue
        else:
            # Location not specified in input
            loc_matched = True

        name_score = compute_cinema_name_score(c_clean, m_name)

        if name_score > 0 and loc_matched:
            candidates.append((name_score, c))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    return None

async def match_cinema_for_release(cinema_name: str, location: str = "") -> Tuple[bool, Optional[str], Optional[str], Dict[str, Any]]:
    """
    Attempts to match cinema name AND location from release excel against cinema_master collection.
    Returns:
        (is_matched, cinema_id_str, matched_cinema_name, matched_cinema_details_dict)
    """
    c_clean = (cinema_name or "").strip()
    l_clean = (location or "").strip()
    if not c_clean:
        return False, None, None, {}

    try:
        matched = await find_cinema_and_location_match(c_clean, l_clean)
        if matched:
            c_id = str(matched["_id"])
            m_name = matched.get("cinema_name") or c_clean
            details = {
                "cinema_id": c_id,
                "cinema_name": m_name,
                "location": matched.get("location") or l_clean,
                "state": matched.get("state") or "",
                "sircuit": matched.get("sircuit") or "",
                "controller": matched.get("controller") or "",
                "gst": matched.get("gst") or "",
                "pan_number": matched.get("pan_number") or "",
                "address": matched.get("address") or "",
                "digital_format": matched.get("digital_format") or "",
                "digital_charges": matched.get("digital_charges") or matched.get("digital_charges_per_show") or "",
                "cdc_charges": matched.get("cdc_charges") or "",
            }
            return True, c_id, m_name, details
        return False, None, None, {}
    except Exception as e:
        logger.error("Error matching cinema '%s' at location '%s' with cinema_master: %s", cinema_name, location, str(e))
        return False, None, None, {}

def compute_digital_charges(rate_str: Any, show_count: Any) -> Tuple[float, str]:
    """
    Computes Digital Charges = cinema_master Digital Charges * show_count.
    Returns (calculated_float, formatted_str).
    """
    try:
        clean_rate = re.sub(r'[^\d.]', '', str(rate_str or "").strip())
        rate_val = float(clean_rate) if clean_rate else 0.0
    except (ValueError, TypeError):
        rate_val = 0.0

    try:
        clean_count = re.sub(r'[^\d.]', '', str(show_count or "").strip())
        count_val = int(float(clean_count)) if clean_count else 1
        if count_val <= 0:
            count_val = 1
    except (ValueError, TypeError):
        count_val = 1

    total = rate_val * count_val
    if total > 0:
        if total.is_integer():
            formatted = f"{int(total):,}"
        else:
            formatted = f"{total:,.2f}"
    elif rate_val == 0.0 and (rate_str is None or str(rate_str).strip() == "" or str(rate_str).strip() == "0"):
        formatted = "0"
    else:
        formatted = "0"
    return total, formatted

async def enrich_release_with_cinema_master(doc: Dict[str, Any], c_master: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Enriches a release record with mapped Cinema Master fields:
    - Location
    - State
    - Circuit (from sircuit)
    - Digital Format
    - Digital Charges (calculated: cinema_master Digital Charges * show_count)
    - CDC Charges
    - Controller
    - GST Number
    - PAN Number
    """
    doc_cinema = doc.get("cinema_name", "")
    doc_location = doc.get("location", "")

    if not c_master and doc.get("cinema_id"):
        try:
            c_master = await db.cinema_master.find_one({"_id": ObjectId(doc["cinema_id"])})
        except Exception:
            c_master = None

    # If c_master is present and doc_location was specified, verify that location matches
    if c_master and doc_location:
        loc_ok = check_location_match(doc_location, c_master.get("location", ""), c_master.get("address", ""))
        if not loc_ok:
            c_master = await find_cinema_and_location_match(doc_cinema, doc_location)
            if not c_master and doc.get("_id"):
                try:
                    await db.release_master.update_one(
                        {"_id": doc["_id"] if isinstance(doc["_id"], ObjectId) else ObjectId(doc["_id"])},
                        {"$set": {"cinema_id": None, "is_matched": False, "matched_cinema_name": ""}}
                    )
                    doc["cinema_id"] = None
                except Exception:
                    pass

    if not c_master and doc_cinema:
        c_master = await find_cinema_and_location_match(doc_cinema, doc_location)
        if c_master and not doc.get("cinema_id"):
            try:
                await db.release_master.update_one(
                    {"_id": doc["_id"] if isinstance(doc["_id"], ObjectId) else ObjectId(doc["_id"])},
                    {"$set": {"cinema_id": c_master["_id"], "is_matched": True, "matched_cinema_name": c_master.get("cinema_name", "")}}
                )
                doc["cinema_id"] = str(c_master["_id"])
            except Exception:
                pass

    show_cnt = doc.get("show_count") if doc.get("show_count") is not None else 1

    if c_master:
        doc["is_matched"] = True
        doc["matched_cinema_name"] = c_master.get("cinema_name") or doc.get("cinema_name", "")
        doc["cinema_id"] = str(c_master["_id"])

        # Mapped fields from cinema_master
        doc["location"] = c_master.get("location") or doc.get("location") or ""
        doc["state"] = c_master.get("state") or ""
        doc["circuit"] = c_master.get("sircuit") or ""
        doc["digital_format"] = c_master.get("digital_format") or ""

        # Calculation: cinema_master Digital Charges * Show Count
        rate_val = c_master.get("digital_charges") or c_master.get("digital_charges_per_show") or ""
        doc["digital_charges_rate"] = rate_val
        total_dc, formatted_dc = compute_digital_charges(rate_val, show_cnt)
        doc["digital_charges_val"] = total_dc
        doc["digital_charges"] = formatted_dc

        doc["cdc_charges"] = c_master.get("cdc_charges") or ""
        doc["controller"] = c_master.get("controller") or ""
        doc["gst"] = c_master.get("gst") or ""
        doc["pan_number"] = c_master.get("pan_number") or ""
        doc["address"] = c_master.get("address") or ""
    else:
        doc["is_matched"] = False
        doc["matched_cinema_name"] = ""
        doc["location"] = doc.get("location") or ""
        doc["state"] = "-"
        doc["circuit"] = "-"
        doc["digital_format"] = "-"
        doc["digital_charges_rate"] = "0"
        doc["digital_charges_val"] = 0.0
        doc["digital_charges"] = "-"
        doc["cdc_charges"] = "-"
        doc["controller"] = "-"
        doc["gst"] = "-"
        doc["pan_number"] = "-"
        doc["address"] = "-"

    return doc

async def list_all_releases(filter_query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Lists all release records from release_master sorted by created_at descending.
    Performs $lookup on cinema_master to retrieve mapped cinema fields and calculated digital charges.
    """
    try:
        query = filter_query or {}
        pipeline = [
            {"$match": query},
            {"$sort": {"created_at": -1}},
            {
                "$lookup": {
                    "from": "cinema_master",
                    "localField": "cinema_id",
                    "foreignField": "_id",
                    "as": "matched_cinema_info"
                }
            }
        ]
        cursor = db.release_master.aggregate(pipeline)
        releases = []
        async for doc in cursor:
            cinema_list = doc.pop("matched_cinema_info", [])
            c_master = cinema_list[0] if cinema_list else None
            doc = await enrich_release_with_cinema_master(doc, c_master)

            doc["id"] = str(doc["_id"])
            doc["_id"] = str(doc["_id"])
            doc["movie_name"] = doc.get("movie_name") or ""
            doc["cinema_name"] = doc.get("cinema_name") or ""
            doc["show_timing"] = doc.get("show_timing") or ""
            doc["show_count"] = doc.get("show_count") if doc.get("show_count") is not None else 1

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

            releases.append(sanitize_mongo_doc(doc))
        return releases
    except Exception as e:
        logger.error("Failed to list releases: %s", str(e))
        return []

async def get_release_by_id(release_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single release document from release_master enriched with mapped Cinema Master fields."""
    try:
        doc = await db.release_master.find_one({"_id": ObjectId(release_id)})
        if doc:
            doc = await enrich_release_with_cinema_master(doc)
            doc["id"] = str(doc["_id"])
            doc["_id"] = str(doc["_id"])
            doc["movie_name"] = doc.get("movie_name") or ""
            doc["cinema_name"] = doc.get("cinema_name") or ""
            doc["show_timing"] = doc.get("show_timing") or ""
            doc["show_count"] = doc.get("show_count") if doc.get("show_count") is not None else 1

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

            return sanitize_mongo_doc(doc)
        return None
    except Exception as e:
        logger.error("Failed to get release %s: %s", release_id, str(e))
        return None

async def create_release_record(
    movie_name: str,
    cinema_name: str,
    location: str = "",
    show_timing: str = "",
    show_count: Any = 1
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Creates a new release record in release_master and performs
    automated matching with cinema_master.
    """
    m_clean = (movie_name or "").strip()
    c_clean = (cinema_name or "").strip()
    if not m_clean:
        return False, "Movie name cannot be empty.", None
    if not c_clean:
        return False, "Cinema name cannot be empty.", None

    try:
        try:
            parsed_count = int(str(show_count).strip())
        except (ValueError, TypeError):
            parsed_count = 1

        loc = (location or "").strip()
        is_matched, c_id, matched_name, matched_details = await match_cinema_for_release(c_clean, loc)

        if not loc and is_matched and matched_details.get("location"):
            loc = matched_details["location"]

        now = datetime.now(timezone.utc)
        doc = {
            "movie_name": m_clean,
            "cinema_name": c_clean,
            "location": loc,
            "show_timing": (show_timing or "").strip(),
            "show_count": parsed_count,
            "cinema_id": ObjectId(c_id) if c_id else None,
            "matched_cinema_name": matched_name or "",
            "is_matched": is_matched,
            "matched_details": matched_details,
            "created_at": now,
            "updated_at": now
        }
        res = await db.release_master.insert_one(doc)
        doc["id"] = str(res.inserted_id)
        doc["_id"] = str(res.inserted_id)
        doc["created_at_formatted"] = now.strftime("%d %b %Y, %I:%M %p")
        doc["updated_at_formatted"] = doc["created_at_formatted"]
        return True, "Release record created successfully.", sanitize_mongo_doc(doc)
    except Exception as e:
        logger.error("Error creating release record: %s", str(e))
        return False, f"Database error: {str(e)}", None

async def update_release_record(
    release_id: str,
    movie_name: str,
    cinema_name: str,
    location: str = "",
    show_timing: str = "",
    show_count: Any = 1
) -> Tuple[bool, str]:
    """
    Updates an existing release record and automatically refreshes its
    Cinema Master match status.
    """
    m_clean = (movie_name or "").strip()
    c_clean = (cinema_name or "").strip()
    if not m_clean:
        return False, "Movie name cannot be empty."
    if not c_clean:
        return False, "Cinema name cannot be empty."

    try:
        obj_id = ObjectId(release_id)
    except Exception:
        return False, "Invalid release ID format."

    try:
        try:
            parsed_count = int(str(show_count).strip())
        except (ValueError, TypeError):
            parsed_count = 1

        loc = (location or "").strip()
        is_matched, c_id, matched_name, matched_details = await match_cinema_for_release(c_clean, loc)

        if not loc and is_matched and matched_details.get("location"):
            loc = matched_details["location"]

        now = datetime.now(timezone.utc)
        update_data = {
            "movie_name": m_clean,
            "cinema_name": c_clean,
            "location": loc,
            "show_timing": (show_timing or "").strip(),
            "show_count": parsed_count,
            "cinema_id": ObjectId(c_id) if c_id else None,
            "matched_cinema_name": matched_name or "",
            "is_matched": is_matched,
            "matched_details": matched_details,
            "updated_at": now
        }
        res = await db.release_master.update_one({"_id": obj_id}, {"$set": update_data})
        if res.matched_count == 0:
            return False, "Release record not found."
        return True, "Release record updated successfully."
    except Exception as e:
        logger.error("Error updating release %s: %s", release_id, str(e))
        return False, f"Database error: {str(e)}"

async def delete_release_record(release_id: str) -> bool:
    """Deletes a single release record by ID."""
    try:
        res = await db.release_master.delete_one({"_id": ObjectId(release_id)})
        return res.deleted_count > 0
    except Exception as e:
        logger.error("Error deleting release %s: %s", release_id, str(e))
        return False

async def clear_all_releases() -> int:
    """Deletes all release records from release_master."""
    try:
        res = await db.release_master.delete_many({})
        return res.deleted_count
    except Exception as e:
        logger.error("Error clearing release_master: %s", str(e))
        return 0

async def bulk_create_releases(releases_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Processes a list of releases extracted from Excel.
    For each item:
    - Extracts Movie Name, Cinema Name, Location, Show Timing, Show Count
    - Matches Cinema Name against cinema_master
    - Detects and skips exact duplicates (same movie, cinema, and timing)
    - Batch inserts valid records into release_master
    Returns statistics dict.
    """
    try:
        # Load existing release signatures to avoid duplicates
        existing_cursor = db.release_master.find({}, {"movie_name": 1, "cinema_name": 1, "show_timing": 1})
        existing_records = await existing_cursor.to_list(length=20000)
        existing_set = {
            (
                str(r.get("movie_name") or "").strip().lower(),
                str(r.get("cinema_name") or "").strip().lower(),
                str(r.get("show_timing") or "").strip().lower()
            )
            for r in existing_records
        }

        seen_in_batch = set()
        to_insert: List[Dict[str, Any]] = []
        created_count = 0
        skipped_count = 0
        matched_count = 0
        unmatched_count = 0

        now = datetime.now(timezone.utc)

        for item in releases_list:
            raw_movie = str(item.get("movie_name") or "").strip()
            raw_cinema = str(item.get("cinema_name") or "").strip()
            raw_location = str(item.get("location") or "").strip()
            raw_timing = str(item.get("show_timing") or "").strip()
            raw_count = item.get("show_count")

            if not raw_movie or not raw_cinema:
                continue

            try:
                parsed_count = int(float(str(raw_count or 1).strip()))
                if parsed_count <= 0:
                    parsed_count = 1
            except (ValueError, TypeError):
                # Count the number of timings separated by commas or slashes if timing provided
                if raw_timing and ("," in raw_timing or "/" in raw_timing or ";" in raw_timing):
                    parsed_count = len([t for t in re.split(r'[,;/]', raw_timing) if t.strip()])
                else:
                    parsed_count = 1

            sig = (raw_movie.lower(), raw_cinema.lower(), raw_timing.lower())
            if sig in existing_set or sig in seen_in_batch:
                skipped_count += 1
                continue

            seen_in_batch.add(sig)

            # Match against cinema_master with cinema_name AND location
            is_matched, c_id, matched_name, matched_details = await match_cinema_for_release(raw_cinema, raw_location)

            loc = raw_location
            if not loc and is_matched and matched_details.get("location"):
                loc = matched_details["location"]

            if is_matched:
                matched_count += 1
            else:
                unmatched_count += 1

            doc = {
                "movie_name": raw_movie,
                "cinema_name": raw_cinema,
                "location": loc,
                "show_timing": raw_timing,
                "show_count": parsed_count,
                "cinema_id": ObjectId(c_id) if c_id else None,
                "matched_cinema_name": matched_name or "",
                "is_matched": is_matched,
                "matched_details": matched_details,
                "created_at": now,
                "updated_at": now
            }
            to_insert.append(doc)
            created_count += 1

        if to_insert:
            await db.release_master.insert_many(to_insert)

        return {
            "status": True,
            "created_count": created_count,
            "skipped_count": skipped_count,
            "matched_count": matched_count,
            "unmatched_count": unmatched_count,
            "total_processed": len(releases_list),
            "message": f"Successfully processed {len(releases_list)} rows: {created_count} new release(s) added ({matched_count} matched with Cinema Master), {skipped_count} skipped as duplicates."
        }
    except Exception as e:
        logger.exception("Error in bulk_create_releases: %s", e)
        return {
            "status": False,
            "created_count": 0,
            "skipped_count": 0,
            "matched_count": 0,
            "unmatched_count": 0,
            "total_processed": len(releases_list),
            "message": f"Database bulk insert error: {str(e)}"
        }

async def get_release_stats(filter_query: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Calculates KPI statistics for the Release Master dashboard."""
    try:
        query = filter_query or {}
        total_releases = await db.release_master.count_documents(query)
        distinct_movies = await db.release_master.distinct("movie_name", query)
        matched_cinemas = await db.release_master.count_documents({**query, "is_matched": True})
        unmatched_cinemas = await db.release_master.count_documents({**query, "is_matched": False})

        # Calculate total shows scheduled
        pipeline = [
            {"$match": query},
            {"$group": {"_id": None, "total_shows": {"$sum": "$show_count"}}}
        ]
        agg_res = await db.release_master.aggregate(pipeline).to_list(length=1)
        total_shows = agg_res[0]["total_shows"] if agg_res else 0

        return {
            "total_releases": total_releases,
            "distinct_movies_count": len([m for m in distinct_movies if m]),
            "matched_cinemas": matched_cinemas,
            "unmatched_cinemas": unmatched_cinemas,
            "total_shows": total_shows,
        }
    except Exception as e:
        logger.error("Error computing release stats: %s", e)
        return {
            "total_releases": 0,
            "distinct_movies_count": 0,
            "matched_cinemas": 0,
            "unmatched_cinemas": 0,
            "total_shows": 0,
        }
