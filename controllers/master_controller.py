import json
import logging
from typing import List
from datetime import datetime

from fastapi import Request, UploadFile, File
from fastapi.templating import Jinja2Templates
import pdfplumber

from config import BASE_URL
from helpers.common_helper import (
    extract_dcr_table_data,
    extract_dcr_table_data_with_diagnostics,
    extract_date_safe,
    extract_address_safe,
    extract_cinema_name_safe,
)
from helpers.database_helper import createrecords, bulk_createrecords

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")

async def index(request: Request):
    context = {"BASE_URL": BASE_URL}
    return templates.TemplateResponse(request=request, name="index.html", context=context)

async def create(request: Request):
    context = {"BASE_URL": BASE_URL}
    return templates.TemplateResponse(request=request, name="create.html", context=context)

async def createprocessmethod(request: Request, pdfpostfiles: List[UploadFile] = File(...)):
    uploaded_files = []
    failed_files = []

    for onepdf in pdfpostfiles:
        try:
            # Validate file object and extension
            if not onepdf.filename.lower().endswith(".pdf"):
                failed_files.append({
                    "file_name": onepdf.filename,
                    "status": "Failed",
                    "reason": "Invalid file format. Only PDF files are supported."
                })
                continue

            with pdfplumber.open(onepdf.file) as pdf:
                # 1. Extract table data matching Day, Shows, Attendance, Nett
                response_data, diagnostic_reason = extract_dcr_table_data_with_diagnostics(pdf)

                if not response_data:
                    failed_files.append({
                        "file_name": onepdf.filename,
                        "status": "Failed",
                        "reason": diagnostic_reason or "No table found with required columns (Day, Shows, Attendance, Nett)."
                    })
                    continue

                # 2. Extract metadata
                pdfdate = extract_date_safe(pdf)
                address = extract_address_safe(pdf)
                cinemaname = extract_cinema_name_safe(pdf, fallback_name=onepdf.filename)

                # 3. Insert parent report record using parameterized query
                sql_insert_report = """
                    INSERT INTO dcr_reports
                    (file_name, report_data, report_date, distributor_address, cinema_name)
                    VALUES (:file_name, :report_data, :report_date, :distributor_address, :cinema_name)
                """
                report_params = {
                    "file_name": onepdf.filename,
                    "report_data": json.dumps(response_data),
                    "report_date": int(pdfdate.timestamp()),
                    "distributor_address": address,
                    "cinema_name": cinemaname,
                }
                report_id = await createrecords(sql_insert_report, report_params)

                # 4. Insert child detail records using parameterized bulk insert
                sql_insert_detail = """
                    INSERT INTO dcr_report_details
                    (report_id, day, shows, audience, final_net)
                    VALUES (:report_id, :day, :shows, :audience, :final_net)
                """
                detail_params_list = []
                for item in response_data:
                    day_val = item.get("Day") or item.get("day") or ""
                    if not day_val:
                        continue
                    detail_params_list.append({
                        "report_id": report_id,
                        "day": day_val,
                        "shows": item.get("Shows", 0),
                        "audience": item.get("Attendance", 0),
                        "final_net": str(item.get("Nett", "0.00")),
                    })

                if detail_params_list:
                    await bulk_createrecords(sql_insert_detail, detail_params_list)

                # 5. Record successful upload (ONCE per file)
                uploaded_files.append({
                    "file_name": onepdf.filename,
                    "status": "Success",
                    "date": pdfdate.strftime("%d/%m/%Y"),
                    "address": address,
                    "cinema_name": cinemaname,
                    "records_count": len(detail_params_list)
                })

        except Exception as e:
            logger.exception(f"Error processing PDF file '{onepdf.filename}': {e}")
            failed_files.append({
                "file_name": onepdf.filename,
                "status": "Failed",
                "reason": str(e)
            })

    context = {
        "status": len(failed_files) == 0,
        "message": f"{len(uploaded_files)} file(s) uploaded successfully, {len(failed_files)} file(s) failed.",
        "uploaded_files": uploaded_files,
        "failed_files": failed_files,
        "BASE_URL": BASE_URL
    }
    return templates.TemplateResponse(request=request, name="createprocessmethod.html", context=context)
