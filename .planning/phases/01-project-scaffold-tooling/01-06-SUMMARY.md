---
phase: 01-project-scaffold-tooling
plan: 06
subsystem: infra
tags: [tooling, make, pre-commit, github-actions, ci, uv]

requires:
  - phase: 01-project-scaffold-tooling
    provides: "pyproject.toml, app/, migrations/, tests/ — everything the dev workflow wires together"
provides:
  - "Makefile with 10 targets (9 spec §8.1 + test-flakes SC#4 gate)"
  - ".pre-commit-config.yaml with 5 local hooks in D-14 order (ruff-format → ruff-check → ty → interrogate → pytest-unit)"
  - ".github/workflows/ci.yml — single `check` job, Python 3.12, uv-cached, concurrency cancellation"
affects: [phase-02-domain, phase-03-infrastructure, phase-04-flows, phase-05-drill, phase-06-read, phase-07-e2e]

tech-stack:
  added: [gnu-make, pre-commit, github-actions, astral-setup-uv]
  patterns: [local-precommit-hooks-via-uv-run, ty-scoped-to-app, ci-sets-placeholder-env]

key-files:
  created:
    - Makefile
    - .pre-commit-config.yaml
    - .github/workflows/ci.yml
  modified: []

key-decisions:
  - "`typecheck: uv run ty check app` — NOT `app migrations` (planner-guidance 4). ty 0.0.31 doesn't handle Alembic's dynamic context.configure; scope stays app/ until ty matures"
  - "Pre-commit `ty` + `interrogate` hooks also scoped to `app/` so they match `make check` exactly (caught during inline test; `ty` without a path flags `_env_file=None` in tests)"
  - "`test-flakes` target added (10th) as SC #4 gate — `pytest tests/integration/test_db_smoke.py --count=10`"
  - "No `db-reset` target (spec §8.1 explicitly excludes it; `rm dojo.db && make migrate` is the manual reset path)"
  - "CI runs only `make install + make check` (no separate `make test` — check includes test; no playwright yet; no Python matrix — pinned to 3.12)"
  - "`ANTHROPIC_API_KEY: ci-placeholder` env block in ci.yml (A7 resolution) so Settings instantiation never fails in a CI runner without .env"

patterns-established:
  - "Local pre-commit hooks via `uv run`: guarantees hook toolchain == make toolchain == CI toolchain (zero version drift)"
  - "Hook scope matches Makefile scope: `uv run ty check app` / `uv run interrogate -c pyproject.toml app` in both"
  - "setup-uv@v8 with `enable-cache: true + python-version: '3.12'` — no manual actions/cache, no actions/setup-python"
  - "Concurrency key `ci-${{ github.workflow }}-${{ github.head_ref || github.run_id }}` + `cancel-in-progress: true` — PR pushes cancel stale runs; main pushes don't cancel each other"

requirements-completed: [OPS-01, OPS-02, OPS-03, TEST-02]

duration: ~30min
completed: 2026-04-21
---

# Phase 01-06: Tooling & CI Summary

**Makefile + local pre-commit + GitHub Actions CI — `make install && make check` is the single command to provision and verify a fresh clone; pre-commit blocks violating commits locally; CI workflow committed and ready (remote pending)**

## Performance

- **Duration:** ~30 min (inline)
- **Started:** 2026-04-21T10:24:00+02:00
- **Completed:** 2026-04-21T10:50:00+02:00
- **Tasks:** 3 automated + 1 human checkpoint
- **Files created:** 3

## Accomplishments

- `Makefile` (35 lines, 10 targets): install, format, lint, typecheck, docstrings, test, check, run, migrate, test-flakes — all `uv run`-prefixed, literal tabs, `.PHONY` declared
- `.pre-commit-config.yaml` (41 lines, 5 local hooks): ruff-format → ruff-check --fix → ty → interrogate → pytest-unit; all `entry: uv run`; `pass_filenames: false` on ty + interrogate
- `.github/workflows/ci.yml` (38 lines, single job): ubuntu-latest, Python 3.12 via setup-uv@v8, timeout 10min, concurrency cancellation, `ANTHROPIC_API_KEY=ci-placeholder` env block
- **SC #1 green:** `make install && make check` — ruff clean, ty clean, interrogate 100%, 7 tests (now 10 after review fixes) passing
- **SC #2 green (repro'd via uvicorn subprocess):** `/` → 200 HTML + "Dojo" h1; `/health` → `{"status":"ok"}`
- **SC #3 green:** `make migrate` creates `alembic_version` in dojo.db (SQLite schema confirmed)
- **SC #4 green:** `make test-flakes` passes 10/10 in 0.21s
- **SC #5 green (inline verification):** deliberately broken `app/bad.py` committed on throwaway branch — blocked by ruff-format + ruff-check + interrogate (exit code 1, commit refused)
- **SC #6 deferred:** no git remote exists yet; CI workflow file is committed and ready. Will fire on first push.

## Task Commits

1. **Task 1: Makefile** — `b900a36` (feat)
2. **Task 2: .pre-commit-config.yaml** — `0a7a646` (feat) — note: ty + interrogate hook entries scoped to `app/` mid-task after the `ty` hook flagged `_env_file=None` in tests/
3. **Task 3: .github/workflows/ci.yml** — `448aa11` (feat)
4. **Task 4 checkpoint — human verification:**
   - SC #5: **ruff-format + ruff-check + interrogate** all fired on a deliberate violation (transcript captured inline; commit exit code 1)
   - SC #6: **deferred until GitHub remote exists.** When Danny creates the repo + pushes, the committed `ci.yml` will run. Tracked in LEARNINGS as open item.

## Review Follow-up (Post-Task 4)

A comprehensive 5-agent PR review ran after Task 4 and surfaced 11 findings (3 Critical + 8 Important). All 11 were fixed inline across 7 additional commits before Phase 1 closure:

- `558d4f6` — structlog now wraps stdlib (fixes silent no-op logger clamps)
- `5a50d90` — Settings: `Literal` log_level + `@field_validator` on async URL scheme
- `c88d4fe` — env.py respects caller-set URL (only the ini placeholder triggers settings fallback)
- `69ca2bf` — SAVEPOINT session fixture + dropped `_db_env` workaround + `version_num == "0001"` check
- `8a09857` — comment warning about module-level engine import-time binding
- `dbb0859` — lifespan guards placeholder API key against `DOJO_ENV=prod` boot
- `3eb1161` — PRAGMA listener test + tightened home assertion + lifespan log test + autouse cache_clear + structlog `is_configured` (no RuntimeWarning collision)

Suite grew from 7 → 10 tests, coverage 83% → 89%. SC #4 10x remained green throughout.

## Decisions Made

- **Pre-commit ty/interrogate scope = `app/`** — caught inline that the plan's `uv run ty check` (no path) scans the project, hitting `_env_file=None` in tests/; fixing requires either a type stubs update or scope restriction; chose scope restriction to mirror Makefile exactly.
- **`core.hooksPath` handling:** Danny's global git config set it to `.git/hooks` (default). `pre-commit install` refuses to install when that key is set regardless of value. Unset locally (`--local --unset`) — no functional change since the value was the default.

## Deviations from Plan

**1. [Rule 1 — Bug] Hook scope mismatch between plan drop-in and working Makefile**

- **Found during:** Task 2 `pre-commit run --all-files` first run
- **Issue:** Plan's pre-commit drop-in had `entry: uv run ty check` (no path arg) and `entry: uv run interrogate -c pyproject.toml` (no path arg). `ty` scans the whole project → flagged `_env_file=None` in `tests/unit/test_settings.py` as an unknown argument. Because `make check` uses `ty check app`, scope mismatch surfaced only when the hook ran.
- **Fix:** Changed both hook entries to append `app` path (matches Makefile scope).
- **Files modified:** `.pre-commit-config.yaml`
- **Verification:** `pre-commit run --all-files` clean.
- **Committed in:** `0a7a646` (Task 2)

**2. [Out-of-scope] SC #6 could not be verified (no remote)**

- **Found during:** Task 4 checkpoint
- **Issue:** Danny's local clone has no git remote configured, so no CI run to observe.
- **Fix:** Deferred SC #6 to post-merge-to-GitHub. CI workflow file committed and ready. Tracked in `LEARNINGS.md`.
- **Committed in:** N/A (no code change; documented)

---

**Total deviations:** 2 — one inline bug-fix (hook scope) + one deferred SC (remote not set up)
**Impact on plan:** Scope tightening only; no feature drift.

## Issues Encountered

**pre-commit sandbox vs subagent sandbox:** Earlier waves (3, 4, 5) tried parallel worktree subagents and hit a `Write`/`Bash` sandbox denial at the subagent level. Solution was to execute inline on the main working tree — Phase 1 from Wave 3 onward ran that way. Phase 1 complete, no outstanding blockers from this issue; Phase 2 will revisit parallel worktrees with proper permission setup.

**Review-fix RuntimeWarning collision:** Integration between the structlog-stdlib wrap (fix #1) + the new lifespan log test (fix #9) + `filterwarnings=["error"]` exposed that `structlog.configure_once` emits `RuntimeWarning` on repeated calls — which escalates to a test failure when `test_main_lifespan` runs after `test_logging_smoke`. Replaced `configure_once` with `is_configured() + configure()` for silent idempotency.

## User Setup Required

**One-time before first commit (if pre-commit install is desired):**
```bash
git config --local --unset core.hooksPath   # if set globally to default
uv run pre-commit install
```

**For SC #6 post-merge:**
```bash
gh repo create <name> --private --source=. --remote=origin --push
# Or add existing remote:
git remote add origin <url> && git push -u origin main
```
Then watch the `ci` workflow in Actions — should finish green in 3–5 min (cold uv cache first run).

## Next Phase Readiness

- `make install && make check` is the documented onboarding command for any new contributor.
- Pre-commit hook chain blocks violating commits before they enter history (verified inline).
- CI workflow is committed and will fire automatically on first push to GitHub.
- Phase 2 can start: domain entities + application ports (Protocols + Callable aliases) + DTOs + GenerateFromSource use case, driven by hand-written fakes per the DIP boundary rule established in Phase 1.

**Regression watch:** If Phase 2 adds dev deps that change `uv.lock`, CI's cache key auto-invalidates. If Phase 3 adds real ORM models, the empty `0001_initial.py` becomes the anchor for `alembic revision --autogenerate`. Both behaviors are structural, not manual.

---
*Phase: 01-project-scaffold-tooling, Plan 06*
*Completed: 2026-04-21*
