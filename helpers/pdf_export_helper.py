import io
from typing import Dict, Any, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

def generate_dcr_pdf(report: Dict[str, Any]) -> io.BytesIO:
    """
    Generates a clean, professional single DCR report PDF using ReportLab.
    Matches the data displayed in the Cinema Report Breakdown view modal.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'DcrTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1e293b'),
        alignment=TA_CENTER
    )
    subtitle_style = ParagraphStyle(
        'DcrSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748b'),
        alignment=TA_CENTER
    )
    meta_label = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#475569')
    )
    meta_val = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0f172a')
    )
    meta_val_bold = ParagraphStyle(
        'MetaValBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1d4ed8')
    )
    th_style = ParagraphStyle(
        'TableHead',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#1e293b'),
        alignment=TA_CENTER
    )
    td_center = ParagraphStyle(
        'TableCenter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        alignment=TA_CENTER
    )
    td_left = ParagraphStyle(
        'TableLeft',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        alignment=TA_LEFT
    )
    td_right = ParagraphStyle(
        'TableRight',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        alignment=TA_RIGHT
    )
    td_bold_right = ParagraphStyle(
        'TableBoldRight',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#047857'),
        alignment=TA_RIGHT
    )

    elements = []

    # 1. Header Banner
    elements.append(Paragraph("DAILY COLLECTION REPORT", title_style))
    file_name = report.get("file_name", "DCR_Report")
    elements.append(Paragraph(f"Source File: {file_name}", subtitle_style))
    elements.append(Spacer(1, 14))

    # 2. Metadata Information Grid (Cinema, Movie, Net, Totals)
    cinema_name = report.get("cinema_name") or "Unknown Cinema"
    movie_name = report.get("movie_name") or "N/A"
    grand_total = float(report.get("grand_total", 0.0) or 0.0)
    net_show = report.get("net_show", 0)
    net_adm = report.get("net_adm", 0)
    total_ded = float(report.get("total_deduction", 0.0) or 0.0)
    address = report.get("distributor_address", "") or "No address text recorded"

    info_data = [
        [
            Paragraph("<b>Cinema / Theatre:</b>", meta_label),
            Paragraph(cinema_name, meta_val_bold),
            Paragraph("<b>Grand Total Collection:</b>", meta_label),
            Paragraph(f"Rs. {grand_total:,.2f}", meta_val_bold),
        ],
        [
            Paragraph("<b>Movie Name:</b>", meta_label),
            Paragraph(movie_name, meta_val),
            Paragraph("<b>Total Deduction:</b>", meta_label),
            Paragraph(f"Rs. {total_ded:,.2f}", meta_val),
        ],
        [
            Paragraph("<b>Net Shows:</b>", meta_label),
            Paragraph(str(net_show), meta_val),
            Paragraph("<b>Net Attendance / Admits:</b>", meta_label),
            Paragraph(f"{net_adm:,}", meta_val),
        ]
    ]

    info_table = Table(info_data, colWidths=[1.6 * inch, 2.3 * inch, 1.8 * inch, 1.8 * inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 16))

    # 3. Day-by-Day Breakdown Table
    details = report.get("details") or report.get("report_data") or []
    table_data = [
        [
            Paragraph("Day", th_style),
            Paragraph("Shows", th_style),
            Paragraph("Attendance / Admits", th_style),
            Paragraph("Nett Collection (Rs.)", th_style),
        ]
    ]

    total_calc_net = 0.0
    total_calc_shows = 0
    total_calc_adm = 0

    if isinstance(details, list) and len(details) > 0:
        for item in details:
            day_str = str(item.get("day") or item.get("Day") or "-")
            shows_val = int(item.get("shows", 0) or item.get("Shows", 0) or 0)
            aud_val = int(item.get("audience", 0) or item.get("Attendance", 0) or 0)
            try:
                net_val = float(str(item.get("final_net", 0.0) or item.get("Nett", 0.0)).replace(",", ""))
            except (ValueError, TypeError):
                net_val = 0.0

            total_calc_shows += shows_val
            total_calc_adm += aud_val
            total_calc_net += net_val

            table_data.append([
                Paragraph(day_str, td_left),
                Paragraph(str(shows_val), td_center),
                Paragraph(f"{aud_val:,}", td_center),
                Paragraph(f"Rs. {net_val:,.2f}", td_right),
            ])

        # Summary Row
        table_data.append([
            Paragraph("<b>TOTAL</b>", td_left),
            Paragraph(f"<b>{total_calc_shows}</b>", td_center),
            Paragraph(f"<b>{total_calc_adm:,}</b>", td_center),
            Paragraph(f"<b>Rs. {total_calc_net:,.2f}</b>", td_bold_right),
        ])
    else:
        table_data.append([
            Paragraph("No individual day rows recorded", td_center),
            Paragraph("-", td_center),
            Paragraph("-", td_center),
            Paragraph(f"Rs. {grand_total:,.2f}", td_right),
        ])

    breakdown_table = Table(table_data, colWidths=[2.2 * inch, 1.4 * inch, 1.8 * inch, 2.1 * inch])
    breakdown_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e0e7ff')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1e1b4b')),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fef3c7')),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
    ]))
    elements.append(breakdown_table)
    elements.append(Spacer(1, 16))

    # 4. Address & Footer Notes
    if address:
        addr_clean = address.replace("\n", "<br/>")
        addr_p = Paragraph(f"<b>Distributor / Theatre Address:</b><br/>{addr_clean}", meta_val)
        addr_table = Table([[addr_p]], colWidths=[7.5 * inch])
        addr_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(addr_table)
        elements.append(Spacer(1, 12))

    # System footer note
    footer_text = Paragraph(
        f"<font size='8' color='#94a3b8'>Generated via First Film Studios &bull; {file_name}</font>",
        subtitle_style
    )
    elements.append(footer_text)

    doc.build(elements)
    buffer.seek(0)
    return buffer
