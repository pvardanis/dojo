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
def _alembic_cfg(test_db_url: str) -> AlembicConfig:
    """Build an Alembic Config that points at the tmp DB.

    env.py respects a caller-set URL (the `driver://user:pass@...`
    placeholder is the only trigger for the settings fallback), so
    setting it here is all that is needed — no DATABASE_URL env var
    monkeypatch or get_settings.cache_clear gymnastics required.
    """
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
    """Function-scoped async session with SAVEPOINT-based isolation.

    Opens an outer transaction on a dedicated connection and binds
    the session to it via `join_transaction_mode="create_savepoint"`.
    Any `sess.commit()` or `sess.begin()` inside a test closes a
    SAVEPOINT — the outer transaction stays rollbackable, so teardown
    guarantees no state leaks to the next test regardless of what the
    test committed (D-06 + SQLAlchemy async "joining a transaction"
    recipe).
    """
    async with _migrated_engine.connect() as conn:
        outer = await conn.begin()
        factory = async_sessionmaker(
            bind=conn,
            expire_on_commit=False,
            class_=AsyncSession,
            join_transaction_mode="create_savepoint",
        )
        async with factory() as sess:
            yield sess
        await outer.rollback()
