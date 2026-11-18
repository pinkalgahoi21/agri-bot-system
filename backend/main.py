from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import database
from database import models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=database.engine)

from api.bot_webhook import startup_bot, shutdown_bot

@asynccontextmanager
async def lifespan(app):
    """Startup/shutdown lifecycle for the FastAPI app."""
    logger.info("Starting up — initializing Telegram bot...")
    await startup_bot()
    yield
    logger.info("Shutting down — stopping Telegram bot...")
    await shutdown_bot()

app = FastAPI(title="Farmer Advisory API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health_check():
    return {"status": "ok"}

from api.routes import router as api_router
from api.bot_webhook import router as bot_router

from api.auth import router as auth_router
app.include_router(auth_router, prefix="/api")
app.include_router(api_router, prefix="/api")
app.include_router(bot_router, prefix="/api")

from pathlib import Path
from fastapi.staticfiles import StaticFiles
site = Path(__file__).resolve().parents[1] / 'frontend' / 'dist'
if site.is_dir():
    app.mount('/', StaticFiles(directory=site, html=True), name='website')

