import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
MONGODB_URI = os.getenv("MONGODB_URI", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "DAILY_COLLECTION_REPORT")

# Email Ingestion Configuration
ENABLE_EMAIL_LISTENER = os.getenv("ENABLE_EMAIL_LISTENER", "true").lower() in ("true", "1", "yes")
EMAIL_HOST = os.getenv("EMAIL_HOST", "imap.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "993"))
EMAIL_USER = os.getenv("EMAIL_USER", "swarndeepvishwa16@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "").replace(" ", "").strip()
EMAIL_FOLDER = os.getenv("EMAIL_FOLDER", "INBOX")
EMAIL_CHECK_INTERVAL_SECONDS = int(os.getenv("EMAIL_CHECK_INTERVAL_SECONDS", "60"))
EMAIL_MARK_AS_SEEN = os.getenv("EMAIL_MARK_AS_SEEN", "true").lower() in ("true", "1", "yes")