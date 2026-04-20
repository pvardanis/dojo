---
phase: 01-project-scaffold-tooling
plan: 01
subsystem: infra
tags:
  - python
  - tooling
  - pyproject
  - uv
  - hatchling
  - ruff
  - pytest
  - pytest-asyncio
  - interrogate
  - ty
  - pre-commit
  - pydantic-settings
  - structlog
  - sqlalchemy
  - aiosqlite
  - alembic
  - fastapi
  - gitignore
  - dotenv

# Dependency graph
requires:
  - phase: 00-planning
    provides: "Phase 1 plan + context + research + patterns + validation docs"
provides:
  - "Repo-root pyproject.toml with Python 3.12 pin and every Phase 1 runtime + dev dep pinned to verified floors"
  - "Reproducible uv.lock (55 packages resolved, editable install of app package enabled via [tool.uv] package = true)"
  - ".gitignore protecting .env, .venv, uv caches, pytest/coverage artifacts, local SQLite DBs, IDE dirs, .DS_Store"
  - ".env.example documenting the four D-18 Settings fields (ANTHROPIC_API_KEY, DATABASE_URL, LOG_LEVEL, RUN_LLM_TESTS) with safe placeholders"
  - "CLAUDE.md reconciled against spec §8.4 (127 lines, all 6 required sections present)"
  - "Tool config (ruff 79-char, pytest asyncio_mode=auto + session loop + filterwarnings=error, interrogate fail-under=100, ty==0.0.31 exact pin) centralized in pyproject.toml"
affects:
  - 01-02-settings-logging  # depends on pyproject + .env.example contract
  - 01-03-database-alembic  # depends on uv sync, editable install, SQLAlchemy/aiosqlite/alembic deps
  - 01-04-web-routes        # depends on uv sync + FastAPI/jinja deps
  - 01-05-test-infrastructure  # depends on pytest + pytest-asyncio + pytest-repeat + filterwarnings config
  - 01-06-tooling-ci        # depends on tool config sections (ruff/pytest/interrogate/ty) + uv.lock for CI cache key

# Tech tracking
tech-stack:
  added:
    - "fastapi 0.136, uvicorn[standard] 0.33, jinja2 3.1, python-multipart (runtime web)"
    - "pydantic 2.13, pydantic-settings 2.14 (config/validation boundary)"
    - "sqlalchemy[asyncio] 2.0.49, aiosqlite 0.22.1, alembic 1.18 (async DB stack)"
    - "structlog 25.5 (structured logging wrapper over stdlib)"
    - "ruff 0.15, ty 0.0.31 (exact pin — beta), interrogate 1.7, pytest 9.0, pytest-asyncio 1.3, pytest-cov 7.1, pytest-repeat 0.9.4, pre-commit 4.5 (dev group)"
    - "hatchling build backend (required by [tool.uv] package = true)"
  patterns:
    - "uv package-mode (editable install) so Alembic env.py can `from app.infrastructure.db import Base` without PYTHONPATH hacks"
    - "pydantic-settings singleton surface contract pre-declared via .env.example (field names land in Plan 02)"
    - "Pristine test output enforced at the config layer: filterwarnings=['error'], strict-markers, strict-config"
    - "Docstring enforcement at 100% (interrogate fail-under=100, migrations/tests/docs excluded)"
    - "Exact pin for beta tooling (ty==0.0.31) vs floor pin for stable libs (D-16 discipline)"
    - "Two-line `# ABOUTME:` header convention applied to .env.example (dotenv uses # comments) but NOT to .gitignore (bare ignore file) or pyproject.toml (TOML config, not Python source)"

key-files:
  created:
    - "pyproject.toml"
    - "uv.lock"
    - ".gitignore"
    - ".env.example"
    - "CLAUDE.md"  # reconciled from untracked main-tree draft; orchestrator replaces the draft at merge
  modified: []

key-decisions:
  - "Collapsed the RESEARCH.md verbatim drop-in's multi-line `filterwarnings` TOML array to `filterwarnings = [\"error\"]` (single line) so the plan's verify grep matches the file exactly. Intent (promote warnings to errors + room for future targeted ignores) is preserved via a two-line comment above the line."
  - "Added `.DS_Store` to `.gitignore` (plan's special_notes mandate macOS noise exclusion); the RESEARCH drop-in did not include it."
  - "Open Question #1 (SecretStr default for ANTHROPIC_API_KEY) deferred to Plan 02 settings task — this plan only documents the field in .env.example with the literal placeholder `sk-ant-your-key-here` and a `# Replace this placeholder for Phase 3 onward` comment. Threat T-1-LLM03-01 mitigated."
  - "Open Question #2 (SC #4 flake-check runner) resolved: added `pytest-repeat>=0.9.4` to dev deps, as planning guidance point 5 directed."
  - "Open Question #3 (`ty check app migrations` scope in the Makefile) deferred to Plan 01-06 per planning guidance point 4."
  - "uv sync succeeded with `packages = [\"app\"]` even though `app/` directory does not yet exist; hatchling's wheel builder packages nothing and does not error. Noted here so Plan 02 knows the package becomes importable only after `app/__init__.py` lands."

patterns-established:
  - "Config-first scaffold: pyproject.toml is the single source for every tool's config (ruff, pytest, interrogate, ty, coverage, uv, hatchling). No stray `pytest.ini` / `ruff.toml` / `.coveragerc` files."
  - "Exact-pin vs floor-pin discipline: exact pin for beta tooling (ty), floor pin for stable libs."
  - "Settings surface contract declared at the env template level (`.env.example`) before any Python code reads it — contract-first across layers."

requirements-completed:
  - OPS-01
  - TEST-02
  - LLM-03

# Metrics
duration: 4m
completed: 2026-04-20
---

# Phase 1 Plan 01: Project Bootstrap Summary

**Foundation pyproject.toml + uv.lock + .gitignore + .env.example + reconciled CLAUDE.md — every Phase 1 dep pinned, secrets ignored, §8.4 sections covered, `uv sync` reproducible.**

## Performance

- **Duration:** 4 min (231s)
- **Started:** 2026-04-20T20:18:00Z
- **Completed:** 2026-04-20T20:21:51Z
- **Tasks:** 3/3
- **Files created:** 5 (pyproject.toml, uv.lock, .gitignore, .env.example, CLAUDE.md)
- **Files modified:** 0

## Accomplishments

- `pyproject.toml` gates `uv sync` with every Phase 1 runtime + dev dep pinned to the RESEARCH-verified floors; `ty==0.0.31` exact-pinned per D-16; `[tool.uv] package = true` + hatchling build backend paired per New Pitfall 6 so editable install works for Alembic in Plan 03.
- `uv.lock` reproducibly resolves 55 packages on Python 3.12.12 against the current PyPI state; committed alongside `pyproject.toml` so CI and fresh clones install identical trees.
- `.gitignore` closes the `^\.env$` gate (LLM-03 verification grep passes) plus ignores `.venv/`, uv caches, pytest/coverage/htmlcov artifacts, local SQLite DB files including WAL/journal/shm, IDE dirs, and macOS `.DS_Store`.
- `.env.example` ships the D-18 Settings surface (ANTHROPIC_API_KEY, DATABASE_URL, LOG_LEVEL, RUN_LLM_TESTS) with safe placeholders, a pydantic-settings precedence note, and the `# Replace this placeholder for Phase 3 onward` comment that resolves Open Question #1.
- `CLAUDE.md` reconciled from the existing 123-line draft: added explicit `make install && make run` under `## Project` and the literal `app/application/ports.py` path under `## Architecture`. Final file is 127 lines (23-line headroom under the 150 cap) and satisfies every spec §8.4 section plus the plan's six verify greps.

## Task Commits

Each task was committed atomically with `--no-verify` (parallel worktree mode):

1. **Task 1: Create pyproject.toml with pinned deps + tool config** — `1013dac` (feat)
2. **Task 2: Create .gitignore and .env.example** — `b44072a` (feat)
3. **Task 3: Reconcile repo-root CLAUDE.md against spec §8.4** — `c3b5f49` (docs)

Plan metadata commit (SUMMARY.md) follows this commit set.

## Files Created/Modified

- `pyproject.toml` — project definition + every tool config (ruff 79-char, pytest asyncio_mode=auto + session loop + filterwarnings=error, interrogate fail-under=100, ty==0.0.31, coverage, uv package mode, hatchling wheel target)
- `uv.lock` — reproducible resolution of 55 packages
- `.gitignore` — Python/uv/pytest/coverage/local-DB/IDE/macOS ignores; `.env` exact-match line (LLM-03)
- `.env.example` — documented Settings surface with safe placeholders; two-line ABOUTME header
- `CLAUDE.md` — reconciled §8.4 instruction file (127 lines, 7 top-level sections)

## Decisions Made

- **`filterwarnings` flattened to a single line** so the plan's verify grep `grep -q 'filterwarnings = \["error"\]' pyproject.toml` matches the file text exactly. The RESEARCH.md drop-in spread the array across 3 lines with an inline comment, which satisfied semantic intent but not the literal grep; I collapsed it and hoisted the intent comment to the two lines above. Both the verify grep and the TOML parser (pytest honors it during collection) are happy.
- **`.DS_Store` added to `.gitignore`** beyond the RESEARCH drop-in — special_notes in the execute prompt explicitly mandate macOS noise exclusion.
- **Deferred Open Question #1 to Plan 02**: `.env.example` carries the literal placeholder `sk-ant-your-key-here` with a "replace for Phase 3 onward" comment. The pydantic `SecretStr` wrapper + the dev-placeholder default behavior lands in Plan 02's `app/settings.py`. Threat T-1-LLM03-01 is mitigated: no real key is shipped.
- **Chose `pytest-repeat` over a shell loop for SC #4**: added `pytest-repeat>=0.9.4` to the dev group (planning guidance point 5); `pytest --count=N` will be wired into `make test-flakes` in Plan 06.
- **Deferred Open Question #3 to Plan 06**: the Makefile `typecheck` target scope (`ty check app migrations` vs `ty check app`) is a Plan 06 concern; this plan creates no Makefile.
- **Noted empty-package build behavior**: `uv sync` succeeded even though `app/` did not yet exist. Hatchling's wheel builder silently packages nothing rather than erroring. Plan 02 should be aware — the editable package becomes importable only once `app/__init__.py` lands.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Reformatted `filterwarnings` TOML array for verify-grep compatibility**
- **Found during:** Task 1 (pyproject.toml verify step)
- **Issue:** Task 1's verify block runs `grep -q 'filterwarnings = \["error"\]' pyproject.toml`, but the RESEARCH.md drop-in spread the array over three lines with an inline comment (`filterwarnings = [\n    "error",  # pristine-output rule\n    ...\n]`). The file was semantically correct — pytest would honor it — but the literal grep failed. The plan's action says "paste verbatim" and "every grep above matches" — a contradiction, which I read as a drop-in formatting bug.
- **Fix:** Collapsed the array to `filterwarnings = ["error"]` on a single line and hoisted the intent comment to two lines above the value so the pristine-output-rule rationale is preserved in-file.
- **Files modified:** `pyproject.toml`
- **Verification:** All 8 Task 1 verify greps pass; `uv sync` re-runs cleanly; pytest config is parsed by the pytest-asyncio 1.3 collector without warnings.
- **Committed in:** `1013dac` (Task 1 commit — fix applied before initial commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Zero scope creep. Fix is a single-line TOML reformatting that keeps both the verify grep and semantic intent satisfied.

## Issues Encountered

- **Worktree did not inherit the untracked `CLAUDE.md` from the main tree**, as expected (the file has never been committed). Handled per the execute prompt's `special_notes`: I read the main-tree draft directly, applied the minimal reconcile deltas, and wrote the new file in the worktree. The orchestrator replaces the main-tree draft at merge time.

## TDD Gate Compliance

Not applicable. Plan 01-01 is a config-bootstrap plan with `type: execute` and no `tdd="true"` tasks. Phase 1 carries a formal TDD exception (D-21 in CONTEXT.md) approved by Danny because the test harness depends on scaffold infrastructure that must exist first. Strict TDD resumes in Phase 2.

## User Setup Required

None — no external service configuration required for this plan. The real `.env` file is NOT created by this plan; developers will copy `.env.example` → `.env` and fill in `ANTHROPIC_API_KEY` when they actually need to hit Anthropic (Phase 3 onward).

## Next Phase Readiness

Plans 01-02 through 01-06 can start immediately:

- **Plan 01-02 (settings + logging)** — `pyproject.toml` has `pydantic-settings>=2.8` and `structlog>=24.4`; `.env.example` pre-declares the Settings surface contract; `uv sync` works. Ready.
- **Plan 01-03 (database + Alembic)** — `sqlalchemy[asyncio]>=2.0.38`, `aiosqlite>=0.22.1`, `alembic>=1.13` are installed; `[tool.uv] package = true` gives Alembic editable-install access to `app.infrastructure.db` once Plan 02/03 create the package. Ready.
- **Plan 01-04 (web routes)** — `fastapi>=0.118`, `jinja2>=3.1`, `uvicorn[standard]>=0.30` installed. Starlette's `Jinja2Templates(directory=...)` provides default autoescape (FLAG 10 resolved). Ready.
- **Plan 01-05 (test infrastructure)** — `pytest>=8.3`, `pytest-asyncio>=1.0`, `pytest-cov>=5.0`, `pytest-repeat>=0.9.4` installed; `[tool.pytest.ini_options]` configured with `asyncio_mode=auto`, session loop scope, `filterwarnings=error`. Ready.
- **Plan 01-06 (tooling + CI)** — `ruff>=0.8`, `ty==0.0.31`, `interrogate>=1.7`, `pre-commit>=3.7` installed; all tool configs centralized in `pyproject.toml`. Ready.

No blockers. One observation for downstream planners: hatchling silently accepts `packages = ["app"]` even when `app/` does not exist, so Plan 02 should add `app/__init__.py` (with the two-line ABOUTME header) as part of its first file creation to flip the editable install from empty-package to real-package.

## Threat Flags

No new security-relevant surface beyond what the plan's `<threat_model>` already enumerates. `.DS_Store` ignore line is a noise mitigation, not a trust-boundary change.

## Self-Check: PASSED

**Files verified on disk:**
- `pyproject.toml` ✓
- `uv.lock` ✓
- `.gitignore` ✓
- `.env.example` ✓
- `CLAUDE.md` ✓
- `.planning/phases/01-project-scaffold-tooling/01-01-SUMMARY.md` ✓

**Commits verified in git log:**
- `1013dac` (Task 1) ✓
- `b44072a` (Task 2) ✓
- `c3b5f49` (Task 3) ✓

---
*Phase: 01-project-scaffold-tooling*
*Plan: 01-01-project-bootstrap*
*Completed: 2026-04-20*
