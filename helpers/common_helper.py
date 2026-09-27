import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Canonical weekday mapping
WEEKDAY_PATTERNS = [
    (re.compile(r'\b(fri|friday)\b', re.IGNORECASE), "Friday"),
    (re.compile(r'\b(sat|saturday)\b', re.IGNORECASE), "Saturday"),
    (re.compile(r'\b(sun|sunday)\b', re.IGNORECASE), "Sunday"),
    (re.compile(r'\b(mon|monday)\b', re.IGNORECASE), "Monday"),
    (re.compile(r'\b(tue|tues|tuesday)\b', re.IGNORECASE), "Tuesday"),
    (re.compile(r'\b(wed|wednesday)\b', re.IGNORECASE), "Wednesday"),
    (re.compile(r'\b(thu|thur|thurs|thursday)\b', re.IGNORECASE), "Thursday"),
]

def match_column_type(header_cell: Any) -> Optional[str]:
    """
    Identifies whether a header cell represents one of the required columns:
    'day', 'shows', 'attendance', or 'nett'.
    Handles multiline header cells (e.g. 'Day\nFri:24...').
    """
    if header_cell is None:
        return None

    raw_str = str(header_cell).strip()
    if not raw_str:
        return None

    # Check first line for multiline cells
    first_line = raw_str.split('\n')[0].strip().lower()
    first_clean = re.sub(r'[^a-zA-Z0-9\/\.\s]', '', first_line).strip()

    # 1. Day Check
    if re.search(r'^(day|days)$', first_clean) or first_clean.startswith("day"):
        if "today" not in first_clean:
            return "day"

    full_clean = re.sub(r'[\r\n]+', ' ', raw_str).strip().lower()
    full_clean = re.sub(r'\s+', ' ', full_clean)

    # 2. Shows Check
    if re.search(r'^(shows?|sh\.?|sh|no\.?\s*(of)?\s*shows?)$', full_clean):
        return "shows"

    # 3. Attendance Check (including Seats Sold, Total Sold, Admits, Aud)
    if re.search(r'^(attendance|admits?|aud(\.|ience)?|pax|attnd|seats?\s*sold|total\s*sold)$', full_clean):
        return "attendance"

    # 4. Nett Check
    # Rule 1: Exclude Housefull / Houseful Net
    if "house" in full_clean:
        return None
    if "gross" in full_clean and "net" not in full_clean:
        return None
    if re.search(r'^(final\s+)?nett?(\s+(amt|amount|collection|coll|total))?$', full_clean):
        return "nett"
    if full_clean in ("net", "nett", "final net", "final nett", "net coll", "nett coll"):
        return "nett"
    if re.search(r'\b(final\s+)?nett?\b', full_clean) and "gross" not in full_clean and "house" not in full_clean:
        return "nett"

    return None

def identify_table_headers(headers: List[Any]) -> Optional[Dict[str, int]]:
    """
    Checks if a list of header cells contains all 4 required columns:
    Day, Shows, Attendance, Nett.
    Returns a dictionary mapping column names to their index.
    """
    col_map: Dict[str, int] = {}
    for idx, cell in enumerate(headers):
        col_type = match_column_type(cell)
        if col_type and col_type not in col_map:
            col_map[col_type] = idx
    required = {"day", "shows", "attendance", "nett"}
    if required.issubset(col_map.keys()):
        return col_map
    return None

def normalize_day(raw_val: Any) -> Optional[str]:
    """
    Normalizes a day cell value to a standard day string ('Friday', 'Saturday', etc.).
    Returns None if the value is empty, a header repeat, or a summary/total row.
    """
    if not raw_val:
        return None

    val_str = str(raw_val).strip()
    lower = val_str.lower()

    if any(term in lower for term in ("total", "subtotal", "summary", "weekly", "gross", "collection")):
        return None
    if lower in ("day", "days", "date"):
        return None

    for pattern, canonical_name in WEEKDAY_PATTERNS:
        if pattern.search(val_str):
            return canonical_name

    return None

def clean_integer(raw_val: Any) -> int:
    """Extracts integer value from raw cell text (e.g. '1,500' -> 1500, '-' -> 0)."""
    if not raw_val:
        return 0
    text = str(raw_val).strip()
    digits = re.sub(r'[^\d]', '', text)
    return int(digits) if digits else 0

def clean_net_amount(raw_val: Any) -> str:
    """Extracts net amount, strips currency symbols and commas, returns format '12345.67'."""
    if not raw_val:
        return "0.00"
    text = str(raw_val).strip()
    cleaned = re.sub(r'[^0-9\.\-]', '', text)
    if not cleaned or cleaned in ("-", ".", "-."):
        return "0.00"
    try:
        val = float(cleaned)
        return f"{val:.2f}"
    except ValueError:
        return "0.00"

def extract_dcr_table_data_with_diagnostics(pdf) -> Tuple[List[Dict[str, Any]], str]:
    """
    Scans all tables across all pages in the PDF for Day, Shows, Attendance, Nett.
    Handles standard tables, embedded sub-tables, and multiline stacked cells.
    Returns: (extracted_records, diagnostic_failure_reason)
    """
    extracted_rows: List[Dict[str, Any]] = []
    tables_inspected = 0
    best_candidate_headers: List[str] = []
    missing_columns: List[str] = []

    for page_idx, page in enumerate(pdf.pages, start=1):
        try:
            tables = page.extract_tables() or []
        except Exception as e:
            logger.warning(f"Error extracting tables on page {page_idx}: {e}")
            continue

        for table in tables:
            if not table or len(table) < 2:
                continue

            tables_inspected += 1

            # Search ALL rows in the table for the header (supports embedded sub-tables)
            for rno, row in enumerate(table):
                col_map: Dict[str, int] = {}
                for idx, cell in enumerate(row):
                    col_type = match_column_type(cell)
                    if col_type and col_type not in col_map:
                        col_map[col_type] = idx

                required = {"day", "shows", "attendance", "nett"}
                found = set(col_map.keys())

                # Track best candidate table for diagnostics if not all 4 match
                if len(found) > len(best_candidate_headers):
                    best_candidate_headers = [str(c).split('\n')[0].strip() for c in row if c is not None and str(c).strip()]
                    missing_columns = [col.capitalize() for col in (required - found)]

                if required.issubset(found):
                    # Found target header row!
                    # Check if the Day cell in the header row itself contains multiline day values (e.g. Day\nFri:24...)
                    day_header_str = str(row[col_map["day"]] or "")
                    day_lines_header = [l.strip() for l in day_header_str.split('\n')[1:] if l.strip()]

                    data_rows = table[rno + 1:]
                    for dr in data_rows:
                        if not dr or not any(dr):
                            continue
                        max_c = max(col_map.values())
                        if len(dr) <= max_c:
                            continue

                        cell_day = dr[col_map["day"]]

                        # Determine if days are stacked in multiline cells
                        if day_lines_header and (not cell_day or '\n' not in str(cell_day)):
                            days_list = day_lines_header
                        elif cell_day and '\n' in str(cell_day):
                            days_list = [l.strip() for l in str(cell_day).split('\n') if l.strip()]
                        else:
                            days_list = None

                        if days_list and len(days_list) > 1:
                            # Stacked multiline row
                            shows_lines = [l.strip() for l in str(dr[col_map["shows"]] or "").split('\n') if l.strip()]
                            att_lines = [l.strip() for l in str(dr[col_map["attendance"]] or "").split('\n') if l.strip()]
                            net_lines = [l.strip() for l in str(dr[col_map["nett"]] or "").split('\n') if l.strip()]

                            # Count active attendance days to align net_lines if 0-attendance days were skipped
                            active_att_count = sum(1 for idx in range(len(days_list)) if (clean_integer(att_lines[idx]) if idx < len(att_lines) else 0) > 0)
                            net_cursor = 0

                            for i, d_str in enumerate(days_list):
                                norm_d = normalize_day(d_str)
                                if not norm_d:
                                    continue
                                s_val = clean_integer(shows_lines[i]) if i < len(shows_lines) else 0
                                a_val = clean_integer(att_lines[i]) if i < len(att_lines) else 0

                                # Rule 2: If attendance is 0, net must be 0.00
                                if a_val == 0:
                                    n_val = "0.00"
                                else:
                                    if len(net_lines) == active_att_count and net_cursor < len(net_lines):
                                        n_val = clean_net_amount(net_lines[net_cursor])
                                        net_cursor += 1
                                    elif i < len(net_lines):
                                        n_val = clean_net_amount(net_lines[i])
                                    else:
                                        n_val = "0.00"

                                extracted_rows.append({
                                    "Day": norm_d,
                                    "Shows": s_val,
                                    "Attendance": a_val,
                                    "Nett": n_val,
                                    "day": norm_d,
                                    "shows": s_val,
                                    "sh.": s_val,
                                    "audience": a_val,
                                    "Aud": a_val,
                                    "final_net": n_val,
                                    "Final Net": n_val,
                                })
                            break  # Processed multiline sub-block
                        else:
                            # Standard single-row entry
                            norm_d = normalize_day(cell_day)
                            if not norm_d:
                                continue
                            s_val = clean_integer(dr[col_map["shows"]])
                            a_val = clean_integer(dr[col_map["attendance"]])

                            # Rule 2: If attendance is 0, net must be 0.00
                            if a_val == 0:
                                n_val = "0.00"
                            else:
                                n_val = clean_net_amount(dr[col_map["nett"]])

                            extracted_rows.append({
                                "Day": norm_d,
                                "Shows": s_val,
                                "Attendance": a_val,
                                "Nett": n_val,
                                "day": norm_d,
                                "shows": s_val,
                                "sh.": s_val,
                                "audience": a_val,
                                "Aud": a_val,
                                "final_net": n_val,
                                "Final Net": n_val,
                            })

                    if extracted_rows:
                        return extracted_rows, ""

    if extracted_rows:
        return extracted_rows, ""

    # Generate specific diagnostic reason for failure
    if tables_inspected == 0:
        reason = "PDF document contains no structured tables."
    elif missing_columns:
        headers_preview = ", ".join(best_candidate_headers[:6])
        if len(best_candidate_headers) > 6:
            headers_preview += ", ..."
        reason = f"Required table not found. Nearest table headers: [{headers_preview}], Missing column(s): {', '.join(missing_columns)}."
    else:
        reason = "No table found with required columns (Day, Shows, Attendance, Nett)."

    return [], reason

def extract_dcr_table_data(pdf) -> List[Dict[str, Any]]:
    """Backward-compatible extraction call."""
    rows, _ = extract_dcr_table_data_with_diagnostics(pdf)
    return rows

def extract_date_safe(pdf) -> datetime:
    """Extracts report date from PDF or defaults to current date."""
    for page in pdf.pages:
        text = page.extract_text() or ""

        match = re.search(r'(?:date|dated)\s*:?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})', text, re.IGNORECASE)
        if match:
            date_str = match.group(1).replace(".", "/")
            for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y"):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    pass

        match = re.search(r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})\b', text)
        if match:
            date_str = match.group(1).replace("-", "/")
            try:
                return datetime.strptime(date_str, "%d/%m/%Y")
            except ValueError:
                pass

        match = re.search(
            r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{4})\b',
            text,
            re.IGNORECASE
        )
        if match:
            date_str = re.sub(r'[,]+', '', match.group(1))
            for fmt in ("%d %b %Y", "%d %B %Y"):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    pass

        match = re.search(
            r'\b(\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{2,4})\b',
            text,
            re.IGNORECASE
        )
        if match:
            for fmt in ("%d-%b-%y", "%d-%b-%Y"):
                try:
                    return datetime.strptime(match.group(1), fmt)
                except ValueError:
                    pass

    return datetime.now()

def extract_cinema_name_safe(pdf, fallback_name: str = "Unknown Cinema") -> str:
    """Extracts cinema / theatre name with resilient fallback strategies."""
    excluded_keywords = ("phone", "date", "address", "distributor", "email", "tel", "report", "gst", "collection", "day:")
    for page in pdf.pages:
        text = page.extract_text() or ""
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        for i, line in enumerate(lines):
            lower = line.lower()
            if "daily collection report" in lower or "distributor report" in lower or "collection report" in lower:
                for offset in range(1, min(i + 1, 6)):
                    candidate = lines[i - offset].strip()
                    cand_lower = candidate.lower()
                    if len(candidate) > 2 and not any(kw in cand_lower for kw in excluded_keywords):
                        return candidate

        try:
            words = page.extract_words()
            if words:
                page_width = page.width
                center_words = [
                    w for w in words
                    if page_width * 0.15 < w["x0"] < page_width * 0.85 and w["top"] < 180
                ]
                if center_words:
                    lines_dict: Dict[int, List[Dict[str, Any]]] = {}
                    for w in center_words:
                        key = round(w["top"] / 5) * 5
                        lines_dict.setdefault(key, []).append(w)
                    for _, line_words in sorted(lines_dict.items()):
                        line_str = " ".join(w["text"] for w in sorted(line_words, key=lambda k: k["x0"])).strip()
                        if line_str and not any(k in line_str.lower() for k in ("report", "distributor", "phone", "date", "collection")):
                            if len(line_str) > 3:
                                return line_str
        except Exception:
            pass

    return fallback_name

def extract_address_safe(pdf) -> str:
    """Safely extracts distributor/cinema address preceding telephone/report markers."""
    for page in pdf.pages:
        try:
            words = page.extract_words()
            phone_y = None
            for word in words:
                if word["text"].lower().startswith("phone") or word["text"].lower().startswith("tel"):
                    phone_y = word["top"]
                    break
            if phone_y is not None:
                addr_words = [w for w in words if w["top"] < phone_y and w["x0"] < 250]
                lines_dict: Dict[int, List[Dict[str, Any]]] = {}
                for w in addr_words:
                    y = round(w["top"] / 4) * 4
                    lines_dict.setdefault(y, []).append(w)
                res = []
                for _, line_words in sorted(lines_dict.items()):
                    line = " ".join(w["text"] for w in sorted(line_words, key=lambda x: x["x0"])).strip()
                    if line:
                        res.append(line)
                if res:
                    return "\n".join(res[:5])
        except Exception:
            pass

        text = page.extract_text() or ""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for i, line in enumerate(lines):
            if "daily collection report" in line.lower() or "distributor report" in line.lower():
                start = max(0, i - 4)
                return "\n".join(lines[start:i])

    return ""

# Backward compatibility wrappers:
def extract_date(pdf):
    dt = extract_date_safe(pdf)
    return dt.strftime("%d/%m/%Y")

def extract_date_from_format_one(pdf):
    dt = extract_date_safe(pdf)
    return dt.strftime("%d/%m/%Y")

def extract_address(pdf):
    return extract_address_safe(pdf)

def extract_address_from_format_one(pdf):
    return extract_address_safe(pdf)

def cinema_name_one(pdf):
    return extract_cinema_name_safe(pdf)

def cinema_name_two(pdf):
    return extract_cinema_name_safe(pdf)

def getformate(pdf):
    data = extract_dcr_table_data(pdf)
    return 1 if data else 0

def extract_data_from_formate_one(pdf):
    return extract_dcr_table_data(pdf)

def extract_data_from_formate_two(pdf):
    return extract_dcr_table_data(pdf)