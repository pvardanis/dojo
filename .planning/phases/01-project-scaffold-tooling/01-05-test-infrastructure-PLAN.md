---
phase: 01-project-scaffold-tooling
plan: 05
type: execute
wave: 4
depends_on:
  - "01-03"
  - "01-04"
files_modified:
  - tests/__init__.py
  - tests/conftest.py
  - tests/unit/__init__.py
  - tests/unit/.gitkeep
  - tests/unit/conftest.py
  - tests/unit/test_settings.py
  - tests/integration/__init__.py
  - tests/integration/.gitkeep
  - tests/integration/test_db_smoke.py
  - tests/integration/test_alembic_smoke.py
  - tests/integration/test_home.py
  - tests/integration/test_logging_smoke.py
autonomous: true
requirements:
  - TEST-02
  - OPS-04
  - LLM-03
tags:
  - python
  - pytest
  - pytest-asyncio
  - alembic
  - sqlalchemy
  - httpx
  - integration-tests

must_haves:
  truths:
    - "`uv run pytest` on the Phase 1 suite exits zero with pristine
      output (no warnings promoted to errors by `filterwarnings =
      [\"error\"]`)"
    - "`uv run pytest tests/integration/test_db_smoke.py --count=10`
      passes 10/10 runs — proves the event-loop + tmp-file SQLite +
      Alembic fixture stack is flake-free (SC #4 gate)"
    - "`uv run pytest tests/integration/test_home.py` passes — proves
      `make run` will serve `/` + `/health` (SC #2 integration gate)"
    - "`uv run pytest tests/unit/test_settings.py` passes — proves
      `ANTHROPIC_API_KEY` round-trips from env → Settings via
      pydantic-settings (LLM-03 gate)"
    - "`uv run pytest tests/integration/test_logging_smoke.py` passes —
      proves `configure_logging` + `get_logger` work without raising
      (OPS-04 gate)"
    - "`uv run pytest tests/integration/test_alembic_smoke.py` passes
      — persists SC #3 (alembic_version table created on fresh tmp DB)
      as a standalone automated test inside `make check`"
  artifacts:
    - path: "tests/conftest.py"
      provides: "Shared async fixtures: event_loop_policy,
        test_db_url (tmp file), _clamp_third_party_loggers,
        _alembic_cfg, _migrated_engine, session (function-scoped)"
      contains: "asyncio.to_thread(command.upgrade"
    - path: "tests/unit/conftest.py"
      provides: "Unit-only overrides (log level clamp to WARNING)"
      contains: "WARNING"
    - path: "tests/integration/test_db_smoke.py"
      provides: "SC #4 canary — open async session, SELECT 1, close"
      contains: "session: AsyncSession"
    - path: "tests/integration/test_alembic_smoke.py"
      provides: "SC #3 persistent gate — alembic_version created"
      contains: "alembic_version"
    - path: "tests/integration/test_home.py"
      provides: "SC #2 integration: ASGI exercise of / and /health"
      contains: "ASGITransport"
    - path: "tests/integration/test_logging_smoke.py"
      provides: "OPS-04 gate: configure_logging + get_logger smoke"
      contains: "configure_logging"
    - path: "tests/unit/test_settings.py"
      provides: "LLM-03 gate: ANTHROPIC_API_KEY env → Settings"
      contains: "monkeypatch.setenv"
  key_links:
    - from: "tests/conftest.py"
      to: "alembic.command.upgrade"
      via: "asyncio.to_thread(command.upgrade, cfg, 'head')"
      pattern: "asyncio\\.to_thread"
    - from: "tests/conftest.py"
      to: "app.infrastructure.db.session (via DATABASE_URL)"
      via: "async_sessionmaker bound to _migrated_engine"
      pattern: "async_sessionmaker"
    - from: "tests/integration/test_home.py"
      to: "app.main.app"
      via: "httpx.AsyncClient(transport=ASGITransport(app=app))"
      pattern: "ASGITransport"
    - from: "tests/unit/test_settings.py"
      to: "app.settings.Settings"
      via: "monkeypatch.setenv + get_settings.cache_clear()"
      pattern: "cache_clear"
    - from: "tests/integration/test_alembic_smoke.py"
      to: "alembic.command.upgrade"
      via: "asyncio.to_thread(command.upgrade, cfg, 'head')"
      pattern: "alembic_version"
---

## TDD Exception (Phase 1 only)

**This plan does NOT follow strict red-green-refactor order.** CLAUDE.md
Rule #1 is unambiguous: "FOR EVERY NEW FEATURE OR BUGFIX, YOU MUST
follow Test Driven Development." Phase 1 is an approved, documented
exception — not a shortcut.

**Why this plan bootstraps the harness after the infrastructure:**

Phase 1 is scaffolding the test harness itself. The `conftest.py`
fixtures, the four smoke tests, and the integration test stack all
depend on these artifacts existing FIRST:

- `app/settings.py` (Plan 02) — `Settings`, `get_settings`
- `app/logging_config.py` (Plan 02) — `configure_logging`, `get_logger`
- `app/infrastructure/db/session.py` (Plan 03) — `Base`, `engine`,
  `AsyncSessionLocal`
- `migrations/env.py` (Plan 03) — `alembic.command.upgrade` target
- `migrations/versions/0001_initial.py` (Plan 03) — the revision the
  harness upgrades to
- `app/main.py` + `app/web/routes/home.py` (Plan 04) — the ASGI app
  the integration tests exercise

Strict TDD would require writing tests before each of those files
exists. But the tests themselves CANNOT be written until the fixtures
exist (they depend on `_migrated_engine`, which depends on `_alembic_cfg`,
which depends on `alembic.ini` existing, which depends on the Alembic
scaffold being generated). This is circular.

**Scope of the exception:**

- Applies ONLY to Phase 1 (scaffold + tooling).
- Plans 02, 03, 04 produce production infrastructure whose behavior is
  verified by the smoke tests written in THIS plan (05) after the fact.
- Waves 2 + 3 still run ruff + ty + interrogate + import smoke tests,
  which catch the obvious regressions. The full 4-test pytest suite
  lands in Wave 4 (this plan).

**Phases 2+ return to strict TDD.** Once the harness is in place, every
new domain entity, use case, adapter, route, and repository is built
red → green → refactor. Plan 05's `conftest.py` fixtures are exactly
the template Phase 2+ tests consume.

**Reference:** This exception was approved by Danny in the
`/gsd-plan-phase 1` discussion on 2026-04-20 (CLAUDE.md Rule #1:
"If you want exception to ANY rule, YOU MUST STOP and get explicit
permission from Danny first"). CONTEXT.md D-21 records the decision.

---

<objective>
Stand up the full test infrastructure: package markers, shared async
fixtures, and the Phase 1 test modules that close SC #2 (home +
health routes), SC #3 (Alembic version table persisted), SC #4 (first
integration test runs 10x flake-free), OPS-04 (structlog boot), and
LLM-03 (ANTHROPIC_API_KEY from `.env`).

Purpose: this is the Wave 0 + Wave 1 of the test pyramid — the fixtures
here are the template every Phase 2+ test will follow, and the Phase 1
tests are the canary for every fixture in conftest.

The first integration test (`test_db_smoke.py`) is explicitly the
"canary" per CONTEXT.md §Specifics — it proves pytest-asyncio 1.x +
tmp-file SQLite + real Alembic + session rollback + structlog
pristine-output all work together.

Output: `make test` (= `uv run pytest`) exits zero with N ≥ 5 tests
passing (satisfies RESEARCH.md verifier note 1 — "make check passing
with an empty test suite is a false pass"). `uv run pytest
tests/integration/test_db_smoke.py --count=10` exits zero.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/01-project-scaffold-tooling/01-CONTEXT.md
@.planning/phases/01-project-scaffold-tooling/01-RESEARCH.md
@.planning/phases/01-project-scaffold-tooling/01-PATTERNS.md
@.planning/phases/01-project-scaffold-tooling/01-VALIDATION.md
@.planning/phases/01-project-scaffold-tooling/01-03-SUMMARY.md
@.planning/phases/01-project-scaffold-tooling/01-04-SUMMARY.md
@.planning/research/PITFALLS.md
@app/settings.py
@app/logging_config.py
@app/main.py
@app/infrastructure/db/session.py
@migrations/env.py
@pyproject.toml
@alembic.ini

<interfaces>
<!-- Fixtures this plan produces for use by Phase 2+ tests. -->

From `tests/conftest.py`:
```python
# session-scoped
@pytest.fixture(scope="session")
def event_loop_policy() -> asyncio.DefaultEventLoopPolicy: ...

@pytest.fixture(scope="session")
def test_db_url(tmp_path_factory) -> str: ...  # "sqlite+aiosqlite:///<tmp>"

@pytest.fixture(scope="session", autouse=True)
def _clamp_third_party_loggers() -> None: ...  # sets noisy libs WARNING

@pytest.fixture(scope="session")
def _alembic_cfg(test_db_url) -> AlembicConfig: ...

@pytest_asyncio.fixture(scope="session")
async def _migrated_engine(test_db_url, _alembic_cfg) -> AsyncEngine:
    # Runs `alembic upgrade head` via asyncio.to_thread once per session
    ...

# function-scoped
@pytest_asyncio.fixture
async def session(_migrated_engine) -> AsyncSession:
    # outer-transaction pattern: begin, yield, rollback
    ...
```

**Consumers** (downstream phases):
- Phase 2+ integration tests use `session` fixture for DB work.
- Phase 2+ unit tests under `tests/unit/` inherit
  `_clamp_third_party_loggers` autouse behaviour via the shared
  conftest.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create tests/ package tree + conftest.py (shared fixtures)</name>
  <files>tests/__init__.py, tests/conftest.py, tests/unit/__init__.py, tests/unit/.gitkeep, tests/unit/conftest.py, tests/integration/__init__.py, tests/integration/.gitkeep</files>
  <read_first>
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      411-516 (verbatim drop-in for conftest.py)
    - .planning/phases/01-project-scaffold-tooling/01-CONTEXT.md
      decisions D-04 (asyncio_mode auto), D-05 (event_loop_policy),
      D-06 (fixture architecture), D-07 (pytest-repeat), D-17 (log
      clamp), D-21 (TDD Exception — Phase 1 only)
    - .planning/phases/01-project-scaffold-tooling/01-PATTERNS.md lines
      339-363 (key structural elements)
    - .planning/research/PITFALLS.md M8 (pytest-asyncio footguns),
      New Pitfall 1 (event_loop fixture removed), New Pitfall 5
      (asyncio.run + pytest loop)
    - pyproject.toml (confirm `asyncio_mode = "auto"` and
      `asyncio_default_fixture_loop_scope = "session"` are set)
  </read_first>
  <action>
    Create the test directory tree with package markers:
    - `tests/` + `tests/__init__.py` (two ABOUTME lines + docstring
      `"""Dojo test suite."""`).
    - `tests/unit/` + `tests/unit/__init__.py` + `tests/unit/.gitkeep`.
    - `tests/integration/` + `tests/integration/__init__.py` +
      `tests/integration/.gitkeep`.

    The `.gitkeep` files are for directory-presence only (PATTERNS.md
    line 75 — the D-14 pre-commit hook runs `pytest tests/unit/`, so
    the dir must exist even when empty; same pattern mirrored for
    `tests/integration/`). Leave `.gitkeep` files empty.

    Write `tests/conftest.py` — paste drop-in from 01-RESEARCH.md lines
    411-516 verbatim. Key structural preservations (PATTERNS.md):

    1. Two-line `# ABOUTME:` header.
    2. Module docstring: `"""Shared async fixtures for the Dojo test
       suite."""`.
    3. `from __future__ import annotations`.
    4. Imports: `asyncio`, `logging`, `os` (may be unused; keep if
       drop-in has it), `AsyncIterator` from `collections.abc`, `Path`,
       `pytest`, `pytest_asyncio`, `alembic.command`, `alembic.config.
       Config as AlembicConfig`, SQLAlchemy async
       (`AsyncSession`, `async_sessionmaker`, `create_async_engine`).
    5. `event_loop_policy` fixture (scope=session) — returns
       `asyncio.DefaultEventLoopPolicy()`. Resolves New Pitfall 1
       (event_loop fixture removed in pytest-asyncio 1.0+).
    6. `test_db_url(tmp_path_factory)` fixture (scope=session) —
       builds a tmp file path and returns
       `f"sqlite+aiosqlite:///{path}"`. Per D-06, NOT `:memory:`.
    7. `_clamp_third_party_loggers` fixture (scope=session,
       autouse=True) — sets WARNING level on `trafilatura`, `httpx`,
       `anthropic`, `sqlalchemy.engine`, `alembic`. D-17 + m8 — ensures
       pristine test output (TEST-02).
    8. `_alembic_cfg(test_db_url)` fixture (scope=session) — builds
       `AlembicConfig("alembic.ini")` and overrides `sqlalchemy.url`
       to the tmp DB URL.
    9. `_migrated_engine(test_db_url, _alembic_cfg)` fixture
       (pytest_asyncio.fixture, scope=session) — runs
       `await asyncio.to_thread(command.upgrade, _alembic_cfg,
       "head")` (per New Pitfall 5 — this wraps Alembic's sync CLI in a
       thread to keep its event-loop bubble separate from pytest's
       loop). Then yields a fresh `create_async_engine(test_db_url)`;
       disposes on teardown.
    10. `session(_migrated_engine)` fixture (pytest_asyncio.fixture,
        function-scoped) — uses `async_sessionmaker(_migrated_engine,
        expire_on_commit=False, class_=AsyncSession)`. Opens a session
        inside `async with sess.begin():`, yields, rolls back on
        teardown. Outer-transaction rollback pattern (D-06).

    **Critical: conftest MUST NOT import `migrations.env`** — per New
    Pitfall 5, env.py's `asyncio.run()` clashes with pytest's running
    loop. Always use `alembic.command.upgrade` via `asyncio.to_thread`.

    Write `tests/unit/conftest.py` — unit-only overrides per
    VALIDATION.md Wave 0 requirement. Content:
    ```python
    # ABOUTME: Unit-test-only fixtures.
    # ABOUTME: Clamp Dojo's own loggers to WARNING for pristine output.
    """Unit-test-only fixture overrides."""

    from __future__ import annotations

    import logging

    import pytest


    @pytest.fixture(scope="session", autouse=True)
    def _clamp_dojo_loggers() -> None:
        """Set Dojo's own loggers to WARNING during unit tests.

        Unit tests should not produce any log output unless the test
        itself is asserting on a log line. Session-scoped clamp runs
        once per pytest process.
        """
        for name in ("dojo", "app"):
            logging.getLogger(name).setLevel(logging.WARNING)
    ```

    Verify each file:
    - `wc -l tests/conftest.py` ≤ 100 (drop-in is ~75 lines).
    - All `__init__.py` files have 2 ABOUTME lines + module docstring.
    - `uv run ruff format --check tests/` passes.
    - `uv run ruff check tests/` passes.
    - Interrogate does NOT scan tests/ (pyproject has `exclude =
      ["migrations", "tests", "docs"]`) — do NOT add docstrings under
      a mistaken belief they're required for interrogate. They ARE
      required by the project's wiki convention (every public
      function/class has a docstring) — so add them to fixtures
      anyway, but interrogate itself is a no-op here.
    - Collection smoke: `uv run pytest --collect-only -q` returns a
      clean listing (zero tests is OK at this point — tests come in
      later tasks).
  </action>
  <verify>
    <automated>test -f tests/__init__.py &amp;&amp; test -f tests/conftest.py &amp;&amp; test -f tests/unit/__init__.py &amp;&amp; test -f tests/unit/conftest.py &amp;&amp; test -f tests/unit/.gitkeep &amp;&amp; test -f tests/integration/__init__.py &amp;&amp; test -f tests/integration/.gitkeep &amp;&amp; test $(wc -l &lt; tests/conftest.py) -le 100 &amp;&amp; grep -c '^# ABOUTME:' tests/conftest.py | grep -q '^2$' &amp;&amp; grep -q 'def event_loop_policy' tests/conftest.py &amp;&amp; grep -q 'def test_db_url' tests/conftest.py &amp;&amp; grep -q '_clamp_third_party_loggers' tests/conftest.py &amp;&amp; grep -q 'asyncio.to_thread(command.upgrade' tests/conftest.py &amp;&amp; grep -q 'expire_on_commit=False' tests/conftest.py &amp;&amp; grep -q 'async with sess.begin()' tests/conftest.py &amp;&amp; ! grep -q 'migrations.env' tests/conftest.py &amp;&amp; uv run ruff format --check tests/ &amp;&amp; uv run ruff check tests/ &amp;&amp; uv run pytest --collect-only -q</automated>
  </verify>
  <done>
    All 7 files exist with ABOUTME headers; conftest.py has all six
    required fixtures; does NOT import `migrations.env`; uses
    `asyncio.to_thread` wrapper for Alembic; `pytest --collect-only`
    runs without errors.
  </done>
</task>

<task type="auto">
  <name>Task 2: Write the 5 Phase 1 tests (db_smoke + alembic_smoke + home + logging_smoke + settings)</name>
  <files>tests/integration/test_db_smoke.py, tests/integration/test_alembic_smoke.py, tests/integration/test_home.py, tests/integration/test_logging_smoke.py, tests/unit/test_settings.py</files>
  <read_first>
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      1210-1235 (test_db_smoke.py drop-in)
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      1604-1680 (Validation Architecture — Req-to-test map)
    - .planning/phases/01-project-scaffold-tooling/01-PATTERNS.md lines
      365-434 (per-file principle-derived guidance for
      test_home, test_logging_smoke, test_settings)
    - .planning/phases/01-project-scaffold-tooling/01-VALIDATION.md
      (per-task verification map)
    - app/main.py (for test_home)
    - app/settings.py (for test_settings)
    - app/logging_config.py (for test_logging_smoke)
    - alembic.ini + migrations/env.py (for test_alembic_smoke)
  </read_first>
  <action>
    Write the five Phase 1 tests. Each file MUST start with two
    `# ABOUTME:` lines and a module docstring. All async tests rely on
    pyproject's `asyncio_mode = "auto"` (D-04).

    ---

    **File 1: `tests/integration/test_db_smoke.py`** — paste drop-in
    from 01-RESEARCH.md lines 1210-1235 verbatim. This is the SC #4
    canary. Key shape:
    ```python
    # ABOUTME: SC #4 canary — async session + real Alembic migrations.
    # ABOUTME: Must pass 10x in a row via `pytest --count=10`.
    """First integration test — proves the fixture stack end-to-end."""

    from __future__ import annotations

    import pytest
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession


    @pytest.mark.asyncio
    async def test_async_session_executes_trivial_query(
        session: AsyncSession,
    ) -> None:
        """Open a session, SELECT 1, close cleanly."""
        result = await session.execute(text("SELECT 1"))
        value = result.scalar_one()
        assert value == 1
    ```
    Note RESEARCH.md verifier note 2: `assert value == 1` is
    deliberately non-trivial — a silent fixture skip would make a bare
    "run to completion" test false-pass. Keep the assertion.

    ---

    **File 2: `tests/integration/test_alembic_smoke.py`** — persists
    SC #3 as a standalone test so `make check` enforces it for the life
    of the repo (I1 resolution). Uses a tmp DB independent of
    conftest's `_migrated_engine` to prove the migration pipeline fresh
    every run. Shape:
    ```python
    # ABOUTME: SC #3 gate — alembic upgrade head creates alembic_version.
    # ABOUTME: Persists the migration-pipeline smoke inside make check.
    """Alembic migration pipeline smoke test."""

    from __future__ import annotations

    import asyncio
    from pathlib import Path

    import pytest
    from alembic import command
    from alembic.config import Config as AlembicConfig
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine


    @pytest.mark.asyncio
    async def test_alembic_upgrade_creates_version_table(
        tmp_path: Path,
    ) -> None:
        """`alembic upgrade head` creates `alembic_version` on fresh DB.

        Uses a tmp-file sqlite DB independent of the session fixture
        stack so the test exercises the entire Alembic pipeline from
        cold: new URL -> set_main_option -> run_async_migrations.
        """
        db_path = tmp_path / "dojo.alembic_smoke.db"
        db_url = f"sqlite+aiosqlite:///{db_path}"

        cfg = AlembicConfig("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", db_url)

        # Wrap the sync Alembic CLI in a thread to avoid clashing
        # with pytest-asyncio's running loop (New Pitfall 5).
        await asyncio.to_thread(command.upgrade, cfg, "head")

        # Inspect the resulting DB for alembic_version.
        engine = create_async_engine(db_url)
        try:
            async with engine.connect() as conn:
                result = await conn.execute(
                    text(
                        "SELECT name FROM sqlite_master "
                        "WHERE type='table'"
                    )
                )
                tables = {row[0] for row in result}
        finally:
            await engine.dispose()

        assert "alembic_version" in tables, tables
    ```

    This test does NOT depend on the `session` fixture — it proves the
    migration pipeline stands up from cold. The conftest's
    `_migrated_engine` is an optimization (migrate once per session);
    this test is the correctness gate (migrate from scratch, observe
    tracking table). Keep them both.

    ---

    **File 3: `tests/integration/test_home.py`** — principle-derived
    per PATTERNS.md. Tests GET `/` and GET `/health` via
    `httpx.AsyncClient(transport=ASGITransport(app=app))`. Shape:
    ```python
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
        """GET / returns 200 with Dojo-titled HTML."""
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Dojo" in response.text


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
    ```

    Note on `httpx`: `httpx` is a transitive dep of `fastapi`'s
    `TestClient`, but FastAPI depends on `httpx` only when `starlette`
    requests it. Confirm it is available via `uv run python -c "import
    httpx"`. If it is NOT installed, add `httpx>=0.28` to
    `[dependency-groups].dev` in pyproject.toml, then `uv sync`. Commit
    the pyproject delta with this task. (Note: `httpx` is expected to
    already be pulled in by FastAPI/Starlette in 2026; verify before
    adding.)

    ---

    **File 4: `tests/integration/test_logging_smoke.py`** —
    principle-derived per PATTERNS.md. Shape:
    ```python
    # ABOUTME: OPS-04 gate — structlog configure + get_logger smoke.
    # ABOUTME: Confirms logging pipeline does not raise at runtime.
    """Structured logging smoke test."""

    from __future__ import annotations

    from app.logging_config import configure_logging, get_logger


    def test_configure_logging_and_log_event_do_not_raise() -> None:
        """`configure_logging` + `get_logger(x).info(...)` is safe.

        pristine-output rule (filterwarnings=error) catches any
        structlog misconfig at runtime. Test passes if the call
        sequence does not raise.
        """
        configure_logging("INFO")
        log = get_logger("dojo.test")
        log.info("smoke", key="value")
    ```
    This is a synchronous test — `configure_logging` + `log.info` are
    both sync. Do not add `@pytest.mark.asyncio`. Per PATTERNS.md line
    415, the capsys-stdout check is OMITTED — it can be flaky across
    pytest verbosity levels. The non-raising shape is sufficient for
    Phase 1; Phase 7 can add richer log-shape tests if needed.

    ---

    **File 5: `tests/unit/test_settings.py`** — principle-derived per
    PATTERNS.md. Shape:
    ```python
    # ABOUTME: LLM-03 gate — ANTHROPIC_API_KEY loads via pydantic-settings.
    # ABOUTME: Exercises lru_cache clear + env override semantics.
    """Settings unit tests."""

    from __future__ import annotations

    import pytest

    from app.settings import Settings, get_settings


    def test_anthropic_key_loaded_from_env(
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`ANTHROPIC_API_KEY` env var takes precedence over default."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        get_settings.cache_clear()  # lru_cache from prior calls
        settings = get_settings()
        assert (
            settings.anthropic_api_key.get_secret_value()
            == "sk-ant-test"
        )
        # Cleanup: clear cache so other tests start fresh
        get_settings.cache_clear()


    def test_defaults_are_present_when_env_empty(
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Settings instantiate with defaults when env is empty."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        monkeypatch.delenv("RUN_LLM_TESTS", raising=False)
        # Bypass .env: pydantic-settings reads .env even when env vars
        # are unset. Point env_file at /dev/null to isolate defaults.
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.database_url == "sqlite+aiosqlite:///dojo.db"
        assert settings.log_level == "INFO"
        assert settings.run_llm_tests is False
    ```

    Note the footgun (PATTERNS.md line 426): the test MUST call
    `get_settings.cache_clear()` BEFORE `get_settings()` — otherwise
    `lru_cache` returns a previously-cached Settings and the
    monkeypatch has no effect. Document this in the docstring.

    The second test uses `Settings(_env_file=None)` to avoid reading
    the repo's real `.env` (if a developer has one locally). This is
    not strictly needed in CI (no `.env` present) but keeps the test
    deterministic across environments.

    ---

    **Gate all five tests before committing:**
    ```bash
    uv run pytest tests/ -q
    ```
    Must show 6 passed (1 in test_db_smoke, 1 in test_alembic_smoke,
    2 in test_home, 1 in test_logging_smoke, 2 in test_settings).

    **SC #4 gate — the 10x flake check:**
    ```bash
    uv run pytest tests/integration/test_db_smoke.py --count=10 -q
    ```
    Must show 10 passed. If any run reports `RuntimeError: Event loop
    is closed` or similar, the fixture stack is wrong — iterate on
    `tests/conftest.py` until 10/10 pass. Do NOT commit this plan's
    task until the SC #4 gate is green.

    **Pristine output check:** `uv run pytest tests/ -v` should have
    zero warnings in the summary. If a third-party warning appears,
    add the minimal `ignore::DeprecationWarning:<module>` to
    `pyproject.toml`'s `filterwarnings` list (per Planning Guidance 4,
    A5 resolution) — do NOT broaden to all DeprecationWarnings.
  </action>
  <verify>
    <automated>test -f tests/integration/test_db_smoke.py &amp;&amp; test -f tests/integration/test_alembic_smoke.py &amp;&amp; test -f tests/integration/test_home.py &amp;&amp; test -f tests/integration/test_logging_smoke.py &amp;&amp; test -f tests/unit/test_settings.py &amp;&amp; grep -c '^# ABOUTME:' tests/integration/test_db_smoke.py | grep -q '^2$' &amp;&amp; grep -c '^# ABOUTME:' tests/integration/test_alembic_smoke.py | grep -q '^2$' &amp;&amp; grep -c '^# ABOUTME:' tests/integration/test_home.py | grep -q '^2$' &amp;&amp; grep -c '^# ABOUTME:' tests/integration/test_logging_smoke.py | grep -q '^2$' &amp;&amp; grep -c '^# ABOUTME:' tests/unit/test_settings.py | grep -q '^2$' &amp;&amp; grep -q 'alembic_version' tests/integration/test_alembic_smoke.py &amp;&amp; grep -q 'asyncio.to_thread(command.upgrade' tests/integration/test_alembic_smoke.py &amp;&amp; grep -q 'ASGITransport' tests/integration/test_home.py &amp;&amp; grep -q 'cache_clear' tests/unit/test_settings.py &amp;&amp; grep -q 'from app.main import app' tests/integration/test_home.py &amp;&amp; uv run ruff format --check tests/ &amp;&amp; uv run ruff check tests/ &amp;&amp; uv run pytest tests/ -q &amp;&amp; uv run pytest tests/integration/test_db_smoke.py --count=10 -q</automated>
  </verify>
  <done>
    Five test files exist with ABOUTME headers; `uv run pytest tests/`
    passes with ≥6 tests green; `uv run pytest
    tests/integration/test_db_smoke.py --count=10` passes 10/10 (SC #4
    gate); `test_alembic_smoke.py` confirms alembic_version table is
    created on a fresh tmp DB (SC #3 persistent gate); output is
    pristine (no warnings promoted to errors).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test fixtures → tmp filesystem | SQLite DB written under pytest `tmp_path_factory` — isolated per session |
| `monkeypatch.setenv` → pydantic-settings | test muts env vars; cleanup on teardown is guaranteed by pytest |
| `ASGITransport` → in-memory app | no real socket; no external network |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1-TEST-LEAK-01 | Information Disclosure | `test_settings.py` setting `ANTHROPIC_API_KEY="sk-ant-test"` | mitigate | `monkeypatch.setenv` scopes the change to the test function; pytest restores the original env on teardown. The test value is a LITERAL placeholder (`sk-ant-test`), not a real key. |
| T-1-TEST-FLAKE-01 | Denial of Service | Event-loop flakes in `test_db_smoke` | mitigate | pytest-asyncio 1.x `asyncio_default_fixture_loop_scope = "session"` + the `event_loop_policy` fixture (D-05). SC #4's 10x check is the verification gate. |
| T-1-TEST-ISOLATION-01 | Tampering | lru_cache pollution between `test_settings` tests | mitigate | Each test clears `get_settings.cache_clear()` before its assertions; the second test uses `Settings(_env_file=None)` to avoid reading a locally-committed `.env`. |
| T-1-CONFTEST-01 | Information Disclosure | `_clamp_third_party_loggers` silences warnings | accept | Per RESEARCH.md verifier note 6, verification that real warnings surface is a one-time phase-close check (remove the clamp, confirm, re-add). Documented; not automated. |
| T-1-TMP-DB-01 | Information Disclosure | tmp-file SQLite at `tmp_path_factory` location | accept | No user data — just `alembic_version` table. Tmp dirs are auto-cleaned by pytest. Phase 2+ will not put secrets in test fixtures. |
| T-1-ALEMBIC-THREAD-01 | Denial of Service | `asyncio.to_thread(command.upgrade)` deadlock risk | mitigate | Per New Pitfall 5, `command.upgrade` internally spawns a fresh event loop inside the thread; no deadlock with pytest's loop. RESEARCH.md drop-in has been verified live 2026-04-20. |
</threat_model>

<verification>
Run after all tasks complete:

```bash
# All test files and fixtures exist
ls -l tests/__init__.py tests/conftest.py tests/unit/ tests/integration/

# Full suite passes
uv run pytest tests/ -v  # should show 6+ passed, zero warnings

# SC #4 gate (explicit)
uv run pytest tests/integration/test_db_smoke.py --count=10 -q

# Linters
uv run ruff format --check tests/
uv run ruff check tests/

# Coverage sanity (pyproject sets --cov=app)
uv run pytest --cov-fail-under=0 2>&1 | grep -E "TOTAL|passed"
```
</verification>

<success_criteria>
- Full `pytest tests/` suite passes with zero warnings (pristine
  output per TEST-02 + filterwarnings=error).
- `pytest tests/integration/test_db_smoke.py --count=10` passes 10/10
  (SC #4).
- `pytest tests/integration/test_alembic_smoke.py` passes — SC #3
  persistent gate inside `make check`.
- `pytest tests/integration/test_home.py` passes 2/2 (SC #2
  integration).
- `pytest tests/unit/test_settings.py` passes 2/2 (LLM-03).
- `pytest tests/integration/test_logging_smoke.py` passes 1/1
  (OPS-04).
- conftest.py exposes `event_loop_policy`, `test_db_url`,
  `_clamp_third_party_loggers`, `_alembic_cfg`, `_migrated_engine`,
  `session` fixtures — the template Phase 2+ will follow.
- Plan 06 (Makefile + CI + pre-commit) can now wire `make check` with
  confidence that `make test` has real tests to run (satisfies
  RESEARCH.md verifier note 1).
</success_criteria>

<output>
After completion, create
`.planning/phases/01-project-scaffold-tooling/01-05-SUMMARY.md` per the
execute-plan template. Summary must note: (a) SC #4 10x gate result
(pass count + wall time), (b) any `filterwarnings` additions required
to keep output pristine (should be none; document if any), (c)
whether `httpx` needed to be added as an explicit dev dep or was
already transitively available via FastAPI, (d) test count and
coverage percentage, (e) SC #3 now verified by the persistent
`test_alembic_smoke.py` test inside `make check` (closes I1).
</output>
</content>
</invoke>