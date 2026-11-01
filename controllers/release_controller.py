import csv
import io
import logging
from io import BytesIO
from typing import Optional, Dict, Any, List

from fastapi import Request, UploadFile, File
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

from config import BASE_URL
from controllers.auth_controller import get_current_user
from helpers.auth_helper import build_movie_filter_query
from helpers.release_helper import (
    list_all_releases,
    get_release_by_id,
    create_release_record,
    update_release_record,
    delete_release_record,
    clear_all_releases,
    bulk_create_releases,
    get_release_stats,
)

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")

async def releases_view(request: Request):
    """Renders the Release Master management page."""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    filter_query = build_movie_filter_query(current_user)
    releases = await list_all_releases(filter_query)
    stats = await get_release_stats(filter_query)

    context = {
        "BASE_URL": BASE_URL,
        "current_user": current_user,
        "releases": releases,
        "stats": stats,
    }
    return templates.TemplateResponse(request=request, name="releases.html", context=context)

async def get_release_action(request: Request, release_id: str):
    """Fetches full JSON details of a single release record."""
    current_user = await get_current_user(request)
    if not current_user:
        return JSONResponse({"status": False, "message": "Unauthorized."}, status_code=401)

    release = await get_release_by_id(release_id)
    if not release:
        return JSONResponse({"status": False, "message": "Release record not found."}, status_code=404)

    return JSONResponse({"status": True, "data": release})

async def create_release_action(request: Request):
    """Creates a new release record (Super Admin only)."""
    current_user = await get_current_user(request)
    if not current_user or current_user.get("role") != "super_admin":
        return JSONResponse({"status": False, "message": "Unauthorized. Super Admin access required."}, status_code=403)

    try:
        data = await request.json()
        movie_name = str(data.get("movie_name", "")).strip()
        cinema_name = str(data.get("cinema_name", "")).strip()
        location = str(data.get("location", "")).strip()
        show_timing = str(data.get("show_timing", "")).strip()
        show_count = data.get("show_count", 1)

        success, message, created_doc = await create_release_record(
            movie_name=movie_name,
            cinema_name=cinema_name,
            location=location,
            show_timing=show_timing,
            show_count=show_count,
        )
        if not success:
            return JSONResponse({"status": False, "message": message}, status_code=400)

        return JSONResponse({
            "status": True,
            "message": message,
            "data": created_doc,
        })
    except Exception as e:
        logger.exception("Error in create_release_action: %s", e)
        return JSONResponse({"status": False, "message": f"Server error: {str(e)}"}, status_code=500)

async def update_release_action(request: Request, release_id: str):
    """Updates release details (Super Admin only)."""
    current_user = await get_current_user(request)
    if not current_user or current_user.get("role") != "super_admin":
        return JSONResponse({"status": False, "message": "Unauthorized. Super Admin access required."}, status_code=403)

    try:
        data = await request.json()
        movie_name = str(data.get("movie_name", "")).strip()
        cinema_name = str(data.get("cinema_name", "")).strip()
        location = str(data.get("location", "")).strip()
        show_timing = str(data.get("show_timing", "")).strip()
        show_count = data.get("show_count", 1)

        success, message = await update_release_record(
            release_id=release_id,
            movie_name=movie_name,
            cinema_name=cinema_name,
            location=location,
            show_timing=show_timing,
            show_count=show_count,
        )
        if not success:
            return JSONResponse({"status": False, "message": message}, status_code=400)

        updated_doc = await get_release_by_id(release_id)
        return JSONResponse({
            "status": True,
            "message": message,
            "data": updated_doc,
        })
    except Exception as e:
        logger.exception("Error in update_release_action: %s", e)
        return JSONResponse({"status": False, "message": f"Server error: {str(e)}"}, status_code=500)

async def delete_release_action(request: Request, release_id: str):
    """Deletes a single release record (Super Admin only)."""
    current_user = await get_current_user(request)
    if not current_user or current_user.get("role") != "super_admin":
        return JSONResponse({"status": False, "message": "Unauthorized. Super Admin access required."}, status_code=403)

    success = await delete_release_record(release_id)
    if success:
        return JSONResponse({"status": True, "message": "Release deleted successfully."})
    return JSONResponse({"status": False, "message": "Failed to delete release."}, status_code=400)

async def clear_all_releases_action(request: Request):
    """Deletes all release records (Super Admin only)."""
    current_user = await get_current_user(request)
    if not current_user or current_user.get("role") != "super_admin":
        return JSONResponse({"status": False, "message": "Unauthorized. Super Admin access required."}, status_code=403)

    count = await clear_all_releases()
    return JSONResponse({"status": True, "message": f"Cleared all {count} release records."})

async def download_releases_excel(request: Request):
    """
    Exports all current releases to an Excel (.xlsx) file.
    Includes match status and matched Cinema Master names.
    """
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    filter_query = build_movie_filter_query(current_user)
    releases = await list_all_releases(filter_query)

    wb = Workbook()
    ws = wb.active
    ws.title = "Release Master"
    ws.views.sheetView[0].showGridLines = True

    headers = [
        "S.No.",
        "Movie Name",
        "Cinema Name",
        "Location",
        "State",
        "Circuit",
        "Show Timing",
        "Show Count",
        "Digital Format",
        "Digital Charges",
        "CDC Charges",
        "Controller",
        "GST Number",
        "PAN Number",
        "Cinema Master Status",
        "Matched Cinema Name",
        "Added On",
        "Last Updated"
    ]

    header_fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    border_thin = Side(border_style="thin", color="CBD5E1")
    cell_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)

    ws.append(headers)
    ws.row_dimensions[1].height = 28

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
        cell.border = cell_border

    data_font = Font(name="Calibri", size=10)
    data_align_left = Alignment(horizontal="left", vertical="center")
    data_align_center = Alignment(horizontal="center", vertical="center")

    for idx, r in enumerate(releases, start=1):
        status_text = "Matched" if r.get("is_matched") else "Not Matched"
        row_vals = [
            idx,
            r.get("movie_name", ""),
            r.get("cinema_name", ""),
            r.get("location", ""),
            r.get("state", ""),
            r.get("circuit", ""),
            r.get("show_timing", ""),
            r.get("show_count", 1),
            r.get("digital_format", ""),
            r.get("digital_charges", ""),
            r.get("cdc_charges", ""),
            r.get("controller", ""),
            r.get("gst", ""),
            r.get("pan_number", ""),
            status_text,
            r.get("matched_cinema_name", "-") if r.get("is_matched") else "-",
            r.get("created_at_formatted", "N/A"),
            r.get("updated_at_formatted", "N/A"),
        ]
        ws.append(row_vals)
        curr_row = idx + 1
        ws.row_dimensions[curr_row].height = 22

        for col_idx in range(1, len(row_vals) + 1):
            cell = ws.cell(row=curr_row, column=col_idx)
            cell.font = data_font
            cell.border = cell_border
            # center align numbers and statuses: S.No (1), State (5), Circuit (6), Shows (8), Format (9), Charges (10), CDC (11), GST (13), PAN (14), Status (15), Dates (17, 18)
            if col_idx in (1, 5, 6, 8, 9, 10, 11, 13, 14, 15, 17, 18):
                cell.alignment = data_align_center
            else:
                cell.alignment = data_align_left

            # Highlight status cell
            if col_idx == 15:
                if r.get("is_matched"):
                    cell.fill = PatternFill(start_color="ECFDF5", end_color="ECFDF5", fill_type="solid")
                    cell.font = Font(name="Calibri", size=10, bold=True, color="059669")
                else:
                    cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                    cell.font = Font(name="Calibri", size=10, bold=True, color="D97706")

    # Auto-adjust column widths
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 13)

    ws.column_dimensions["A"].width = 7   # S.No
    ws.column_dimensions["B"].width = 24  # Movie Name
    ws.column_dimensions["C"].width = 28  # Cinema Name
    ws.column_dimensions["D"].width = 18  # Location
    ws.column_dimensions["E"].width = 16  # State
    ws.column_dimensions["F"].width = 16  # Circuit
    ws.column_dimensions["G"].width = 28  # Show Timing
    ws.column_dimensions["H"].width = 14  # Show Count
    ws.column_dimensions["I"].width = 16  # Digital Format
    ws.column_dimensions["J"].width = 16  # Digital Charges
    ws.column_dimensions["K"].width = 16  # CDC Charges
    ws.column_dimensions["L"].width = 18  # Controller
    ws.column_dimensions["M"].width = 18  # GST Number
    ws.column_dimensions["N"].width = 16  # PAN Number
    ws.column_dimensions["O"].width = 18  # Status
    ws.column_dimensions["P"].width = 28  # Matched Cinema Name

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = "Release_Master_Export.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

async def download_release_template_excel(request: Request):
    """
    Downloads an empty/sample pre-formatted Excel template for bulk uploading releases.
    Contains the 5 specified columns:
    1. Movie Name
    2. Cinema Name
    3. Location
    4. Show Timing
    5. Show Count
    """
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    wb = Workbook()
    ws = wb.active
    ws.title = "Release_Template"
    ws.views.sheetView[0].showGridLines = True

    headers = [
        "Movie Name *",
        "Cinema Name *",
        "Location",
        "Show Timing",
        "Show Count"
    ]

    header_fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center")

    border_thin = Side(border_style="thin", color="CBD5E1")
    cell_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)

    ws.append(headers)
    ws.row_dimensions[1].height = 26

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
        cell.border = cell_border

    sample_rows = [
        ["KGF Chapter 2", "PVR Phoenix Marketcity", "Viman Nagar, Pune", "10:30 AM, 02:15 PM, 06:45 PM, 10:15 PM", 4],
        ["Pushpa 2: The Rule", "Inox City Center", "Sector 12, Ghaziabad", "11:00 AM, 03:00 PM, 07:00 PM", 3],
        ["Singham Again", "Cinepolis Nexus Mall", "Koramangala, Bangalore", "09:45 AM, 01:15 PM, 05:00 PM, 08:30 PM", 4],
        ["Stree 2", "INOX AIPL Joy Street Gurugram", "Gurugram, Haryana", "12:00 PM, 04:30 PM, 08:30 PM", 3],
    ]

    for r_idx, row_data in enumerate(sample_rows, start=2):
        ws.append(row_data)
        ws.row_dimensions[r_idx].height = 22
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=r_idx, column=col_idx)
            cell.font = Font(name="Calibri", size=10)
            cell.border = cell_border
            if col_idx == 5:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = 24
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["D"].width = 36
    ws.column_dimensions["E"].width = 14

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = "Release_Master_Upload_Template.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

async def bulk_upload_releases_action(request: Request, file: UploadFile = File(...)):
    """
    Handles file upload (.xlsx, .xls, .csv) for bulk importing releases.
    Automatically matches Cinema Name against Cinema Master.
    """
    current_user = await get_current_user(request)
    if not current_user or current_user.get("role") != "super_admin":
        return JSONResponse({"status": False, "message": "Unauthorized. Super Admin access required."}, status_code=403)

    if not file or not file.filename:
        return JSONResponse({"status": False, "message": "No file uploaded."}, status_code=400)

    filename = file.filename.lower()
    if not (filename.endswith(".xlsx") or filename.endswith(".xls") or filename.endswith(".csv")):
        return JSONResponse({
            "status": False,
            "message": "Invalid file format. Please upload an Excel (.xlsx, .xls) or CSV file."
        }, status_code=400)

    try:
        content = await file.read()
        rows_data = []

        if filename.endswith(".csv"):
            text_stream = io.StringIO(content.decode("utf-8-sig", errors="replace"))
            csv_reader = csv.reader(text_stream)
            rows_data = [row for row in csv_reader if any(cell.strip() for cell in row)]
        else:
            wb = load_workbook(filename=BytesIO(content), data_only=True)
            ws = wb.active
            for row in ws.iter_rows(values_only=True):
                if row and any(v is not None and str(v).strip() for v in row):
                    rows_data.append(list(row))

        if not rows_data or len(rows_data) < 2:
            return JSONResponse({
                "status": False,
                "message": "The uploaded file does not contain any data rows."
            }, status_code=400)

        header_row = [str(cell or "").strip().lower() for cell in rows_data[0]]
        header_map = _extract_release_header_indices(header_row)

        if "movie_name" not in header_map or "cinema_name" not in header_map:
            return JSONResponse({
                "status": False,
                "message": "Required columns ('Movie Name' and 'Cinema Name') could not be identified in the header row."
            }, status_code=400)

        releases_to_create = []
        for row in rows_data[1:]:
            item = _build_release_dict(row, header_map)
            if item.get("movie_name") and item.get("cinema_name"):
                releases_to_create.append(item)

        if not releases_to_create:
            return JSONResponse({
                "status": False,
                "message": "No valid release records found with both Movie Name and Cinema Name."
            }, status_code=400)

        result = await bulk_create_releases(releases_to_create)
        return JSONResponse(result)

    except Exception as e:
        logger.exception("Bulk upload releases failed: %s", e)
        return JSONResponse({
            "status": False,
            "message": f"Failed to process file: {str(e)}"
        }, status_code=500)

def _extract_release_header_indices(header_row: List[str]) -> Dict[str, int]:
    """
    Intelligently maps column indices for:
    - movie_name
    - cinema_name
    - location
    - show_timing
    - show_count
    """
    header_map = {}
    for idx, raw_h in enumerate(header_row):
        h = raw_h.lower().replace("_", " ").replace("-", " ").strip()

        # Movie Name
        if ("movie" in h or "film" in h or "title" in h) and "movie_name" not in header_map:
            header_map["movie_name"] = idx

        # Cinema Name
        elif ("cinema" in h or "theatre" in h or "theater" in h or "hall" in h) and "cinema_name" not in header_map:
            header_map["cinema_name"] = idx

        # Show Timing
        elif ("timing" in h or "timings" in h or "show time" in h or "time" in h) and "show_timing" not in header_map:
            header_map["show_timing"] = idx

        # Show Count
        elif ("show count" in h or "showcount" in h or "no of shows" in h or "shows" in h or "count" in h) and "show_count" not in header_map:
            header_map["show_count"] = idx

        # Location
        elif ("location" in h or "city" in h or "place" in h or "area" in h) and "location" not in header_map:
            header_map["location"] = idx

    # Positional fallback if standard 5 columns order was used
    if "movie_name" not in header_map and len(header_row) > 0:
        header_map["movie_name"] = 0
    if "cinema_name" not in header_map and len(header_row) > 1:
        header_map["cinema_name"] = 1
    if "location" not in header_map and len(header_row) > 2:
        header_map["location"] = 2
    if "show_timing" not in header_map and len(header_row) > 3:
        header_map["show_timing"] = 3
    if "show_count" not in header_map and len(header_row) > 4:
        header_map["show_count"] = 4

    return header_map

def _build_release_dict(row: Any, header_map: Dict[str, int]) -> Dict[str, Any]:
    """Extracts release fields from a data row using the resolved header map."""
    def get_val(key: str) -> str:
        idx = header_map.get(key)
        if idx is not None and idx < len(row):
            val = row[idx]
            return str(val).strip() if val is not None else ""
        return ""

    raw_count = get_val("show_count")
    try:
        parsed_count = int(float(raw_count)) if raw_count else 1
    except (ValueError, TypeError):
        parsed_count = 1

    return {
        "movie_name": get_val("movie_name"),
        "cinema_name": get_val("cinema_name"),
        "location": get_val("location"),
        "show_timing": get_val("show_timing"),
        "show_count": parsed_count,
    }
