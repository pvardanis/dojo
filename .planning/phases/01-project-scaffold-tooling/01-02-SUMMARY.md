---
phase: 01-project-scaffold-tooling
plan: 02
subsystem: infra
tags:
  - python
  - pydantic-settings
  - structlog
  - secrets
  - logging
  - cross-cutting

# Dependency graph
requires:
  - phase: 01-project-scaffold-tooling
    provides: "Plan 01-01 — pyproject.toml with pydantic-settings>=2.8 and structlog>=24.4 installed, [tool.uv] package = true + hatchling packages = ['app'] configured, .env.example pre-declaring the four D-18 fields"
provides:
  - "app/__init__.py — top-level package marker (D-20 installable package) with two-line ABOUTME header + module docstring only (no re-exports)"
  - "app/settings.py — Settings(BaseSettings) class + @lru_cache'd get_settings() singleton; four D-18 fields with SecretStr('dev-placeholder') default for anthropic_api_key (Open Question #1 resolved)"
  - "app/logging_config.py — configure_logging(log_level) + get_logger(name) helpers; idempotent via structlog.configure_once; env-switched ConsoleRenderer (dev) vs JSONRenderer (prod)"
  - "LLM-03 key-loading and non-leakage surface: SecretStr wraps the API key; repr renders as '**********'; real value only accessible via .get_secret_value() at SDK boundary"
  - "OPS-04 structured logging surface: every module will do 'from app.logging_config import get_logger; log = get_logger(__name__)'"
affects:
  - 01-03-database-alembic       # imports get_settings for DATABASE_URL; migrations/env.py reads the same singleton
  - 01-04-web-routes             # app/main.py calls configure_logging in lifespan + get_settings as a dependency
  - 01-05-test-infrastructure    # tests/unit/test_settings.py + tests/integration/test_logging_smoke.py import from these modules
  - 02-domain-layer              # future modules obtain loggers via get_logger(__name__)
  - 03-infrastructure-anthropic  # Anthropic provider calls .get_secret_value() at the SDK boundary (only sanctioned breach of SecretStr)

# Tech tracking
tech-stack:
  added: []  # no new deps — pydantic-settings and structlog were pulled in by Plan 01-01
  patterns:
    - "SecretStr('dev-placeholder') default — Open Question #1 resolution: dev clones can 'make run' without a real key; Phase 3's Anthropic adapter validates on first use, not at Settings construction"
    - "structlog.configure_once idempotency — the helper is safe to call from both FastAPI lifespan startup AND pytest fixtures. A repeated call emits RuntimeWarning; under filterwarnings=['error'] (pyproject) the test fixture must configure once per session, which D-06's session-scoped fixture architecture already assumes"
    - "Composition-root-only runtime call to configure_logging — neither app/settings.py nor app/logging_config.py configure logging at import time; app/main.py's lifespan is the one runtime entry (Plan 01-04)"
    - "get_logger(name) wraps structlog.get_logger — stdlib logging ergonomics (log = get_logger(__name__)) with structlog's structure underneath. Modules never import structlog directly (OPS-04)"

key-files:
  created:
    - "app/__init__.py"
    - "app/settings.py"
    - "app/logging_config.py"
  modified: []

key-decisions:
  - "Resolved Open Question #1 per planning guidance: `anthropic_api_key: SecretStr = SecretStr('dev-placeholder')`. Makes `make run` work on a fresh clone without `.env`; Phase 3 (Anthropic adapter) raises on first SDK call if the placeholder is still present. The alternative (required-no-default) was rejected because it creates import-time boot failures in tests that never touch Anthropic."
  - "Added a module docstring line (`'''Application settings loaded from .env via pydantic-settings.'''`) between the two-line ABOUTME header and `from __future__ import annotations` in `app/settings.py`. Same pattern in `app/logging_config.py`. Interrogate at 100% counts module-level docstrings; this closes the last coverage gap without inflating the file beyond the 100-line limit."
  - "Kept the structlog processor chain verbatim from the RESEARCH drop-in (merge_contextvars → add_log_level → TimeStamper(iso, utc) → StackInfoRenderer → format_exc_info → renderer). No processor adds or elides SecretStr-unwrapping behavior; logging `settings.anthropic_api_key` directly is safe because SecretStr formats as `****` (threat T-1-LLM03-03 mitigated by omission, not by an active filter)."
  - "`app/__init__.py` contains only the two-line ABOUTME header and a one-line module docstring. No `__version__`, no re-exports, no `__all__`. D-11's 'no empty shells' rule is satisfied because D-20's installable-package requirement gives the marker structural purpose."

patterns-established:
  - "Two-line `# ABOUTME:` header + module docstring on every Python file (including `__init__.py`) — required for interrogate to hit 100% coverage; established here as the template every Phase 2+ module follows"
  - "@lru_cache'd singleton for stateless config — `get_settings()` is the reference shape; FastAPI's `Depends(get_settings)`, Alembic's `env.py`, and tests that `get_settings.cache_clear()` + monkeypatch all share one instance"
  - "Idempotent configure_* helpers at composition boundaries — `configure_logging` uses `structlog.configure_once` so test fixtures and lifespan can both invoke it without concern; same pattern will apply to future configure_* helpers (DB engine dispose, metrics, etc.)"
  - "Environment-branched renderer selection via `os.getenv('DOJO_ENV', 'dev') == 'prod'` — not a Settings field because this controls log-output shape (pre-Settings bootstrap concern), not application config"

requirements-completed:
  - OPS-04
  - LLM-03

# Metrics
duration: 2m
completed: 2026-04-20
---

# Phase 1 Plan 02: Settings & Logging Summary

**pydantic-settings singleton with SecretStr-wrapped Anthropic key (dev-placeholder default) plus idempotent structlog configuration — every Phase 1+ module can now import `get_settings()` and `get_logger(__name__)` without raising.**

## Performance

- **Duration:** 2 min (~114s)
- **Started:** 2026-04-20T20:26:56Z
- **Completed:** 2026-04-20T20:28:50Z
- **Tasks:** 2/2
- **Files created:** 3 (app/__init__.py, app/settings.py, app/logging_config.py)
- **Files modified:** 0

## Accomplishments

- `app/__init__.py` created unconditionally per D-20: hatchling's `packages = ["app"]` in `pyproject.toml` (Plan 01-01) now resolves to a real package instead of silently packaging nothing. The file is the minimal ABOUTME + module-docstring marker with no re-exports or `__version__`.
- `app/settings.py` ships the D-18 Settings surface (`anthropic_api_key`, `database_url`, `log_level`, `run_llm_tests`) with `SecretStr('dev-placeholder')` as the API-key default. `repr(settings.anthropic_api_key)` → `SecretStr('**********')`; the real value is only accessible via `.get_secret_value()` (LLM-03 + threat T-1-LLM03-02 mitigated).
- `app/logging_config.py` ships `configure_logging(log_level)` + `get_logger(name)`. `structlog.configure_once` makes `configure_logging` idempotent; env-switched final processor (`DOJO_ENV=prod` → `JSONRenderer`; else `ConsoleRenderer`). OPS-04 is satisfied: every Phase 2+ module will do `log = get_logger(__name__)`.
- All three files pass ruff format/check, interrogate at 100%, line-length ≤79, and file-length ≤100 (actual: 3, 37, 51). Python import smoke tests succeed: `get_settings()` returns the cached singleton; `configure_logging('INFO')` + `get_logger('dojo.smoke').info('hello', key='value')` prints a valid structured log line.

## Task Commits

Each task was committed atomically with `--no-verify` (parallel worktree mode):

1. **Task 1: Create app/ package + app/__init__.py + app/settings.py** — `e08b57d` (feat)
2. **Task 2: Create app/logging_config.py (structlog + get_logger)** — `2edc4f9` (feat)

Plan metadata commit (SUMMARY.md) follows this commit set.

## Files Created/Modified

- `app/__init__.py` — 3 lines; top-level package marker (D-20). Two-line ABOUTME header + module docstring only.
- `app/settings.py` — 37 lines; Settings(BaseSettings) with SettingsConfigDict (env_file=.env, extra=ignore, case_sensitive=False) + four D-18 fields + `@lru_cache get_settings()`.
- `app/logging_config.py` — 51 lines; `configure_logging(log_level)` with five-processor structlog chain + env-switched renderer + `configure_once`; `get_logger(name)` returns a module-bound structlog logger.

## Decisions Made

- **Open Question #1 resolved with the recommended default:** `anthropic_api_key: SecretStr = SecretStr("dev-placeholder")`. Dev clones run `make run` without a real key; Phase 3's Anthropic adapter will raise on first SDK call if the placeholder survives. The alternative (required-without-default) was rejected because it would fail Settings instantiation at import time in any test that does not set `ANTHROPIC_API_KEY`, defeating the Phase 1 smoke-test contract.
- **Module docstrings added between ABOUTME and `from __future__ import annotations`.** The RESEARCH.md drop-in omits this; interrogate at `fail-under = 100` (pyproject) counts module-level docstrings, so without the one-liner the coverage falls to 3/4 = 75% in `app/__init__.py` and 3/4 = 75% in `app/settings.py`. The one-liner is the minimum change that keeps interrogate green without growing the file past 100 lines.
- **`app/__init__.py` contains no re-exports, no `__version__`, no `__all__`.** D-11's "no empty shells" rule applies to sub-packages that serve no structural purpose; the top-level marker IS structural (D-20 installable package), so the minimal form is correct. Re-exports would prematurely define an API surface before any Phase 2+ code exists.
- **RESEARCH.md drop-in pasted verbatim for `app/logging_config.py`.** The processor chain (merge_contextvars → add_log_level → TimeStamper → StackInfoRenderer → format_exc_info → renderer) is from structlog's getting-started guide; no project-specific additions. `configure_once` ensures test fixtures and FastAPI lifespan can both call the helper without conflict.

## Deviations from Plan

None — plan executed exactly as written.

Both tasks followed the planner's verbatim drop-in (with the single documented addition of a module docstring line in each file for interrogate compliance, which the plan already called out in its action block: *"Add a module-level docstring between the ABOUTME lines and the `from __future__` import"*). Every verify grep, linter, and smoke import passed on the first commit.

## Issues Encountered

- **`configure_once` emits `RuntimeWarning: Repeated configuration attempted.` on the second call.** This is expected structlog behavior and matches the plan's `<done>` criterion ("idempotent"). The warning does NOT raise, so the function is truly idempotent. Under `filterwarnings = ["error"]` (pyproject.toml from Plan 01-01), pytest will promote this warning to a test failure if a test calls `configure_logging()` more than once. Plan 01-05's conftest must configure logging exactly once per session (D-06 session-scoped fixture architecture already assumes this). Flagged here so Plan 05 doesn't get surprised.
- No other issues encountered.

## TDD Gate Compliance

Not applicable. Plan 01-02 has `type: execute` and no `tdd="true"` tasks. Phase 1 carries a formal TDD exception (D-21 in 01-CONTEXT.md): the test harness depends on these modules existing first. Plan 01-05 will write the test-after smoke tests for both `Settings` (`tests/unit/test_settings.py`) and `configure_logging`/`get_logger` (`tests/integration/test_logging_smoke.py`). Strict TDD resumes in Phase 2.

## User Setup Required

None — no external service configuration required for this plan. The real `.env` is still not required; Settings will instantiate cleanly from defaults only. Developers will copy `.env.example` → `.env` and supply `ANTHROPIC_API_KEY` when Phase 3 lands.

## Next Phase Readiness

- **Plan 01-03 (database + Alembic)** — can import `from app.settings import get_settings` for `DATABASE_URL` (D-01 single source of truth); `migrations/env.py` will use the same singleton. Ready.
- **Plan 01-04 (web routes + main.py)** — can import `configure_logging`, `get_logger`, `get_settings`. The FastAPI lifespan hook will call `configure_logging(settings.log_level)` exactly once at startup (D-17). Ready.
- **Plan 01-05 (test infrastructure)** — `tests/unit/test_settings.py` can monkeypatch `ANTHROPIC_API_KEY`, call `get_settings.cache_clear()`, and assert via `.get_secret_value()`. `tests/integration/test_logging_smoke.py` can call `configure_logging("INFO")` once (per session fixture) and assert `get_logger("dojo.test").info(...)` doesn't raise. Ready.
- **Plan 01-06 (tooling + CI)** — no direct dependency; tool config was centralized in `pyproject.toml` in Plan 01-01. Ready.

No blockers. One observation for Plan 01-05: the `configure_once` `RuntimeWarning` under `filterwarnings = ["error"]` means the conftest fixture must configure logging exactly once per session (this is what D-06's session-scoped fixture architecture intends).

## Threat Flags

No new security-relevant surface beyond what the plan's `<threat_model>` already enumerates. The SecretStr default (`dev-placeholder`) is NOT a secret: it's a sentinel string explicitly intended to fail loudly at Phase 3's SDK boundary if it's never replaced. Logging `settings.anthropic_api_key` anywhere in the codebase is safe because SecretStr formats as `****` (threat T-1-LLM03-02 mitigated structurally, not by a logging filter).

## Self-Check

**Files verified on disk:**
- `app/__init__.py` — FOUND (3 lines, 2 ABOUTME headers, module docstring)
- `app/settings.py` — FOUND (37 lines, 2 ABOUTME headers, Settings class + get_settings)
- `app/logging_config.py` — FOUND (51 lines, 2 ABOUTME headers, configure_logging + get_logger + configure_once)
- `.planning/phases/01-project-scaffold-tooling/01-02-SUMMARY.md` — will be committed after this write

**Commits verified in git log:**
- `e08b57d` (Task 1: feat — app package marker + settings) — FOUND
- `2edc4f9` (Task 2: feat — structlog logging configuration) — FOUND

**Linters verified:**
- `uv run ruff format --check app/` — 3 files already formatted
- `uv run ruff check app/` — All checks passed!
- `uv run interrogate -c pyproject.toml app/` — 100.0% (6/6 items covered)

**Smoke tests verified:**
- `get_settings()` returns cached Settings with `database_url='sqlite+aiosqlite:///dojo.db'`, `log_level='INFO'`, `run_llm_tests=False`, `repr(anthropic_api_key) == "SecretStr('**********')"`
- `configure_logging('INFO')` idempotent (second call emits RuntimeWarning but does not raise)
- `get_logger('dojo.smoke').info('hello', key='value')` prints a valid ISO-UTC-timestamped structured log line and returns successfully

## Self-Check: PASSED

---
*Phase: 01-project-scaffold-tooling*
*Plan: 01-02-settings-logging*
*Completed: 2026-04-20*
