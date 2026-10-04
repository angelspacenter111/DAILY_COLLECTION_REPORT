from contextlib import asynccontextmanager
from fastapi import FastAPI
from routes.approuter import router as applicationrouter
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from helpers.database_helper import init_db_indexes
from helpers.auth_helper import seed_default_super_admin
from config import ENABLE_EMAIL_LISTENER
from services.email_listener import run_email_listener_loop

import asyncio
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await asyncio.wait_for(init_db_indexes(), timeout=4.0)
        await seed_default_super_admin()
    except Exception as e:
        logger.warning("Startup initialization notice: %s", str(e))

    email_task = None
    if ENABLE_EMAIL_LISTENER:
        logger.info("Initializing automated email listener background service...")
        email_task = asyncio.create_task(run_email_listener_loop())

    yield

    if email_task and not email_task.done():
        logger.info("Shutting down email listener background service...")
        email_task.cancel()
        try:
            await email_task
        except asyncio.CancelledError:
            pass

app = FastAPI(lifespan=lifespan)

app.include_router(applicationrouter)
app.mount("/static", StaticFiles(directory="static"), name="static")

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)

