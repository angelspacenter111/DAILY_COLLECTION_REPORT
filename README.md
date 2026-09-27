# Daily Collection Report (DCR) PDF Reader & Extractor

A robust web application built with **FastAPI** and **MySQL** to automatically parse Daily Collection Reports (DCR) and Distributor Reports from multiple cinema PDFs, clean and extract week-wise show metrics, and export them into structured formats.

## Features
- **Dynamic Table & Header Recognition**: Scans all PDF tables and accurately maps `Day`, `Shows`, `Attendance` (including `Seats Sold`), and `Nett` regardless of column order.
- **Housefull Net Exclusion**: Safely ignores capacity-based theoretical figures and captures true box office net collections.
- **Zero Attendance Normalization**: Automatically ensures that if attendance is zero, net collection is set to 0.00.
- **Embedded Sub-table & Multiline Parsing**: Supports complex multiplex layouts (including Miraj, CityPride, INOX, PVR) with stacked multiline cells.
- **Interactive UI**: Upload multiple PDF files simultaneously and view extraction status with clear diagnostic error reporting.
- **Excel Export**: Download formatted, color-coded `.xlsx` weekly reports with freeze panes and automatic border styling.
- **SQL Injection Prevention**: Parameterized queries using SQLAlchemy ensure safe and resilient database transactions.

## Tech Stack
- **Backend**: Python 3.10+, FastAPI, Uvicorn
- **PDF Extraction**: `pdfplumber`, Regular Expressions (`re`), `pandas`
- **Database**: MySQL, SQLAlchemy (`pymysql` driver)
- **Excel Generation**: `openpyxl`
- **Frontend**: Jinja2 Templates, Bootstrap CSS, Lucide Icons

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/angelspacenter111/DAILY_COLLECTION_REPORT.git
cd DAILY_COLLECTION_REPORT
```

### 2. Setup Virtual Environment & Dependencies
```bash
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
# source venv/bin/activate

pip install -r requirements.txt
```

### 3. Setup MySQL Database
1. Create a MySQL database named `fastapi_practice`.
2. Import the database schema from `fastapi_practice.sql`:
```bash
mysql -u root -p fastapi_practice < fastapi_practice.sql
```

### 4. Run the Application
```bash
uvicorn main:app --reload
```

Open your browser and navigate to:
- Dashboard: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Upload PDFs: [http://127.0.0.1:8000/create](http://127.0.0.1:8000/create)
- Extracted Records: [http://127.0.0.1:8000/dcrextracter](http://127.0.0.1:8000/dcrextracter)
- API Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
