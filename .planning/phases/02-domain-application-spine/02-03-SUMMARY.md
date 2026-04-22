---
phase: 02-domain-application-spine
plan: 03
subsystem: test-infrastructure
tags:
  - fakes
  - test-infrastructure
  - structural-subtyping
  - tdd
  - dip-boundary

requires:
  - phase: 02-domain-application-spine
    plan: 01
    provides: "Domain entities (Source/Note/Card/CardReview), value objects (SourceKind/Rating StrEnums + 4 typed-ID NewTypes)"
  - phase: 02-domain-application-spine
    plan: 02
    provides: "6 typing.Protocol ports + 2 PEP 695 Callable aliases + DraftToken + NoteDTO/CardDTO/DraftBundle"
provides:
  - "tests/fakes/__init__.py: re-export surface for all 6 fakes via __all__"
  - "tests/fakes/fake_llm_provider.py: hand-written LLMProvider fake with .calls_with + .next_response public state"
  - "tests/fakes/fake_source_repository.py: dict-backed SourceRepository fake keyed by SourceId"
  - "tests/fakes/fake_note_repository.py: dict-backed NoteRepository fake keyed by NoteId (regenerate-overwrites)"
  - "tests/fakes/fake_card_repository.py: dict-backed CardRepository fake keyed by CardId"
  - "tests/fakes/fake_card_review_repository.py: list-backed CardReviewRepository fake (append-only log)"
  - "tests/fakes/fake_draft_store.py: dict-backed DraftStore fake with atomic pop + force_expire(token) TTL test hook"
  - "tests/unit/fakes/: 23 unit tests across 7 files covering every fake + structural-subtype smoke"
affects:
  - 02-04-generate-from-source-use-case
  - 02-05-contract-harness-import-linter
  - 03-infrastructure-adapters
  - 04-generate-review-save-flow

tech-stack:
  added: []
  patterns:
    - "Structural subtyping against typing.Protocol (no inheritance, no @runtime_checkable)"
    - "Public-attribute assertion style: fake.saved / fake.puts / fake.calls_with / fake.next_response — no Mock().assert_called_with"
    - "Dict-backed CRUD fakes for Source/Note/Card repositories"
    - "List-backed append-only fake for CardReviewRepository"
    - "force_expire(token) TTL test hook lives on FakeDraftStore, NOT the Protocol (D-05 keeps port surface clean)"
    - "Mutable next_response override + calls_with recorder on FakeLLMProvider (failure-mode simulation without Mock)"
    - "Per-test fake instantiation (no session-scoped fake fixtures) — each test owns its own state"

key-files:
  created:
    - tests/fakes/__init__.py
    - tests/fakes/fake_llm_provider.py
    - tests/fakes/fake_source_repository.py
    - tests/fakes/fake_note_repository.py
    - tests/fakes/fake_card_repository.py
    - tests/fakes/fake_card_review_repository.py
    - tests/fakes/fake_draft_store.py
    - tests/unit/fakes/__init__.py
    - tests/unit/fakes/test_fake_llm_provider.py
    - tests/unit/fakes/test_fake_source_repository.py
    - tests/unit/fakes/test_fake_note_repository.py
    - tests/unit/fakes/test_fake_card_repository.py
    - tests/unit/fakes/test_fake_card_review_repository.py
    - tests/unit/fakes/test_fake_draft_store.py
    - tests/unit/fakes/test_structural_subtype.py
  modified: []

key-decisions:
  - "Kept RED+GREEN merged per fake, per Plan 02-01/02 commit-convention override. The pytest-unit pre-commit hook blocks any RED-only commit that imports an unbuilt module, so splitting RED from GREEN would force --no-verify usage. TDD discipline lives in the dev loop (write test → run pytest → see red → write impl → rerun → see green), not in commit granularity."
  - "Aligned all test bodies with Plan 01 + Plan 02's actual types: NoteDTO requires title + content_md (not the plan-skeleton's content); Source requires display_name. The plan-skeleton's NoteDTO(content='n') and Source(kind=..., user_prompt=...) calls would have ValidationError'd / TypeError'd. Rule 3 (blocking issue) fix: every test uses the real entity/DTO signatures from Plans 01 + 02."
  - "tests/fakes/__init__.py shipped with the full __all__ re-export list in Task 3, landing a single file mutation over the Task-1 marker-only stub. The plan's two-phase landing (marker in Task 1 → re-exports in Task 3) is preserved."
  - "FakeSourceRepository, FakeNoteRepository, FakeCardRepository all share the identical dict-by-id shape. Resisted the urge to extract a `_BaseDictRepository[K, V]` superclass — YAGNI, and each fake's file-size is ≤24 lines where the shared base would save ~10 lines at the cost of one more layer of indirection when a reader is scanning for a single fake's behavior."
  - "Annotated-assignment structural-subtype test (test_fakes_are_assignable_to_their_protocols) validates at **ty type-check time** — the runtime pass is `assert llm is not None`. The load-bearing assertion is that ty accepts `llm: LLMProvider = FakeLLMProvider()`; if any fake drifts from its Protocol, `ty check` fails and make check fails."

patterns-established:
  - "Hand-written fake shape: plain class, __init__ seeds public state, methods mutate public state + delegate to internal storage when needed (FakeDraftStore's _store vs. .puts)"
  - "No inheritance from Protocol — structural subtyping is the contract"
  - "Public-attribute state > call-pattern mocks (fake.saved, fake.puts, fake.calls_with, fake.next_response)"
  - "Configurable failure modes via pre-seeded override hooks (next_response), not Mock.side_effect"
  - "Fake files live under tests/fakes/; unit tests for fakes live under tests/unit/fakes/ (parallel hierarchy)"

requirements-completed:
  - DRAFT-01
  - TEST-01

# Metrics
duration: ~18min
completed: 2026-04-22
---

# Phase 2 Plan 03: Hand-Written Fakes Summary

**Seven hand-written fakes delivered — one per Plan 02-02 application port — each a structural subtype of its Protocol, each exposing assertable state as public attributes, each exercised by per-fake unit tests plus a cross-cutting structural-subtype smoke test. 23 fake unit tests green; make check clean end-to-end; zero `Mock()` usage anywhere. Closes Phase 2 SC #4 and discharges DRAFT-01 + TEST-01.**

## What Landed

### Six fakes under `tests/fakes/`

| File | Port | State Shape | LOC |
|------|------|-------------|-----|
| `fake_llm_provider.py` | `LLMProvider` | `.calls_with: list[tuple[str\|None, str]]` + mutable `.next_response` | 26 |
| `fake_source_repository.py` | `SourceRepository` | `.saved: dict[SourceId, Source]` | 24 |
| `fake_note_repository.py` | `NoteRepository` | `.saved: dict[NoteId, Note]` | 24 |
| `fake_card_repository.py` | `CardRepository` | `.saved: dict[CardId, Card]` | 24 |
| `fake_card_review_repository.py` | `CardReviewRepository` | `.saved: list[CardReview]` (append-only) | 19 |
| `fake_draft_store.py` | `DraftStore` | `.puts: list[tuple[DraftToken, DraftBundle]]` + `force_expire(token)` hook | 30 |

All six use structural subtyping (no `class FakeX(Port):` inheritance, no `@runtime_checkable`). All six expose state as public attributes assertable directly by tests. None imports from `unittest.mock`.

### Re-export surface

`tests/fakes/__init__.py` — re-exports every fake with an `__all__` list so downstream tests (Plan 04's use-case test; Plan 05's contract harness) do `from tests.fakes import FakeLLMProvider, FakeDraftStore, ...`.

### Seven unit-test files under `tests/unit/fakes/`

| File | Tests | Coverage |
|------|-------|----------|
| `test_fake_llm_provider.py` | 4 | default canned response, .calls_with log, .next_response override, return-shape assertion |
| `test_fake_source_repository.py` | 4 | round-trip, missing→None, .saved dict exposure, same-id overwrite |
| `test_fake_note_repository.py` | 3 | round-trip, missing→None, overwrite-by-note-id |
| `test_fake_card_repository.py` | 3 | round-trip, missing→None, overwrite-by-card-id |
| `test_fake_card_review_repository.py` | 2 | append-order preservation, list-not-dict type assertion |
| `test_fake_draft_store.py` | 5 | put→pop round-trip, atomic read-and-delete, missing→None, .puts log, force_expire |
| `test_structural_subtype.py` | 2 | hasattr runtime checks + type-check-time annotated-assignment Protocol conformance |

**Total: 23 fake unit tests, all passing.**

## TDD Log

RED+GREEN merged per fake, per Plan 02-01/02 commit-convention override. Each commit lands a fake + its unit tests together; the pytest-unit pre-commit hook enforces GREEN on every commit. Dev-loop discipline is:

1. Write the test file using the target fake module path
2. Run `uv run pytest <test>` → see `ModuleNotFoundError` (RED)
3. Write the fake
4. Run `uv run pytest <test>` → see green
5. Run `uv run ruff format` + `uv run ruff check` locally
6. `git add <paired files>` + `git commit` (hooks re-verify GREEN)

| Cycle | Fake | Commit | Tests | LOC |
|-------|------|--------|-------|-----|
| 1 | FakeDraftStore + FakeLLMProvider | `c6ddf23` | 5 + 4 | 56 (impl) + 94 (tests) |
| 2-A | FakeSourceRepository | `d4f313a` | 4 | 24 + 62 |
| 2-B | FakeNoteRepository | `43dea89` | 3 | 24 + 45 |
| 2-C | FakeCardRepository | `0a61b2d` | 3 | 24 + 44 |
| 2-D | FakeCardReviewRepository | `df63879` | 2 | 19 + 36 |
| 3 | Re-exports + structural-subtype smoke | `d1b0c64` | 2 | 22 (init) + 52 (test) |

**Six commits total on branch `phase-02-plan-03-hand-written-fakes`.**

## Verification

```
$ uv run pytest tests/unit/fakes/ -v
... 23 passed in 0.19s

$ make check
... 76 passed in 0.96s (96% coverage)

$ grep -rE "(unittest\.mock|Mock\(|MagicMock|AsyncMock)" tests/fakes/ tests/unit/fakes/ | grep -v "# ABOUTME"
(empty — the only 'Mock' match is the "No Mock()" line in the ABOUTME banner)

$ grep -E "class Fake[A-Z][a-zA-Z]+\(" tests/fakes/*.py
(empty — no Protocol inheritance)

$ grep -rE "\.(saved|puts|calls_with|next_response)" tests/fakes/ tests/unit/fakes/ | wc -l
51  (proves the public-attribute assertion style is used throughout)

$ uv run python -c "from tests.fakes import FakeLLMProvider, FakeSourceRepository, FakeNoteRepository, FakeCardRepository, FakeCardReviewRepository, FakeDraftStore; print('ok')"
ok
```

## Deviations from Plan

**1. [Rule 3 - Blocking] Aligned test bodies with real Plan 01 + Plan 02 types**

- **Found during:** Task 1 setup (reading existing `app/application/dtos.py` + `app/domain/entities.py`)
- **Issue:** The plan's RED-test skeletons called `NoteDTO(content="n")` and `Source(kind=SourceKind.TOPIC, user_prompt="p")`. The actual DTO/entity shapes (locked by Plan 02-02 Summary and 02-01 Summary) require `NoteDTO(title=..., content_md=...)` and `Source(kind=..., user_prompt=..., display_name=...)`. Using the plan skeletons as-written would have produced `ValidationError` / `TypeError` at construction — the tests would fail for the wrong reason (bad fixture), never reaching the assertions they're meant to drive.
- **Fix:** Every test fixture uses the real field names (title/content_md, display_name). `_sample_bundle()` in `test_fake_draft_store.py` builds `NoteDTO(title="t", content_md="body")`. Test helpers like `_make_source()` in `test_fake_source_repository.py` include `display_name="test topic"`.
- **Files modified:** all 6 fake test files + structural-subtype test (test helpers only)
- **Commits:** spread across `c6ddf23` (Task 1), `d4f313a` / `43dea89` / `0a61b2d` / `df63879` (Task 2).

**2. [Plan convention override] RED+GREEN merged per fake**

- **Per `<critical_project_conventions>` in the plan prompt:** pytest-unit pre-commit hook runs the full unit suite, so a RED-only commit that imports an unbuilt fake module would fail the hook. Plan 02-01 + 02-02 already overrode the standard TDD commit convention to merge RED+GREEN per unit. Plan 02-03's PLAN.md text still showed separate `test(...)` + `feat(...)` commits per fake for historical clarity — in execution, per the convention override, every commit in this plan is a single `feat(...)` (or `test(...)` for Task 3's pure-test delta) that lands the fake + its tests together.
- **Net effect:** 6 commits instead of the plan's projected ~10. All acceptance criteria still met — the hooks independently verify GREEN on every commit.
- **Not a Rule deviation**, just a convention the plan prompt already spelled out.

No Rule 1, Rule 2, or Rule 4 deviations.

## Authentication Gates

None — this plan is pure test-code synthesis; no external services touched.

## Phase 2 SC #4 Coverage

| Criterion | How discharged |
|-----------|----------------|
| "Fakes live under `tests/fakes/`" | 7 files (1 marker + 6 fakes) under `tests/fakes/` |
| "Implement each Protocol by structural subtyping" | `grep -E "class Fake[A-Z][a-zA-Z]+\(" tests/fakes/*.py` returns empty |
| "Expose assertable state (not call patterns)" | Every fake has a public `.saved` / `.puts` / `.calls_with` / `.next_response` attribute; 51 `.attr` assertion hits across the test files |
| "Exercised by unit tests that use no `Mock()` behavior-testing" | 23 fake unit tests; zero `Mock()` / `MagicMock` / `AsyncMock` imports anywhere (verified via grep) |

## Self-Check: PASSED

**Files created (verified via `ls`):**
- [x] `tests/fakes/__init__.py`
- [x] `tests/fakes/fake_llm_provider.py`
- [x] `tests/fakes/fake_source_repository.py`
- [x] `tests/fakes/fake_note_repository.py`
- [x] `tests/fakes/fake_card_repository.py`
- [x] `tests/fakes/fake_card_review_repository.py`
- [x] `tests/fakes/fake_draft_store.py`
- [x] `tests/unit/fakes/__init__.py`
- [x] `tests/unit/fakes/test_fake_llm_provider.py`
- [x] `tests/unit/fakes/test_fake_source_repository.py`
- [x] `tests/unit/fakes/test_fake_note_repository.py`
- [x] `tests/unit/fakes/test_fake_card_repository.py`
- [x] `tests/unit/fakes/test_fake_card_review_repository.py`
- [x] `tests/unit/fakes/test_fake_draft_store.py`
- [x] `tests/unit/fakes/test_structural_subtype.py`

**Commits verified (via `git log`):**
- [x] `c6ddf23` feat(02-03): add FakeDraftStore and FakeLLMProvider
- [x] `d4f313a` feat(02-03): add FakeSourceRepository
- [x] `43dea89` feat(02-03): add FakeNoteRepository
- [x] `0a61b2d` feat(02-03): add FakeCardRepository
- [x] `df63879` feat(02-03): add FakeCardReviewRepository
- [x] `d1b0c64` test(02-03): add re-exports + structural-subtype smoke tests
