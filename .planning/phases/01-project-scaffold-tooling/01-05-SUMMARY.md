---
phase: 01-project-scaffold-tooling
plan: 05
subsystem: testing
tags: [pytest, pytest-asyncio, httpx, asgitransport, alembic, sqlalchemy, fixtures]

requires:
  - phase: 01-project-scaffold-tooling
    provides: "Async DB session + Alembic pipeline + FastAPI app to exercise"
provides:
  - "Shared async conftest fixtures (event_loop_policy, test_db_url, _clamp_third_party_loggers, _db_env, _alembic_cfg, _migrated_engine, session)"
  - "5 Phase 1 smoke tests (db, alembic, home, logging, settings) — all SC gates automated"
  - "`httpx>=0.28` added to dev deps for ASGITransport client"
  - "Fixture template Phase 2+ tests will clone"
affects: [phase-02-domain, phase-03-infrastructure, phase-04-flows, phase-05-drill, phase-06-read, phase-07-e2e]

tech-stack:
  added: [httpx, pytest-asyncio-1.x-fixtures]
  patterns: [session-scoped-alembic-upgrade, outer-transaction-rollback, asgi-transport-in-memory-tests, lru-cache-clear-on-env-change]

key-files:
  created:
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
  modified:
    - pyproject.toml (added httpx>=0.28 to [dependency-groups].dev)

key-decisions:
  - "New session-scoped fixture `_db_env` monkeypatches `DATABASE_URL` before any Alembic/engine work and clears `get_settings()` lru_cache — without this, env.py's `get_settings().database_url` override silently migrates `dojo.db` instead of the tmp DB"
  - "`test_alembic_smoke.py` also monkeypatches DATABASE_URL directly because it runs `command.upgrade` with its own fresh Config outside the session fixture stack"
  - "Outer-transaction rollback via `async with factory() as sess: async with sess.begin(): ... await sess.rollback()` — needs `# noqa: SIM117` because the two contexts have distinct purposes (session creation vs transaction start)"
  - "`Settings(_env_file=None)` in the defaults test bypasses local `.env` so the assertion is deterministic across developer machines and CI"
  - "httpx added as dev dep (FastAPI 0.118 does not pull it in transitively in this install)"

patterns-established:
  - "pytest-asyncio 1.x session-scoped async fixtures with `@pytest_asyncio.fixture(scope='session')`"
  - "Alembic sync CLI wrapped in `asyncio.to_thread` to avoid event-loop contention (New Pitfall 5)"
  - "Env-var + cache-clear pattern for testing pydantic-settings fields without editing env.py"
  - "ASGITransport in-memory ASGI exercise — no socket, no external network"
  - "Third-party logger clamp fixture (autouse session-scoped) for pristine output under `filterwarnings = ['error']`"

requirements-completed: [TEST-02, OPS-04, LLM-03]

duration: ~15min
completed: 2026-04-21
---

# Phase 01-05: Test Infrastructure Summary

**pytest-asyncio 1.x fixture stack + 5 smoke tests closing SC #2/3/4/OPS-04/LLM-03. `pytest tests/` 7 passed, pristine output; `pytest --count=10` on the canary 10/10 flake-free (SC #4 green)**

## Performance

- **Duration:** ~15 min (inline)
- **Started:** 2026-04-21T10:34:00+02:00
- **Completed:** 2026-04-21T10:49:00+02:00
- **Tasks:** 2
- **Files created:** 12 (7 in Task 1 + 5 in Task 2)
- **Files modified:** 1 (`pyproject.toml` — added httpx dev dep)

## Accomplishments

- **7 tests passing, zero warnings** under `filterwarnings = ["error"]` (TEST-02 pristine output gate)
- **SC #4 (10x flake check) green:** `pytest tests/integration/test_db_smoke.py --count=10` → 10/10 in 0.21s
- **SC #3 persistent:** `test_alembic_smoke.py` verifies `alembic upgrade head` creates `alembic_version` on a fresh cold tmp DB — this now lives inside `make check`, closing I1
- **SC #2 integration:** `test_home.py` via `httpx.AsyncClient(transport=ASGITransport(app=app))` proves both `/` (200 HTML with "Dojo") and `/health` (`{"status":"ok"}`) through real ASGI wiring
- **OPS-04 gate:** `test_logging_smoke.py` confirms `configure_logging("INFO") + get_logger.info(...)` is non-raising under filterwarnings=error
- **LLM-03 gate:** `test_settings.py` round-trips `ANTHROPIC_API_KEY` env → `SecretStr.get_secret_value()` AND confirms defaults hold when env is empty
- **Coverage on Phase 1 scope:** 83% — remaining uncovered lines are SQLite PRAGMA listener (fires on first connect but not hit by sync inspection), settings log-level branches, and lifespan startup hooks

## Task Commits

1. **Task 1: tests/ tree + conftest fixtures** — `2f7b…` (test — package tree + 6 fixtures)
2. **Task 2: 5 phase-1 tests + httpx dev dep** — `9d3d…` (test — smoke tests, SC#2/3/4 gates)

## Files Created/Modified

- `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py` — package markers with ABOUTME
- `tests/conftest.py` — shared async fixture stack (7 fixtures incl. new `_db_env`)
- `tests/unit/conftest.py` — unit-test logger clamp
- `tests/unit/.gitkeep`, `tests/integration/.gitkeep` — dir markers
- `tests/integration/test_db_smoke.py` — SC #4 canary (SELECT 1 via async session)
- `tests/integration/test_alembic_smoke.py` — SC #3 gate (fresh cold migrate + alembic_version assertion)
- `tests/integration/test_home.py` — SC #2 integration (ASGITransport; 2 tests)
- `tests/integration/test_logging_smoke.py` — OPS-04 non-raising assertion
- `tests/unit/test_settings.py` — LLM-03 env round-trip + defaults (2 tests)
- `pyproject.toml` — added `httpx>=0.28` to `[dependency-groups].dev`

## Decisions Made

**Critical fix (not in plan drop-in):** Added a session-scoped `_db_env` fixture that monkeypatches `DATABASE_URL=<tmp>` and clears `get_settings.cache_clear()` before any Alembic migration or engine instantiation. This was required because `migrations/env.py` calls `config.set_main_option("sqlalchemy.url", get_settings().database_url)` — which overrides any caller-set URL on the Config. Without this fix, `_migrated_engine` would migrate the default `dojo.db` (in the project root) while the `session` fixture talked to the tmp DB — hidden because `test_db_smoke` only `SELECT 1`s and doesn't need any tables. `test_alembic_smoke.py` caught the bug honestly by asserting on `sqlite_master` contents.

The 01-03 SUMMARY pre-flagged this exact footgun: "Plan 05's session-scoped Alembic fixture must set `DATABASE_URL` before importing anything that triggers `get_settings()` — otherwise the cached singleton binds to the `dojo.db` default." The `_db_env` fixture is the realization of that flag.

## Deviations from Plan

**1. [Rule 1 — Bug] Added `_db_env` fixture to address env.py override silently migrating wrong DB**

- **Found during:** Task 2, first `pytest tests/` run
- **Issue:** `test_alembic_smoke.py` failed with `set()` — the tmp DB had no tables. Alembic logs confirmed "Running upgrade -> 0001, initial" (so the command ran) but the inspection engine saw nothing. Root cause: `env.py` unconditionally does `config.set_main_option("sqlalchemy.url", get_settings().database_url)`, overriding the caller-set URL; `get_settings()` is lru_cached with the default; so Alembic migrated `dojo.db` (project root), leaving tmp DB empty.
- **Fix:** (a) Added session-scoped `_db_env` fixture in `tests/conftest.py` that sets `DATABASE_URL` env var and clears `get_settings.cache_clear()` via `pytest.MonkeyPatch.context()` for the whole session. (b) `_alembic_cfg` now depends on `_db_env`. (c) `test_alembic_smoke.py` does the same monkeypatch + cache_clear locally (because it runs its OWN Alembic command outside the session fixture chain).
- **Files modified:** `tests/conftest.py`, `tests/integration/test_alembic_smoke.py`
- **Verification:** 7/7 tests pass; SC #4 10x gate green; SC #3 persistent test confirms `alembic_version` in tmp DB's `sqlite_master`
- **Committed in:** same Task 2 commit (fix lived inline before commit)
- **Note for future:** An alternative would be to change `env.py` to honor caller-set URLs (check if Config's URL equals the ini placeholder before overriding). That's a cleaner long-term fix but was out of scope for Plan 05 — flagged for Phase 3 or a future plan 01.x.

**2. [Rule 0 — Lint] Combined-with → nested-with with `# noqa: SIM117`**

- **Found during:** Task 1 verify
- **Issue:** ruff SIM117 flagged the nested `async with factory() as sess: / async with sess.begin():` pattern.
- **Fix:** Added `# noqa: SIM117` comment — combining into `async with factory() as sess, sess.begin():` is incorrect because `sess.begin()` requires `sess` to already exist from the preceding manager. The plan's verify block explicitly greps for `async with sess.begin()` so the shape must stay nested.
- **Files modified:** `tests/conftest.py`
- **Verification:** ruff check passes; plan verify grep matches
- **Committed in:** same Task 1 commit

---

**Total deviations:** 2 — one real bug-fix (env.py override), one lint noqa for a correct pattern
**Impact on plan:** No scope creep. Both deviations keep Phase 1 within its own boundaries.

## Issues Encountered

**env.py override footgun:** Pre-flagged by 01-03 SUMMARY but the severity wasn't obvious until the Alembic-smoke test failed. Fixing in the test harness (not env.py) keeps production code clean; Phase 3 or a later gap-closure can revisit env.py if the programmatic-caller UX becomes a recurring pain point.

## User Setup Required

None.

## Next Phase Readiness

- Plan 06 can now write `make test` = `uv run pytest` with confidence: the suite is non-empty (7 tests), pristine, and exercises every Phase 1 must-have.
- Pre-commit hook under Plan 06 should invoke `ruff format --check`, `ruff check`, `interrogate -c pyproject.toml app/`, and `pytest tests/unit/` (fast lane) per D-14.
- CI workflow should run the full `make check` (ruff + ty + interrogate + pytest) on push/PR.
- Phase 2+ tests inherit `_clamp_third_party_loggers` and `session` fixtures from this conftest. New fake adapters should mirror the outer-transaction-rollback pattern when they touch the DB.

**Regression watch:** If any future change to `app/settings.py` or `migrations/env.py` removes or bypasses the `_db_env` fixture's DATABASE_URL pivot, `test_alembic_smoke.py` fails loudly. That's the intended canary.

---
*Phase: 01-project-scaffold-tooling, Plan 05*
*Completed: 2026-04-21*
