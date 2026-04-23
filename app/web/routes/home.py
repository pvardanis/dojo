# ABOUTME: Home + health routes — the Phase 1 minimum endpoints.
# ABOUTME: Proves FastAPI + Jinja + autoescape wiring end-to-end.
"""Home and health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Render the minimal Dojo home page.

    :param request: Incoming FastAPI request; used to resolve the
        Jinja2 templates registered on `app.state`.
    :returns: The rendered `home.html` response.
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request, name="home.html", context={}
    )


@router.get("/health", response_class=JSONResponse)
async def health() -> dict[str, str]:
    """Return a lightweight health probe JSON payload.

    :returns: `{"status": "ok"}` for liveness checks.
    """
    return {"status": "ok"}
