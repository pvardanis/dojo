# ABOUTME: FastAPI composition root — wires settings, templates, routes.
# ABOUTME: The only module allowed to import across layers.
"""FastAPI composition root for Dojo."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
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
_PLACEHOLDER_API_KEY = "dev-placeholder"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: configure logging, guard the placeholder API key.

    :param app: The FastAPI application whose lifecycle this manager
        brackets. Required by FastAPI's lifespan contract; Dojo does
        not attach state to it at startup.
    :yields: Control back to FastAPI for the serving phase; no state
        is yielded to the caller.
    :raises RuntimeError: If ``DOJO_ENV=prod`` and the Anthropic API
        key is still the dev placeholder.
    """
    settings = get_settings()
    configure_logging(settings.log_level)
    _guard_api_key(settings.anthropic_api_key.get_secret_value())
    log.info("dojo.startup", database_url=settings.database_url)
    yield


def _guard_api_key(api_key: str) -> None:
    """Refuse to boot in prod with the placeholder Anthropic key.

    Without this guard, a prod deploy that forgets to set
    ANTHROPIC_API_KEY starts clean and only fails at the first LLM
    call with an opaque 401 buried in tenacity retries.
    """
    if api_key != _PLACEHOLDER_API_KEY:
        return
    if os.getenv("DOJO_ENV", "dev") == "prod":
        raise RuntimeError(
            "ANTHROPIC_API_KEY is the dev placeholder in a prod "
            "environment (DOJO_ENV=prod). Set a real key before boot."
        )
    log.warning("dojo.startup.placeholder_key")


def create_app() -> FastAPI:
    """Build the FastAPI app. Called by uvicorn via ``app.main:app``.

    :returns: A fully-wired ``FastAPI`` instance with templates,
        static files, and routers attached.
    """
    app = FastAPI(title="Dojo", lifespan=lifespan)
    app.state.templates = _TEMPLATES
    app.mount("/static", StaticFiles(directory=_STATIC), name="static")
    app.include_router(home.router)
    return app


app = create_app()
