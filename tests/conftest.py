# ABOUTME: Shared pytest fixtures for the whole test suite.
# ABOUTME: Wires async event loop + tmp-file SQLite + real Alembic.
"""Shared async fixtures for the Dojo test suite."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest.fixture(scope="session")
def event_loop_policy():
    """Override pytest-asyncio default policy for the whole session.

    Using the default asyncio policy explicitly makes the session's
    event loop deterministic across platforms; pairs with
    `asyncio_default_fixture_loop_scope = "session"` in pyproject.
    """
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="session")
def test_db_url(tmp_path_factory) -> str:
    """Tmp-file SQLite URL, shared across the session (not :memory:).

    `:memory:` SQLite is per-connection in aiosqlite; a tmp file
    lets the session-scoped engine survive across fixtures.
    """
    path: Path = tmp_path_factory.mktemp("db") / "dojo.db"
    return f"sqlite+aiosqlite:///{path}"


@pytest.fixture(scope="session", autouse=True)
def _clamp_third_party_loggers() -> None:
    """Pristine test output: silence noisy libs at WARNING.

    D-17 + PITFALL m8: trafilatura/httpx/anthropic occasionally emit
    INFO/WARNING noise that violates the pristine-output rule.
    """
    for name in (
        "trafilatura",
        "httpx",
        "anthropic",
        "sqlalchemy.engine",
        "alembic",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)


@pytest.fixture(scope="session")
def _db_env(test_db_url: str) -> AsyncIterator[None]:
    """Point `DATABASE_URL` at the tmp DB for the whole session.

    env.py reads the URL via `get_settings().database_url`, and
    `get_settings` is `@lru_cache`'d — so we set the env var AND
    clear the cache before any migration or engine creation.
    Without this, env.py migrates the default `dojo.db` instead of
    the tmp DB, silently diverging from the session/engine fixtures.
    """
    from app.settings import get_settings

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATABASE_URL", test_db_url)
        get_settings.cache_clear()
        yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def _alembic_cfg(test_db_url: str, _db_env: None) -> AlembicConfig:
    """Build an Alembic Config that points at the tmp DB."""
    cfg = AlembicConfig("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", test_db_url)
    return cfg


@pytest_asyncio.fixture(scope="session")
async def _migrated_engine(
    test_db_url: str, _alembic_cfg: AlembicConfig
) -> AsyncIterator:
    """Run alembic upgrade head once per session against tmp DB.

    Running the real migration (not Base.metadata.create_all)
    exercises the async Alembic pipeline — defends against C4 drift.
    Alembic's sync CLI is wrapped in `asyncio.to_thread` to keep its
    event loop separate from pytest-asyncio's (New Pitfall 5).
    """
    await asyncio.to_thread(command.upgrade, _alembic_cfg, "head")

    engine = create_async_engine(test_db_url, future=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def session(
    _migrated_engine,
) -> AsyncIterator[AsyncSession]:
    """Function-scoped async session with outer-transaction rollback.

    Every test opens a session inside a transaction; teardown rolls
    back so tests don't see each other's data (D-06).
    """
    factory = async_sessionmaker(
        _migrated_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with factory() as sess:  # noqa: SIM117
        async with sess.begin():
            yield sess
            await sess.rollback()
