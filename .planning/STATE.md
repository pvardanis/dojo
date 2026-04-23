---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Phase 2 complete — all 5 plans shipped; ready to plan Phase 3 (Infrastructure Adapters)
last_updated: "2026-04-23T12:26:00.000Z"
last_activity: 2026-04-23 -- Phase 2 Plan 05 (contract harness + import-linter) complete on phase-02-plan-05-contract-harness-import-linter; Phase 2 closed
progress:
  total_phases: 7
  completed_phases: 2
  total_plans: 5
  completed_plans: 11
  percent: 28
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-18)

**Core value:** Generate Q&A cards from user-supplied source material, drill them interactively, retain knowledge. The generate → drill → learn loop must work even if everything else fails.
**Current focus:** Phase 2 closed; Phase 3 — Infrastructure Adapters is next (planning not yet started)

## Current Position

Phase: 2 of 7 — complete
Plan: 5 of 5 complete — Plan 05 landed on branch phase-02-plan-05-contract-harness-import-linter; Phase 2 closed
Status: Plan 02-05 delivered tests/contract/__init__.py (3 LOC) + tests/contract/test_llm_provider_contract.py (38 LOC) — TEST-03 harness parameterised over ["fake", "anthropic"] with double-gate (RUN_LLM_TESTS + pytest.importorskip on app.infrastructure.llm.anthropic_provider); anthropic leg auto-skips cleanly in Phase 2 whether RUN_LLM_TESTS is set or not. pyproject.toml gained import-linter>=2.0 + [tool.importlinter] with two forbidden contracts (app.domain and app.application must not import app.infrastructure or app.web). Makefile lint: target extended to two lines (ruff + lint-imports). Negative-path proof captured (deliberate boundary violation made lint-imports exit non-zero, reverted without commit). make check: 94 passed, 1 skipped, 97% coverage, 2.48s end-to-end. Discharges Phase 2 SC #5 + SC #6 and TEST-03; closes Phase-1 LEARNINGS open item "Phase-2 boundary lint".
Last activity: 2026-04-23 -- Plan 02-05 complete; SUMMARY.md + STATE + ROADMAP + REQUIREMENTS updated; Phase 1 LEARNINGS open item closed

Progress: [███░░░░░░░] 28%

## Performance Metrics

**Velocity:**

- Total plans completed: 11 (6 Phase 1 + 5 Phase 2)
- Average duration: ~12 min (Phase 2 portion)
- Total execution time: ~55 min (Phase 2 portion)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 2     | 5     | ~55m  | ~11 min  |

**Recent Trend:**

- Last 5 plans: Phase 2 Plan 01 (domain entities), Phase 2 Plan 02 (application ports + DTOs), Phase 2 Plan 03 (hand-written fakes), Phase 2 Plan 04 (GenerateFromSource use case), Phase 2 Plan 05 (contract harness + import-linter)
- Trend: on-plan; Plan 05 landed in ~4 min with zero Rule deviations and zero pre-commit retries. Both tasks' acceptance criteria passed first try; make check end-to-end 2.48s. Closed Phase 2 in full — all 6 SC satisfied, 3 requirements discharged (DRAFT-01, TEST-01, TEST-03), Phase-1 LEARNINGS open item "Phase-2 boundary lint" closed.

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
- 02-04: `GenerateFromSource.__init__` takes `llm: LLMProvider` and `draft_store: DraftStore` only — NOT the four repository ports. The Phase 2 `execute()` path only touches those two ports and RESEARCH §3.8 Green bullet is explicit ("if not used by execute() they're omitted until needed"). Phase 4 extends `__init__` when Save wiring arrives; extending the signature later is a one-line change at the composition root.
- 02-04: Kind-coherence validation lives in the use case's `execute()`, not in `GenerateRequest` or the domain. `GenerateRequest` is a plain frozen stdlib dataclass with no `__post_init__`; `execute()` is the first boundary that sees `request.kind` + `request.input` together, making it the right place to enforce the TOPIC-has-no-input and FILE/URL-must-go-through-real-adapters rules. Per the 02-01 "validation at boundary layers" decision. Phase 4 replaces the FILE/URL raises with real `SourceReader` / `UrlFetcher` calls.
- 02-04: Per-kind dispatch is a two-branch `if` (TOPIC vs. `raise UnsupportedSourceKind`), NOT a strategy table. RESEARCH §3.8 Refactor is explicit that pre-designing a dispatch as a strategy table is YAGNI — the current shape extends cleanly when Phase 4 replaces the raise with FILE + URL branches.
- 02-04: `test_generate_from_source.py` was split into `test_generate_topic.py` (4 TOPIC-path tests, 75 LOC) + `test_generate_unsupported.py` (3 raise-path tests, 62 LOC) per the PATTERNS.md sizing flag — the plan explicitly flagged 100 LOC as the ceiling and provided the target filenames. Split is along a natural behavioral seam (happy-path vs. raise-path).

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

Last session: 2026-04-22T11:42:00.000Z
Stopped at: Phase 2 Plan 04 complete on phase-02-plan-04-generate-from-source-use-case; push + open PR, then start Plan 05 (TEST-03 contract harness + import-linter boundary enforcement)
Resume file: .planning/phases/02-domain-application-spine/02-05-contract-harness-import-linter-PLAN.md
