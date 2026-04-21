# ABOUTME: Shared pytest fixtures for the whole test suite.
# ABOUTME: Wires tmp-file SQLite + real Alembic + SAVEPOINT session.
"""Shared fixtures for the Dojo test suite."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture(scope="session")
def event_loop_policy():
    """Override pytest-asyncio default policy for route tests.

    FastAPI routes are still async; the event loop is only relevant for
    tests under `tests/integration/test_home.py` and
    `tests/integration/test_main_lifespan.py`. DB tests became sync in
    the Phase 1 async → sync refactor; they do not use this fixture.
    """
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="session")
def test_db_url(tmp_path_factory) -> str:
    """Tmp-file SQLite URL, shared across the session."""
    path: Path = tmp_path_factory.mktemp("db") / "dojo.db"
    return f"sqlite:///{path}"


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
    setting it here is all that is needed.
    """
    cfg = AlembicConfig("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", test_db_url)
    return cfg


@pytest.fixture(scope="session")
def _migrated_engine(
    test_db_url: str, _alembic_cfg: AlembicConfig
) -> Iterator[Engine]:
    """Run alembic upgrade head once per session against tmp DB.

    Running the real migration (not Base.metadata.create_all)
    exercises the Alembic pipeline — defends against schema drift.
    """
    command.upgrade(_alembic_cfg, "head")

    engine = create_engine(test_db_url, future=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def session(_migrated_engine: Engine) -> Iterator[Session]:
    """Function-scoped sync session with SAVEPOINT-based isolation.

    Opens an outer transaction on a dedicated connection and binds
    the session to it via `join_transaction_mode="create_savepoint"`.
    Any `sess.commit()` or `sess.begin()` inside a test closes a
    SAVEPOINT — the outer transaction stays rollbackable, so teardown
    guarantees no state leaks to the next test regardless of what the
    test committed (D-06 + SQLAlchemy "joining a transaction" recipe).
    """
    with _migrated_engine.connect() as conn:
        outer = conn.begin()
        factory = sessionmaker(
            bind=conn,
            expire_on_commit=False,
            class_=Session,
            join_transaction_mode="create_savepoint",
        )
        with factory() as sess:
            yield sess
        outer.rollback()
