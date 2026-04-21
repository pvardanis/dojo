# ABOUTME: FastAPI composition root — wires settings, templates, routes.
# ABOUTME: The only module allowed to import across layers.
"""FastAPI composition root for Dojo."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.logging_config import configure_logging, get_logger
from app.settings import get_settings
from app.web.routes import home

log = get_logger(__name__)

_HERE = Path(__file__).resolve().parent
_TEMPLATES = Jinja2Templates(directory=_HERE / "web" / "templates")
_STATIC = _HERE / "web" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: configure logging. Shutdown: nothing in Phase 1."""
    settings = get_settings()
    configure_logging(settings.log_level)
    log.info("dojo.startup", database_url=settings.database_url)
    yield


def create_app() -> FastAPI:
    """Build the FastAPI app. Called by uvicorn via `app.main:app`."""
    app = FastAPI(title="Dojo", lifespan=lifespan)
    app.state.templates = _TEMPLATES
    app.mount("/static", StaticFiles(directory=_STATIC), name="static")
    app.include_router(home.router)
    return app


app = create_app()
