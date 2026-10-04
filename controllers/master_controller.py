import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from fastapi import Request, UploadFile, File
from fastapi.templating import Jinja2Templates
import pdfplumber

from config import BASE_URL
from helpers.common_helper import (
    extract_dcr_table_data,
    extract_dcr_table_data_with_diagnostics,
    extract_all_metadata_fast,
    extract_total_deduction,
    extract_date_safe,
    extract_address_safe,
    extract_cinema_name_safe,
    extract_movie_name_safe,
)
from helpers.database_helper import insert_dcr_report

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")

async def index(request: Request):
    context = {"BASE_URL": BASE_URL}
    return templates.TemplateResponse(request=request, name="index.html", context=context)

async def create(request: Request):
    context = {"BASE_URL": BASE_URL}
    return templates.TemplateResponse(request=request, name="create.html", context=context)

import asyncio
from io import BytesIO

def _parse_pdf_sync(file_bytes: bytes, filename: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """CPU-bound parsing executed inside thread pool for optimal async performance."""
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        response_data, diagnostic_reason = extract_dcr_table_data_with_diagnostics(pdf)
        if not response_data:
            return None, diagnostic_reason or "No table found with required columns (Day, Shows, Attendance, Nett)."

        pdfdate, cinemaname, address = extract_all_metadata_fast(pdf, filename)
        moviename = extract_movie_name_safe(pdf)
        total_deduction = extract_total_deduction(pdf)

        detail_records = []
        for item in response_data:
            day_val = item.get("Day") or item.get("day") or ""
            if not day_val:
                continue
            detail_records.append({
                "day": day_val,
                "shows": item.get("Shows", 0),
                "audience": item.get("Attendance", 0),
                "final_net": str(item.get("Nett", "0.00")),
            })

        return {
            "file_name": filename,
            "report_data": response_data,
            "report_date": int(pdfdate.timestamp()),
            "distributor_address": address,
            "cinema_name": cinemaname,
            "movie_name": moviename,
            "total_deduction": total_deduction,
            "details": detail_records,
            "date_display": pdfdate.strftime("%d/%m/%Y"),
        }, None

async def createprocessmethod(request: Request, pdfpostfiles: List[UploadFile] = File(...)):
    uploaded_files = []
    failed_files = []
    semaphore = asyncio.Semaphore(4)

    async def handle_single_file(upload_file: UploadFile):
        filename = upload_file.filename
        if not filename.lower().endswith(".pdf"):
            return None, {
                "file_name": filename,
                "status": "Failed",
                "reason": "Invalid file format. Only PDF files are supported."
            }

        try:
            content = await upload_file.read()
            async with semaphore:
                parsed_data, error_reason = await asyncio.to_thread(_parse_pdf_sync, content, filename)

            if not parsed_data:
                return None, {
                    "file_name": filename,
                    "status": "Failed",
                    "reason": error_reason
                }

            report_id = await insert_dcr_report(parsed_data)
            return {
                "file_name": filename,
                "status": "Success",
                "date": parsed_data["date_display"],
                "address": parsed_data["distributor_address"],
                "cinema_name": parsed_data["cinema_name"],
                "movie_name": parsed_data.get("movie_name", ""),
                "records_count": len(parsed_data["details"])
            }, None
        except Exception as e:
            logger.exception("Error processing PDF file '%s': %s", filename, e)
            return None, {
                "file_name": filename,
                "status": "Failed",
                "reason": str(e)
            }

    tasks = [handle_single_file(f) for f in pdfpostfiles]
    results = await asyncio.gather(*tasks)

    for success_item, fail_item in results:
        if success_item:
            uploaded_files.append(success_item)
        if fail_item:
            failed_files.append(fail_item)

    context = {
        "status": len(failed_files) == 0,
        "message": f"{len(uploaded_files)} file(s) uploaded successfully, {len(failed_files)} file(s) failed.",
        "uploaded_files": uploaded_files,
        "failed_files": failed_files,
        "BASE_URL": BASE_URL
    }
    return templates.TemplateResponse(request=request, name="createprocessmethod.html", context=context)
