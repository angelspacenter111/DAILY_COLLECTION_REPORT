from contextlib import asynccontextmanager
from fastapi import FastAPI
from routes.approuter import router as applicationrouter
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from helpers.database_helper import init_db_indexes

import asyncio
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await asyncio.wait_for(init_db_indexes(), timeout=4.0)
    except Exception as e:
        logger.warning("Startup index initialization notice: %s", str(e))
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(applicationrouter)
app.mount("/static", StaticFiles(directory="static"), name="static")

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)

