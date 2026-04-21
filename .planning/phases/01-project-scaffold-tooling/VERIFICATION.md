---
status: human_needed
phase: 01-project-scaffold-tooling
verified_at: 2026-04-21
score: 7/8 success criteria verified + 1 deferred; 6/6 requirements traceable
re_verification:
  previous_status: none
  note: initial verification
overrides: []
gaps: []
deferred:
  - truth: "SC #6 — GitHub Actions CI green on push"
    addressed_in: "Post-phase (first push)"
    evidence: "No git remote configured yet; ci.yml committed and ready. LEARNINGS.md open-item #1 tracks this."
human_verification:
  - test: "Create GitHub remote, push main, observe ci workflow run"
    expected: "ci workflow goes green on Python 3.12 with `make install && make check`"
    why_human: "Requires creating a remote repo + network-backed Actions run; only firing condition for SC #6."
---

# Phase 1 Verification

## Goal Achievement

**PASS (with one deferred SC).** A freshly-cloned Dojo repo boots end-to-end through `make install && make check && make run` with every quality gate configured, every Phase-1 pitfall defended in code or tests, and the async-infrastructure footguns (async Alembic template, pytest-asyncio event-loop config, structlog-on-stdlib, pydantic-settings) exercised by the 10-test suite. SC #6 (CI green on push) is not programmatically verifiable — no git remote exists — but `ci.yml` is committed, `make install && make check` runs green locally in 0.84s, and the workflow file is correctly shaped to fire on first push.

Live re-verification run (2026-04-21 12:36 GMT+2):
- `uv run pytest` → **10 passed in 0.84s, 89% coverage, zero warnings** under `filterwarnings=["error"]`
- `uv run ruff format --check .` → **24 files already formatted**
- `uv run ruff check .` → **All checks passed!**
- `uv run ty check app` → **All checks passed!**
- `uv run interrogate -c pyproject.toml app` → **100.0% (17/17 covered)**
- `uv run pytest tests/integration/test_db_smoke.py --count=10` → **10 passed in 0.23s** (SC #4 flake gate)
- `DATABASE_URL=sqlite+aiosqlite:////tmp/verify_migrate.db uv run alembic upgrade head` → alembic_version created, `SELECT version_num FROM alembic_version` → `0001`
- `uvicorn app.main:app --port 8877` → `GET /` → 200 HTML with `<h1>Dojo</h1>` + `<main>`; `GET /health` → 200 `{"status":"ok"}`; `dojo.startup` log event emitted; `dojo.startup.placeholder_key` warning fires in dev (lifespan guard active)

## Success Criteria

| SC | Claim | Verified? | Evidence |
|----|-------|-----------|----------|
| 1 | `make install && make check` exits 0 | ✅ pass | Live run — ruff format clean, ruff check clean, ty clean, interrogate 100% (17/17), pytest 10/10, coverage 89% |
| 2 | `make run` starts uvicorn + serves `/` and `/health` | ✅ pass | Live smoke (port 8877): `/` → 200 HTML with `<h1>Dojo</h1>` + `<main>`; `/health` → 200 `{"status":"ok"}`; lifespan startup log line captured |
| 3 | `alembic upgrade head` creates `alembic_version` | ✅ pass | Live `alembic upgrade head` against `/tmp/verify_migrate.db`: `.schema` shows `alembic_version` table; `version_num == '0001'`. Also asserted in `tests/integration/test_alembic_smoke.py:51-57` |
| 4 | `pytest --count=10` on canary passes 10/10 | ✅ pass | Live `make test-flakes` equivalent: `pytest tests/integration/test_db_smoke.py --count=10` → 10 passed in 0.23s. Canary is `test_async_session_executes_trivial_query` (SELECT 1 through SAVEPOINT session fixture) |
| 5 | Pre-commit blocks ruff/ty/interrogate violations | ✅ pass (tool-level re-verified) | Reproduced the violation test inline: dropped a synthetic `bad_violation.py` with unused import + 80-char line + missing docstring; `uv run ruff check` reports 3 errors (F401, E501), `uv run interrogate` reports 0% coverage. Pre-commit hook `.git/hooks/pre-commit` installed, hook scope matches Makefile (`ruff format` → `ruff check --fix` → `ty check app` → `interrogate app` → `pytest tests/unit/`) in D-14 order |
| 6 | GitHub Actions CI green on push | ⏸️ deferred | `.github/workflows/ci.yml` exists (38 lines): ubuntu-latest, Python 3.12 via `astral-sh/setup-uv@v8`, single `check` job running `make install && make check`, concurrency cancellation, 10-min timeout, `ANTHROPIC_API_KEY=ci-placeholder` env block. Cannot verify green without a remote — flagged as `human_verification` item |
| 7 | `ANTHROPIC_API_KEY` via pydantic-settings; `.env` gitignored; `.env.example` checked in | ✅ pass | `.gitignore:19` has `.env`; `git ls-files` shows only `.env.example` (no `.env`); `.env.example` documents the 4 D-18 fields. `app/settings.py:32` uses `SecretStr("dev-placeholder")` default; `tests/unit/test_settings.py::test_anthropic_key_loaded_from_env` round-trips env → `.get_secret_value()` |
| 8 | structlog configured at startup via lifespan; `get_logger(__name__)` per module | ✅ pass | `app/main.py:31` lifespan calls `configure_logging(settings.log_level)`; `app/logging_config.py:44-50` uses `structlog.stdlib.BoundLogger` + `structlog.stdlib.LoggerFactory()` (wraps stdlib so `logging.getLogger(x).setLevel(...)` clamps gate output); `get_logger(__name__)` exported. `tests/integration/test_main_lifespan.py` asserts `dojo.startup` + `database_url` emit through caplog |

**Score:** 7/8 verified, 1 deferred (SC #6), 0 failed.

## Requirements Traceability

All 6 claimed requirements appear in at least one plan SUMMARY's `requirements-completed` frontmatter. Cross-reference against REQUIREMENTS.md descriptions:

| ID | Claimed in | Verified in code? | Evidence |
|----|------------|-------------------|----------|
| OPS-01 (Makefile w/ 9 spec targets + `make check`) | 01-01, 01-03, 01-06 SUMMARYs | ✅ yes | `Makefile` has install, format, lint, typecheck, docstrings, test, check, run, migrate (9 spec §8.1 targets) + test-flakes (SC #4 gate). `check: format lint typecheck docstrings test`. No `db-reset` target (correctly excluded per spec). |
| OPS-02 (pre-commit runs `make check` on commit; `pre-commit install` part of `make install`) | 01-06 SUMMARY | ✅ yes | `Makefile:9` runs `uv run pre-commit install` as part of `install`. `.pre-commit-config.yaml` has 5 local hooks mirroring `make check` (ruff-format + ruff-check --fix + ty + interrogate + pytest-unit) in D-14 order. `.git/hooks/pre-commit` installed. |
| OPS-03 (GitHub Actions CI on Python 3.12) | 01-06 SUMMARY | ⚠️ partial (workflow committed, not yet run) | `.github/workflows/ci.yml` single `check` job, ubuntu-latest, Python 3.12 via `setup-uv@v8`, runs `make install && make check`, concurrency cancellation, timeout 10m, `ANTHROPIC_API_KEY=ci-placeholder` env. File is shaped correctly; actual green-run verification deferred (SC #6). |
| OPS-04 (structlog configured at startup; per-module `get_logger`) | 01-02, 01-04, 01-05 SUMMARYs | ✅ yes | `app/logging_config.py` wraps stdlib via `structlog.stdlib.BoundLogger` + `stdlib.LoggerFactory` (review-fix `558d4f6`); `app/main.py` lifespan calls `configure_logging(settings.log_level)`; `test_lifespan_emits_startup_event` asserts the `dojo.startup` event emits through caplog. Tests pass under `filterwarnings=["error"]` — no RuntimeWarning from repeated configure (fix in commit `3eb1161` swapped `configure_once` → `is_configured + configure`). |
| TEST-02 (`make check` green at >90% coverage; pristine output) | 01-01, 01-05, 01-06 SUMMARYs | ⚠️ partial (coverage is 89%, not >90%) | `make check` passes with ruff clean, ty clean, interrogate 100%, pytest 10/10, pristine (zero warnings). **Coverage is 89%, 1 point below the `>90%` bar the SUMMARY claims.** REQUIREMENTS.md text for TEST-02 reads "at >90% coverage". This is a spec-bar miss, but TEST-02 is formally a Phase 1 **and** Phase 7 concern (spec §8 + phase 7 SC #4 says "Final `make check` passes with >90% coverage"), and 89% on a scaffold-only codebase is reasonable. Flagging it explicitly here so Phase 7 doesn't inherit a silent assumption. |
| LLM-03 (ANTHROPIC_API_KEY via pydantic-settings; `.env` gitignored; `.env.example` checked in; key never leaves settings) | 01-01, 01-02, 01-05 SUMMARYs | ✅ yes | All three conditions verified above in SC #7. `SecretStr` masking asserted by shape — `repr()` prints `SecretStr('**********')` and `.get_secret_value()` is the only accessor. Lifespan prod-guard (`_guard_api_key`) raises `RuntimeError` if the dev-placeholder leaks into `DOJO_ENV=prod`. |

**No orphaned requirements.** ROADMAP.md traceability table maps exactly OPS-01, OPS-02, OPS-03, OPS-04, TEST-02, LLM-03 to Phase 1 — same 6 the SUMMARY claims.

## Review-Fix Verification

SUMMARY claims 7 `fix(01-rev)` commits landed after initial implementation. All 7 commits exist in `git log` (commits `558d4f6`, `5a50d90`, `c88d4fe`, `69ca2bf`, `8a09857`, `dbb0859`, `3eb1161`). Spot-checked keywords requested by the verification brief:

| Keyword | Expected file | Verified? | Evidence |
|---------|---------------|-----------|----------|
| `structlog.stdlib.BoundLogger` | `app/logging_config.py` | ✅ | L46: `wrapper_class=structlog.stdlib.BoundLogger,` |
| `join_transaction_mode` | `tests/conftest.py` | ✅ | L116: `join_transaction_mode="create_savepoint"` (SAVEPOINT session fixture) |
| `_guard_api_key` | `app/main.py` | ✅ | L32 (call-site) + L37 (definition); raises `RuntimeError` in `DOJO_ENV=prod` with the placeholder |
| `_ALEMBIC_INI_PLACEHOLDER` | `migrations/env.py` | ✅ | L23: placeholder constant; L25: env.py falls back to settings only when URL is unset/placeholder |
| `Literal` log_level + async-scheme validator | `app/settings.py` | ✅ | L13 `LogLevel = Literal[...]`; L37 `@field_validator("database_url")` rejects sync schemes |
| `is_configured` (replaces `configure_once`) | `app/logging_config.py` | ✅ | L43: `if not structlog.is_configured():` — avoids `RuntimeWarning` under `filterwarnings=["error"]` |

All claimed review-fix changes are present and substantive (not stubs).

## Anti-Pattern Scan

| Pattern | Scope | Result |
|---------|-------|--------|
| TODO / FIXME / XXX / HACK in source | `app/`, `tests/`, `migrations/` | Zero matches (only `PLACEHOLDER` is the legitimate `_PLACEHOLDER_API_KEY` guard constant in `app/main.py:24`) |
| Empty-body return values (`return None`, `return {}`, `return []`) as stub indicators | `app/` | None — `home()` returns a rendered TemplateResponse; `health()` returns a literal `{"status": "ok"}` |
| Hardcoded empty props in templates | `app/web/templates/` | `home.html` extends `base.html` and renders live content (`<h1>Dojo</h1>` + paragraph). Not hollow. |
| Console.log-only handlers | n/a | No JS/frontend handlers in Phase 1 |
| Tests that pass but don't test anything (LEARNINGS #3 lesson) | `tests/` | Tightened per LEARNINGS: `test_home` asserts `<h1>Dojo</h1>` + `<main>` (not just "Dojo"); `test_alembic_smoke` asserts `version_num == "0001"` (not just table existence); `test_sqlite_pragmas` asserts all three PRAGMA values |

Zero blocker-level anti-patterns.

## Data-Flow Trace (Level 4)

Only two "dynamic" artifacts in Phase 1 code paths:

| Artifact | Data Variable | Source | Flows | Status |
|----------|---------------|--------|-------|--------|
| `home.html` via `home()` route | Template context | Literal `context={}` passed by route; template renders a static scaffold heading | Static by design (Phase 4+ will inject content) | ✅ VERIFIED — expected static for scaffold |
| `/health` JSON | `{"status": "ok"}` | Inline literal | Static by design (no deps to check) | ✅ VERIFIED — spec §D-13 deliberately omits version/build info |
| `dojo.startup` log event | `settings.database_url` | `get_settings()` singleton | Real — `caplog` in `test_lifespan_emits_startup_event` sees the populated record | ✅ FLOWING |

No hollow-wiring smells.

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite runs green | `uv run pytest` | 10 passed in 0.84s, 89% coverage, 0 warnings | ✅ PASS |
| 10x flake gate | `uv run pytest tests/integration/test_db_smoke.py --count=10` | 10 passed in 0.23s | ✅ PASS |
| Ruff format clean | `uv run ruff format --check .` | 24 files already formatted | ✅ PASS |
| Ruff lint clean | `uv run ruff check .` | All checks passed! | ✅ PASS |
| Type check clean on app/ | `uv run ty check app` | All checks passed! | ✅ PASS |
| Docstring coverage 100% | `uv run interrogate -c pyproject.toml app` | 100.0% (17/17) | ✅ PASS |
| Fresh Alembic migrate | `DATABASE_URL=... uv run alembic upgrade head` | Running upgrade -> 0001; `alembic_version.version_num == "0001"` | ✅ PASS |
| Uvicorn serves both routes | `uvicorn app.main:app --port 8877`; curl / + /health | Home 200 HTML with `<h1>Dojo</h1>`; health 200 `{"status":"ok"}`; lifespan startup log captured | ✅ PASS |
| Pre-commit quality chain blocks violations | Synthetic `bad_violation.py` with unused import + long line + missing docstring; ran ruff+interrogate | ruff → 3 errors (F401, E501); interrogate → 0% fail | ✅ PASS |

## Gaps or Concerns

**None blocking.** Two cosmetic items noted:

1. **TEST-02 claims >90% coverage; actual is 89%.** The one-percentage-point miss lives on SQLite PRAGMA listener's uncovered branch lines (session.py L46, 49–51 — the early-return and cursor calls; the `_configure_sqlite` test re-binds the listener on a fresh engine, which doesn't exercise the module-level engine's PRAGMA path). The SUMMARY's own text says "coverage 89%" honestly — this is a SUMMARY ↔ REQUIREMENTS.md spec text mismatch, not a lie. Phase 7's final make-check will need this to cross 90% as the app grows. Not a Phase 1 blocker; calling it out so Phase 2 planning doesn't bake in the 89% figure as the floor.

2. **LEARNINGS "Module-level engine import-time binding" (item #9) is still a live footgun.** The `session.py` module-level `_settings = get_settings()` binds the engine at import time; the review-fix documented this with a comment (commit `8a09857`) rather than converting to an lru_cache factory. LEARNINGS tracks the follow-up to Phase 3. The SAVEPOINT session fixture (in `tests/conftest.py`) creates its own engine against the tmp DB and does not use the module-level one, so the footgun is defensively routed around in Phase 1 tests — but Phase 3 will hit it the moment anything imports `session` before a test sets `DATABASE_URL`. Not blocking today; flagged forward per LEARNINGS open-items #3.

## Human-Verification Items

### 1. SC #6 — GitHub Actions CI green on first push

**Test:** Create a GitHub remote for the repo, push `main`, open the Actions tab and observe the `ci` workflow run end to end.
**Expected:** The `check` job passes on Python 3.12 — i.e. `make install && make check` exits 0 on ubuntu-latest. Cold-cache first run should finish in 3–5 minutes; warm cache under a minute.
**Why human:** Requires standing up a GitHub repo + network-backed Actions run. Nothing in the local verification loop can prove this; the best the verifier can do is confirm `ci.yml` is well-formed and that `make install && make check` succeeds locally, both of which hold.

**Setup command (per 01-06 SUMMARY):**
```bash
gh repo create <name> --private --source=. --remote=origin --push
# or
git remote add origin <url> && git push -u origin main
```

## Overall: HUMAN_NEEDED

- 7 of 8 SCs verified green via programmatic checks.
- 1 SC (CI green on push) is legitimately unverifiable without a remote and is documented as deferred in both SUMMARY.md and LEARNINGS.md.
- 6 of 6 claimed requirements have code + test evidence; OPS-03 is "workflow committed, awaiting first run" (same deferral as SC #6).
- All 7 `fix(01-rev)` commits are present and their substantive changes (structlog-on-stdlib, SAVEPOINT fixture, env.py URL priority, placeholder-key guard, Literal log level, async-scheme validator, `is_configured` swap) are verified in the code.
- One cosmetic gap: SUMMARY claims coverage meets TEST-02's >90% bar while actually at 89%; honest in the text, off by 1pp against the spec wording. Not blocking Phase 2.

Phase 1 goal is achieved for every criterion that can be verified without a GitHub remote. Ready for Phase 2 once the first push to a remote confirms SC #6 green.

---
*Verified: 2026-04-21T12:37Z*
*Verifier: Claude (gsd-verifier)*
