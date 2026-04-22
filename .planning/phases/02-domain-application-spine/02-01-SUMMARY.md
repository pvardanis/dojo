---
phase: 02-domain-application-spine
plan: 01
subsystem: domain
tags:
  - dataclasses
  - frozen
  - newtype
  - uuid
  - enum
  - stdlib
  - tdd

requires:
  - phase: 01-project-scaffold-tooling
    provides: "uv package-mode install, pre-commit (ruff + ty + interrogate + pytest-unit), pytest-asyncio, Phase 1 ABOUTME and docstring conventions"
provides:
  - "app/domain/value_objects.py: SourceKind + Rating enums; SourceId/NoteId/CardId/ReviewId NewType aliases over uuid.UUID"
  - "app/domain/entities.py: Source, Note, Card, CardReview frozen dataclasses with default_factory-minted IDs and __post_init__ invariants"
  - "app/domain/exceptions.py: DojoError base class (root of domain + application exception hierarchy)"
  - "tests/unit/domain/: 22 stdlib-only unit tests covering enums, typed IDs, entity invariants, frozen semantics, and is_correct derivation"
  - "_require_nonempty helper in entities.py (private, docstring'd) shared across Source/Note/Card __post_init__"
affects:
  - 02-02-application-ports-dtos
  - 02-03-hand-written-fakes
  - 02-04-generate-from-source-use-case
  - 02-05-contract-harness-import-linter
  - 03-infrastructure-adapters
  - 04-generate-review-save-flow

tech-stack:
  added: []
  patterns:
    - "Frozen stdlib dataclasses with __post_init__ invariant validation (bare ValueError)"
    - "NewType over uuid.UUID for typed IDs at zero runtime cost (D-01)"
    - "IDs minted by the constructor via field(default_factory=lambda: XId(uuid.uuid4())) (D-02)"
    - "Shared _require_nonempty(value, field_name) helper for empty-string invariants"
    - "is_correct as @property derived from Rating enum (no stored/computed drift)"
    - "Single DojoError root for the whole exception hierarchy"

key-files:
  created:
    - app/domain/__init__.py
    - app/domain/value_objects.py
    - app/domain/entities.py
    - app/domain/exceptions.py
    - tests/unit/domain/__init__.py
    - tests/unit/domain/test_value_objects.py
    - tests/unit/domain/test_exceptions.py
    - tests/unit/domain/test_source.py
    - tests/unit/domain/test_note.py
    - tests/unit/domain/test_card.py
    - tests/unit/domain/test_card_review.py
  modified: []

key-decisions:
  - "Merged RED+GREEN per entity into single commits (project-wide override from this plan): pytest-unit pre-commit hook blocks RED-only commits, so TDD discipline lives in the dev loop and atomic commits are per unit of behavior"
  - "Added _require_nonempty helper upfront in the first entity commit (Source) rather than as a later refactor: known shared invariant across three entities, so the YAGNI waiting cost was zero and it eliminated an otherwise-required refactor commit"
  - "Shipped DojoError alone (no InvalidEntity subclass): YAGNI per CONTEXT Claude's discretion — bare ValueError is sufficient for __post_init__ empty-string checks at this phase; domain exceptions gain subclasses when a real call-site needs to branch on the error type"
  - "tags on Card is tuple[str, ...] = () not list: tuples are hashable and frozen-dataclass-safe (RESEARCH §3.3)"
  - "CardReview.is_correct is a @property returning self.rating is Rating.CORRECT — not a stored field — removing any computed-vs-stored drift risk"

patterns-established:
  - "Two-line # ABOUTME: header + one-line module docstring + from __future__ import annotations on every non-marker source/test file"
  - "One-line docstrings on every public class, method, and property (interrogate 100% preserved)"
  - "pytest file layout: one entity per test file; tests are function-scoped with typed signatures and no fixtures for pure unit tests"
  - "Stdlib-only domain layer: imports limited to __future__, uuid, dataclasses, datetime, enum, typing, and intra-layer app.domain.*"

requirements-completed:
  - TEST-01

# Metrics
duration: ~25min
completed: 2026-04-22
---

# Phase 2 Plan 01: Domain Entities Summary

**Four frozen stdlib dataclasses (Source, Note, Card, CardReview) with NewType-UUID typed IDs, SourceKind/Rating enums, and DojoError root exception — delivered test-first with 22 unit tests and zero third-party imports.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-04-22T09:20:00Z
- **Completed:** 2026-04-22T09:45:00Z
- **Tasks:** 3 (per plan) → executed as 7 atomic commits per the commit-convention override
- **Files created:** 11

## Accomplishments

- Pure-stdlib domain layer: `app/domain/` imports only `__future__`, `uuid`, `dataclasses`, `datetime`, `enum`, `typing` (verified by grep; import-linter in Plan 05 will prove it at CI level)
- Four frozen dataclasses with constructor-time ID minting: no `Optional[SourceId]`, no "unsaved" state (D-02)
- Shared `_require_nonempty(value, field_name)` helper keeps `__post_init__` for Source/Note/Card uniform and drops duplicate code
- `CardReview.is_correct` derives from `Rating.CORRECT` via `@property` — no stored-vs-computed drift
- 22/22 domain unit tests green; 100% coverage on all three new domain modules
- `make check` green end-to-end (32 tests pass; ruff clean; ty clean; interrogate 100%)

## Task Commits

Per the commit-convention override in the execution context (merged RED+GREEN for commit atomicity per unit of behavior, because the pre-commit `pytest-unit` hook blocks RED-only commits that import unbuilt modules), commits are per-entity rather than per-TDD-phase:

1. **Scaffold packages** — `6254794` (`chore(02-01): scaffold app/domain/ and tests/unit/domain/ packages`)
2. **Value objects + typed IDs** — `b513ab4` (`feat(02-01): add typed IDs, SourceKind, Rating value objects (TDD)`)
3. **DojoError base exception** — `22fc8d8` (`feat(02-01): add DojoError base exception (TDD)`)
4. **Source entity** — `b70c6e2` (`feat(02-01): add Source entity (TDD)`)
5. **Note entity** — `6d7f836` (`feat(02-01): add Note entity (TDD)`)
6. **Card entity** — `3c95886` (`feat(02-01): add Card entity (TDD)`)
7. **CardReview entity** — `5524332` (`feat(02-01): add CardReview entity (TDD)`)

**Plan metadata commit:** forthcoming (adds this SUMMARY.md + STATE.md + ROADMAP.md update).

## TDD Log

Per the override, RED-commit proof is replaced with this in-commit proof-of-process. For every entity and every value-object/exception module, the tests were written and executed locally **before** the implementation file existed, then re-executed after the implementation landed. The observed failure modes and pass counts were:

| Unit | RED failure observed | GREEN result |
|------|----------------------|--------------|
| `value_objects.py` | `ModuleNotFoundError: No module named 'app.domain.value_objects'` on test collection | 3/3 tests passed |
| `exceptions.py` | `ModuleNotFoundError: No module named 'app.domain.exceptions'` on test collection | 1/1 test passed |
| `entities.Source` | `ModuleNotFoundError: No module named 'app.domain.entities'` on test collection | 5/5 tests passed |
| `entities.Note` | `ImportError: cannot import name 'Note' from 'app.domain.entities'` | 4/4 tests passed |
| `entities.Card` | `ImportError: cannot import name 'Card' from 'app.domain.entities'` | 5/5 tests passed |
| `entities.CardReview` | `ImportError: cannot import name 'CardReview' from 'app.domain.entities'` | 4/4 tests passed |

TDD discipline lived in the dev loop: write-test → run-pytest-fail → write-impl → run-pytest-pass → stage-all → commit. The `pytest-unit` pre-commit hook (which re-runs `pytest tests/unit/ -x --ff` on every commit that touches Python) then independently re-verified the GREEN state at commit time.

## Files Created/Modified

| File | Lines | Purpose |
|------|-------|---------|
| `app/domain/__init__.py` | 3 | Domain package marker (ABOUTME + one-line docstring; no re-exports per D-11) |
| `app/domain/value_objects.py` | 30 | `SourceKind` + `Rating` enums; four `*Id` NewType aliases over `uuid.UUID` |
| `app/domain/entities.py` | 85 | `Source`, `Note`, `Card`, `CardReview` frozen dataclasses + `_require_nonempty` helper |
| `app/domain/exceptions.py` | 9 | `DojoError(Exception)` base class — root of domain + application hierarchy |
| `tests/unit/domain/__init__.py` | 3 | Test-package marker |
| `tests/unit/domain/test_value_objects.py` | 39 | 3 tests: enum membership + NewType-over-UUID smoke |
| `tests/unit/domain/test_exceptions.py` | 17 | 1 test: DojoError subclass-of-Exception + message round-trip |
| `tests/unit/domain/test_source.py` | 44 | 5 tests: empty/whitespace prompt rejection, unique IDs, default input=None, frozen |
| `tests/unit/domain/test_note.py` | 46 | 4 tests: empty content rejection, source_id association, unique IDs, frozen |
| `tests/unit/domain/test_card.py` | 50 | 5 tests: empty question/answer rejection, default tags=(), source_id, frozen |
| `tests/unit/domain/test_card_review.py` | 50 | 4 tests: rating+time record, is_correct derivation, card_id, frozen |

All 11 files start with the two-line `# ABOUTME:` header; every public symbol carries a one-line docstring.

## Decisions Made

1. **Merged RED+GREEN per entity into a single commit** — see `tdd_commit_convention_override` in the execution context. Danny's resolution of the prior-attempt checkpoint. TDD discipline stays in the dev loop; atomic commits become per unit of behavior. The "TDD Log" table above is the proof-of-process substitute for the RED-commit git-log pattern.
2. **`_require_nonempty` helper landed in the first entity commit** — not refactored later. Three of four entities need it, so the YAGNI waiting cost is zero and I avoid a separate `refactor(02-01):` commit.
3. **Shipped `DojoError` alone, no `InvalidEntity`** — CONTEXT Claude's discretion explicitly allows MVP-only-base. Bare `ValueError` in `__post_init__` is sufficient at this phase; named domain exceptions land when a caller needs to branch on type.
4. **`Card.tags` is `tuple[str, ...] = ()` not `list[str] = []`** — hashability + frozen-dataclass safety (RESEARCH §3.3).
5. **`CardReview.is_correct` is a `@property`, not a stored `bool` field** — RESEARCH §3.4; removes the stored-vs-computed drift risk.

## Deviations from Plan

None from the plan's **technical** content. The one procedural deviation is explicitly mandated by the execution context:

- **Commit convention** — the plan's per-task `test(02-01): add failing tests for ...` RED-only commits were merged with their follow-up `feat(02-01):` GREEN commits, per the `tdd_commit_convention_override` in the execution prompt (Danny's locked decision). Plan acceptance criteria that regex-matched those split commit messages were explicitly waived by the override. All other acceptance criteria (file existence, file contents, pytest green, ruff clean, ty clean, interrogate 100%, ABOUTME headers, stdlib-only imports, entities.py ≤100 lines, ≥20 tests) are satisfied.

**Total deviations:** 0 technical; 1 procedural (pre-authorized by override).
**Impact on plan:** None. Every success criterion is satisfied.

## Issues Encountered

- **Ruff auto-formatter reflowed a multi-line `field(...)` call to one line** on the first Source commit — hook reported `ruff format: files were modified by this hook` and aborted the commit. Re-staged and re-committed cleanly. Not a bug, expected autofix behaviour.

## Self-Check

Files created (all present):
- app/domain/__init__.py — FOUND
- app/domain/value_objects.py — FOUND
- app/domain/entities.py — FOUND
- app/domain/exceptions.py — FOUND
- tests/unit/domain/__init__.py — FOUND
- tests/unit/domain/test_value_objects.py — FOUND
- tests/unit/domain/test_exceptions.py — FOUND
- tests/unit/domain/test_source.py — FOUND
- tests/unit/domain/test_note.py — FOUND
- tests/unit/domain/test_card.py — FOUND
- tests/unit/domain/test_card_review.py — FOUND

Commits (all present in `git log`):
- 6254794 — FOUND (chore: scaffold packages)
- b513ab4 — FOUND (feat: value objects)
- 22fc8d8 — FOUND (feat: DojoError)
- b70c6e2 — FOUND (feat: Source)
- 6d7f836 — FOUND (feat: Note)
- 3c95886 — FOUND (feat: Card)
- 5524332 — FOUND (feat: CardReview)

Gate checks (final run, 2026-04-22):
- `make check` — PASSED (32 tests; ruff/ty/interrogate clean)
- stdlib-only imports in `app/domain/` — PASSED (grep)
- Every `*.py` starts with two `# ABOUTME:` lines — PASSED
- `wc -l app/domain/entities.py` = 85 (≤100) — PASSED

## Self-Check: PASSED

## Next Phase Readiness

- **Plan 02-02 (application ports + DTOs) unblocked** — can now `from app.domain.value_objects import SourceKind, Rating, SourceId, NoteId, CardId, ReviewId` and `from app.domain.exceptions import DojoError` and `from app.domain.entities import Source, Note, Card, CardReview`.
- **No blockers** carried forward.
- **Phase 2 Success Criterion #1 partially satisfied** — entities, value objects, typed IDs, and domain exceptions exist with stdlib-only imports. The `import-linter` structural proof ships in Plan 05.

---
*Phase: 02-domain-application-spine*
*Completed: 2026-04-22*
