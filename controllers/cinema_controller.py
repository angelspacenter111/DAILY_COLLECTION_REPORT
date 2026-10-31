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
from helpers.database_helper import (
    list_all_cinemas,
    get_cinema_by_id,
    create_cinema_master_record,
    update_cinema_record,
    delete_cinema_master_record,
    bulk_create_cinemas,
    migrate_existing_cinemas_to_master,
)

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")

async def cinemas_view(request: Request):
    """Renders the Cinema Master management page."""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    cinemas = await list_all_cinemas()
    total_cinemas = len(cinemas)
    cinemas_with_reports = sum(1 for c in cinemas if c.get("report_count", 0) > 0)
    total_linked_reports = sum(c.get("report_count", 0) for c in cinemas)

    context = {
        "BASE_URL": BASE_URL,
        "current_user": current_user,
        "cinemas": cinemas,
        "stats": {
            "total_cinemas": total_cinemas,
            "cinemas_with_reports": cinemas_with_reports,
            "total_linked_reports": total_linked_reports,
        }
    }
    return templates.TemplateResponse(request=request, name="cinemas.html", context=context)

async def create_cinema_action(request: Request):
    """Manual cinema creation is disabled per system rules. Cinemas can only be created via Excel Bulk Upload."""
    current_user = await get_current_user(request)
    if not current_user or current_user.get("role") != "super_admin":
        return JSONResponse({"status": False, "message": "Unauthorized. Super Admin access required."}, status_code=403)

    return JSONResponse({
        "status": False,
        "message": "Manual cinema creation is disabled. Cinemas can only be created via Excel Bulk Upload."
    }, status_code=400)

async def update_cinema_action(request: Request, cinema_id: str):
    """API endpoint to edit and update a cinema and its details."""
    current_user = await get_current_user(request)
    if not current_user or current_user.get("role") != "super_admin":
        return JSONResponse({"status": False, "message": "Unauthorized. Super Admin access required."}, status_code=403)

    try:
        data = await request.json()
        new_name = str(data.get("cinema_name", "")).strip()
        address = str(data.get("address", "")).strip()
        location = str(data.get("location", "")).strip()
        state = str(data.get("state", "")).strip()
        sircuit = str(data.get("sircuit", "")).strip()
        controller = str(data.get("controller", "")).strip()
        gst = str(data.get("gst", "")).strip()
        pan_number = str(data.get("pan_number", "")).strip()

        if not new_name:
            return JSONResponse({"status": False, "message": "Cinema name cannot be empty."}, status_code=400)

        success, message = await update_cinema_record(
            cinema_id=cinema_id,
            new_name=new_name,
            address=address,
            location=location,
            state=state,
            sircuit=sircuit,
            controller=controller,
            gst=gst,
            pan_number=pan_number,
        )
        if not success:
            return JSONResponse({"status": False, "message": message}, status_code=400)

        logger.info("[CINEMA MASTER] Super Admin '%s' updated cinema %s to '%s'", current_user["username"], cinema_id, new_name)
        return JSONResponse({
            "status": True,
            "message": message,
            "cinema_id": cinema_id,
            "cinema_name": new_name,
            "address": address,
            "location": location,
            "state": state,
            "sircuit": sircuit,
            "controller": controller,
            "gst": gst,
            "pan_number": pan_number,
        })
    except Exception as e:
        logger.exception("Error updating cinema: %s", e)
        return JSONResponse({"status": False, "message": f"Server error: {str(e)}"}, status_code=500)

async def delete_cinema_action(request: Request, cinema_id: str):
    """API endpoint to delete a cinema from cinema_master."""
    current_user = await get_current_user(request)
    if not current_user or current_user.get("role") != "super_admin":
        return JSONResponse({"status": False, "message": "Unauthorized. Super Admin access required."}, status_code=403)

    try:
        success, message = await delete_cinema_master_record(cinema_id)
        if not success:
            return JSONResponse({"status": False, "message": message}, status_code=400)

        logger.info("[CINEMA MASTER] Super Admin '%s' deleted cinema ID '%s'", current_user["username"], cinema_id)
        return JSONResponse({
            "status": True,
            "message": message
        })
    except Exception as e:
        logger.exception("Error deleting cinema: %s", e)
        return JSONResponse({"status": False, "message": f"Server error: {str(e)}"}, status_code=500)

async def get_cinema_action(request: Request, cinema_id: str):
    """API endpoint to fetch a single cinema details."""
    current_user = await get_current_user(request)
    if not current_user:
        return JSONResponse({"status": False, "message": "Unauthorized."}, status_code=401)

    cinema = await get_cinema_by_id(cinema_id)
    if not cinema:
        return JSONResponse({"status": False, "message": "Cinema not found."}, status_code=404)

    return JSONResponse({
        "status": True,
        "cinema": cinema
    })

# -------------------------------------------------------------
# Excel Download & Bulk Upload Endpoints
# -------------------------------------------------------------

async def download_cinemas_excel(request: Request):
    """Generates and downloads formatted Excel file containing all cinemas."""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    cinemas = await list_all_cinemas()

    wb = Workbook()
    ws = wb.active
    ws.title = "Cinema Master"

    headers = [
        "S.No.",
        "Cinema / Theatre Name",
        "Address",
        "Location",
        "State",
        "Sircuit",
        "Contoller",
        "GST Number",
        "PAN Number",
        "Linked DCR Reports",
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

    for idx, c in enumerate(cinemas, start=1):
        row_vals = [
            idx,
            c.get("cinema_name", ""),
            c.get("address", ""),
            c.get("location", ""),
            c.get("state", ""),
            c.get("sircuit", ""),
            c.get("controller", ""),
            c.get("gst", ""),
            c.get("pan_number", ""),
            c.get("report_count", 0),
            c.get("created_at_formatted", "N/A"),
            c.get("updated_at_formatted", "N/A"),
        ]
        ws.append(row_vals)
        curr_row = idx + 1
        ws.row_dimensions[curr_row].height = 22

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=curr_row, column=col_idx)
            cell.font = data_font
            cell.border = cell_border
            # center align numbers and dates
            if col_idx in (1, 10, 11, 12):
                cell.alignment = data_align_center
            else:
                cell.alignment = data_align_left

    # Auto-fit column widths
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 32
    ws.freeze_panes = "A2"

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Cinema_Master_Report.xlsx"}
    )

async def download_cinema_template_excel(request: Request):
    """Downloads sample template Excel file for bulk upload."""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    wb = Workbook()
    ws = wb.active
    ws.title = "Cinema Template"

    headers = [
        "Cinema Name *",
        "Address",
        "Location",
        "State",
        "Sircuit",
        "Contoller",
        "GST",
        "PAN Number"
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
        ["PVR Phoenix Marketcity", "Viman Nagar Road", "Pune", "Maharashtra", "Bombay", "Mr. Sharma", "27AAAAA0000A1Z5", "ABCDE1234F"],
        ["Inox City Center", "Sector 12", "Ghaziabad", "Uttar Pradesh", "Delhi-UP", "Mr. Verma", "07BBBBB0000B1Z6", "BBBBB0000B"],
        ["Cinepolis Nexus Mall", "Koramangala 7th Block", "Bangalore", "Karnataka", "South", "Mr. Rao", "29CCCCC0000C1Z7", "CCCCC0000C"]
    ]

    for r_idx, row_data in enumerate(sample_rows, start=2):
        ws.append(row_data)
        ws.row_dimensions[r_idx].height = 22
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=r_idx, column=col_idx)
            cell.font = Font(name="Calibri", size=10)
            cell.border = cell_border
            cell.alignment = Alignment(horizontal="left", vertical="center")

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = 24
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 30

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Cinema_Bulk_Upload_Template.xlsx"}
    )

async def bulk_upload_cinemas_action(request: Request, file: UploadFile = File(...)):
    """
    API endpoint for bulk uploading cinemas from an Excel or CSV file.
    If a cinema name already exists, it is safely skipped.
    Only new cinemas are inserted into cinema_master.
    """
    current_user = await get_current_user(request)
    if not current_user or current_user.get("role") != "super_admin":
        return JSONResponse({"status": False, "message": "Unauthorized. Super Admin access required."}, status_code=403)

    filename = file.filename or ""
    lower_fname = filename.lower()
    if not (lower_fname.endswith(".xlsx") or lower_fname.endswith(".xls") or lower_fname.endswith(".csv")):
        return JSONResponse({"status": False, "message": "Invalid file format. Please upload an Excel (.xlsx/.xls) or CSV (.csv) file."}, status_code=400)

    try:
        content = await file.read()
        cinemas_to_process: List[Dict[str, Any]] = []

        if lower_fname.endswith(".csv"):
            text_content = content.decode("utf-8-sig", errors="ignore")
            csv_reader = csv.reader(io.StringIO(text_content))
            rows = list(csv_reader)
            if not rows:
                return JSONResponse({"status": False, "message": "The uploaded CSV file is empty."}, status_code=400)

            header_row = [str(c).strip().lower() for c in rows[0]]
            header_map = _extract_header_indices(header_row)

            for row in rows[1:]:
                if not any(str(cell).strip() for cell in row):
                    continue
                cinemas_to_process.append(_build_cinema_dict(row, header_map))
        else:
            # Excel file
            wb = load_workbook(BytesIO(content), data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return JSONResponse({"status": False, "message": "The uploaded Excel file is empty."}, status_code=400)

            header_row = [str(c or "").strip().lower() for c in rows[0]]
            header_map = _extract_header_indices(header_row)

            for row in rows[1:]:
                if not any(str(cell or "").strip() for cell in row):
                    continue
                cinemas_to_process.append(_build_cinema_dict(row, header_map))

        if not cinemas_to_process:
            return JSONResponse({"status": False, "message": "No valid data rows found in the uploaded file."}, status_code=400)

        result = await bulk_create_cinemas(cinemas_to_process)
        if not result.get("status"):
            return JSONResponse({"status": False, "message": result.get("message", "Database error occurred.")}, status_code=500)

        created_cnt = result.get("created_count", 0)
        skipped_cnt = result.get("skipped_count", 0)

        if created_cnt > 0:
            try:
                await migrate_existing_cinemas_to_master()
            except Exception as mig_err:
                logger.warning("Post bulk-upload migration notice: %s", mig_err)

        msg = f"Bulk upload completed: {created_cnt} new cinema(s) added successfully."
        if skipped_cnt > 0:
            msg += f" {skipped_cnt} cinema(s) skipped (already exists)."

        logger.info(
            "[CINEMA MASTER] Bulk upload by '%s': created=%d, skipped=%d from file '%s'",
            current_user["username"], created_cnt, skipped_cnt, filename
        )

        return JSONResponse({
            "status": True,
            "message": msg,
            "created_count": created_cnt,
            "skipped_count": skipped_cnt,
            "created_cinemas": result.get("created_cinemas", []),
            "skipped_cinemas": result.get("skipped_cinemas", [])
        })

    except Exception as e:
        logger.exception("Error during bulk upload of cinemas: %s", e)
        return JSONResponse({"status": False, "message": f"Failed to process file: {str(e)}"}, status_code=500)

def _extract_header_indices(header_row: List[str]) -> Dict[str, int]:
    """Maps header column indices based on common column names."""
    header_map: Dict[str, int] = {}
    for idx, col in enumerate(header_row):
        c = col.strip().lower()
        if not c:
            continue
        if "name" in c or "cinema" in c or "theatre" in c or "hall" in c:
            if "cinema_name" not in header_map:
                header_map["cinema_name"] = idx
        elif "addr" in c:
            if "address" not in header_map:
                header_map["address"] = idx
        elif "loc" in c or "city" in c or "area" in c:
            if "location" not in header_map:
                header_map["location"] = idx
        elif "state" in c or "region" in c:
            if "state" not in header_map:
                header_map["state"] = idx
        elif "sirc" in c or "circ" in c:
            if "sircuit" not in header_map:
                header_map["sircuit"] = idx
        elif "cont" in c or "incharge" in c or "manager" in c:
            if "controller" not in header_map:
                header_map["controller"] = idx
        elif "gst" in c:
            if "gst" not in header_map:
                header_map["gst"] = idx
        elif "pan" in c:
            if "pan_number" not in header_map:
                header_map["pan_number"] = idx

    if "cinema_name" not in header_map and len(header_row) > 0:
        header_map["cinema_name"] = 0
    return header_map

def _build_cinema_dict(row: Any, header_map: Dict[str, int]) -> Dict[str, str]:
    """Extracts cinema fields from a data row using the resolved header map."""
    def get_val(key: str) -> str:
        idx = header_map.get(key)
        if idx is not None and idx < len(row):
            val = row[idx]
            return str(val).strip() if val is not None else ""
        return ""

    return {
        "cinema_name": get_val("cinema_name"),
        "address": get_val("address"),
        "location": get_val("location"),
        "state": get_val("state"),
        "sircuit": get_val("sircuit"),
        "controller": get_val("controller"),
        "gst": get_val("gst"),
        "pan_number": get_val("pan_number"),
    }
