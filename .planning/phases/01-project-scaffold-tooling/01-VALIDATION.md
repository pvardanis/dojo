---
phase: 1
slug: project-scaffold-tooling
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-20
approved: 2026-04-20
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 1.x (`asyncio_mode = "auto"`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (created in Phase 1) |
| **Quick run command** | `uv run pytest tests/unit/ -x --ff` |
| **Full suite command** | `make check` |
| **Estimated runtime** | ~15 seconds (unit only); ~30-45 seconds (full `make check` with Phase 1 suite) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/ -x --ff`
- **After every plan wave:** Run `make check`
- **Before `/gsd-verify-work`:** `make check` must be green AND SC #4 (`make test-flakes` → `pytest --count 10 tests/integration/test_db_smoke.py`) must pass
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Each row maps a Phase 1 requirement / success criterion to the plan
+ task that implements it and the automated command that proves it.
Task IDs use the convention `{phase}-{plan}-T{n}` where `n` is the
task index inside the plan.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01-01 | 1 | OPS-01, TEST-02, LLM-03 | T-1-DEPS-01 | `pyproject.toml` installs cleanly, pytest config valid | smoke | `uv sync && make -n check` exits 0 | ✅ | ⬜ pending |
| 01-01-T2 | 01-01 | 1 | LLM-03 | T-1-SECRETS-01 | `.gitignore` protects `.env`; `.env.example` documents Settings surface | smoke | `grep -qE '^\.env$' .gitignore && grep -c '^# ABOUTME:' .env.example` = 2 | ✅ | ⬜ pending |
| 01-02-T1 | 01-02 | 2 | LLM-03 | T-1-LLM03-02 | `Settings` loads `ANTHROPIC_API_KEY` as `SecretStr` with dev-placeholder default | unit | `uv run pytest tests/unit/test_settings.py` (created by 01-05-T2) | ✅ (after 05) | ⬜ pending |
| 01-02-T2 | 01-02 | 2 | OPS-04 | T-1-LLM03-03 | `configure_logging` + `get_logger` work without raising | integration | `uv run pytest tests/integration/test_logging_smoke.py` (created by 01-05-T2) | ✅ (after 05) | ⬜ pending |
| 01-03-T1 | 01-03 | 3 | OPS-01 | T-1-SQLi-02 | `session.py` exposes `Base`, `engine`, `AsyncSessionLocal`; dialect-guarded PRAGMAs | smoke | `uv run python -c "from app.infrastructure.db.session import Base, engine, AsyncSessionLocal; assert Base.metadata.tables == {}; print('OK')"` (inline in 01-03-T1 verify block) | ✅ | ⬜ pending |
| 01-03-T2 | 01-03 | 3 | OPS-01, SC-3 | T-1-DOS-01 | `alembic upgrade head` runs async, creates `alembic_version` | integration | `uv run pytest tests/integration/test_alembic_smoke.py` (created by 01-05-T2; persists SC #3 in `make check`) | ✅ (after 05) | ⬜ pending |
| 01-04-T1 | 01-04 | 3 | OPS-04 | T-1-XSS-01 | Jinja templates + package shells present with autoescape default | smoke | `test -f app/web/templates/home.html && test -f app/web/static/.gitkeep && ! grep -r 'autoescape=False' app/web/` | ✅ | ⬜ pending |
| 01-04-T2 | 01-04 | 3 | OPS-04, SC-2 | T-1-HEALTH-LEAK-01 | `/` + `/health` routes correctly defined | unit | `uv run python -c "from app.web.routes.home import router; paths = sorted(r.path for r in router.routes); assert paths == ['/', '/health']; print('OK')"` (inline in 01-04-T2 verify block) | ✅ | ⬜ pending |
| 01-04-T3 | 01-04 | 3 | OPS-04, SC-2 | T-1-LOG-LEAK-01 | `make run` serves `/` + `/health` end-to-end via ASGI | integration | `uv run pytest tests/integration/test_home.py` (created by 01-05-T2) | ✅ (after 05) | ⬜ pending |
| 01-05-T1 | 01-05 | 4 | TEST-02 | T-1-TEST-FLAKE-01 | conftest fixtures collect cleanly | smoke | `uv run pytest --collect-only -q` | ✅ | ⬜ pending |
| 01-05-T2 | 01-05 | 4 | TEST-02, OPS-04, LLM-03, SC-2, SC-3, SC-4 | T-1-TEST-LEAK-01, T-1-TEST-FLAKE-01, T-1-TEST-ISOLATION-01 | Full Phase 1 suite passes; SC #4 10x gate green; SC #3 persistent gate green | integration | `uv run pytest tests/ -q && uv run pytest tests/integration/test_db_smoke.py --count=10 -q` | ✅ | ⬜ pending |
| 01-06-T1 | 01-06 | 5 | OPS-01, SC-1, SC-4 | T-1-MAKE-SHELL-INJECTION-01 | All 10 Makefile targets declared + dry-run parse; `make check` + `make test-flakes` green | smoke | `make -n install && make -n check && make -n test-flakes && make check && make test-flakes` | ✅ | ⬜ pending |
| 01-06-T2 | 01-06 | 5 | OPS-02, SC-5 (auto portion) | T-1-HOOK-TOOLCHAIN-DRIFT-01 | pre-commit installs; idempotent on clean tree | smoke | `uv run pre-commit install && uv run pre-commit run --all-files` | ✅ | ⬜ pending |
| 01-06-T3 | 01-06 | 5 | OPS-03 | T-1-CI-WORKFLOW-INJECTION-01, T-1-CI-TIMEOUT-01 | CI YAML is well-formed, single job, Python 3.12, uv-cached | smoke | YAML structure grep + `grep -q 'make check' .github/workflows/ci.yml` | ✅ | ⬜ pending |
| 01-06-T4 | 01-06 | 5 | OPS-02, OPS-03, SC-5, SC-6 | T-1-PRECOMMIT-BYPASS-01, T-1-CI-SECRET-01 | Pre-commit blocks violation (manual); CI goes green (manual) | manual | Human checkpoint — see Manual-Only Verifications below | ✅ | ⚠️ manual (one-time) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*File Exists column reflects state after the plan's task commits; tests tagged "after 05" are created in Plan 05 but verify infrastructure written in earlier plans.*

---

## Wave 0 Requirements

All Wave 0 infrastructure is owned by Plan 01 (pyproject.toml + dev
deps) and Plan 05 (test harness). Completion status below is tracked
against the plan files that create the artefact.

- [x] `pyproject.toml` — `[tool.pytest.ini_options]` with `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "session"`, `--strict-markers`, `--cov=app --cov-report=term-missing` → **Plan 01-01 Task 1** (framework install + config)
- [x] `tests/__init__.py` + `tests/unit/__init__.py` + `tests/integration/__init__.py` → **Plan 01-05 Task 1** (package markers)
- [x] `tests/conftest.py` — shared fixtures (`event_loop_policy` session fixture, session-scoped tmp-file async engine, function-scoped session with rollback, `alembic upgrade head` once per session) → **Plan 01-05 Task 1**
- [x] `tests/unit/conftest.py` — unit-only overrides (log-level clamp to WARNING for pristine output per D-17) → **Plan 01-05 Task 1**
- [x] `pytest-repeat` added as a dev-group dep (for SC #4 flake check) → **Plan 01-01 Task 1**
- [x] `make test-flakes` target in Makefile that runs `pytest --count 10 tests/integration/test_db_smoke.py` → **Plan 01-06 Task 1**
- [x] `tests/integration/test_alembic_smoke.py` for SC #3 persistent gate inside `make check` → **Plan 01-05 Task 2**

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Owning Task |
|----------|-------------|------------|-------------------|-------------|
| GitHub Actions CI goes green on push to a fresh branch | OPS-03, SC-6 | CI runs off-host; can only be observed after push | Push the scaffold commit to a throwaway branch, open the Actions tab on GitHub, confirm the `ci` job turns green. Screenshot / link in verification report. | 01-06-T4 |
| Pre-commit hook blocks a ruff violation | OPS-02, SC-5 | Involves making a deliberately-broken commit and observing rejection | Create a `/tmp/bad.py` with a ruff-violating file (e.g., `import os;import sys` on one line), stage it, attempt `git commit`, confirm hook exits non-zero with the ruff error message. | 01-06-T4 |
| `sqlite3 dojo.db .schema` shows `alembic_version` after `make migrate` | SC-3 | Optional developer sanity check (the authoritative automated gate is `tests/integration/test_alembic_smoke.py` — see 01-05-T2) | Run `rm -f dojo.db && make migrate && sqlite3 dojo.db .schema`, confirm output contains `CREATE TABLE alembic_version`. | 01-06-T1 (optional follow-up) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-20
</content>
</invoke>