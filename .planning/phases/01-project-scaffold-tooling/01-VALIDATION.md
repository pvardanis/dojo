---
phase: 1
slug: project-scaffold-tooling
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-20
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
| **Estimated runtime** | ~15 seconds (unit only); ~30-45 seconds (full `make check` with empty suite) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit/ -x --ff`
- **After every plan wave:** Run `make check`
- **Before `/gsd-verify-work`:** `make check` must be green AND SC #4 (`pytest --count 10 tests/integration/test_db_smoke.py`) must pass
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

*To be filled by the planner during plan generation. Each plan task must map to an automated command from the RESEARCH.md drop-in snippets, or to a Wave 0 infrastructure task.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | OPS-01 | — | `make` targets exist and run | smoke | `make -n check` exits 0 | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | OPS-02 | — | pre-commit installed, blocks violations | smoke | `pre-commit run --all-files` exits 0 on clean tree | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | OPS-03 | — | CI runs `make check` on push/PR | manual | Push a test branch, confirm CI green on actions tab | ❌ W0 | ⚠️ manual (one-time) |
| TBD | TBD | 0 | OPS-04 | — | structlog configured, `get_logger(__name__)` available | unit | `uv run pytest tests/unit/test_logging_config.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | TEST-02 | — | `make check` exits 0 on clean scaffold | smoke | `make check` exits 0 | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | LLM-03 | T-1-LLM03 | `ANTHROPIC_API_KEY` loads via pydantic-settings; never leaks from settings | unit | `uv run pytest tests/unit/test_settings.py::test_anthropic_key_loaded_from_env` | ❌ W0 | ⬜ pending |
| TBD | TBD | 1 | SC-4 | — | First integration test passes 10x in a row (event-loop stability) | integration | `uv run pytest --count 10 tests/integration/test_db_smoke.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | 1 | SC-3 | — | `alembic upgrade head` creates `alembic_version` on fresh tmp DB | integration | `uv run pytest tests/integration/test_alembic_smoke.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | 1 | SC-2 | — | `make run` → `/` returns 200 with Jinja-rendered HTML; `/health` returns `{"status": "ok"}` | integration | `uv run pytest tests/integration/test_routes_smoke.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — `[tool.pytest.ini_options]` with `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "session"`, `--strict-markers`, `--cov=app --cov-report=term-missing` (framework install + config)
- [ ] `tests/__init__.py` + `tests/unit/__init__.py` + `tests/integration/__init__.py` — package markers
- [ ] `tests/conftest.py` — shared fixtures (`event_loop_policy` session fixture, session-scoped tmp-file async engine, function-scoped session with rollback, `alembic upgrade head` once per session)
- [ ] `tests/unit/conftest.py` — unit-only overrides (log-level clamp to WARNING for pristine output per D-17)
- [ ] Add `pytest-repeat` as a dev-group dep (for SC #4 flake check)
- [ ] `make test-flakes` target in Makefile that runs `pytest --count 10 tests/integration/test_db_smoke.py`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GitHub Actions CI goes green on push to a fresh branch | OPS-03, SC-6 | CI runs off-host; can only be observed after push | Push the scaffold commit to a throwaway branch, open the Actions tab on GitHub, confirm the `ci` job turns green. Screenshot / link in verification report. |
| Pre-commit hook blocks a ruff violation | OPS-02, SC-5 | Involves making a deliberately-broken commit and observing rejection | Create a `/tmp/bad.py` with a ruff-violating file (e.g., `import os;import sys` on one line), stage it, attempt `git commit`, confirm hook exits non-zero with the ruff error message. |
| `sqlite3 dojo.db .schema` shows `alembic_version` after `make migrate` | SC-3 | Requires shelling out to `sqlite3` binary, cross-platform installation varies | Run `rm -f dojo.db && make migrate && sqlite3 dojo.db .schema`, confirm output contains `CREATE TABLE alembic_version`. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
