# ABOUTME: SC #2 integration — exercises / and /health via ASGI.
# ABOUTME: Proves FastAPI + Jinja + composition-root wiring work.
"""Home and health route integration tests."""

from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_home_route_returns_200_html() -> None:
    """GET / returns 200 with the rendered home template.

    Assertions target template-specific markers (the <h1> heading and
    the base template's <main> landmark) rather than a bare "Dojo"
    substring — an error page or a stub containing the word "Dojo"
    anywhere must not false-pass.
    """
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<h1>Dojo</h1>" in response.text
    assert "<main>" in response.text


@pytest.mark.asyncio
async def test_health_route_returns_ok_json() -> None:
    """GET /health returns `{"status": "ok"}` JSON."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
