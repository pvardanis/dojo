# ABOUTME: Lifespan smoke — configure_logging + dojo.startup emission.
# ABOUTME: Regression net for the only cross-layer wiring point in Phase 1.
"""FastAPI lifespan integration test."""

from __future__ import annotations

import logging

import pytest

from app.main import app


@pytest.mark.asyncio
async def test_lifespan_emits_startup_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """ASGI lifespan startup emits `dojo.startup` with `database_url`.

    A regression that drops the lifespan hook or skips the startup
    log (e.g. someone removes `log.info("dojo.startup", ...)`) would
    silently pass SC #2 — the home route still works. This test
    drives the lifespan context directly (httpx.ASGITransport does NOT
    invoke lifespan) and captures via stdlib caplog — structlog is
    wired on top of stdlib so events flow through the root logger.
    """
    caplog.set_level(logging.INFO, logger="app.main")
    async with app.router.lifespan_context(app):
        pass

    messages = [r.getMessage() for r in caplog.records if r.name == "app.main"]
    assert any("dojo.startup" in m for m in messages), messages
    assert any("database_url" in m for m in messages), messages
