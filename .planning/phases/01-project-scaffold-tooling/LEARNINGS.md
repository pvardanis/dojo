---
phase: 01-project-scaffold-tooling
captured: 2026-04-21
---

# Phase 1 Learnings

## Process

### 1. Parallel worktree subagents are fragile in this environment
**What happened:** Waves 3 tried spawning 2 background subagents in parallel worktrees; both were denied Write/Bash by a sandbox the subagents can't negotiate. First attempt also hit Claude's usage limit before either agent made progress.
**Takeaway:** For future phases, default to either (a) sequential inline execution for plans with heavy file creation, or (b) foreground subagent calls (non-background) where permission prompts can surface to the user. Don't assume parallel background subagents work across all Claude Code setups. Phase 1 execution style memo: "wave-by-wave callouts with inline execution" was the path that worked.
**Cost:** ~1 hour of retries + cleanup of stale worktree state.

### 2. 5-agent PR review is worth the tokens
**What happened:** After inline implementation finished, ran 5 specialized review agents in parallel (code-reviewer, pr-test-analyzer, comment-analyzer, silent-failure-hunter, type-design-analyzer). They converged on 3 Critical + 8 Important findings. Many would have shipped silently otherwise.
**Takeaway:** For phases that add real code (vs. pure scaffolding), run the 5-agent review *before* declaring the phase complete. The convergent findings (env.py URL override, session rollback pattern, SecretStr placeholder prod guard) surfaced because three independent agents caught them from different angles.
**Cost:** ~20 min of review agent runtime + ~30 min of aggregation + ~90 min of inline fixes. Yielded 7 correctness fixes + 3 new tests + 6 percentage points of coverage.

### 3. Tests that pass but don't test anything are the most dangerous outcome
**What happened:** `test_db_smoke` (SELECT 1) passed for days while env.py silently migrated the wrong DB. Only `test_alembic_smoke`, which inspected `sqlite_master`, caught it. `test_home` matched any response containing "Dojo" — would have false-passed a literal error page. PRAGMA listener regression would have shipped unnoticed until a Phase 3 FK constraint hit prod.
**Takeaway:** Every smoke test needs at least one assertion that would fail if the underlying feature broke. "Runs without raising" is not a test. Favor tight, feature-specific markers over loose substring matches.

## Technical

### 4. `migrations/env.py` Alembic URL priority
**Decision:** `env.py` respects a caller-set `cfg.set_main_option("sqlalchemy.url", ...)` and only falls back to `get_settings().database_url` when the Config URL is the generator placeholder (`driver://user:pass@localhost/dbname`).
**Why:** The unconditional override pattern forced the test harness to monkeypatch `DATABASE_URL` + clear `get_settings.cache_clear()` BEFORE `command.upgrade`. Fragile + invisible + load-bearing. Flipping the priority makes programmatic callers (tests, tools, future internal migrations service) trivial.

### 5. Settings singleton + `_env_file=None`
**Decision:** Unit tests that assert on Settings *defaults* use `Settings(_env_file=None)` to bypass any local `.env`. Tests that assert on env-var overrides use `monkeypatch.setenv(...) + get_settings.cache_clear()` via an autouse fixture.
**Why:** pydantic-settings silently reads `.env` when present. Without `_env_file=None`, a developer with a local `.env` sees different test outcomes than CI. The autouse cache_clear fixture prevents lru_cache pollution across tests.

### 6. Structlog wrapping stdlib, not alongside
**Decision:** `structlog.stdlib.LoggerFactory() + structlog.stdlib.BoundLogger + filter_by_level` processor = structlog delegates to stdlib loggers.
**Why:** CLAUDE.md's convention "`log = logging.getLogger(__name__)` per module (structlog wraps this)" only holds if structlog actually routes through stdlib. The original setup used `PrintLoggerFactory` + `make_filtering_bound_logger` → structlog was parallel to stdlib, not on top of it. Any `logging.getLogger(...).setLevel(...)` clamp was a silent no-op. Now clamps actually gate output, and pytest's `caplog` works for asserting log events.

### 7. SAVEPOINT session fixture (canonical async recipe)
**Decision:** Test session fixture opens an outer transaction on a dedicated connection + binds the sessionmaker with `join_transaction_mode="create_savepoint"`. Rollback at teardown guarantees isolation even if the test calls `sess.commit()`.
**Why:** The naive `async with sess.begin(): yield; await sess.rollback()` pattern has a redundant rollback inside `begin()` that will break the moment a test legitimately commits. The SAVEPOINT pattern is the SQLAlchemy-documented async equivalent of `pytest-sqlalchemy`'s isolation recipe.

### 8. `configure_once` vs `is_configured() + configure`
**Decision:** Use `if not structlog.is_configured(): structlog.configure(...)` instead of `structlog.configure_once(...)`.
**Why:** `configure_once` emits a `RuntimeWarning` when called on an already-configured structlog. Under `filterwarnings = ["error"]` (pyproject setting), that warning escalates to a test failure the moment two tests configure logging in sequence (e.g. `test_logging_smoke` + `test_main_lifespan`). `is_configured + configure` is semantically identical for our use case and silent.

### 9. Module-level engine import-time binding
**Decision:** Documented in a comment above `_settings = get_settings()` in `session.py`. Deferred the actual fix (converting `engine`/`AsyncSessionLocal` to `get_engine()` / `get_session_factory()` lru_cached factories) to Phase 3.
**Why:** Import order matters: anything that imports `app.infrastructure.db.session` before DATABASE_URL is set or the settings cache is cleared binds the engine to whatever default `get_settings()` saw first. Phase 1 test harness works around this via fixture ordering; Phase 3 will mirror the `get_settings` pattern for engines so import order becomes irrelevant.

### 10. SecretStr("dev-placeholder") + prod guard
**Decision:** Default `anthropic_api_key` stays `SecretStr("dev-placeholder")` so `make run` and non-LLM tests don't need a real key. Lifespan checks the key; in `DOJO_ENV=prod`, raises `RuntimeError` with actionable text. Dev logs a warning.
**Why:** Requiring the key at `get_settings()` time forces every test (even unit tests that never touch LLM) to monkeypatch it. Runtime guard at the composition root is the right place — it fails loud before serving traffic but doesn't crash the import graph.

## Surprises

### 11. httpx.ASGITransport doesn't invoke lifespan
**Surprise:** `httpx.AsyncClient(transport=ASGITransport(app=app))` bypasses FastAPI lifespan entirely. `test_home` passed with zero lifespan coverage — the `dojo.startup` log event was emitted by the module-level `app = create_app()` call... except it wasn't, because `create_app()` doesn't invoke lifespan.
**Takeaway:** Use `app.router.lifespan_context(app)` to drive lifespan in tests that need it. Don't assume ASGI test clients invoke lifespan; most don't.

### 12. Hook scope drift
**Surprise:** Plan 06's pre-commit drop-in had `entry: uv run ty check` (no path) and `entry: uv run interrogate -c pyproject.toml` (no path). Makefile had `ty check app` and `interrogate -c pyproject.toml app`. Running `pre-commit run --all-files` after Task 2 failed on `tests/unit/test_settings.py` because the unscoped `ty` scan hit `_env_file=None`. Fix: append `app` to both hook entries so scope matches Makefile.
**Takeaway:** Whenever `make X` and a pre-commit hook `X` are both meant to run the same tool, the hook entry must match the Makefile invocation byte-for-byte.

### 13. `core.hooksPath` blocks `pre-commit install` even at default value
**Surprise:** Git's `core.hooksPath` defaults to `.git/hooks`. Danny's global config explicitly set the key to that same default. `pre-commit install` refuses whenever the key exists regardless of value — the message is `"Cowardly refusing to install hooks with core.hooksPath set."`.
**Takeaway:** `git config --local --unset core.hooksPath` is a no-op functionally but necessary for `pre-commit install`. Document for new contributors; maybe add to `make install` as a best-effort unset.

## Open items (tracked, not blocking)

- **SC #6 deferred:** no GitHub remote yet. Will fire on first push.
- **Phase-2 boundary lint:** `importlinter` or grep-in-CI to enforce "application/domain never imports infrastructure" — needed before any Phase 2 code lands.
- **Module-level engine → factory:** convert to `get_engine()` lru_cache pattern in Phase 3.
- **`test_home` content-type negotiation:** revisit when HTMX partials land in Phase 4+.
- **`alembic` logger INFO for integration tests:** currently clamped to WARNING; Phase 3 may want the upgrade breadcrumb back.

---
*Captured: 2026-04-21*
