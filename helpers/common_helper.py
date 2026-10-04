import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Canonical weekday mapping with pre-compiled patterns
WEEKDAY_PATTERNS = [
    (re.compile(r'\b(fri|friday)\b', re.IGNORECASE), "Friday"),
    (re.compile(r'\b(sat|saturday)\b', re.IGNORECASE), "Saturday"),
    (re.compile(r'\b(sun|sunday)\b', re.IGNORECASE), "Sunday"),
    (re.compile(r'\b(mon|monday)\b', re.IGNORECASE), "Monday"),
    (re.compile(r'\b(tue|tues|tuesday)\b', re.IGNORECASE), "Tuesday"),
    (re.compile(r'\b(wed|wednesday)\b', re.IGNORECASE), "Wednesday"),
    (re.compile(r'\b(thu|thur|thurs|thursday)\b', re.IGNORECASE), "Thursday"),
]

# Pre-compiled regex patterns for maximum matching performance
RE_NON_ALPHANUM = re.compile(r'[^a-zA-Z0-9\/\.\s]')
RE_WHITESPACE = re.compile(r'\s+')
RE_DAY_EXACT = re.compile(r'^(day|days)$')
RE_SHOWS = re.compile(r'^(shows?|sh\.?|sh|no\.?\s*(of)?\s*shows?)$')
RE_ATTENDANCE = re.compile(r'^(attendance|admits?|aud(\.|ience)?|pax|attnd|seats?\s*sold|total\s*sold)$')
RE_NETT_EXACT = re.compile(r'^(final\s+)?nett?(\s+(amt|amount|collection|coll|total))?$')
RE_NETT_WORD = re.compile(r'\b(final\s+)?nett?\b')
RE_DIGITS = re.compile(r'[^\d]')
RE_FLOAT_CLEAN = re.compile(r'[^0-9\.\-]')

# Cinema keywords for intelligent identification
CINEMA_PRIMARY_KW = ('cinema', 'cinemas', 'cinemaz', 'cineplex', 'miniplex', 'inox', 'pvr')
CINEMA_SECONDARY_KW = ('miraj', 'citypride', 'pride', 'mall', 'heritage', 'eylex', 'station')
CINEMA_EXCLUDE_TERMS = ('distributor', 'share report', 'gstin', 'gst no', 'pincode', 'dulhaniya', 'first film', 'total', 'phone', 'tel', 'contact')

# Date regexes
RE_DATE_1 = re.compile(r'(?:date|dated)\s*:?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})', re.IGNORECASE)
RE_DATE_2 = re.compile(r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})\b')
RE_DATE_3 = re.compile(r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{4})\b', re.IGNORECASE)
RE_DATE_4 = re.compile(r'\b(\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{2,4})\b', re.IGNORECASE)

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
    first_clean = RE_NON_ALPHANUM.sub('', first_line).strip()

    # 1. Day Check
    if RE_DAY_EXACT.search(first_clean) or first_clean.startswith("day"):
        if "today" not in first_clean:
            return "day"

    full_clean = raw_str.replace('\r', ' ').replace('\n', ' ').strip().lower()
    full_clean = RE_WHITESPACE.sub(' ', full_clean)

    # 2. Shows Check
    if RE_SHOWS.search(full_clean):
        return "shows"

    # 3. Attendance Check (including Seats Sold, Total Sold, Admits, Aud)
    if RE_ATTENDANCE.search(full_clean):
        return "attendance"

    # 4. Nett Check
    # Rule 1: Exclude Housefull / Houseful Net
    if "house" in full_clean:
        return None
    if "gross" in full_clean and "net" not in full_clean:
        return None
    if RE_NETT_EXACT.search(full_clean):
        return "nett"
    if full_clean in ("net", "nett", "final net", "final nett", "net coll", "nett coll"):
        return "nett"
    if RE_NETT_WORD.search(full_clean) and "gross" not in full_clean and "house" not in full_clean:
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
    digits = RE_DIGITS.sub('', text)
    return int(digits) if digits else 0

def clean_net_amount(raw_val: Any) -> str:
    """Extracts net amount, strips currency symbols and commas, returns format '12345.67'."""
    if not raw_val:
        return "0.00"
    text = str(raw_val).strip()
    cleaned = RE_FLOAT_CLEAN.sub('', text)
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

def clean_duplicate_words(s: str) -> str:
    """Removes repetitive adjacent words or phrases (e.g. 'MIRAJ CINEMAS MIRAJ CINEMAS' -> 'MIRAJ CINEMAS')."""
    words = s.split()
    cleaned = []
    for w in words:
        if not cleaned or w.lower() != cleaned[-1].lower():
            cleaned.append(w)
    half = len(cleaned) // 2
    for l in range(1, half + 1):
        if [w.lower() for w in cleaned[:l]] == [w.lower() for w in cleaned[l:2*l]]:
            cleaned = cleaned[l:]
            break
    return ' '.join(cleaned)

def extract_all_metadata_fast(pdf, fallback_name: str = "Unknown Cinema") -> Tuple[datetime, str, str]:
    """
    Extracts report date, distributor address, and cinema name in a single fast pass.
    Reuses page text and word extractions to avoid redundant CPU-heavy pdfplumber calls.
    Returns: (report_date, cinema_name, distributor_address)
    """
    extracted_date = None
    extracted_cinema = None
    extracted_address = ""

    # Most DCR metadata is on Page 1
    for page in pdf.pages:
        text = page.extract_text() or ""
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        # 1. Date Extraction
        if not extracted_date:
            m = RE_DATE_1.search(text)
            if m:
                d_str = m.group(1).replace(".", "/")
                for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y"):
                    try:
                        extracted_date = datetime.strptime(d_str, fmt)
                        break
                    except ValueError:
                        pass
            if not extracted_date:
                m = RE_DATE_2.search(text)
                if m:
                    try:
                        extracted_date = datetime.strptime(m.group(1).replace("-", "/"), "%d/%m/%Y")
                    except ValueError:
                        pass
            if not extracted_date:
                m = RE_DATE_3.search(text)
                if m:
                    d_str = m.group(1).replace(",", "")
                    for fmt in ("%d %b %Y", "%d %B %Y"):
                        try:
                            extracted_date = datetime.strptime(d_str, fmt)
                            break
                        except ValueError:
                            pass
            if not extracted_date:
                m = RE_DATE_4.search(text)
                if m:
                    for fmt in ("%d-%b-%y", "%d-%b-%Y"):
                        try:
                            extracted_date = datetime.strptime(m.group(1), fmt)
                            break
                        except ValueError:
                            pass

        # 2. Cinema Name Extraction (Scored segment heuristic)
        if not extracted_cinema and lines:
            candidates = []
            for line in lines[:10]:
                l_low = line.lower()
                if any(term in l_low for term in ('share report', 'gstin', 'gst no', 'dulhaniya', 'first film')):
                    continue

                segments = [s.strip() for s in re.split(r'[,|]|\s{3,}', line) if s.strip()]
                for seg in segments:
                    seg_clean = re.sub(r'\s*(week|day|days|date)\s*:.*$', '', seg, flags=re.IGNORECASE).strip()
                    s_low = seg_clean.lower()
                    if any(term in s_low for term in CINEMA_EXCLUDE_TERMS):
                        continue

                    has_primary = any(kw in s_low for kw in CINEMA_PRIMARY_KW)
                    has_secondary = any(kw in s_low for kw in CINEMA_SECONDARY_KW)

                    if has_primary or has_secondary:
                        seg_clean = re.split(r'\s+(s\.?r\.?no|near|opp|behind|road|survey|plot|floor|4th)\b', seg_clean, flags=re.IGNORECASE)[0].strip(' ,-')
                        seg_clean = clean_duplicate_words(seg_clean)
                        if len(seg_clean) > 3 and seg_clean.lower() not in ('cinema', 'cinemas', 'theatre', 'mall', 'miniplex'):
                            is_corporate = any(co in s_low for co in ('ltd', 'limited', 'pvt', 'private', 'corporation'))
                            score = 1 if is_corporate else (5 if has_primary else 3)
                            candidates.append((score, seg_clean))

            if candidates:
                candidates.sort(key=lambda x: x[0], reverse=True)
                extracted_cinema = candidates[0][1]

        # 3. Address Extraction
        if not extracted_address:
            try:
                words = page.extract_words()
                phone_y = None
                for word in words:
                    w_low = word["text"].lower()
                    if w_low.startswith("phone") or w_low.startswith("tel"):
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
                        line_str = " ".join(w["text"] for w in sorted(line_words, key=lambda x: x["x0"])).strip()
                        if line_str:
                            res.append(line_str)
                    if res:
                        extracted_address = "\n".join(res[:5])
            except Exception:
                pass

            if not extracted_address:
                for i, line in enumerate(lines):
                    if "daily collection report" in line.lower() or "distributor report" in line.lower():
                        start = max(0, i - 4)
                        extracted_address = "\n".join(lines[start:i])
                        break

        # If all metadata extracted from page 1, early exit!
        if extracted_date and extracted_cinema and extracted_address:
            break

    final_date = extracted_date or datetime.now()
    final_cinema = extracted_cinema or fallback_name.replace('.pdf', '').replace('.PDF', '')
    return final_date, final_cinema, extracted_address

def extract_total_deduction(pdf) -> float:
    """
    Extracts the deduction amount from the PDF document.
    Supports:
      - Structured table cells with stacked header/value (e.g. 'Deduction\\n975.00')
      - Dedicated vertical/horizontal deduction cells in tables
      - Same-line text (e.g. 'deduction  : 1,250.00')
      - Next-line text (e.g. 'deduction\\n          1,250.00')
    Searches tables first for high precision, then line text, and regex fallbacks.
    """
    patterns_to_check = [
        # Pass 1: Prioritize explicit 'total deduction' / 'total deductions'
        (r'\btotal\s+deductions?\b', r'total\s+deductions?\s*[:\-]?', "total deduction"),
        # Pass 2: Standalone 'deduction' / 'deductions'
        (r'\bdeductions?\b', r'\bdeductions?\b\s*[:\-]?', "deduction")
    ]

    # Layer 1: Structured Tables First (accurately captures 'Deduction\n975.00', vertical cells, or row pairs)
    for word_regex, split_regex, keyword in patterns_to_check:
        for page in pdf.pages:
            try:
                tables = page.extract_tables() or []
            except Exception:
                tables = []
            for t in tables:
                if not t:
                    continue
                for r_idx, row in enumerate(t):
                    if not row:
                        continue
                    for c_idx, cell in enumerate(row):
                        if not cell:
                            continue
                        c_clean = str(cell).strip()
                        if re.search(word_regex, c_clean, re.IGNORECASE):
                            # Case A: Inside same cell (e.g. 'Deduction\n975.00' or 'Total Deduction : 975.00')
                            lines_in_cell = [l.strip() for l in c_clean.split('\n') if l.strip()]
                            for l in lines_in_cell:
                                if re.fullmatch(r'(?:total\s+)?deductions?\s*[:\-]?', l, re.IGNORECASE):
                                    continue
                                num_m = re.search(r'([0-9,]+(?:\.[0-9]{1,2})?)', l)
                                if num_m:
                                    try:
                                        return round(float(num_m.group(1).replace(',', '')), 2)
                                    except ValueError:
                                        pass

                            # Case B: In cell directly below in next row (same column)
                            if r_idx + 1 < len(t):
                                next_row = t[r_idx + 1]
                                if c_idx < len(next_row) and next_row[c_idx]:
                                    next_cell = str(next_row[c_idx]).strip()
                                    num_m = re.search(r'^(?:(?:Rs\.?|INR|[^\x00-\x7F])\s*)?([0-9,]+(?:\.[0-9]{1,2})?)', next_cell)
                                    if num_m:
                                        try:
                                            return round(float(num_m.group(1).replace(',', '')), 2)
                                        except ValueError:
                                            pass

                            # Case C: In adjacent cell to the right (same row)
                            if c_idx + 1 < len(row) and row[c_idx + 1]:
                                adj_cell = str(row[c_idx + 1]).strip()
                                num_m = re.search(r'^(?:(?:Rs\.?|INR|[^\x00-\x7F])\s*)?([0-9,]+(?:\.[0-9]{1,2})?)', adj_cell)
                                if num_m and not re.search(r'[a-zA-Z]{3,}', adj_cell):
                                    try:
                                        return round(float(num_m.group(1).replace(',', '')), 2)
                                    except ValueError:
                                        pass

                            # Case D: Row ends with the total deduction amount (e.g. ['Total Deduction', '', '', '975.00'])
                            for end_cell in reversed(row[c_idx+1:]):
                                if not end_cell:
                                    continue
                                end_clean = str(end_cell).strip()
                                num_m = re.search(r'([0-9,]+(?:\.[0-9]{1,2})?)', end_clean)
                                if num_m and not re.search(r'(?:total\s+)?deductions?|weekly\s+nett|final|bor|tax', end_clean, re.IGNORECASE):
                                    try:
                                        return round(float(num_m.group(1).replace(',', '')), 2)
                                    except ValueError:
                                        pass

    # Layer 2: Line-by-line text search
    for word_regex, split_regex, keyword in patterns_to_check:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if not text:
                continue

            lines = text.split('\n')
            for idx, line in enumerate(lines):
                l_clean = line.strip()
                l_lower = l_clean.lower()
                if keyword in l_lower and re.search(word_regex, l_lower):
                    # Check same line (avoid table headers with multiple category labels like 'I.N.R. : 0.00 Show Tax')
                    if not re.search(r'i\.n\.r|show\s+tax|pub\s*\.?\s*exp|others', l_clean, re.IGNORECASE):
                        parts = re.split(split_regex, l_clean, flags=re.IGNORECASE)
                        if len(parts) > 1 and parts[1].strip():
                            rem = parts[1].strip()
                            num_match = re.search(r'([0-9,]+(?:\.[0-9]{1,2})?)', rem)
                            if num_match:
                                try:
                                    return round(float(num_match.group(1).replace(',', '')), 2)
                                except ValueError:
                                    pass

                    # Next line check (handles 'deduction\n 1,250.00')
                    for offset in range(1, 4):
                        if idx + offset < len(lines):
                            next_line = lines[idx + offset].strip()
                            if not next_line:
                                continue
                            num_match = re.search(r'^(?:(?:Rs\.?|INR|[^\x00-\x7F])\s*)?([0-9,]+(?:\.[0-9]{1,2})?)', next_line, re.IGNORECASE)
                            if num_match:
                                try:
                                    return round(float(num_match.group(1).replace(',', '')), 2)
                                except ValueError:
                                    pass
                            break

    # Layer 3: Multiline fallback regex on page text
    for word_regex, split_regex, keyword in patterns_to_check:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if not text:
                continue
            m = re.search(rf'{word_regex}\s*[:\-]?\s*(?:\r?\n\s*)?(?:(?:Rs\.?|INR|[^\x00-\x7F])\s*)?([0-9,]+(?:\.[0-9]{1,2})?)', text, re.IGNORECASE)
            if m:
                try:
                    return round(float(m.group(1).replace(',', '')), 2)
                except ValueError:
                    pass

    return 0.0

def clean_movie_name_str(name: str) -> str:
    if not name:
        return ""
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.strip(' ,-:_')
    name = re.split(r'\s+(?:Day|Date|Week)\s*:', name, flags=re.IGNORECASE)[0].strip()
    return name

def extract_movie_name_safe(pdf, fallback_name: str = "") -> str:
    """
    Extracts the movie/film name from the PDF document.
    Handles multiple layout styles:
      1. Explicit 'Film Name : <name>' (PVR/INOX layout)
      2. Explicit 'Film : <name>' (Eylex layout)
      3. Distributor Report header boxes/tables (Abhiruchi, Miraj, Bhutani, Silwasa, Ramnagar, etc.)
      4. Show details / screen lines containing movie titles
    """
    if not pdf or not getattr(pdf, "pages", None):
        return fallback_name

    # Strategy 1: Explicit 'Film Name :' or 'Film :' in text
    for page in pdf.pages[:2]:
        text = page.extract_text() or ""
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        for line in lines:
            m = re.search(r'Film\s*Name\s*:\s*([^,\n\r]+)', line, re.IGNORECASE)
            if m:
                val = clean_movie_name_str(m.group(1))
                if val:
                    return val

            m2 = re.search(r'Film\s*:\s*([^,\n\r]+)', line, re.IGNORECASE)
            if m2:
                val = m2.group(1).strip()
                if not re.search(r'\b(?:distributor|studios|corporation|ent|pvt|ltd)\b', val, re.IGNORECASE):
                    val = clean_movie_name_str(val)
                    if val:
                        return val

    # Strategy 2: Small header tables (e.g. Abhiruchi City Pride, Miraj, Bhutani, Silwasa, Ramnagar, etc.)
    for page in pdf.pages[:1]:
        try:
            tables = page.extract_tables() or []
        except Exception:
            tables = []

        for t in tables:
            if not t:
                continue
            if len(t) in (2, 3) and all(len(row) == 1 for row in t):
                for row_idx in (1, 0):
                    cand = str(t[row_idx][0] or '').strip()
                    cand_lower = cand.lower()
                    if cand and not any(term in cand_lower for term in ('miraj', 'cineplex', 'studios', 'cinema', 'mall', 'miniplex', 'report', '* * hindi * *')):
                        return clean_movie_name_str(cand)
                    if cand and row_idx == 1:
                        return clean_movie_name_str(cand)

            for row in t:
                for cell in row:
                    if not cell:
                        continue
                    cell_str = str(cell).strip()
                    m_show = re.search(r'(?:(?:1st|2nd|3rd|4th|\d+th|Morning|Evening|Noon|Matinee)\s+Show\s*,\s*)([^,(\n\r]+)', cell_str, re.IGNORECASE)
                    if m_show:
                        return clean_movie_name_str(m_show.group(1))

    # Strategy 3: Text line search for Show rows or lines above Date / below Day
    for page in pdf.pages[:1]:
        text = page.extract_text() or ""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        for line in lines:
            m_show = re.search(r'(?:(?:1st|2nd|3rd|4th|\d+th|Morning|Evening|Noon|Matinee)\s+Show\s*,\s*)([^,(\n\r]+)', line, re.IGNORECASE)
            if m_show:
                return clean_movie_name_str(m_show.group(1))

            m_screen = re.search(r'^([A-Za-z0-9\s\-]+(?:\([A-Za-z0-9\s\-]+\))?)\s*\((?:SCREEN|AUDI)\s*\d+\)\s*@', line, re.IGNORECASE)
            if m_screen:
                return clean_movie_name_str(m_screen.group(1))

        for i, line in enumerate(lines[:15]):
            if re.search(r'^Date\s*:\s*\d{1,2}\s+[A-Za-z]+,\s*\d{4}', line, re.IGNORECASE) or re.search(r'^Date\s*:\s*\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}', line, re.IGNORECASE):
                if i > 0:
                    prev = lines[i - 1].strip()
                    if prev and not any(k in prev.lower() for k in ['gst', 'distributor', 'week', 'studio', 'limited', 'cinemas', 'pincode', 'phone']):
                        return clean_movie_name_str(prev)

    return fallback_name

def extract_date_safe(pdf) -> datetime:
    dt, _, _ = extract_all_metadata_fast(pdf)
    return dt

def extract_cinema_name_safe(pdf, fallback_name: str = "Unknown Cinema") -> str:
    _, cin, _ = extract_all_metadata_fast(pdf, fallback_name)
    return cin

def extract_address_safe(pdf) -> str:
    _, _, addr = extract_all_metadata_fast(pdf)
    return addr

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