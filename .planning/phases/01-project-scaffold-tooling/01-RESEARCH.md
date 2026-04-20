# Phase 1: Project Scaffold & Tooling - Research

**Researched:** 2026-04-20
**Domain:** Python 3.12 async web-app scaffold (FastAPI + SQLAlchemy 2.0
async + aiosqlite + Alembic + pytest-asyncio + uv/ruff/ty/interrogate
+ pre-commit + GitHub Actions + structlog + pydantic-settings)
**Confidence:** HIGH on version pins and canonical patterns (verified
live 2026-04-20); MEDIUM on a couple of anticipated-gotcha items
flagged inline.

## Summary

Phase 1 is a reference-implementation scaffold for a 2026-standard
async Python web app. CONTEXT.md has already locked the architectural
and testing decisions (D-01 through D-20); the job of this research
is to confirm the [VERIFY] items against live docs, pin exact
versions, and hand the planner concrete drop-in snippets for the
config files, fixtures, and migration skeletons it will need to
write tasks against.

**All 10 [VERIFY] items resolved live.** The CONTEXT.md decisions all
hold. Two small refinements surfaced:

1. **pytest-asyncio 1.0+ is live** (current: 1.3.0). The canonical
   pattern has evolved since CONTEXT.md was written: the
   `event_loop_policy` session-scoped fixture is still the blessed
   knob for overriding the event-loop policy, but the newer
   `asyncio_default_fixture_loop_scope = "session"` config option in
   `pyproject.toml` is the preferred way to bind async fixtures to a
   session-scoped loop. Use **both** belt-and-braces: the config
   option for fixture scope + the `event_loop_policy` fixture for
   when a custom policy is ever needed.
2. **Anthropic SDK default retries = 2**, not 3 — the default stacks
   with a tenacity wrapper to produce 3 × (2 + 1) = 9 attempts. D-11
   puts the Anthropic adapter in Phase 3, but Phase 1's
   `settings.py` should reserve a `max_retries` knob so Phase 3 can
   pass it in without a config refactor. Optional — do not block
   Phase 1 on this if it complicates the settings surface.

**Primary recommendation:** Follow every CONTEXT.md decision verbatim.
Use the drop-in snippets below. The two refinements above are
additive, not overrides.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 — DB portability by construction.** The scaffold does not
hardcode SQLite as the only supported database:
- `DATABASE_URL` is a pydantic-settings field (default:
  `sqlite+aiosqlite:///dojo.db`) — not hardcoded in `session.py`.
- SQLite PRAGMA setup (`foreign_keys=ON`, `journal_mode=WAL`,
  `busy_timeout=5000`) lives in a connection-event listener that is
  dialect-guarded (only fires when `engine.dialect.name == "sqlite"`).
- Alembic `env.py` reads the DB URL from the same `pydantic-settings`
  singleton the app uses (no parallel config source).
- Tests parameterise their DB fixture off `DATABASE_URL` too.

**D-02 — Portability is "not slamming the door," not plug-and-play.**
Column-type portability is a Phase 3 concern and is not pre-decided
here.

**D-03 — Rationale:** marginal cost is ~3-5 lines (the dialect guard
around PRAGMAs); the rest is correctness-mandated anyway.

**D-04 — `asyncio_mode = "auto"`** in `pyproject.toml` under
`[tool.pytest.ini_options]`. No per-test `@pytest.mark.asyncio`
decorators.

**D-05 — pytest-asyncio 0.24+ canonical pattern:** session-scoped
`event_loop_policy` fixture (not deprecated `event_loop` fixture).

**D-06 — DB fixture architecture:**
- Session-scoped async engine bound to a tmp-file SQLite DB (not
  `:memory:`).
- Session-scoped migration run: `alembic upgrade head` once per test
  session against the tmp DB.
- Function-scoped session with outer-transaction rollback.

**D-07 — SC #4 verified via `pytest-repeat` or equivalent.** The
first integration test opens a real async session, executes a trivial
query, closes cleanly.

**D-08 — Empty initial Alembic revision in Phase 1** (no DDL, no
`op.create_table`). `alembic upgrade head` creates
`alembic_version` table — that is the "expected table" for SC #3.

**D-09 — Rationale:** canonical Alembic pattern; proves the full
async-migration pipeline.

**D-10 — Phase 3 owns the first real-schema migration.**

**D-11 — Absolute-minimum scaffold.** Only create:
- `app/main.py`, `app/settings.py`, `app/logging_config.py`
- `app/web/routes/home.py`, `app/web/templates/base.html`,
  `app/web/templates/home.html`, `app/web/static/` (empty)
- `app/infrastructure/db/session.py`
- `migrations/env.py` + `migrations/versions/<stamp>_initial.py`
- `tests/conftest.py` + `tests/integration/test_db_smoke.py`
- No empty `__init__.py` shells; no `app/domain/`,
  `app/application/`, `app/infrastructure/repositories/`, etc.

**D-12 — `/` renders minimal Jinja home page** (title "Dojo" +
placeholder text, no real links). Template extends `base.html`.

**D-13 — `/health` returns JSON `{"status": "ok"}`.** SC #2 reads as
two routes.

**D-14 — Pre-commit hook scope** matches spec §8.2: ruff format +
ruff check + ty + interrogate + pytest. But pytest in the hook runs
only `pytest tests/unit/ -x --ff`, not the full suite. Hook order:
(1) ruff format, (2) ruff check --fix, (3) ty, (4) interrogate,
(5) pytest tests/unit/ -x --ff.

**D-15 — interrogate + Protocol methods:** accept one-line docstrings
on Protocol methods. Do NOT add `app/application/ports.py` to
interrogate's ignore list. 100% means 100%.

**D-16 — `ty` pinned to exact patch version** (not a floor).

**D-17 — Structlog rendering:** dev uses
`structlog.dev.ConsoleRenderer`; tests use the same renderer but with
log level `WARNING` via a conftest fixture; prod uses
`structlog.processors.JSONRenderer`. One `get_logger(__name__)`
helper.

**D-18 — Settings surface** on day one: `ANTHROPIC_API_KEY`,
`DATABASE_URL` (default `sqlite+aiosqlite:///dojo.db`), `LOG_LEVEL`
(default `INFO`), `RUN_LLM_TESTS` (default `False`). All from `.env`
via pydantic-settings. `.env.example` ships every field with safe
placeholders.

**D-19 — CI workflow:** `.github/workflows/ci.yml` — single job,
Python 3.12, steps: checkout → setup uv → `make install` →
`make check`. Cache uv on `uv.lock` hash. Concurrency group cancels
in-progress runs for the same PR. No Playwright in Phase 1 CI.

**D-20 — `pyproject.toml` declares Dojo as installable package**
(`[project]` + `[tool.uv] package = true`) so Alembic's `env.py` can
`from app.infrastructure.db import Base` without PYTHONPATH hacks.

### Claude's Discretion

- Exact `tmp_path_factory` fixture shape for session DB tmp file.
- Whether to use `pytest-repeat` (dev dep) or a shell loop for SC #4.
- Concrete `ty` patch version (resolve via `uv sync` then pin).
- Whether `pre-commit` config uses `local` hooks calling `uv run`
  vs language-native hook repositories.
- `.env.example` exact field wording.

### Deferred Ideas (OUT OF SCOPE)

- Full DB portability (plug-and-play Postgres swap) — Phase 1 keeps
  the door open but doesn't make a swap free.
- Playwright in CI — Phase 7 adds E2E; Phase 1 CI stays Playwright-free.
- `mypy` as ty fallback — documented in CLAUDE.md, not pre-installed.
- Import-linter — Phase 2 owns the layer-boundary test.
- Playwright + HTMX flake mitigations — Phase 5/7.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OPS-01 | Makefile with install/format/lint/typecheck/docstrings/test/check/run/migrate targets; `make check` = format+lint+typecheck+docstrings+test; no `db-reset` target | §Makefile drop-in below gives all 9 targets, commented to map 1:1 with spec §8.1 |
| OPS-02 | `pre-commit` runs on every commit; `pre-commit install` part of `make install` | §.pre-commit-config.yaml drop-in uses `repo: local` with `uv run` + `pass_filenames` toggles per D-14 hook order |
| OPS-03 | GitHub Actions CI runs `make check` on push and PR; single job on Python 3.12 | §ci.yml drop-in uses `astral-sh/setup-uv@v8` with `enable-cache: true` + concurrency cancel-in-progress per D-19 |
| OPS-04 | Structlog configured at app startup; every module uses `get_logger(__name__)` | §structlog config drop-in shows `configure_once()` pattern with env-switched `ConsoleRenderer`/`JSONRenderer` per D-17; test fixture clamps stdlib loggers to WARNING per M8 |
| TEST-02 | `make check` exits zero: ruff clean, ty clean, interrogate 100%, pytest pristine | §pyproject.toml drop-in sets `[tool.interrogate] fail-under = 100`, `[tool.ruff] line-length = 79`, `[tool.pytest.ini_options] filterwarnings = error` for pristine enforcement |
| LLM-03 | `ANTHROPIC_API_KEY` loads from `.env` via pydantic-settings; `.env.example` checked in; `.env` gitignored; key never leaves settings | §Settings drop-in uses `SettingsConfigDict(env_file=".env", extra="ignore")` with `SecretStr`; `.gitignore` adds `.env`; `.env.example` pattern below |

</phase_requirements>

## Architectural Responsibility Map

Phase 1 establishes the foundation for later-phase tiers but does
**not** implement business-tier capabilities. The capabilities below
are the ones Phase 1 delivers.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HTTP routing + Jinja rendering (`/`, `/health`) | Presentation (`app/web/`) | — | FastAPI + Jinja2 live in the outermost layer per spec §4.1 |
| App composition / lifespan | Presentation (`app/main.py`) | Application (future) | `main.py` is the composition root — the only module that wires layers per CLAUDE.md; Phase 1 wires only settings + templates, no use cases yet |
| Config loading | Application-boundary (`app/settings.py`) | Infrastructure (reads `.env` file) | pydantic-settings is a validation boundary (Pydantic is allowed here per wiki), imported by any layer |
| Structured logging | Infrastructure (`app/logging_config.py`) | All layers (via `get_logger`) | Logging config is an infrastructure concern; every layer consumes the `get_logger` helper |
| Async DB session factory | Infrastructure (`app/infrastructure/db/session.py`) | — | SQLAlchemy + aiosqlite are infra per spec §4.1; the dialect-guarded PRAGMA listener lives here |
| Alembic migrations + env.py | Infrastructure (`migrations/`) | — | env.py imports `app.settings.Settings` (app-boundary) and reaches toward `app.infrastructure.db.Base` (infra) — dependency flows outward-from-inner per CLAUDE.md's inward-only rule (this is fine: migrations are tooling, not application code) |
| Test infrastructure (conftest, fixtures) | Test tier (`tests/`) | Infrastructure (consumes real session + real migrations) | Integration tests are allowed to reach infra per spec §7.2 |

**Why this matters for Phase 1:** everything delivered in Phase 1
lives in Presentation, Infrastructure, and app-boundary (`settings`,
`logging_config`). Phase 1 must not create `app/domain/`,
`app/application/`, `app/infrastructure/repositories/` — those are
Phase 2 / Phase 3 concerns (D-11). If the planner produces a task
that touches those directories, it has overreached.

## Standard Stack

### Core (verified live 2026-04-20)

| Library | Version (verified) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12.x | Language | Spec pin; mature wheels across stack [VERIFIED: PROJECT.md + spec §4] |
| FastAPI | ≥ 0.118, use 0.136 floor | Web framework | Current latest is 0.136.0; 0.118+ required because 0.118 changed dependency-exit-code timing in a way later versions depend on [VERIFIED: PyPI + release notes] |
| Uvicorn | ≥ 0.30 | ASGI dev server | Standard FastAPI pairing [VERIFIED: STACK.md, unchanged] |
| Pydantic | ≥ 2.9 | Data modelling | v2 required by FastAPI 0.115+; 2.9 is the current-stable floor [VERIFIED: PyPI] |
| pydantic-settings | ≥ 2.8, use 2.14 floor | Config via env | Current latest is 2.14.0 (released 2026-04-20); 2.8+ has the `SettingsConfigDict` API the scaffold uses [VERIFIED: PyPI 2026-04-20] |
| Jinja2 | ≥ 3.1 | Templating | Starlette's `Jinja2Templates(directory=...)` enables autoescape by default for `.html/.htm/.xml` [VERIFIED: Starlette PR #3148 — resolves FLAG 10] |
| SQLAlchemy | ≥ 2.0.38, floor 2.0.49 | ORM | Current is 2.0.49 (2026-04-03); 2.0.38+ has the aiosqlite daemon-thread fix [VERIFIED: sqlalchemy.org blog] |
| aiosqlite | ≥ 0.22.1 | Async SQLite driver | 0.22.1 unlocks the SQLAlchemy 2.0.38 `terminate` support [VERIFIED: SQLAlchemy 2.0.38 release notes] |
| Alembic | ≥ 1.13, use 1.18 floor | Migrations | Current is 1.18.4; async env template is unchanged in shape [VERIFIED: Alembic docs + GitHub async template at main branch] |
| anthropic (SDK) | ≥ 0.87, floor 0.96 | Claude API client | Current is 0.96.0 (2026-04-16). **Default `max_retries=2`** — important for PITFALL C7 [VERIFIED: anthropic-sdk-python README + PyPI] |
| structlog | ≥ 24.4, floor 25.5 | Structured logging | Current stable docs at 25.5.0; `ConsoleRenderer` + `JSONRenderer` + `configure_once()` pattern all stable since 24.x [VERIFIED: structlog.org stable docs] |

### Supporting (dev tooling, verified live)

| Library | Version (verified) | Purpose | Notes |
|---------|---------|---------|-------|
| uv | ≥ 0.4 | Package / env manager | Current-stable workflow; `[tool.uv] package = true` is the canonical opt-in to editable-install [VERIFIED: docs.astral.sh/uv/concepts/projects/config/] |
| ruff | ≥ 0.8, floor 0.9 | Linter + formatter | 0.9 released 2026-02-26; 79-char line length lives under `[tool.ruff]` (top-level) or `[tool.ruff.format]` per current config layout [VERIFIED: docs.astral.sh/ruff/configuration/] |
| ty | exact pin **0.0.31** | Type checker | **Still beta as of 2026-04-15.** Current is 0.0.31. Stable 1.0 targeted 2026. Pin exact patch per D-16; expect breaking releases [VERIFIED: PyPI + pydevtools.com/blog/ty-beta/] |
| interrogate | ≥ 1.7 | Docstring coverage | Stable [ASSUMED — no change since STACK.md] |
| pytest | ≥ 8.3 | Test runner | Stable [ASSUMED — no change since STACK.md] |
| pytest-asyncio | **≥ 1.0, floor 1.3.0** | Async test support | **Major version 1.0 has shipped** since STACK.md was written. 1.3.0 is current (2025-11-10). 1.0 removed the deprecated `event_loop` fixture [VERIFIED: PyPI + pytest-asyncio docs 1.3.0] |
| pytest-cov | ≥ 5.0 | Coverage | Stable [ASSUMED] |
| pytest-repeat | ≥ 0.9.4 | Repeat test N times for SC #4 | Current is 0.9.4 (2025-04-07); `pytest --count=N` is the invocation [VERIFIED: PyPI] |
| pre-commit | ≥ 3.7 | Git hook runner | Stable [ASSUMED] |

### Not installed in Phase 1 (deferred)

| Library | Deferred to | Why |
|---------|------------|-----|
| respx, playwright, tenacity, nh3, markdown-it-py, trafilatura, httpx | Phase 3+ | Phase 1 is absolute-minimum scaffold per D-11; these arrive when the phases that use them arrive |

### Alternatives Considered and Rejected

| Instead of | Rejected | Why |
|------------|----------|-----|
| `pytest-asyncio` 0.24 pattern | pytest-asyncio ≥ 1.0 | 1.0 is stable and removes the deprecation noise from `event_loop` fixture |
| `mypy` | `ty` | Spec-mandated; `mypy` stays as a fallback only (D-16) |
| `pip-tools` | uv | uv is 2026-standard, one tool instead of three |
| `Base.metadata.create_all` in tests | `alembic upgrade head` in tests | D-06 mandates running real migrations in tests to guard C4 drift |

**Installation:**

```bash
uv sync
uv run pre-commit install
uv run alembic upgrade head
```

**Version verification at implementation time:** before committing
`pyproject.toml`, run `uv tree --depth 1` and confirm each top-level
dep's resolved version matches or exceeds the floor in this file.
`uv sync` will resolve the current-stable patch for each floor.

## Architecture Patterns

### System Architecture Diagram (Phase 1 runtime)

```
                    ┌──────────────────────────────────────┐
                    │  Developer shell: `make run`         │
                    └───────────────┬──────────────────────┘
                                    ▼
                    ┌──────────────────────────────────────┐
                    │  Uvicorn (asgi) — dev reload          │
                    └───────────────┬──────────────────────┘
                                    ▼
        ┌───────────────────────────────────────────────────────┐
        │                 FastAPI app                           │
        │                                                       │
        │   ┌────────────┐                     ┌─────────────┐  │
  HTTP →│   │ /          │ Jinja autoescape    │ /health     │──│→ JSON
        │   │ home.html  │ (Starlette default) │             │  │
        │   └─────┬──────┘                     └─────────────┘  │
        │         │                                             │
        │         ▼                                             │
        │   ┌──────────────┐          ┌──────────────────────┐  │
        │   │ get_settings │◀─────────│ pydantic-settings    │  │
        │   │  (dep cache) │          │  reads .env on boot  │  │
        │   └──────────────┘          └──────────────────────┘  │
        │                                                       │
        │   ┌──────────────────────────────────────────────┐    │
        │   │ structlog.configure_once() at startup        │    │
        │   │  → get_logger(__name__) everywhere           │    │
        │   └──────────────────────────────────────────────┘    │
        └───────────────────────────────┬───────────────────────┘
                                        │ (future phases only)
                                        ▼
                             ┌───────────────────────┐
                             │ async_sessionmaker    │
                             │  (expire_on_commit=   │
                             │   False)              │
                             └───────────┬───────────┘
                                         ▼
                             ┌───────────────────────┐
                             │ AsyncEngine           │
                             │   + connect listener  │
                             │   (dialect-guarded):  │
                             │   SQLite → PRAGMA     │
                             │   foreign_keys=ON,    │
                             │   journal_mode=WAL,   │
                             │   busy_timeout=5000   │
                             └───────────┬───────────┘
                                         ▼
                             ┌───────────────────────┐
                             │ aiosqlite → dojo.db   │
                             │  (schema: just        │
                             │   `alembic_version`)  │
                             └───────────────────────┘

   ┌────────────────────────────────────────────────────────────┐
   │          Alembic (out-of-process: `make migrate`)           │
   │                                                             │
   │   env.py → imports app.settings.Settings                    │
   │          → constructs async engine from DATABASE_URL        │
   │          → run_sync(do_run_migrations) inside               │
   │            async connection                                 │
   │          → revisions/<stamp>_initial.py (empty)             │
   └────────────────────────────────────────────────────────────┘
```

**Component responsibilities (Phase 1 only):**

| File | Responsibility |
|------|---------------|
| `app/main.py` | Composition root; creates FastAPI app; mounts templates, static, home router; configures logging on startup |
| `app/settings.py` | Single `Settings` pydantic-settings class; `get_settings()` `@lru_cache`'d for DI |
| `app/logging_config.py` | `configure_logging(settings)` called once at startup; `get_logger(name)` helper; env-switched renderer |
| `app/web/routes/home.py` | Two routes: `GET /` (renders `home.html`) and `GET /health` (returns `{"status": "ok"}`) |
| `app/web/templates/base.html` | Minimal HTML5 shell; extend-points for Phase 4+ |
| `app/web/templates/home.html` | Extends `base.html`; title "Dojo" + one `<p>` placeholder |
| `app/infrastructure/db/session.py` | `engine`, `async_sessionmaker`, dialect-guarded `@event.listens_for(engine.sync_engine, "connect")` for SQLite pragmas; exports `Base` (empty `DeclarativeBase` subclass) |
| `migrations/env.py` | Async Alembic env; imports `app.settings.Settings`; imports `app.infrastructure.db.Base` as `target_metadata`; runs migrations via `run_sync(do_run_migrations)` |
| `migrations/versions/<stamp>_initial.py` | Empty revision: `upgrade()` and `downgrade()` bodies are `pass` |
| `tests/conftest.py` | `event_loop_policy` fixture, session-scoped engine fixture, session-scoped `alembic upgrade head`, function-scoped session with rollback, stdlib logger clamp to WARNING |
| `tests/integration/test_db_smoke.py` | One test: open session, execute `SELECT 1`, close. This is the SC #4 canary |

### Pattern: dialect-guarded connection listener (addresses M12, FLAG 6, C9)

**What:** set SQLite pragmas only when the dialect is SQLite, so a
future Postgres swap doesn't blow up.

**Example drop-in for `app/infrastructure/db/session.py`:**

```python
# ABOUTME: Async SQLAlchemy engine + session factory.
# ABOUTME: Dialect-guarded connection listener sets SQLite pragmas.

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.settings import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models (populated in Phase 3)."""


_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    echo=False,
    future=True,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = (
    async_sessionmaker(
        engine,
        expire_on_commit=False,  # C3 mitigation
        class_=AsyncSession,
    )
)


@event.listens_for(engine.sync_engine, "connect")
def _configure_sqlite(dbapi_conn, _):
    """Apply SQLite-only pragmas; no-op on other dialects."""
    if engine.dialect.name != "sqlite":
        return
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()
```

**Source:** listener pattern is canonical SQLAlchemy (see
`docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html`); WAL + busy
timeout per M12. Dialect guard is the D-01 deliverable.

### Pattern: pytest-asyncio 1.x fixture architecture (addresses D-05,
M8)

**What:** session-scoped event loop + session-scoped engine +
session-scoped `alembic upgrade head` + function-scoped session with
rollback.

**Example drop-in for `tests/conftest.py`:**

```python
# ABOUTME: Shared pytest fixtures for the whole test suite.
# ABOUTME: Wires async event loop + tmp-file SQLite + real Alembic.

from __future__ import annotations

import asyncio
import logging
import os
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
def _clamp_third_party_loggers():
    """Pristine test output: silence noisy libs at WARNING.

    D-17 + PITFALL m8: trafilatura/httpx/anthropic occasionally emit
    INFO/WARNING noise that violates the pristine-output rule.
    """
    for name in ("trafilatura", "httpx", "anthropic",
                 "sqlalchemy.engine", "alembic"):
        logging.getLogger(name).setLevel(logging.WARNING)


@pytest.fixture(scope="session")
def _alembic_cfg(test_db_url: str) -> AlembicConfig:
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
    """
    # Alembic's online mode is sync-aware; it drives async under the
    # hood via the env.py we ship. Running in a thread keeps the
    # sync Alembic CLI out of our test event loop.
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
        _migrated_engine, expire_on_commit=False,
        class_=AsyncSession,
    )
    async with factory() as sess:
        async with sess.begin():
            yield sess
            await sess.rollback()
```

**Why this shape:** addresses all of D-04, D-05, D-06, D-07, M8, and
m8 in one fixture file. `asyncio_default_fixture_loop_scope =
"session"` in pyproject.toml (see pyproject drop-in below) is what
actually binds async fixtures to a single session-scoped loop;
`event_loop_policy` is the blessed override point if a custom policy
is ever needed.

**Source:** pytest-asyncio 1.0+ migration guide
(`pytest-asyncio.readthedocs.io/en/stable/reference/fixtures/`);
session-scoped pattern from SQLAlchemy + pytest-asyncio community
guide.

### Pattern: empty initial Alembic revision (addresses D-08/D-09)

**Filename shape:** `migrations/versions/20260420_0000-initial.py`
(or whatever stamp `alembic revision -m "initial" --rev-id=0001`
generates).

**Body:**

```python
# ABOUTME: Initial empty Alembic revision.
# ABOUTME: Creates the alembic_version tracking table as a side effect.

"""initial

Revision ID: 0001
Revises:
Create Date: 2026-04-20 00:00:00.000000

"""

from collections.abc import Sequence

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No schema changes in Phase 1; Phase 3 adds real tables."""


def downgrade() -> None:
    """No-op; initial revision has nothing to undo."""
```

**Why:** Alembic's first `upgrade head` run creates the
`alembic_version` table regardless of the revision's body. That
table is the "expected table" satisfying SC #3 when
`sqlite3 dojo.db .schema` is run.

**Source:** Alembic tutorial
(`alembic.sqlalchemy.org/en/latest/tutorial.html`); confirms that
`alembic_version` is created on every fresh DB the first time
`upgrade` runs.

### Pattern: async Alembic env.py with pydantic-settings

**Drop-in for `migrations/env.py`** (adapted from the canonical
async template, with D-01 pydantic-settings wiring and M9 eager
import):

```python
# ABOUTME: Async Alembic env.py.
# ABOUTME: Reads DB URL from app.settings; imports Base for autogen.

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.infrastructure.db.session import Base  # noqa: F401 (M9)
from app.settings import get_settings

config = context.config

# Override the static URL in alembic.ini with the pydantic-settings
# value — single source of truth for DATABASE_URL (D-01).
config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode (for --sql output)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations inside a sync connection wrapper."""
    context.configure(
        connection=connection, target_metadata=target_metadata
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations inside it."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in online mode (the usual path)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Key deltas vs vanilla `alembic init -t async`:**

1. `from app.infrastructure.db.session import Base` replaces the
   placeholder `target_metadata = None`.
2. `config.set_main_option("sqlalchemy.url", ...)` replaces the
   hardcoded URL in `alembic.ini` — D-01 single source of truth.
3. `# noqa: F401` is intentional — importing `Base` has the side
   effect of triggering model-module imports (M9 defense, even
   though Phase 1 has no models yet).

**Source:** Alembic async template (verified fetched from
`github.com/sqlalchemy/alembic/blob/main/alembic/templates/async/env.py`
2026-04-20).

### Pattern: settings with pydantic-settings (addresses D-18, LLM-03)

**Drop-in for `app/settings.py`:**

```python
# ABOUTME: App settings loaded from .env via pydantic-settings.
# ABOUTME: Single source of truth for config, including DB + API key.

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Real environment variables take precedence over .env values
    (pydantic-settings default). Keep the surface minimal; add
    fields only when a phase needs them.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    anthropic_api_key: SecretStr
    database_url: str = "sqlite+aiosqlite:///dojo.db"
    log_level: str = "INFO"
    run_llm_tests: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return the app's singleton settings (cached)."""
    return Settings()  # type: ignore[call-arg]
```

**Why `SecretStr` for the API key:**
- `repr(settings.anthropic_api_key)` → `"SecretStr('**********')"`
  — key can't accidentally land in logs.
- Access the real value only at the SDK boundary via
  `.get_secret_value()`.

**`.env.example` (ship this, gitignore the real `.env`):**

```dotenv
# ABOUTME: Example environment config for Dojo.
# ABOUTME: Copy to .env and fill in the real key; never commit .env.

# Real env vars win over .env values (pydantic-settings precedence).

# Required: your Anthropic API key (sk-ant-...)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional: async SQLAlchemy URL; default is local SQLite.
DATABASE_URL=sqlite+aiosqlite:///dojo.db

# Optional: log level (DEBUG/INFO/WARNING/ERROR).
LOG_LEVEL=INFO

# Optional: set to 1 to run contract tests against real Anthropic.
RUN_LLM_TESTS=0
```

**Source:** pydantic-settings
`docs.pydantic.dev/latest/api/pydantic_settings/`; `SecretStr`
pattern from pydantic docs.

### Pattern: structlog config (addresses D-17, OPS-04)

**Drop-in for `app/logging_config.py`:**

```python
# ABOUTME: Structlog + stdlib logging configuration.
# ABOUTME: Dev → ConsoleRenderer; prod → JSONRenderer; tests → WARNING.

from __future__ import annotations

import logging
import os
import sys
from typing import Any

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog + stdlib logging once at app startup."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if os.getenv("DOJO_ENV", "dev") == "prod":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure_once(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """Return a module-bound structlog logger.

    Every module uses `log = get_logger(__name__)` — identical ergonomics
    to stdlib logging, structlog's structure underneath.
    """
    return structlog.get_logger(name)
```

**Source:** structlog
`www.structlog.org/en/stable/getting-started.html` and
`api.html#structlog.configure_once`.

**In `app/main.py`:** call `configure_logging(settings.log_level)`
inside the FastAPI lifespan startup hook (not at import time —
lifespan gives tests control over when logging is configured).

### Pattern: FastAPI main.py composition root (addresses D-11/D-12/D-13)

**Drop-in for `app/main.py`:**

```python
# ABOUTME: FastAPI composition root — wires settings, templates, routes.
# ABOUTME: The only module allowed to import across layers.

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
    app.mount(
        "/static", StaticFiles(directory=_STATIC), name="static"
    )
    app.include_router(home.router)
    return app


app = create_app()
```

**Note on Jinja2 autoescape (FLAG 10 resolution):** Starlette's
`Jinja2Templates(directory=...)` enables `select_autoescape()` by
default for `.html/.htm/.xml` since PR Kludex/starlette#3148. No
explicit `autoescape=True` needed. **Verified:** Starlette source
confirms `select_autoescape(["html", "htm", "xml"])` is the baseline.

**Drop-in for `app/web/routes/home.py`:**

```python
# ABOUTME: Home + health routes — the Phase 1 minimum endpoints.
# ABOUTME: Proves FastAPI + Jinja + autoescape wiring end-to-end.

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Render the minimal Dojo home page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request, name="home.html", context={}
    )


@router.get("/health", response_class=JSONResponse)
async def health() -> dict[str, str]:
    """Return a lightweight health probe JSON payload."""
    return {"status": "ok"}
```

**Templates:**

```html
{# app/web/templates/base.html #}
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>{% block title %}Dojo{% endblock %}</title>
  </head>
  <body>
    <main>
      {% block content %}{% endblock %}
    </main>
  </body>
</html>
```

```html
{# app/web/templates/home.html #}
{% extends "base.html" %}
{% block title %}Dojo{% endblock %}
{% block content %}
  <h1>Dojo</h1>
  <p>MLOps interview-prep study app. Scaffold only —
     flows land in later phases.</p>
{% endblock %}
```

### Pattern: pyproject.toml (addresses D-04, D-16, D-20, OPS-01,
TEST-02)

**Drop-in skeleton:**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "dojo"
version = "0.1.0"
description = "Local MLOps interview-prep study app."
requires-python = ">=3.12,<3.13"
dependencies = [
    "fastapi>=0.118",
    "uvicorn[standard]>=0.30",
    "jinja2>=3.1",
    "python-multipart>=0.0.9",
    "pydantic>=2.9",
    "pydantic-settings>=2.8",
    "sqlalchemy[asyncio]>=2.0.38",
    "aiosqlite>=0.22.1",
    "alembic>=1.13",
    "structlog>=24.4",
]

[dependency-groups]
dev = [
    "ruff>=0.8",
    "ty==0.0.31",              # D-16: exact pin, still beta
    "interrogate>=1.7",
    "pytest>=8.3",
    "pytest-asyncio>=1.0",     # 1.0+ removed deprecated event_loop
    "pytest-cov>=5.0",
    "pytest-repeat>=0.9.4",    # For SC #4's 10x flake check
    "pre-commit>=3.7",
]

[tool.uv]
package = true                 # D-20: editable-install for Alembic

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.ruff]
line-length = 79               # wiki: python-project-setup convention
target-version = "py312"

[tool.ruff.lint]
# Conservative baseline; expand in Phase 2 when code volume grows.
select = ["E", "F", "W", "I", "B", "UP", "SIM"]

[tool.ruff.format]
quote-style = "double"

[tool.pytest.ini_options]
asyncio_mode = "auto"                            # D-04
asyncio_default_fixture_loop_scope = "session"   # pytest-asyncio 1.x
addopts = [
    "--strict-markers",
    "--strict-config",
    "-ra",
    "--cov=app",
    "--cov-report=term-missing",
]
filterwarnings = [
    "error",                                     # pristine-output rule
    # Add targeted ignores here as Phase 3+ libs need them.
]
testpaths = ["tests"]

[tool.coverage.run]
branch = true
source = ["app"]

[tool.interrogate]
fail-under = 100                                 # D-15
verbose = 2
# D-15: do NOT add app/application/ports.py to `exclude`.
exclude = ["migrations", "tests", "docs"]
ignore-init-method = true
ignore-init-module = true
ignore-magic = true

[tool.ty]
# D-16: pin exact patch; review release notes on every bump.
# Detailed rules TBD — start with defaults, tighten when Phase 2
# introduces real code.
```

**Notes on the pyproject:**

1. **`[tool.uv] package = true`** — the canonical way to tell uv to
   install the project as an editable package, which is what makes
   `from app.infrastructure.db import Base` work from Alembic's
   `env.py` (D-20). Pair with `[build-system]` + hatchling (any PEP
   517 backend is fine) so `uv sync` actually has something to build.
2. **`asyncio_default_fixture_loop_scope = "session"`** — the
   pytest-asyncio 1.x config knob that makes async fixtures share
   the session loop without each fixture having to set `loop_scope=`.
3. **`filterwarnings = ["error"]`** — promotes warnings to errors
   during tests, enforcing the pristine-output rule (TEST-02, m8).
   Add targeted ignores only when a real third-party warning can't
   be fixed at source.
4. **`[tool.ty]`** — the ty config section is deliberately empty in
   Phase 1. ty is still beta (0.0.31); adding strictness flags
   aspirationally now will churn when ty changes its config schema
   pre-1.0. Defaults are sensible for an empty scaffold; tighten
   when Phase 2 adds real domain code.

### Pattern: Makefile (addresses OPS-01)

**Drop-in:**

```makefile
# ABOUTME: Dojo dev workflow. `make check` is the CI contract.
# ABOUTME: Mirrors spec §8.1 exactly: 9 targets, no db-reset.

.PHONY: install format lint typecheck docstrings test check run migrate

install:
	uv sync
	uv run pre-commit install

format:
	uv run ruff format .

lint:
	uv run ruff check --fix .

typecheck:
	uv run ty check app migrations

docstrings:
	uv run interrogate -c pyproject.toml app

test:
	uv run pytest

check: format lint typecheck docstrings test

run:
	uv run uvicorn app.main:app --reload --port 8000

migrate:
	uv run alembic upgrade head

# Not a phony target on purpose — planner should not add db-reset.
```

**Notes:**

- `lint` includes `--fix` so ruff can auto-correct; this matches the
  pre-commit hook order (format → lint-with-fix → ty → interrogate
  → pytest).
- `ty check app migrations` — scope ty to `app/` and `migrations/`.
  `tests/` is excluded because pytest fixtures often use patterns ty
  doesn't like yet (beta-tool tolerance).

### Pattern: pre-commit (addresses D-14, OPS-02, M10)

**Drop-in `.pre-commit-config.yaml`:**

```yaml
# ABOUTME: Pre-commit hooks. Mirrors make check on staged files.
# ABOUTME: Hook order matters (M10): format → lint --fix → ty → docs → unit tests.

repos:
  - repo: local
    hooks:
      - id: ruff-format
        name: ruff format
        entry: uv run ruff format
        language: system
        types: [python]
        pass_filenames: true

      - id: ruff-check
        name: ruff check (with --fix)
        entry: uv run ruff check --fix
        language: system
        types: [python]
        pass_filenames: true

      - id: ty
        name: ty typecheck
        entry: uv run ty check
        language: system
        types: [python]
        pass_filenames: false     # ty discovers from pyproject config

      - id: interrogate
        name: interrogate docstring coverage
        entry: uv run interrogate -c pyproject.toml
        language: system
        types: [python]
        pass_filenames: false

      - id: pytest-unit
        name: pytest (unit only, fast)
        entry: uv run pytest tests/unit/ -x --ff
        language: system
        types: [python]
        pass_filenames: false
        stages: [pre-commit]
```

**Why `repo: local` with `uv run`:**

- Guarantees the hook uses the same dependency versions as
  `make check` — no "version drift between pre-commit and the rest of
  the toolchain" footgun.
- `ty` doesn't have an official `pre-commit` repo hook yet (beta);
  `local` is the only option.
- Tools that scan the project by themselves (`ty`, `interrogate`,
  `pytest`) need `pass_filenames: false` — otherwise pre-commit
  appends the staged file list and overrides the tool's own scanning.

**Why pytest runs `tests/unit/` only in the hook (D-14):** Phase 1
has no unit tests yet, so this hook is a no-op in Phase 1. It comes
alive in Phase 2 when domain tests land. Keeping it configured from
Phase 1 avoids the pre-commit re-config churn later.

**Source:** pydevtools.com how-to + docs.astral.sh/uv/guides/
integration/pre-commit/.

### Pattern: GitHub Actions CI (addresses D-19, OPS-03)

**Drop-in `.github/workflows/ci.yml`:**

```yaml
# ABOUTME: CI — runs make check on push and PR against Python 3.12.
# ABOUTME: Single job, uv-cached, cancels stale PR runs.

name: ci

on:
  push:
    branches: [main]
  pull_request:

concurrency:
  group: ci-${{ github.workflow }}-${{ github.head_ref || github.run_id }}
  cancel-in-progress: true

jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v5

      - name: Set up uv
        uses: astral-sh/setup-uv@v8
        with:
          enable-cache: true
          python-version: "3.12"
          # setup-uv@v8 caches on **/uv.lock by default.

      - name: make install
        run: make install

      - name: make check
        run: make check
```

**Notes:**

- `astral-sh/setup-uv@v8` is current (v8.1.0 at 2026-04-16) and
  already caches on `uv.lock`. No manual `actions/cache` step needed.
- The `python-version: "3.12"` input to `setup-uv` installs Python
  through uv (faster than `actions/setup-python`).
- `concurrency.group` uses `github.head_ref || github.run_id`: on
  PRs, the head ref is stable across pushes so new commits cancel
  stale runs; on pushes to main the run_id fallback prevents
  unrelated main pushes from cancelling each other.
- `cancel-in-progress: true` per D-19.
- No Playwright step (D-19).

**Source:** docs.astral.sh/uv/guides/integration/github/ +
GitHub Actions concurrency docs.

### Pattern: the first integration test (addresses SC #4, D-07)

**Drop-in `tests/integration/test_db_smoke.py`:**

```python
# ABOUTME: SC #4 canary — proves async session + real migrations work.
# ABOUTME: Must pass 10x in a row via `pytest --count=10` without flakes.

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_async_session_executes_trivial_query(
    session: AsyncSession,
) -> None:
    """Open a session, SELECT 1, close cleanly.

    Proves:
    - pytest-asyncio loop is alive for this test.
    - Alembic migrations applied (alembic_version table exists).
    - Session rollback on teardown leaves the DB clean.
    """
    result = await session.execute(text("SELECT 1"))
    value = result.scalar_one()
    assert value == 1
```

**SC #4 verification command:**

```bash
uv run pytest tests/integration/test_db_smoke.py --count=10 -q
```

If any of the 10 runs fails with `RuntimeError: Event loop is
closed` or similar, the fixture architecture is wrong. Iterate on
`conftest.py` until 10/10 pass.

**Alternative to `pytest-repeat`:** a shell loop
(`for i in $(seq 10); do pytest ... || break; done`) works too, but
the dev dep is simpler and survives into Phase 2 where the unit suite
will also benefit from `--count=N` on individual tests.

### Pattern: `.gitignore` essentials

**Drop-in `.gitignore`** (minimum viable, add more as needed):

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/

# uv
.uv/
uv-cache/

# Test / build
.pytest_cache/
.coverage
htmlcov/
dist/
build/

# Secrets — NEVER commit these (LLM-03)
.env

# Local DB (created by alembic upgrade head)
dojo.db
dojo.db-journal
dojo.db-wal
dojo.db-shm

# IDE
.idea/
.vscode/
```

### Anti-Patterns to Avoid

- **Hardcoding `DATABASE_URL` in `session.py` or `alembic.ini`.**
  D-01 mandates single source of truth via pydantic-settings.
- **Skipping `alembic init -t async` and manually editing sync env.py.**
  The async template isn't a "fancy option" — it's the only template
  that runs against aiosqlite (C4, FLAG 3).
- **Using `:memory:` SQLite for tests.** Per-connection in aiosqlite;
  breaks session-scoped engine (D-06).
- **Using `Base.metadata.create_all` in tests instead of real Alembic.**
  Bypasses the migration pipeline, hides C4 drift.
- **Setting `expire_on_commit=True` on the async sessionmaker.** C3 —
  re-expired objects blow up on attribute access post-commit.
- **Importing `anthropic` or `httpx` in Phase 1 `settings.py` or
  `main.py`.** Absolute-minimum scaffold (D-11); those arrive in
  Phase 3.
- **Creating empty `__init__.py` shells for `app/domain/`,
  `app/application/`, etc.** D-11 — Phase 2+ creates the layer
  directories when they have real contents.
- **Stacking `tenacity` over Anthropic SDK default retries.** PITFALL
  C7. Phase 1 has no Anthropic code yet, but when Phase 3 adds it,
  the SDK's `max_retries=2` default will need to be explicitly
  overridden to `0`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async-test event-loop management | Custom `asyncio.new_event_loop()` + `run_until_complete()` in conftest | pytest-asyncio 1.x + `asyncio_default_fixture_loop_scope = "session"` | The canonical fixture shape has moved across 5 versions; rolling your own re-invents every bug the plugin already fixed (M8) |
| `.env` parsing | `os.getenv()` scattered across modules | pydantic-settings `BaseSettings` | Type coercion, `SecretStr`, precedence rules, layer isolation — all free |
| Async migration env.py | Hand-patching the sync Alembic template | `alembic init -t async migrations` + tweaks above | C4; hand-patches get the `run_sync(do_run_migrations)` trampoline subtly wrong |
| Structured logging | `logging.Formatter` with JSON strings | structlog `configure_once()` + `ConsoleRenderer` / `JSONRenderer` | Context vars, stdlib interop, per-env rendering — all free |
| uv dependency caching in CI | `actions/cache` with hand-rolled keys | `astral-sh/setup-uv@v8` with `enable-cache: true` | Maintains the cache key on `uv.lock` automatically |
| "Kill stale PR workflow runs" | Custom workflow that polls and cancels | `concurrency: group + cancel-in-progress: true` | One-block GitHub-native solution |
| Python version pinning in CI | `actions/setup-python` + manual version | `astral-sh/setup-uv@v8` with `python-version: "3.12"` | Faster, one fewer action, same version uv resolved locally |

**Key insight:** every "rolled-your-own" option in this table is a
known source of footguns in this exact domain. The scaffold's job is
to set up once, correctly, and move on.

## Common Pitfalls

These are the new/refined pitfalls surfaced by live verification.
**PITFALLS.md already documents C4, C9, M8–M12** with Phase 1 as the
entry gate; those are not restated here.

### New Pitfall 1: pytest-asyncio 1.0+ removed `event_loop` fixture

**What goes wrong:** A developer copies a 2024-era conftest snippet
that defines `@pytest.fixture def event_loop()`. Under pytest-asyncio
≥ 1.0 this is silently ignored (deprecation became removal), and the
session fixture scope doesn't apply — tests flake on event-loop-closed
errors.

**Why it happens:** The canonical pattern has moved; older tutorials
are actively wrong, not just outdated.

**How to avoid:** Use `event_loop_policy` fixture (scope=session) +
`asyncio_default_fixture_loop_scope = "session"` in pyproject.toml.
Both in the conftest drop-in above.

**Warning signs:** pytest warning about unknown `event_loop` fixture;
`RuntimeError: Event loop is closed` on the second test in a session.

**Source:** thinhdanggroup.github.io/pytest-asyncio-v1-migrate/;
pytest-asyncio 1.0 changelog.

**Severity:** High for Phase 1 since SC #4 is explicit about
flake-free 10x runs.

[CITED: pytest-asyncio.readthedocs.io/en/stable/reference/fixtures/]

### New Pitfall 2: Anthropic SDK default retries = 2 (not 0, not 3)

**What goes wrong:** Phase 3 adds the Anthropic adapter and wraps it
in `tenacity(stop_after_attempt=3)`, expecting 3 total attempts. The
SDK's default `max_retries=2` stacks: 3 × (2 + 1) = 9 real HTTP calls
per logical request.

**Why it happens:** The SDK's retry is silent and default. STACK.md
assumed 3; the real default is 2.

**How to avoid:** Phase 3 must pass `max_retries=0` to the
`Anthropic()` client constructor when wiring it in the composition
root. `client = Anthropic(api_key=..., max_retries=0)`. Phase 1 can
pre-emptively reserve a config knob in `Settings` if the planner
wants — but it is optional and not part of Phase 1's requirements.

**Warning signs:** Phase 3 integration tests see "retry attempt 7 of
9" in logs when spec says 3.

**Source:** anthropic-sdk-python README; confirms
`max_retries` defaults to `2`, not `3`.

**Severity:** Medium for Phase 1 (no Anthropic code yet). High for
Phase 3. Flagging now so CONTEXT.md for Phase 3 can inherit it.

[CITED: github.com/anthropics/anthropic-sdk-python/blob/main/README.md]

### New Pitfall 3: `ty` beta version churn

**What goes wrong:** `ty` is still 0.0.x beta (current 0.0.31,
released 2026-04-15). Astral has publicly said pre-1.0 releases may
change error output and config schema. A CI bump can go red on
unchanged code.

**Why it happens:** Beta means pre-1.0 API contract.

**How to avoid:** Exact-pin ty in `pyproject.toml` (`ty==0.0.31`)
per D-16. Bumping is a deliberate action, not `uv sync`-driven.
Document this in CLAUDE.md so any future session respects the pin.

**Warning signs:** ty release notes mention "breaking change to error
format" or "strictness default changed." CI fails on the same code
that passed yesterday.

**Fallback:** mypy is documented as a fallback in CLAUDE.md; if ty
blocks progress on a specific Phase-2 construct, swap. Do not
pre-install mypy (D-16).

**Severity:** Moderate. Watchable.

[VERIFIED: pypi.org/project/ty/ 2026-04-20]

### New Pitfall 4: pydantic-settings + `SecretStr` double-edge

**What goes wrong:** `SecretStr` makes `repr()` safe, but a developer
hits "hm, let me just log the key to debug" and writes
`log.info("key", key=settings.anthropic_api_key.get_secret_value())`.
The SecretStr protection is bypassed and the key ends up in log
aggregation.

**Why it happens:** `SecretStr` is a hint, not a wall. The wall is
code review + logging discipline.

**How to avoid:**
- Keep a project-wide convention: never call `.get_secret_value()`
  outside the Anthropic SDK boundary (Phase 3's
  `anthropic_provider.py`).
- structlog's `add_log_level` processor can't see inside a SecretStr,
  so passing `settings.anthropic_api_key` (not the unwrapped value)
  to a log call renders as `****` — safe.
- Add a ruff lint rule or a simple grep test: no call to
  `.get_secret_value()` outside `app/infrastructure/llm/`. Phase 1
  doesn't have that directory yet; flag for Phase 3.

**Severity:** Low for Phase 1 (no LLM code yet). Worth noting now so
the discipline starts at scaffold time.

### New Pitfall 5: `asyncio.run()` inside Alembic env.py vs pytest loop

**What goes wrong:** The async Alembic env.py calls
`asyncio.run(run_async_migrations())` at module top level. If the
test fixture imports the env.py module while pytest-asyncio already
has a loop running, `asyncio.run()` raises
`RuntimeError: asyncio.run() cannot be called from a running event loop`.

**Why it happens:** The canonical async env.py is designed for
standalone CLI invocation (`alembic upgrade head` as a subprocess),
not for import from inside a running event loop.

**How to avoid:** Do NOT import `migrations.env` from test code. Use
`alembic.command.upgrade` (the Python API) wrapped in
`asyncio.to_thread(...)` in the test fixture — which is what the
conftest drop-in above does. `command.upgrade` spawns a subprocess
internally, keeping its event-loop bubble separate.

**Warning signs:** Test fixture wired for "just import env.py and
call run_async_migrations" — refactor it.

**Severity:** Low, but subtle. The conftest drop-in above is correct.

### New Pitfall 6: `[tool.uv] package = true` without `[build-system]`

**What goes wrong:** Setting `package = true` without a matching
`[build-system]` table produces an opaque `uv sync` error about
missing build backend. D-20 mentions the package flag but not the
build-system requirement.

**Why it happens:** uv's package mode needs a PEP 517 backend to
actually build the wheel it installs.

**How to avoid:** Always pair `[tool.uv] package = true` with a
`[build-system] requires = [...] build-backend = "..."` table. The
pyproject drop-in above uses hatchling; setuptools works too.

**Severity:** Low — one `uv sync` attempt will surface the error
clearly if it's wrong.

[VERIFIED: docs.astral.sh/uv/concepts/projects/config/]

## Code Examples

All drop-in snippets already live inside "Architecture Patterns"
above. The full set:

- `app/infrastructure/db/session.py` — dialect-guarded engine/session
- `tests/conftest.py` — async fixtures, tmp-file SQLite, Alembic run
- `migrations/env.py` — async Alembic with pydantic-settings
- `migrations/versions/0001_initial.py` — empty revision
- `app/settings.py` — pydantic-settings with SecretStr
- `.env.example` — field-by-field template
- `app/logging_config.py` — structlog `configure_once`
- `app/main.py` — FastAPI composition root with lifespan
- `app/web/routes/home.py` — `/` + `/health`
- `app/web/templates/base.html` + `home.html`
- `tests/integration/test_db_smoke.py` — SC #4 canary
- `pyproject.toml` — full skeleton with ruff/ty/pytest/interrogate
- `Makefile` — 9 targets per spec §8.1
- `.pre-commit-config.yaml` — 5-hook local config
- `.github/workflows/ci.yml` — single-job CI
- `.gitignore` — essentials

## State of the Art

| Old Approach (as of STACK.md 2026-04-18) | Current Approach (verified 2026-04-20) | Why Changed | Impact |
|--------------|------------------|--------------|--------|
| pytest-asyncio 0.24 with deprecated `event_loop` fixture | pytest-asyncio ≥ 1.0 (current 1.3.0) + `asyncio_default_fixture_loop_scope = "session"` | 1.0 removed `event_loop` fixture | Drop-in conftest uses both new config option and `event_loop_policy` fixture |
| Manual `actions/cache` for uv in CI | `astral-sh/setup-uv@v8` with `enable-cache: true` | v8 bakes in uv.lock-keyed caching | One fewer step in ci.yml |
| Anthropic SDK `max_retries` assumed to be 3 | Default is **2**; override to 0 with `Anthropic(max_retries=0)` | Verified against 0.96 SDK source | Phase 3 must explicitly disable SDK retries to avoid stacking with tenacity (C7) |
| `instructor` as "consider for tool-use parsing" | Stick with raw tool-use + Pydantic DTO | Phase 3 decision; Phase 1 doesn't choose | No Phase 1 impact |

**Nothing deprecated for Phase 1** — all the libraries Phase 1 uses
are in their current-stable majors.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `pytest-cov>=5.0` is still current; no major 6.x break | Standard Stack | Low. `--cov` flag is stable API; bump floor if uv resolves higher |
| A2 | `interrogate>=1.7` still supports the 2026 Python AST | Standard Stack | Low. interrogate is low-churn; any breakage would be immediate on `make docstrings` |
| A3 | `uv>=0.4` still supports `[tool.uv] package = true` | Pattern: pyproject.toml | Verified against docs.astral.sh; risk low |
| A4 | Hatchling is an acceptable PEP 517 backend for the app | Pattern: pyproject.toml | Low. Setuptools is a drop-in if hatchling disagrees with anything |
| A5 | `filterwarnings = ["error"]` won't explode on pytest's own deprecation warnings in pytest 8.3 | Pattern: pyproject.toml | Low-to-medium. If pytest emits a self-warning, add `ignore::DeprecationWarning:pytest` and move on |
| A6 | `ty check app migrations` will not error on the Alembic env.py under ty 0.0.31 | Pattern: Makefile | Medium. ty may not handle alembic's dynamic `context.configure(...)` gracefully; fallback is `ty check app` only (exclude migrations/) |
| A7 | The spec's `SecretStr` for `ANTHROPIC_API_KEY` works even when the field has no default (Phase 1 can run without the key set) | Pattern: settings | Medium. If pydantic-settings requires the key at instantiation and `make run` tries to instantiate without a real key, boot fails. Mitigation: `.env.example` documents the requirement; CI provides a dummy `ANTHROPIC_API_KEY=ci-placeholder` env var. **Planner should add a CI env var for the placeholder key.** |

**Items A5, A6, A7 need user confirmation at plan-discuss time** (or
acceptance that the planner will resolve them empirically during
execution — `uv sync && make check` is the cheap oracle).

## Open Questions (RESOLVED)

1. **Should `Settings.anthropic_api_key` have a placeholder default
   for Phase 1 so `make run` works without a real key?**
   - What we know: LLM-03 requires the key to load from `.env`; D-11
     says absolute-minimum scaffold (home page doesn't call
     Anthropic).
   - What's unclear: If `SecretStr` is required-without-default,
     `make run` fails on a fresh clone with no `.env` — dev-loop
     hostile.
   - Recommendation: **Make `anthropic_api_key: SecretStr = SecretStr("dev-placeholder")`**
     for Phase 1, with a `.env.example` comment "replace this for
     Phase 3 onward." Phase 3's Anthropic provider can validate on
     first use (not at settings construction).
   - Alternative: keep it required; CI and local dev both need a
     real-or-dummy `.env`. Slightly more friction, slightly more
     honest about the required config surface.
   - **Flag for planner / discuss-phase review.**
   - RESOLVED: `anthropic_api_key: SecretStr = SecretStr("dev-placeholder")` lands in Plan 02 Task 1 (app/settings.py). `.env.example` in Plan 01 Task 2 carries the "replace this for Phase 3 onward" comment.

2. **Is `pytest-repeat` the right tool for SC #4's 10x check, or
   should we prefer a `make test-flakes` target with a shell loop?**
   - What we know: D-07 allows either; Claude's Discretion lists
     this as a planner choice.
   - What's unclear: Whether pytest-repeat's addition to dev deps is
     worth the dep count, given only one test needs it.
   - Recommendation: **Use `pytest-repeat`.** It's a 1-file plugin
     with zero production impact and the `--count=N` syntax is
     self-documenting. The Makefile can expose it as
     `make test-flakes` that runs
     `uv run pytest tests/integration/test_db_smoke.py --count=10`.
   - RESOLVED: `pytest-repeat>=0.9.4` added to `[dependency-groups].dev` in Plan 01 Task 1 (pyproject.toml). The `test-flakes` Makefile target lands in Plan 06 Task 1 and runs `uv run pytest tests/integration/test_db_smoke.py --count=10`.

3. **Does `ty check migrations/` cleanly handle Alembic's dynamic
   import pattern?**
   - What we know: `migrations/env.py` does
     `config.set_main_option(...)` and `context.configure(...)`
     which are runtime-dynamic.
   - What's unclear: Whether ty 0.0.31 has type stubs or a happy
     path for this.
   - Recommendation: **Plan for the Makefile `typecheck` target to
     initially scope to `ty check app` only** (exclude
     `migrations/`). If ty handles `migrations/` cleanly, broaden
     later. Open a follow-up task in Phase 2 to revisit.
   - RESOLVED: Plan 06 Task 1 scopes the Makefile `typecheck` target to `uv run ty check app` only (NOT `ty check app migrations`). Phase 2 may revisit broadening to migrations/ once ty matures.

## Environment Availability

Phase 1 depends only on what `uv` can install. No system services,
no OS daemons.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Project | (resolved by uv at install time) | 3.12.x | uv installs if absent |
| uv | Package management | ? (check at plan time) | ≥ 0.4 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| SQLite | App runtime (aiosqlite driver wraps system sqlite) | (OS-provided on macOS + Linux) | ≥ 3.40 | macOS/Linux default; Windows users install separately |
| git | Pre-commit | ✓ (required; repo already initialized) | — | — |
| GNU make | Makefile targets | (OS-provided) | — | macOS/Linux default |

**No blocking missing dependencies.** The scaffold is designed to
boot on any Mac/Linux dev machine with git + make + a network
connection (for uv-resolved wheels).

**Planner note:** the first task should probably be `uv --version ||
curl ... | sh` to self-install uv if missing. Low cost, high
friendliness.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio 1.0+ |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest -x --ff` |
| Full suite command | `make check` (runs pytest + coverage + lint + type + docstrings) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OPS-01 | `make install && make check` exits zero | integration-via-make | `make install && make check` | ❌ Wave 0 |
| OPS-01 | All 9 Makefile targets exist and invoke correct tools | shell-smoke | `make -n install format lint typecheck docstrings test check run migrate && make --targets 2>&1 \| grep -c '^'` | ❌ Wave 0 |
| OPS-02 | `pre-commit install` wired into `make install` | shell-grep | `grep -q 'pre-commit install' Makefile` | ❌ Wave 0 |
| OPS-02 | Violating commit is blocked | manual / integration | (commit a bad file, verify hook fails) — also exercised by `make check` | ❌ Wave 0 |
| OPS-03 | CI green on scaffold | external | GitHub Actions status check on PR | ❌ Wave 0 (CI file) |
| OPS-04 | structlog configured at startup | integration | `uv run pytest tests/integration/test_logging_smoke.py` (check that `get_logger("x").info("event")` doesn't raise and that output matches ConsoleRenderer shape) | ❌ Wave 0 |
| TEST-02 | ruff clean | unit | `uv run ruff check .` | ❌ Wave 0 (config) |
| TEST-02 | ty clean | unit | `uv run ty check app` | ❌ Wave 0 (config) |
| TEST-02 | interrogate 100% | unit | `uv run interrogate -c pyproject.toml app` | ❌ Wave 0 (config) |
| TEST-02 | pytest pristine output | integration | `uv run pytest` with `filterwarnings = ["error"]` | ❌ Wave 0 (pyproject + conftest) |
| LLM-03 | `ANTHROPIC_API_KEY` loads from `.env` | unit | `uv run pytest tests/unit/test_settings.py::test_loads_api_key_from_env` | ❌ Wave 0 |
| LLM-03 | `.env` is gitignored | shell-grep | `grep -qE '^\.env$' .gitignore` | ❌ Wave 0 |
| LLM-03 | `.env.example` checked in | shell-exists | `test -f .env.example` | ❌ Wave 0 |
| SC #2 | `make run` serves `/` and `/health` | integration | `uv run pytest tests/integration/test_home.py` (use `httpx.AsyncClient(transport=ASGITransport(app=app))`) | ❌ Wave 0 |
| SC #3 | `alembic upgrade head` creates `alembic_version` on fresh DB | integration | `rm -f /tmp/dojo.db && DATABASE_URL=sqlite+aiosqlite:////tmp/dojo.db uv run alembic upgrade head && sqlite3 /tmp/dojo.db '.schema' \| grep -q alembic_version` | ❌ Wave 0 (migration) |
| SC #4 | First integration test runs 10x without flakes | integration (repeat) | `uv run pytest tests/integration/test_db_smoke.py --count=10` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest -x --ff` (fast feedback; fails
  on first error, retries failed tests first on next run).
- **Per wave merge:** `uv run pytest` (full test run, still
  Phase-1-small).
- **Phase gate:** `make check` green + the SC-specific shell checks
  in the table above (`alembic upgrade head` against a fresh DB;
  `pytest --count=10` on the smoke test; visual inspection of CI
  badge).

### Wave 0 Gaps

- [ ] `pyproject.toml` — declares deps, configures ruff/ty/pytest/
      interrogate, sets `asyncio_mode = "auto"` + session fixture
      scope + `filterwarnings = ["error"]`
- [ ] `Makefile` — 9 targets per spec §8.1
- [ ] `.pre-commit-config.yaml` — 5 local hooks per D-14
- [ ] `.github/workflows/ci.yml` — single-job CI per D-19
- [ ] `.env.example` + `.gitignore` entry for `.env`
- [ ] `tests/conftest.py` — fixtures per D-04/05/06 drop-in
- [ ] `tests/unit/` directory (empty but present for D-14 hook)
- [ ] `tests/integration/test_db_smoke.py` — SC #4 canary
- [ ] `tests/integration/test_home.py` — SC #2 smoke (using
      `httpx.AsyncClient` + `ASGITransport`)
- [ ] `tests/integration/test_logging_smoke.py` — OPS-04 structlog
      boot test
- [ ] `tests/unit/test_settings.py` — LLM-03 settings-loads test
- [ ] `migrations/env.py` + `migrations/versions/0001_initial.py`
- [ ] Framework install: `uv sync` after pyproject lands

**Verifier boundary cases to check (prevent false-positive passes):**

1. **`make check` passing with an empty test suite is a false pass.**
   Require at least the `test_db_smoke` test to exist and be
   executed (check pytest's exit summary for "N passed" where N ≥ 1).
2. **`pytest --count=10` passing could hide a fixture that silently
   skips.** The smoke test must assert a non-trivial value
   (`assert value == 1`, not just run-to-completion).
3. **`alembic upgrade head` succeeding on a pre-existing DB doesn't
   prove the pipeline works.** Always `rm -f dojo.db` before the
   check.
4. **CI green on a forked PR may not exercise the cache.** The first
   push populates the cache; the second push exercises the hit. Don't
   take first-push green as full validation; second-push time should
   drop substantially.
5. **`ty` passing on empty code is trivial.** Include a single
   type-annotated function in `app/settings.py` (the `get_settings`
   return annotation) so ty has something to type-check.
6. **Pristine output could hide a muted warning.** Remove the
   third-party logger clamp in `conftest.py` temporarily and confirm
   real warnings surface; re-add after confirmation.
7. **Pre-commit passing could reflect an unchanged staging area.**
   Run `pre-commit run --all-files` (not just `pre-commit run`) to
   exercise hooks against every file, not just staged ones.

## Project Constraints (from CLAUDE.md)

CLAUDE.md directives the planner must honor in every Phase 1 task:

- **Every Python file starts with two `# ABOUTME:` lines** — every
  drop-in snippet above follows this.
- **Files ≤100 lines (split if >150)** — `app/main.py` drop-in is
  ~45 lines; `conftest.py` is ~75 lines; within limits. If a task
  generates a file >100 lines, split before commit.
- **`ruff` 79-char line length** — all snippets formatted to this.
- **Every public module/class/function/method has a sphinx-style
  docstring** (interrogate enforces at 100%).
- **`dataclasses` for containers; `Pydantic` only at validation
  boundaries** — `Settings` is a validation boundary (external env
  file); Pydantic is correct there.
- **`logging` with `log = logging.getLogger(__name__)` per module** —
  Dojo's `get_logger(__name__)` via structlog wraps stdlib logging
  (consistent with wiki + spec).
- **Custom exceptions live in a central `exceptions.py` per layer** —
  Phase 1 has no layers with exceptions yet (D-11); Phase 2+ will.
- **GSD workflow enforcement:** all file changes go through a GSD
  command — the planner's tasks are the mechanism.
- **TDD mandatory** — Phase 1 has a tricky edge: Wave 0 scaffold
  files (pyproject, Makefile, CI config) are not code-under-test.
  The first real TDD cycle is the `test_db_smoke.py` + conftest +
  session.py + migrations/env.py quartet. The planner should order
  tasks so the test is written first, fails (red), then the fixtures
  + session factory + env.py + initial migration land (green).
- **Protocol vs function rule:** Phase 1 has no ports yet (D-11);
  Phase 2 owns `app/application/ports.py`.

## Sources

### Primary (HIGH confidence — verified live 2026-04-20)

- PyPI `anthropic` project — `pypi.org/project/anthropic/` — current
  version 0.96.0, release date 2026-04-16
- PyPI `pytest-asyncio` — `pypi.org/project/pytest-asyncio/` — current
  1.3.0, 2025-11-10
- PyPI `ty` — `pypi.org/project/ty/` — current 0.0.31, 2026-04-15
- PyPI `pydantic-settings` — 2.14.0, 2026-04-20
- PyPI `pytest-repeat` — 0.9.4, 2025-04-07
- Alembic async env.py template —
  `github.com/sqlalchemy/alembic/blob/main/alembic/templates/async/env.py`
  (fetched live)
- Anthropic SDK README —
  `github.com/anthropics/anthropic-sdk-python/blob/main/README.md` —
  confirms `max_retries=2` default
- `docs.astral.sh/uv/concepts/projects/config/` — `package = true`
  canonical pattern
- `docs.astral.sh/uv/guides/integration/pre-commit/` — `uv-pre-commit`
  repo pattern
- `docs.astral.sh/uv/guides/integration/github/` — setup-uv v8 CI
  pattern
- `pytest-asyncio.readthedocs.io/en/stable/reference/fixtures/` —
  `event_loop_policy` fixture + `asyncio_default_fixture_loop_scope`
  config
- `github.com/astral-sh/setup-uv` — v8.1.0 and cache-on-uv.lock behaviour
- `github.com/Kludex/starlette/pull/3148` — autoescape-by-default
  verification for FLAG 10

### Secondary (MEDIUM confidence — verified against a primary source)

- pydevtools.com how-tos — pre-commit hook shape with local hooks
- SQLAlchemy 2.0 async docs —
  `docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html` — lazy=raise
  + AsyncAttrs discussion (informs Phase 3 repos; Phase 1 doesn't
  foreclose)
- thinhdanggroup.github.io/pytest-asyncio-v1-migrate/ — 1.0 migration
  guide

### Tertiary (LOW confidence — training data, flagged as assumption)

- Version floors for `pytest-cov` and `interrogate` (A1, A2 in
  Assumptions Log)

## Metadata

**Confidence breakdown:**

- Standard stack versions: HIGH — every version pinned was
  verified against PyPI 2026-04-20
- Architecture patterns (fixture shape, env.py shape, settings
  shape): HIGH — all drop-ins verified against current official docs
- Common pitfalls (new items 1-6): HIGH — each verified via a
  specific official source or changelog line
- Open Questions: MEDIUM — real uncertainties requiring user/planner
  decisions
- CLAUDE.md + wiki constraints: HIGH — read directly from source

**Research date:** 2026-04-20
**Valid until:** 2026-05-20 for stack versions (tooling ecosystem
moves fast — re-verify if planning slips beyond a month); indefinite
for structural patterns (fixture shape, PRAGMA listener, composition
root) which are stable across years.
