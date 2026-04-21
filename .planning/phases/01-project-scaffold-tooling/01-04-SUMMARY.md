---
phase: 01-project-scaffold-tooling
plan: 04
subsystem: infra
tags: [fastapi, jinja2, uvicorn, asgi, routes, lifespan, composition-root]

requires:
  - phase: 01-project-scaffold-tooling
    provides: "pydantic-settings Settings + configure_logging (lifespan target) + get_logger"
provides:
  - "FastAPI composition root (`app/main.py`) with lifespan-driven logging"
  - "Module-level `app = create_app()` that uvicorn imports as `app.main:app`"
  - "Home (`GET /` HTML) and health (`GET /health` JSON) route module"
  - "Jinja base + home templates + empty static dir for Phase 4+ assets"
affects: [tests, phase-04-generate-flow, phase-05-drill, phase-06-read]

tech-stack:
  added: []
  patterns: [composition-root, lifespan-startup-logging, app-state-templates, apirouter-per-module]

key-files:
  created:
    - app/main.py
    - app/web/__init__.py
    - app/web/routes/__init__.py
    - app/web/routes/home.py
    - app/web/templates/base.html
    - app/web/templates/home.html
    - app/web/static/.gitkeep
  modified: []

key-decisions:
  - "`app/main.py` is the ONLY module importing across layers (OPS-04 + architecture constraint)"
  - "Lifespan startup calls `configure_logging(settings.log_level)` exactly once — not at import time (tests need isolation)"
  - "Templates mounted via `app.state.templates` so route modules don't import Jinja2Templates (keeps composition-root boundary)"
  - "No explicit `autoescape=True` kwarg — Starlette's `Jinja2Templates` default enables `select_autoescape(['html', 'htm', 'xml'])` (FLAG 10 resolved)"
  - "`GET /health` returns literal `{'status': 'ok'}` — no version/build/env fingerprint (D-13 info-disclosure mitigation)"

patterns-established:
  - "Composition root: `create_app()` returns FastAPI + module-level `app` binding; uvicorn targets via `app.main:app`"
  - "Lifespan pattern: `@asynccontextmanager async def lifespan(app)` configures logging + logs structured `dojo.startup` event"
  - "Route modules access templates via `request.app.state.templates` — Jinja2Templates instantiated only in main.py"

requirements-completed: [OPS-04]

duration: ~5min
completed: 2026-04-21
---

# Phase 01-04: Web Composition Root Summary

**FastAPI app with lifespan-driven structlog config, Jinja-rendered `/` home, and JSON `/health` — `uvicorn app.main:app` boots clean and serves both routes (SC #2 gate closed)**

## Performance

- **Duration:** ~5 min (inline execution)
- **Started:** 2026-04-21T10:28:00+02:00
- **Completed:** 2026-04-21T10:33:00+02:00
- **Tasks:** 3
- **Files created:** 7

## Accomplishments

- `app/main.py` (43 lines): `create_app()` factory, `@asynccontextmanager lifespan` that configures logging + logs `dojo.startup`, module-level `app = create_app()` for uvicorn
- `app/web/routes/home.py` (25 lines): `APIRouter` with two routes — `GET /` renders `home.html`, `GET /health` returns `{"status": "ok"}`
- Base + home Jinja templates; home extends base; content-type correctly served as `text/html; charset=utf-8`
- `app/web/__init__.py` + `app/web/routes/__init__.py` package markers with ABOUTME headers
- `app/web/static/.gitkeep` zero-byte marker (StaticFiles mount won't crash on empty dir)
- **SC #2 gate confirmed** via uvicorn subprocess smoke on port 8765:
  - `GET /` → 200 with body containing "Dojo"
  - `GET /health` → `{"status":"ok"}`
  - Lifespan startup log line emitted: `dojo.startup database_url=sqlite+aiosqlite:///dojo.db`

## Task Commits

1. **Task 1: Templates + __init__ shells + static marker** — `6c88…` (feat)
2. **Task 2: Home + health route module** — `a38a8cb` (feat)
3. **Task 3: app/main.py composition root** — `4b000ed` (feat)

## Files Created/Modified

- `app/main.py` — composition root + lifespan + create_app factory
- `app/web/__init__.py` — presentation layer package marker
- `app/web/routes/__init__.py` — routes subpackage marker
- `app/web/routes/home.py` — home + health APIRouter
- `app/web/templates/base.html` — Jinja base (title + content blocks)
- `app/web/templates/home.html` — extends base, Dojo h1 + placeholder copy
- `app/web/static/.gitkeep` — empty dir marker

## Decisions Made

None beyond plan — drop-ins pasted verbatim from RESEARCH.md §Pattern.

## Deviations from Plan

**1. [Rule — verification substitution] Used uvicorn subprocess smoke instead of httpx ASGI smoke**
- **Found during:** Task 3 verify block
- **Issue:** The plan's primary automated verification uses `httpx.AsyncClient(transport=ASGITransport(...))` to exercise both routes. However, `httpx` is NOT a declared dependency (it's a transitive of FastAPI's `TestClient` but not pulled in by the Phase 1 subset — confirmed via `uv pip list | grep -i httpx` returning empty).
- **Fix:** Executed the alternative `uvicorn app.main:app --port 8765 &` subprocess smoke that the plan documents as "an extra guardrail" — `curl / && curl /health`. Both returned 200 with expected bodies. `tail /tmp/uvicorn.log` confirmed lifespan startup line emitted.
- **Files modified:** None (verification-only)
- **Verification:** HTTP 200 on both endpoints, lifespan log line present, uvicorn shuts down cleanly
- **Committed in:** `4b000ed` (Task 3)
- **Note for Plan 05:** Plan 05 explicitly handles this case — it instructs to add `httpx>=0.28` to `[dependency-groups].dev` in pyproject.toml if not installed. That's the right moment to close this gap; Phase 1-04 does not prematurely add test-only deps.

---

**Total deviations:** 1 (verification path substitution, zero functional change)
**Impact on plan:** None — both smoke paths prove the same thing (GET / → 200 HTML Dojo; GET /health → 200 JSON status:ok). Plan 05 adds httpx and tests via ASGITransport.

## Issues Encountered

**Orchestrator-level:** Same as 01-03 — earlier parallel worktree subagent was sandboxed out of Write/Bash and could not execute. Ran inline on the main working tree after Danny confirmed.

## User Setup Required

None.

## Next Phase Readiness

- Plan 05 can now build `tests/integration/test_home.py` targeting `app.main.app` via `httpx.AsyncClient(transport=ASGITransport(app=app))` — and will add `httpx>=0.28` to dev deps at that time.
- Plan 06 Makefile can wire `run: uv run uvicorn app.main:app --reload --port 8000`.
- Phase 4+ can add route modules under `app/web/routes/` and `app.include_router(...)` in `create_app()`.

**Regression watch:** If any future change accidentally logs `settings.anthropic_api_key` at startup, `SecretStr` masks repr as `'**********'` — defense-in-depth is intact. The current lifespan logs only `database_url`, which for Phase 1 SQLite is a safe literal.

---
*Phase: 01-project-scaffold-tooling, Plan 04*
*Completed: 2026-04-21*
