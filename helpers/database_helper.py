from typing import Any, Dict, List, Optional
from sqlalchemy import text
from database import engine

async def createrecords(sql_string: str, params: Optional[Dict[str, Any]] = None) -> int:
    """Executes an INSERT statement with optional parameters and returns lastrowid."""
    with engine.begin() as conn:
        result = conn.execute(text(sql_string), params or {})
        return result.lastrowid

async def bulk_createrecords(sql_string: str, params_list: List[Dict[str, Any]]) -> None:
    """Executes a bulk INSERT statement with a list of parameter dictionaries."""
    if not params_list:
        return
    with engine.begin() as conn:
        conn.execute(text(sql_string), params_list)

async def fetchrecords(sql_string: str, params: Optional[Dict[str, Any]] = None):
    """Executes a SELECT query with optional parameters and returns result rows."""
    with engine.begin() as conn:
        result = conn.execute(text(sql_string), params or {})
        return result.mappings().all()

def main_query():
    sql_string = """
            SELECT
            r.id,
            r.cinema_name,
            r.distributor_address,
            r.file_name,
            r.report_date,
    
            MAX(CASE WHEN rd.day LIKE 'Fri%' THEN rd.shows END) AS fri_show,
            MAX(CASE WHEN rd.day LIKE 'Fri%' THEN rd.audience END) AS fri_admits,
            ROUND(MAX(CASE WHEN rd.day LIKE 'Fri%' THEN rd.final_net END), 2) AS fri_net,
    
            MAX(CASE WHEN rd.day LIKE 'Sat%' THEN rd.shows END) AS sat_show,
            MAX(CASE WHEN rd.day LIKE 'Sat%' THEN rd.audience END) AS sat_admits,
            ROUND(MAX(CASE WHEN rd.day LIKE 'Sat%' THEN rd.final_net END), 2) AS sat_net,
    
            MAX(CASE WHEN rd.day LIKE 'Sun%' THEN rd.shows END) AS sun_show,
            MAX(CASE WHEN rd.day LIKE 'Sun%' THEN rd.audience END) AS sun_admits,
            ROUND(MAX(CASE WHEN rd.day LIKE 'Sun%' THEN rd.final_net END), 2) AS sun_net,
    
            MAX(CASE WHEN rd.day LIKE 'Mon%' THEN rd.shows END) AS mon_show,
            MAX(CASE WHEN rd.day LIKE 'Mon%' THEN rd.audience END) AS mon_admits,
            ROUND(MAX(CASE WHEN rd.day LIKE 'Mon%' THEN rd.final_net END), 2) AS mon_net,
    
            MAX(CASE WHEN rd.day LIKE 'Tue%' THEN rd.shows END) AS tue_show,
            MAX(CASE WHEN rd.day LIKE 'Tue%' THEN rd.audience END) AS tue_admits,
            ROUND(MAX(CASE WHEN rd.day LIKE 'Tue%' THEN rd.final_net END), 2) AS tue_net,
    
            MAX(CASE WHEN rd.day LIKE 'Wed%' THEN rd.shows END) AS wed_show,
            MAX(CASE WHEN rd.day LIKE 'Wed%' THEN rd.audience END) AS wed_admits,
            ROUND(MAX(CASE WHEN rd.day LIKE 'Wed%' THEN rd.final_net END), 2) AS wed_net,
    
            MAX(CASE WHEN rd.day LIKE 'Thu%' THEN rd.shows END) AS thu_show,
            MAX(CASE WHEN rd.day LIKE 'Thu%' THEN rd.audience END) AS thu_admits,
            ROUND(MAX(CASE WHEN rd.day LIKE 'Thu%' THEN rd.final_net END), 2) AS thu_net,
    
            ROUND(SUM(COALESCE(rd.final_net, 0)), 2) AS grand_total
    
            FROM dcr_reports r
            LEFT JOIN dcr_report_details rd
                ON r.id = rd.report_id
    
            GROUP BY
                r.id,
                r.cinema_name,
                r.report_date
    
            ORDER BY r.id;
            """
    return sql_string