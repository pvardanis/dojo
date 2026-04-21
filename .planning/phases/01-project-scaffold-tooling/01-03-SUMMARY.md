---
phase: 01-project-scaffold-tooling
plan: 03
subsystem: database
tags: [sqlalchemy, async, aiosqlite, alembic, migrations, pydantic-settings]

requires:
  - phase: 01-project-scaffold-tooling
    provides: "pydantic-settings Settings singleton with `database_url`, app package marker"
provides:
  - "Async SQLAlchemy engine + session factory (`Base`, `engine`, `AsyncSessionLocal`)"
  - "Dialect-guarded SQLite PRAGMA listener (foreign_keys, WAL, busy_timeout)"
  - "Async Alembic scaffold wired to pydantic-settings (single source of truth for DATABASE_URL)"
  - "Empty baseline revision (`0001_initial.py`) that creates `alembic_version` tracking table"
affects: [tests, integration, phase-03-infrastructure, phase-04-persistence]

tech-stack:
  added: [sqlalchemy-async, alembic-async-template, aiosqlite]
  patterns: [dialect-guarded-connection-listener, settings-driven-migration-env, empty-initial-revision]

key-files:
  created:
    - app/infrastructure/__init__.py
    - app/infrastructure/db/__init__.py
    - app/infrastructure/db/session.py
    - alembic.ini
    - migrations/env.py
    - migrations/script.py.mako
    - migrations/versions/0001_initial.py
    - migrations/README
  modified: []

key-decisions:
  - "Module-level `_settings = get_settings()` at import time — engine is bound once; downstream code imports `get_settings` directly, not `_settings`"
  - "Dialect guard `engine.dialect.name != 'sqlite'` short-circuits PRAGMAs so a Postgres swap is a no-op portability cost (D-01/D-03)"
  - "`expire_on_commit=False` non-negotiable (C3) — attribute access after commit must not trigger lazy-load in async context"
  - "env.py uses canonical async template with `config.set_main_option` to override static alembic.ini URL (D-01 single source of truth)"
  - "Initial revision body is docstring-only (no `pass`, no `op.create_table`) — D-08 mandates empty upgrade so first real schema lives in Phase 3"
  - "`noqa: F401` on `Base` import in env.py is INTENTIONAL (M9 defense for future eager model loading)"

patterns-established:
  - "Dialect-guarded PRAGMA listener pattern: `@event.listens_for(engine.sync_engine, 'connect')` with early-return guard; pasted verbatim from RESEARCH.md §Pattern drop-in"
  - "Settings-driven Alembic env.py: import `app.settings.get_settings()`, override `sqlalchemy.url` at runtime — prevents hardcoded DB URLs in alembic.ini"
  - "Empty initial revision pattern: docstring-only `upgrade()`/`downgrade()` bodies; interrogate counts the docstring so no-op migrations are still 100% documented"

requirements-completed: [OPS-01]

duration: ~7min
completed: 2026-04-21
---

# Phase 01-03: Database & Alembic Summary

**Async SQLAlchemy + Alembic pipeline wired to pydantic-settings — `alembic upgrade head` creates `alembic_version` on a fresh aiosqlite DB (SC #3 gate closed)**

## Performance

- **Duration:** ~7 min (inline execution after background subagent permission block)
- **Started:** 2026-04-21T10:20:00+02:00 (inline re-run)
- **Completed:** 2026-04-21T10:27:00+02:00
- **Tasks:** 2
- **Files created:** 8

## Accomplishments

- `app/infrastructure/db/session.py` exposes `Base`, `engine`, `AsyncSessionLocal` (46 lines, ABOUTME + docstring, ruff+interrogate clean, `expire_on_commit=False`)
- Dialect-guarded SQLite PRAGMA listener fires `foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000` only when connected to SQLite (no-op on Postgres)
- Async Alembic scaffold generated via `alembic init -t async migrations`; `env.py` replaced with drop-in that reads DB URL from `get_settings()` (D-01 single source of truth)
- `migrations/versions/0001_initial.py` committed with empty `upgrade()`/`downgrade()` docstring-only bodies (D-08)
- **SC #3 gate passed:** `DATABASE_URL=sqlite+aiosqlite:////tmp/dojo.smoke.db uv run alembic upgrade head` succeeds and `alembic_version` table appears in `.schema`; `alembic downgrade base` also runs clean (bidirectional contract honored)

## Task Commits

1. **Task 1: Package markers + session.py** — `48563e9` (feat)
2. **Task 2: Async Alembic scaffold + env.py + 0001_initial.py** — `96589cb` (feat)

## Files Created/Modified

- `app/infrastructure/__init__.py` — infrastructure layer package marker (ABOUTME + docstring)
- `app/infrastructure/db/__init__.py` — DB subpackage marker
- `app/infrastructure/db/session.py` — async engine, AsyncSessionLocal, DeclarativeBase, `_configure_sqlite` listener
- `alembic.ini` — CLI config (two ABOUTME lines prepended; `sqlalchemy.url` left at generator default since env.py overrides it)
- `migrations/env.py` — async env wired to `app.settings.get_settings()` and `Base.metadata`
- `migrations/script.py.mako` — stock async template, untouched
- `migrations/versions/0001_initial.py` — revision `"0001"`, no-op upgrade/downgrade
- `migrations/README` — generator output, untouched

## Decisions Made

None beyond plan — followed RESEARCH.md drop-ins verbatim. Filename produced: `0001_initial.py` (written by hand, not by `alembic revision`, so the date-stamp convention was skipped per plan guidance).

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

**Orchestrator-level:** Two earlier attempts to run this plan as a parallel worktree subagent were blocked by the sandbox (Write + Bash denied on worktree paths). First attempt hit the Claude usage limit immediately; second attempt reached a second subagent layer that had no Write/Bash permission. Orchestrator switched to inline execution per Danny's direction and the plan ran cleanly on the main working tree.

## User Setup Required

None — no external services configured in this plan.

## Next Phase Readiness

- Plan 04 (web routes) can run now — no file overlap with this plan's files_modified.
- Plan 05 (test infra) has the full Alembic pipeline to point its session-scoped fixture at; `alembic.command.upgrade` against tmp DB is proven working.
- Phase 3+ (infrastructure adapters) can `from app.infrastructure.db.session import Base, AsyncSessionLocal, engine` directly.

**Open Question forward:** Plan 05's session-scoped Alembic fixture must set `DATABASE_URL` before importing anything that triggers `get_settings()` — otherwise the cached singleton binds to the `dojo.db` default. Flagged explicitly so Plan 05 doesn't miss it.

---
*Phase: 01-project-scaffold-tooling, Plan 03*
*Completed: 2026-04-21*
