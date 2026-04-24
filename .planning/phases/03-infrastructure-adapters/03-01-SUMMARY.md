---
phase: 03-infrastructure-adapters
plan: 01
subsystem: infra
tags: [python, dependencies, exceptions, anthropic, tenacity, trafilatura, httpx, respx]

# Dependency graph
requires:
  - phase: 02-domain-application-spine
    provides: "DojoError base in app/domain/exceptions.py; application-layer exceptions.py scaffold with 4 existing DojoError subclasses"
provides:
  - runtime deps anthropic, tenacity, trafilatura (promoted httpx) available to app.infrastructure.* at import time
  - dev dep respx available to integration tests that stub httpx calls
  - 9 new DojoError subclasses in app.application.exceptions (5 LLM-* + 4 Source-*) that Plans 02-05 raise and callers catch
affects: [03-infrastructure-adapters, 04-generate-flow, 05-persistence-routes]

# Tech tracking
tech-stack:
  added: [anthropic>=0.97, tenacity>=9.1, trafilatura>=2.0, respx>=0.23]
  patterns:
    - "Exception types live in the layer that defines their meaning (RESEARCH R4) — LLM + Source wrap targets in app.application.exceptions, not app.infrastructure"
    - "Marker-only DojoError subclasses — no __init__, no state; validation lives at trust boundaries per Phase 2 convention"

key-files:
  created: []
  modified:
    - pyproject.toml — 4 new runtime deps, httpx moved dev→runtime, respx added to dev
    - uv.lock — refreshed lockfile includes anthropic, tenacity, trafilatura, respx
    - app/application/exceptions.py — extended from 29 to 64 lines with 9 new DojoError subclasses

key-decisions:
  - "RESEARCH R3 discharged: httpx moved from [dependency-groups].dev to [project].dependencies because the URL fetcher imports it at runtime (Plan 03)"
  - "RESEARCH R4 discharged: all 9 new exception types live in app/application/exceptions.py — consistent with the existing 4-class file — per DDD principle that exception types belong to the layer that defines their meaning"
  - "Exception classes are pure marker classes (no __init__, no fields) per Phase 2 'validation at boundaries' convention — message content comes from adapter raise sites, not invariants baked into the type"

patterns-established:
  - "Per-plan dependency promotion: touch pyproject.toml + uv.lock in a single chore(03-NN) commit; import-check the new names before moving on"
  - "Extending app/application/exceptions.py: append classes after the last existing one, preserve 2-blank-line PEP 8 spacing, keep one-line docstrings (pydoclint skip-checking-short-docstrings covers them), no new ABOUTME headers"

requirements-completed: [LLM-01, LLM-02, GEN-02, PERSIST-02]

# Metrics
duration: 3min
completed: 2026-04-24
---

# Phase 3 Plan 01: Dependencies + Application Exception Types Summary

**Promotes anthropic, tenacity, trafilatura to runtime deps (plus httpx dev→runtime), adds respx to dev, and extends app.application.exceptions with 9 DojoError subclasses (5 LLM + 4 Source wrap targets) that Plans 02-05 will raise and catch.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-24T11:24:51Z
- **Completed:** 2026-04-24T11:27:20Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Four runtime dependencies live in the project environment (anthropic 0.97.0, tenacity 9.1.4, trafilatura 2.0.0, httpx 0.28.1), unblocking Plans 02-05.
- One dev dependency (respx 0.23.1) available for integration tests that stub httpx.
- `app/application/exceptions.py` now carries the full 13-class DojoError taxonomy the rest of Phase 3 needs — 5 LLM-* + 4 Source-* + the 4 pre-existing types.
- `make check` stays green end-to-end (94 tests pass, 1 skipped for opt-in Anthropic contract leg; ruff/ty/interrogate/pydoclint/import-linter all clean).
- RESEARCH entries R3 (httpx promotion) and R4 (exception-type ownership) discharged with PATTERNS-level guidance baked into this plan.

## Task Commits

Each task was committed atomically on the worktree branch:

1. **Task 1: Promote runtime deps + add respx to dev group** — `6da28de` (chore)
2. **Task 2: Extend app/application/exceptions.py with 9 new DojoError subclasses** — `ad86da2` (feat)

_Plan metadata commit (this SUMMARY.md) follows as `docs(03-01)`._

## Files Created/Modified

- `pyproject.toml` — added `anthropic>=0.97`, `httpx>=0.28`, `tenacity>=9.1`, `trafilatura>=2.0` to `[project].dependencies`; removed `httpx>=0.28` from `[dependency-groups].dev`; added `respx>=0.23` to `[dependency-groups].dev`.
- `uv.lock` — regenerated via `uv sync` so the four new packages and their transitive deps are locked (anthropic pulled in `jiti` / `distro` / `hpack` etc.; trafilatura pulled in `lxml`, `justext`, `tld`; full diff captured in the commit).
- `app/application/exceptions.py` — appended 9 new `DojoError` subclasses in this order: `LLMRateLimited`, `LLMAuthFailed`, `LLMUnreachable`, `LLMContextTooLarge`, `LLMInvalidRequest`, `SourceNotFound`, `SourceUnreadable`, `SourceFetchFailed`, `SourceNotArticle`. File grew from 29 → 64 lines (under 75-line plan ceiling, under 100-line CLAUDE.md ceiling). ABOUTME header count stays at 2.

## Decisions Made

No new decisions — R3 and R4 were already locked in RESEARCH; this plan is their mechanical discharge. No deviations from PLAN text. One alignment check: the four new runtime deps were inserted **alphabetically** (anthropic / httpx / tenacity / trafilatura) immediately after `alembic>=1.13` as the PLAN action instructs — this choice breaks the existing file's loose web→db→logging grouping but matches the PLAN's explicit "ordered alphabetically after `alembic`" instruction and keeps the structlog entry unchanged at the end of the list.

## Deviations from Plan

None — plan executed exactly as written. Task 3 ("open PR") was adapted to worktree mode per the parallel-executor system prompt: the SUMMARY.md was created and committed on the worktree branch with `--no-verify` (pre-commit hook contention avoidance), and the PR itself will be opened centrally by the orchestrator after all worktree agents in Wave 1 complete. No branch-creation / `git push` / `gh pr create` was run from this agent.

## Issues Encountered

None. First-try pass on every verification step:

- `uv sync` resolved 88 packages, audited 86 (including the new anthropic / tenacity / trafilatura / respx transitively) without conflict.
- `uv run python -c "import anthropic, tenacity, trafilatura, httpx, respx"` exited 0.
- `uv run python -c "from app.application.exceptions import ..."` confirmed all 9 new types importable and each `issubclass(DojoError)`.
- `uv run make check` green: ruff format + ruff check + import-linter (3 contracts kept) + ty + interrogate + pydoclint + pytest (94 passed, 1 skipped, coverage 97%).
- `filterwarnings = ["error"]` in pytest config stayed silent — none of the new deps emit import-time warnings under our current test surface. (Phase 3 adapter plans that actually *use* these deps may hit DeprecationWarnings and need targeted ignores; this plan only imports them at verify time.)

No auto-fix attempts; no Rule 1/2/3 deviations. Task 3 adaptation (worktree mode, no PR here) is documented above, not a deviation.

## User Setup Required

None — all new deps resolve from PyPI and are locked. `ANTHROPIC_API_KEY` is still optional (RUN_LLM_TESTS gate from Phase 2 D-11 unchanged). `uv sync` on a clean clone picks up the new lockfile without further action.

## Next Phase Readiness

**Wave 1 co-executor** (Plan 03-02, URL/FILE source extractors) can now import `httpx`, `trafilatura`, `SourceNotFound`, `SourceUnreadable`, `SourceFetchFailed`, `SourceNotArticle` directly — this plan's commits are visible on the Wave 1 feature branch once the orchestrator merges both worktrees.

**Wave 2** (Plans 03-03 SQL repositories + 03-04 Anthropic provider):
- 03-03 inherits `app/infrastructure/db/session.py` (live since Phase 1), will extend with models + mappers + four `Sql*Repository` classes. No new deps required beyond SQLAlchemy (already locked).
- 03-04 can now import `anthropic`, `tenacity`, and catch-raise the 5 LLM-* exception types. Retry + wrap pattern (CONTEXT.md D-03 / D-03a / D-03b) has all its named domain types available.

**Wave 3** (Plan 03-05 composition root): no new deps — wires all adapters together.

**No blockers, no concerns.** Pure prep plan; runtime behavior is unchanged until downstream plans start importing the new deps and raising the new exception types.

## TDD Gate Compliance

Plan 03-01 is `type: execute` (not `type: tdd`) — no RED/GREEN gate applies. Task 2 is explicitly `tdd="false"` per PLAN frontmatter because pure marker exception classes have no behavior to test (Phase 2's `tests/unit/application/test_exceptions.py` already covers `DojoError`-subclass instantiation generically via the 4 existing types — no new test required for these 9). The plan's stated coverage gate is `make check`, which ran green.

## Self-Check: PASSED

Verification commands run after SUMMARY.md was written:

- `test -f .planning/phases/03-infrastructure-adapters/03-01-SUMMARY.md` → FOUND
- `grep -c "^name = \"anthropic\"" uv.lock` → 1 (FOUND)
- `grep -c "^name = \"tenacity\"" uv.lock` → 1 (FOUND)
- `grep -c "^name = \"trafilatura\"" uv.lock` → 1 (FOUND)
- `grep -c "^name = \"respx\"" uv.lock` → 1 (FOUND)
- `grep -c "^class LLMRateLimited(DojoError):" app/application/exceptions.py` → 1 (FOUND) — and identical 1 for each of the 8 other new classes.
- Commit `6da28de` (Task 1) present in `git log` (FOUND)
- Commit `ad86da2` (Task 2) present in `git log` (FOUND)
- `uv run make check` → green (FOUND)

---
*Phase: 03-infrastructure-adapters*
*Completed: 2026-04-24*
