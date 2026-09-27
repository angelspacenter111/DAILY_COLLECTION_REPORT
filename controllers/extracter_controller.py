from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse, JSONResponse
from config import BASE_URL
from helpers.database_helper import (
    fetchrecords,
    main_query,
    get_dcr_summary,
    delete_dcr_report,
    clear_all_dcr_reports,
)
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from io import BytesIO

templates = Jinja2Templates(directory="templates")

async def extracterindex(request: Request):
    result = await fetchrecords(main_query())
    summary = get_dcr_summary(result)
    context = {
        "BASE_URL": BASE_URL,
        "reports": result,
        "summary": summary
    }
    return templates.TemplateResponse(request=request, name="extracterindex.html", context=context)

async def delete_record(request: Request, record_id: str):
    success = await delete_dcr_report(record_id)
    return JSONResponse({
        "status": success,
        "message": "Record deleted successfully." if success else "Failed to delete record."
    })

async def clear_all_records(request: Request):
    count = await clear_all_dcr_reports()
    return JSONResponse({
        "status": True,
        "deleted_count": count,
        "message": f"{count} records cleared successfully."
    })

async def downloadExcel(request: Request):

    result = await fetchrecords(main_query())

    wb = Workbook()
    ws = wb.active
    ws.title = "DCR REPORT"

    # ------------------------
    # Header
    # ------------------------

    ws.merge_cells("A1:A2")
    ws.merge_cells("B1:B2")

    ws["A1"] = "FILE NAME"
    ws["B1"] = "CINEMA NAME"

    header_groups = [
        ("FRIDAY", "C", "E"),
        ("SATURDAY", "F", "H"),
        ("SUNDAY", "I", "K"),
        ("MONDAY", "L", "N"),
        ("TUESDAY", "O", "Q"),
        ("WEDNESDAY", "R", "T"),
        ("THURSDAY", "U", "W"),
        ("TOTAL", "X", "Z"),
    ]

    for title, start, end in header_groups:
        ws.merge_cells(f"{start}1:{end}1")
        ws[f"{start}1"] = title

    headers = [
        "SHOW","ADMITS","NET",
        "SHOW","ADMITS","NET",
        "SHOW","ADMITS","NET",
        "SHOW","ADMITS","NET",
        "SHOW","ADMITS","NET",
        "SHOW","ADMITS","NET",
        "SHOW","ADMITS","NET",
        "SHOW","ADMITS","NET"
    ]

    col = 3

    for h in headers:
        ws.cell(row=2,column=col).value = h
        col += 1

    # ------------------------
    # Data
    # ------------------------

    for row in result:

        ws.append([

            row.get("file_name",""),
            row.get("cinema_name",""),

            row.get("fri_show",0),
            row.get("fri_admits",0),
            row.get("fri_net",0),

            row.get("sat_show",0),
            row.get("sat_admits",0),
            row.get("sat_net",0),

            row.get("sun_show",0),
            row.get("sun_admits",0),
            row.get("sun_net",0),

            row.get("mon_show",0),
            row.get("mon_admits",0),
            row.get("mon_net",0),

            row.get("tue_show",0),
            row.get("tue_admits",0),
            row.get("tue_net",0),

            row.get("wed_show",0),
            row.get("wed_admits",0),
            row.get("wed_net",0),

            row.get("thu_show",0),
            row.get("thu_admits",0),
            row.get("thu_net",0),

            row.get("net_show", 0),
            row.get("net_adm", 0),
            row.get("grand_total", 0)

        ])

    # ------------------------
    # Styling
    # ------------------------

    thin = Side(style="thin")

    for row in ws.iter_rows():

        for cell in row:

            cell.alignment = Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True
            )

            cell.border = Border(
                left=thin,
                right=thin,
                top=thin,
                bottom=thin
            )

    # Header Bold
    for r in [1,2]:

        for cell in ws[r]:
            cell.font = Font(bold=True)

    # Row Height

    ws.row_dimensions[1].height = 25
    ws.row_dimensions[2].height = 22

    # ------------------------
    # Auto Width
    # ------------------------

    for column in ws.columns:

        max_length = 0
        column_letter = get_column_letter(column[0].column)

        for cell in column:

            try:
                if cell.value:

                    max_length = max(
                        max_length,
                        len(str(cell.value))
                    )

            except:
                pass

        ws.column_dimensions[column_letter].width = max_length + 3

    # Freeze Header

    ws.freeze_panes = "C3"

    # ------------------------
    # Download
    # ------------------------

    stream = BytesIO()

    wb.save(stream)

    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition":"attachment; filename=DCR_Report.xlsx"
        }
    )