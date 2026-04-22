---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Phase 2 Wave 3 — plan 03 (hand-written fakes) landed; ready to open PR
last_updated: "2026-04-22T11:17:00.000Z"
last_activity: 2026-04-22 -- Phase 2 Plan 03 (hand-written fakes) complete on phase-02-plan-03-hand-written-fakes
progress:
  total_phases: 7
  completed_phases: 1
  total_plans: 6
  completed_plans: 9
  percent: 20
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-18)

**Core value:** Generate Q&A cards from user-supplied source material, drill them interactively, retain knowledge. The generate → drill → learn loop must work even if everything else fails.
**Current focus:** Phase 2 — Domain & Application Spine (executing, Wave 3)

## Current Position

Phase: 2 of 7 — executing
Plan: 3 of 5 complete — hand-written fakes landed on branch phase-02-plan-03-hand-written-fakes; awaiting PR merge before Plan 04 begins
Status: Plan 02-03 delivered 6 hand-written fakes under tests/fakes/ (FakeLLMProvider, FakeSourceRepository, FakeNoteRepository, FakeCardRepository, FakeCardReviewRepository, FakeDraftStore with force_expire TTL hook) + re-export __init__.py + 7 unit-test files (23 tests) including a structural-subtype smoke test. Structural subtyping only (no Protocol inheritance, no @runtime_checkable); zero Mock() usage; public-attribute assertion style (.saved/.puts/.calls_with/.next_response). make check clean (76 tests, 96% coverage); closes Phase 2 SC #4 + DRAFT-01 + TEST-01.
Last activity: 2026-04-22 -- Plan 02-03 complete; SUMMARY.md + STATE + ROADMAP updated

Progress: [██░░░░░░░░] 20%

## Performance Metrics

**Velocity:**

- Total plans completed: 9 (6 Phase 1 + 3 Phase 2)
- Average duration: ~16 min (Phase 2 portion)
- Total execution time: ~48 min (Phase 2 portion)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 2     | 3     | ~48m  | ~16 min  |

**Recent Trend:**

- Last 5 plans: Phase 2 Plan 01 (domain entities), Phase 2 Plan 02 (application ports + DTOs), Phase 2 Plan 03 (hand-written fakes)
- Trend: on-plan; one Rule-3 deviation on Plan 03 (plan test-skeletons used obsolete NoteDTO(content=...) + Source without display_name; every test fixture corrected to Plan 01/02 actual signatures before first pytest run); RED+GREEN merged per fake per project commit convention (six commits total)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Pre-roadmap: `DraftStore` is a first-class Protocol port in `app/application/ports.py`; concrete `InMemoryDraftStore` in infrastructure
- Pre-roadmap: `tenacity` for LLM retry/backoff (not hand-rolled); one retry layer, not stacked with SDK default
- Pre-roadmap: `structlog` configured at app startup; per-module `get_logger(__name__)`
- Pre-roadmap: `nh3` sanitizes LLM-generated markdown rendered as HTML (Read mode, drill Q&A)
- Pre-roadmap: Spec at `docs/superpowers/specs/2026-04-18-dojo-design.md` is authoritative; PROJECT.md is distilled
- Pre-roadmap: Drafts in-memory only; DB writes only on explicit user save
- Pre-roadmap: Hand-written fakes at DIP boundaries, no `Mock()` behavior-testing
- 02-01: Commit convention override — merge RED+GREEN per unit of behavior (pytest-unit pre-commit hook blocks RED-only commits that import unbuilt modules); TDD discipline lives in the dev loop, not in commit granularity
- 02-01: Ship `DojoError` alone at the domain layer (YAGNI); named subclasses (InvalidEntity etc.) land when a caller needs to branch on error type
- 02-01: `CardReview.is_correct` is an `@property` derived from `Rating.CORRECT` (not a stored bool) to eliminate computed-vs-stored drift
- 02-01: **Validation lives at boundary layers, not in domain entities.** `__post_init__` invariants were pulled after PR #4 convergent review → invariant bloat. Domain entities are pure typed data containers; validation is in Pydantic DTOs (LLM boundary), use cases (external-input boundary), and ORM mappers / DB constraints (storage boundary). `_require_nonempty`, `_require_tz_aware`, `_validate_tags` helpers removed
- 02-02: Application DTOs ARE the trust boundary — `NoteDTO`, `CardDTO`, `GeneratedContent` Pydantic models carry `ConfigDict(extra="ignore")` + `Field(min_length=1)` on every required string and on the `cards` list (closes PITFALL M6). Stdlib frozen dataclasses `GenerateRequest`/`GenerateResponse`/`DraftBundle` are internal and carry no validation
- 02-02: PEP 695 `type X = Y` syntax adopted for `UrlFetcher` + `SourceReader` Callable aliases (ruff UP040 autofix requires it on Python 3.12+); the older `X: TypeAlias = Y` form is retired across the project
- 02-02: Circular `ports.py ↔ dtos.py` import broken via `if TYPE_CHECKING:` guards on both sides; both modules use `from __future__ import annotations` so the cross-module type references never resolve at runtime
- 02-02: `GeneratedContent` Pydantic envelope added as the LLM tool-use deserialisation target (note + cards with `min_length=1`); Phase 3's Anthropic adapter will unpack it to match `LLMProvider.generate_note_and_cards`'s `tuple[NoteDTO, list[CardDTO]]` return shape
- 02-03: Hand-written fakes at every DIP boundary use structural subtyping — no inheritance from Protocol, no `@runtime_checkable`. `grep -E "class Fake[A-Z][a-zA-Z]+\("` returns empty across `tests/fakes/`. Drift is caught by `test_fakes_are_assignable_to_their_protocols` (ty type-checks annotated assignments `llm: LLMProvider = FakeLLMProvider()`) + Plan 05's TEST-03 contract harness.
- 02-03: Assertion style is public-attribute state (`.saved`, `.puts`, `.calls_with`, `.next_response`), NOT Mock().assert_called_with. Zero `unittest.mock` imports anywhere under `tests/fakes/` or `tests/unit/fakes/`. `FakeLLMProvider.next_response` is mutable so tests simulate failure modes (malformed output, empty cards) by pre-seeding — no Mock.side_effect needed.
- 02-03: `force_expire(token)` TTL test hook lives on `FakeDraftStore`, NOT on the `DraftStore` Protocol (D-05). Port surface stays clean (`put` + `pop` only); tests that need the expiry path call `force_expire` instead of advancing wall-clock. Phase 3's `InMemoryDraftStore` will own real TTL logic + `asyncio.Lock`.
- 02-03: Shared dict-by-id shape across `FakeSourceRepository` / `FakeNoteRepository` / `FakeCardRepository` was NOT extracted to a `_BaseDictRepository[K, V]` superclass — YAGNI, each fake ≤24 lines, shared base would save ~10 lines at the cost of one more layer of indirection when a reader scans for single-fake behavior.

### Pending Todos

None yet.

### Blockers/Concerns

Phase-entry gates to address in their assigned phase (from PITFALLS.md):

- Phase 1: C4 async Alembic scaffold + M8 pytest-asyncio event-loop — must be verified green before any business code
- Phase 2: M7 fake drift — TEST-03 contract tests scaffolded here and extended as each new port/adapter pair arrives
- Phase 3: C10 draft-store race conditions (atomic pop, asyncio.Lock, lazy TTL); C6/C7 LLM schema validation and retry stacking
- Phase 5: M3 drill slide-off animation timing — prototype early in phase, do not defer to polish

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-04-22T11:17:00.000Z
Stopped at: Phase 2 Plan 03 complete on phase-02-plan-03-hand-written-fakes; push + open PR, then start Plan 04 (GenerateFromSource use case)
Resume file: .planning/phases/02-domain-application-spine/02-04-generate-from-source-use-case-PLAN.md
