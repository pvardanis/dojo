---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Phase 2 Wave 2 (plans 02+03 parallel) — plan 02 landed; ready to open PR
last_updated: "2026-04-22T10:52:53.000Z"
last_activity: 2026-04-22 -- Phase 2 Plan 02 (application ports & DTOs) complete on phase-02-plan-02-application-ports-dtos
progress:
  total_phases: 7
  completed_phases: 1
  total_plans: 6
  completed_plans: 8
  percent: 18
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-18)

**Core value:** Generate Q&A cards from user-supplied source material, drill them interactively, retain knowledge. The generate → drill → learn loop must work even if everything else fails.
**Current focus:** Phase 2 — Domain & Application Spine (executing, Wave 2)

## Current Position

Phase: 2 of 7 — executing
Plan: 2 of 5 complete — application ports + DTOs + exceptions landed on branch phase-02-plan-02-application-ports-dtos; awaiting PR merge before Plan 03 begins
Status: Plan 02-02 delivered 6 typing.Protocol ports + 2 PEP 695 Callable aliases + DraftToken NewType + NoteDTO/CardDTO/GeneratedContent Pydantic DTOs + 3 stdlib frozen use-case dataclasses + 3 DojoError-derived app exceptions. 22/22 new application unit tests green (55/55 overall); make check clean; inward-only imports verified.
Last activity: 2026-04-22 -- Plan 02-02 complete; SUMMARY.md + STATE + ROADMAP updated

Progress: [██░░░░░░░░] 18%

## Performance Metrics

**Velocity:**

- Total plans completed: 8 (6 Phase 1 + 2 Phase 2)
- Average duration: ~15 min (Phase 2 portion)
- Total execution time: ~30 min (Phase 2 portion)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 2     | 2     | ~30m  | ~15 min  |

**Recent Trend:**

- Last 5 plans: Phase 2 Plan 01 (domain entities), Phase 2 Plan 02 (application ports + DTOs)
- Trend: on-plan; two Rule-1/3 tooling deviations on Plan 02 (ruff UP040 → PEP 695 `type` keyword; test_dtos.py split at 100-line ceiling); all auto-fixed within the execution window

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

Last session: 2026-04-22T10:52:53.000Z
Stopped at: Phase 2 Plan 02 complete on phase-02-plan-02-application-ports-dtos; push + open PR, then start Plan 03 (hand-written fakes)
Resume file: .planning/phases/02-domain-application-spine/02-03-hand-written-fakes-PLAN.md
