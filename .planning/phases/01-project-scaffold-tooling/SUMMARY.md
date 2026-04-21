---
phase: 01-project-scaffold-tooling
status: complete
started: 2026-04-20
completed: 2026-04-21
milestone: v1.0

total_commits: 34
total_tests: 10
coverage: 89%

success_criteria_final:
  SC_1_make_check_green: pass
  SC_2_make_run_serves_routes: pass
  SC_3_alembic_upgrade_head: pass
  SC_4_db_smoke_10x_flake_free: pass
  SC_5_precommit_blocks_violation: pass (inline verified — ruff-format + ruff-check + interrogate)
  SC_6_github_actions_ci_green: deferred (no remote yet; workflow file ready)
  OPS_04_structlog_at_startup: pass
  LLM_03_anthropic_key_from_env: pass

requirements_completed:
  - OPS-01
  - OPS-02
  - OPS-03
  - OPS-04
  - TEST-02
  - LLM-03

plans_completed:
  - 01-01-project-bootstrap
  - 01-02-settings-logging
  - 01-03-database-alembic
  - 01-04-web-routes
  - 01-05-test-infrastructure
  - 01-06-tooling-ci
---

# Phase 1: Project Scaffold & Tooling — Summary

**A fresh clone now runs `make install && make check` to provision a reproducible Python 3.12 dev env, exercise every quality gate, and pass 10 automated tests in <1s. FastAPI + Jinja home page renders, async Alembic applies the baseline migration, and the pre-commit chain blocks violating commits before they land.**

Phase 1 shipped the boring-but-correct foundation the next six phases will build on — no business logic, no domain entities, nothing that ever calls an LLM — only the scaffolding that proves every tooling pitfall from PITFALLS.md (C3 expire_on_commit, C4 async Alembic, M8 pytest-asyncio event loops, M10 hook ordering, M12 SQLite PRAGMAs) is already defended against.

## Phase Outcomes

### Architecture primitives in place

- **Settings boundary** (`app/settings.py`) — `BaseSettings` + `SecretStr` masked repr + `Literal` log_level + async-scheme `database_url` validator. `get_settings()` is the `@lru_cache`'d singleton; `get_settings.cache_clear()` is the test escape hatch.
- **Structured logging** (`app/logging_config.py`) — structlog wrapped on stdlib (`stdlib.LoggerFactory` + `stdlib.BoundLogger`), `structlog.is_configured()`-idempotent, env-switched JSON vs Console renderer. `logging.getLogger(...).setLevel(...)` clamps actually gate output.
- **Async DB primitives** (`app/infrastructure/db/session.py`) — `Base(DeclarativeBase)` for Phase 3+ models, async `engine` + `AsyncSessionLocal` with `expire_on_commit=False`, dialect-guarded SQLite PRAGMA listener (`foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000`).
- **Async Alembic** (`migrations/env.py`, `migrations/versions/0001_initial.py`) — `async_engine_from_config` + `connection.run_sync` + empty baseline revision. Env.py respects caller-set URLs; falls back to settings only when the ini placeholder is present.
- **FastAPI composition root** (`app/main.py`) — lifespan wires `configure_logging` + emits `dojo.startup`; `create_app()` factory mounts templates, static dir, routes; module-level `app = create_app()` for uvicorn.
- **Home + health routes** (`app/web/routes/home.py`) — `GET /` renders Jinja home template (Starlette default autoescape ON); `GET /health` returns `{"status":"ok"}`. Routes access templates via `request.app.state.templates` — route modules never import Jinja2Templates.
- **Lifespan prod guard** — `_guard_api_key()` raises `RuntimeError` in `DOJO_ENV=prod` if the Anthropic key is the `dev-placeholder`. Dev logs a warning; real keys are a no-op.

### Test infrastructure primitives in place

- **pytest-asyncio 1.x fixture stack** (`tests/conftest.py`) — session-scoped `event_loop_policy` + `test_db_url` (tmp-file, not `:memory:`) + `_clamp_third_party_loggers` (pristine output) + `_alembic_cfg` + `_migrated_engine` (real `alembic upgrade head` via `asyncio.to_thread`).
- **SAVEPOINT session fixture** — outer transaction on a dedicated connection + `join_transaction_mode="create_savepoint"` on the sessionmaker; test commits become savepoint-closures; outer transaction rollback at teardown guarantees no state leaks. Replaces the broken "explicit rollback inside `sess.begin()`" pattern caught in review.
- **Phase 1 canary tests (10 total):**
  - `test_async_session_executes_trivial_query` — SC #4 flake canary (10× via `make test-flakes`)
  - `test_alembic_upgrade_creates_version_table` — SC #3 persistent gate (tables + `version_num == "0001"`)
  - `test_sqlite_pragmas_applied_on_connect` + `test_pragma_listener_is_dialect_guarded` — PRAGMA listener regression net
  - `test_home_route_returns_200_html` + `test_health_route_returns_ok_json` — SC #2 ASGI integration (tight markers: `<h1>Dojo</h1>` + `<main>`)
  - `test_lifespan_emits_startup_event` — OPS-04 lifespan regression net (caplog-based, structlog-via-stdlib)
  - `test_configure_logging_and_log_event_do_not_raise` — OPS-04 logging boot
  - `test_anthropic_key_loaded_from_env` + `test_defaults_are_present_when_env_empty` — LLM-03 + autouse `get_settings.cache_clear()` fixture
- **Pristine output** — `filterwarnings = ["error"]` in pyproject + third-party logger clamp fixture = any DeprecationWarning/RuntimeWarning is a test failure.

### Dev workflow primitives in place

- `Makefile` (10 targets): install, format, lint, typecheck, docstrings, test, check, run, migrate, test-flakes. All `uv run`-prefixed. `check` = format+lint+typecheck+docstrings+test.
- `.pre-commit-config.yaml` (5 local hooks in D-14 order): ruff-format → ruff-check --fix → ty app → interrogate app → pytest-unit. Hook scope matches Makefile scope exactly.
- `.github/workflows/ci.yml` (single `check` job): setup-uv@v8 + Python 3.12 + `make install && make check`; concurrency cancellation; `ANTHROPIC_API_KEY=ci-placeholder` env block; timeout 10 min.

## Success Criteria Status

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | `make install && make check` exits 0 | ✅ pass | 10 tests green, ruff/ty/interrogate clean, coverage 89% |
| 2 | `make run` serves `/` + `/health` | ✅ pass | Uvicorn subprocess + ASGI integration tests both green |
| 3 | `alembic upgrade head` creates `alembic_version` | ✅ pass | `make migrate` + `test_alembic_smoke` (table + `version_num == "0001"`) |
| 4 | `pytest --count=10` on canary passes 10/10 | ✅ pass | `make test-flakes` → 10 passed in 0.21s |
| 5 | Pre-commit blocks a violating commit | ✅ pass (inline) | ruff-format + ruff-check + interrogate all fired on `app/bad.py` (exit 1) |
| 6 | GitHub Actions CI green on push | ⏸️ deferred | No remote set up yet; workflow file committed; fires on first push |
| OPS-04 | structlog configured at startup | ✅ pass | Lifespan + `test_lifespan_emits_startup_event` regression net |
| LLM-03 | `ANTHROPIC_API_KEY` loads via pydantic-settings | ✅ pass | `test_anthropic_key_loaded_from_env` + SecretStr repr masking |

## Execution Shape

**5 waves, 6 plans, 1 mid-phase replan (inline execution) + post-phase review-fix cycle.**

| Wave | Plans | Mode | Result |
|------|-------|------|--------|
| 1 | 01-01 | parallel worktree (1 agent) | ✅ bootstrap + deps + CLAUDE.md |
| 2 | 01-02 | parallel worktree (1 agent) | ✅ Settings + logging |
| 3 | 01-03 + 01-04 | parallel worktree (2 agents) → **hit usage limit + sandbox denial** → **retry inline** | ✅ DB + web |
| 4 | 01-05 | inline | ✅ tests (7) + real bug-fix inline (`_db_env` workaround for env.py override) |
| 5 | 01-06 | inline | ✅ Makefile + pre-commit + CI workflow |
| Review | — | 5 parallel review agents → 11 findings → 7 atomic fix commits | ✅ tests 7 → 10, coverage 83% → 89% |

**Pivotal moments:**
1. **Wave 3 sandbox denial** — parallel worktree subagents had Write/Bash denied; pivoted to inline execution for Waves 3/4/5.
2. **Wave 4 env.py bug** — `test_alembic_smoke` failed with empty `sqlite_master`; root cause was env.py unconditionally overriding caller URLs. Fixed with workaround (`_db_env` monkeypatch fixture) in Wave 4; the real fix (conditional override) came later in the review cycle and removed the workaround.
3. **Post-phase PR review** — 5 parallel specialized review agents (code-reviewer, pr-test-analyzer, comment-analyzer, silent-failure-hunter, type-design-analyzer) found 3 Critical + 8 Important issues. All 11 fixed inline. Suite grew, coverage grew, zero regressions.

## Key Technical Decisions

1. **`SecretStr("dev-placeholder")` default + lifespan prod guard** — lets `make run` and non-LLM tests start without a real API key in dev; in prod, raises before serving the first request.
2. **env.py priority flip** — caller-set URL wins; settings fallback only triggers on the alembic.ini generator placeholder. Makes programmatic testing trivial; eliminates the `_db_env` monkeypatch dance.
3. **SAVEPOINT session fixture** — canonical SQLAlchemy async recipe (`join_transaction_mode="create_savepoint"`). Test commits are savepoint-closures; outer-transaction rollback guarantees isolation even if tests write.
4. **structlog over stdlib, not alongside** — `stdlib.LoggerFactory` + `stdlib.BoundLogger` + `filter_by_level` processor. Makes `logging.getLogger(...).setLevel(...)` actually gate structlog output. CLAUDE.md's "structlog wraps stdlib" convention is now literally true.
5. **Literal log_level + async-scheme URL validator** — invariants in the type, not in the config docs. Typos fail fast at Settings load, not at first request.
6. **Hook scope = Makefile scope** — both `ty` and `interrogate` run against `app/` only, both in pre-commit and in `make check`. Prevents hook-vs-make drift.

## Key Patterns Established

- `app/main.py` is the only module allowed to import across layers (composition root)
- Every Python file: two `# ABOUTME:` header lines + sphinx-style docstring on every public callable
- `logging.getLogger(__name__)` convention stands: structlog wraps it; `get_logger(name)` returns a structlog BoundLogger backed by the stdlib logger of that name
- Outer-transaction-rollback + SAVEPOINT session fixture is the template Phase 2+ DB tests clone
- `asyncio.to_thread(command.upgrade, ...)` is the only sanctioned way to run Alembic inside a pytest-asyncio loop
- `_env_file=None` + `get_settings.cache_clear()` is the sanctioned way to test Settings defaults without bleeding into the `.env` file
- `structlog.testing.capture_logs()` is incompatible with stdlib-wrapped structlog under `filterwarnings=error`; use pytest `caplog` instead

## Pitfalls Defended

| ID | Pitfall | Where it's defended |
|----|---------|---------------------|
| C3 | `expire_on_commit=True` (SA async) | `session.py` factory + verified in code |
| C4 | Sync Alembic template on async DB | `migrations/env.py` uses `async_engine_from_config` + `run_sync`; `test_alembic_smoke` asserts `version_num == "0001"` |
| M8 | pytest-asyncio event loop flakes | `event_loop_policy` fixture + `asyncio_default_fixture_loop_scope = "session"` + SC #4 10x gate |
| M9 | Eager import of `Base` | `from app.infrastructure.db.session import Base  # noqa: F401` in env.py |
| M10 | Hook ordering | D-14 order enforced in `.pre-commit-config.yaml` |
| M12 | SQLite PRAGMAs | `_configure_sqlite` listener + `test_sqlite_pragmas_applied_on_connect` |
| New-5 | Alembic `asyncio.run` vs pytest loop | `asyncio.to_thread(command.upgrade, ...)` wrapping everywhere |

## Deferred Items

| Item | Scope | Follow-up |
|------|-------|-----------|
| SC #6 (CI green on push) | Operational | Runs automatically once a GitHub remote is added + pushed |
| Import-lint for Phase 2 boundary | Phase 2 | Add `importlinter` or pre-commit grep to enforce "application/domain never imports infrastructure" |
| Module-level engine → deferred factory | Phase 3 | Convert `engine`/`AsyncSessionLocal` to `get_engine()` / `get_session_factory()` behind lru_cache, matching `get_settings` shape. Removes the import-time binding footgun |
| `test_home` assertion tightness | Phase 4+ | Once HTMX partials arrive, add content-type negotiation + partial-response tests |
| Integration-test `alembic` logger at INFO | Phase 3 | Currently clamped to WARNING; Phase 3 may want the "Running upgrade" breadcrumb back for schema-migration tests |

## Artifact Map

```
Root:
├── Makefile                             # 10 targets (9 spec + test-flakes)
├── pyproject.toml                       # Py 3.12, deps pinned, uv.lock tracked
├── alembic.ini                          # ABOUTME + placeholder URL (env.py overrides)
├── .gitignore .env.example
├── .pre-commit-config.yaml              # 5 local hooks, D-14 order, app-scoped
├── .github/workflows/ci.yml             # Single check job, setup-uv@v8, Python 3.12
├── CLAUDE.md                            # Project instructions (reconciled against spec §8.4)
│
app/
├── __init__.py
├── main.py                              # Composition root — ONLY cross-layer importer
├── settings.py                          # Settings (Literal log_level, URL validator, SecretStr)
├── logging_config.py                    # structlog-over-stdlib
├── infrastructure/
│   └── db/
│       ├── __init__.py
│       └── session.py                   # Base + engine + AsyncSessionLocal + PRAGMA listener
└── web/
    ├── __init__.py
    ├── routes/
    │   ├── __init__.py
    │   └── home.py                      # GET / + GET /health
    ├── templates/{base,home}.html
    └── static/.gitkeep
│
migrations/
├── env.py                               # Async Alembic, settings-fallback only on placeholder
├── script.py.mako                       # Stock async template
└── versions/0001_initial.py             # Empty baseline
│
tests/ (10 tests, 89% coverage, 0 warnings under filterwarnings=error)
├── conftest.py                          # 6 session fixtures + SAVEPOINT session fixture
├── unit/
│   ├── conftest.py                      # Dojo logger clamp
│   └── test_settings.py                 # 2 tests + autouse cache_clear
└── integration/
    ├── test_db_smoke.py                 # SC #4 canary
    ├── test_alembic_smoke.py            # SC #3 persistent
    ├── test_home.py                     # SC #2 (2 tests, tight markers)
    ├── test_logging_smoke.py            # OPS-04 boot
    ├── test_main_lifespan.py            # OPS-04 lifespan regression
    └── test_sqlite_pragmas.py           # PRAGMA listener regression (2 tests)
```

## Commit Total

34 commits across 5 execution waves + 7 review-fix commits:
- 26 task/plan commits (feat/test/docs)
- 4 orchestrator commits (worktree merges + tracking updates)
- 7 review-fix commits (`fix(01-rev): ...`)

## Phase Sign-Off

✅ All 8 success criteria are **addressable**.
✅ 7 of 8 are **green** (SC #6 deferred cleanly).
✅ All 6 requirements (OPS-01/02/03/04, TEST-02, LLM-03) validated.
✅ All identified pitfalls defended in code or tests.
✅ Zero known correctness issues carried into Phase 2.

**Ready for:** Phase 2 — Domain & Application Spine.

---

*Phase 1 complete: 2026-04-21.*
