---
phase: 03-infrastructure-adapters
plan: 03
subsystem: infrastructure/repositories
tags: [python, sqlalchemy, repositories, contract-tests, phase-3]
requires:
  - 03-02  # ORM row classes + mappers + initial schema migration
  - 02-02  # Phase 2 repository Protocols (SourceRepository, etc.)
  - 02-05  # Phase 2 contract-harness template (test_llm_provider_contract.py)
provides:
  - SqlSourceRepository  # session.merge upsert
  - SqlNoteRepository  # session.merge upsert (regenerate-overwrites)
  - SqlCardRepository  # session.add append (regenerate-appends, PERSIST-02)
  - SqlCardReviewRepository  # session.add append-only log
  - test_source_repository_contract  # [fake, sql] parametrized
  - test_note_repository_contract  # [fake, sql] parametrized
  - test_card_repository_contract  # [fake, sql] parametrized
  - test_card_review_repository_contract  # [fake, sql] parametrized
  - test_sql_repositories_atomic  # SC #2 discharge
  - test_sql_repositories_regenerate  # SC #7 discharge
affects:
  - app.infrastructure.repositories  # new package
tech-stack:
  added: []  # no new runtime deps — SQLAlchemy 2.0 already pinned
  patterns:
    - structural-subtyping-Protocol-conformance
    - mapper-function-at-persistence-boundary
    - session-merge-for-upsert
    - session-add-for-append
    - savepoint-rollback-under-conftest-outer-transaction
key-files:
  created:
    - app/infrastructure/repositories/__init__.py
    - app/infrastructure/repositories/sql_source_repository.py
    - app/infrastructure/repositories/sql_note_repository.py
    - app/infrastructure/repositories/sql_card_repository.py
    - app/infrastructure/repositories/sql_card_review_repository.py
    - tests/contract/test_source_repository_contract.py
    - tests/contract/test_note_repository_contract.py
    - tests/contract/test_card_repository_contract.py
    - tests/contract/test_card_review_repository_contract.py
    - tests/integration/test_sql_repositories_atomic.py
    - tests/integration/test_sql_repositories_regenerate.py
  modified: []
decisions:
  - "D-01/D-01a/D-01b discharged: repos hold Session at init, never commit or rollback"
  - "D-02 + save-primitive matrix discharged: Source/Note use merge (upsert); Card/CardReview use add (append)"
  - "D-02a discharged: domain stays stdlib-only (lint-imports green)"
  - "D-02b discharged: flat repos, no ORM relationships"
  - "D-07 discharged: contract harness extended to 4 new ports with [fake, sql] legs (no env gate)"
metrics:
  duration_seconds: 226
  completed: 2026-04-24
  tasks_completed: 3
  files_created: 11
  contract_tests: 16  # 4 files × [fake, sql] legs
  integration_tests: 3
  tests_passed: 153
  coverage_new_code: 100%
commits:
  - 5188717: feat(03-03) — 4 SQL repos + 4 parametrized contract tests
  - 21604d9: test(03-03) — SC #2 atomic-save + SC #7 regenerate tests
---

# Phase 3 Plan 03: SQL Repositories + Contract Tests + SC#2/SC#7 Summary

Delivered four SQL repositories (Source / Note / Card / CardReview)
as thin glue layers over the Phase 2 Protocols, four parametrized
`[fake, sql]` contract tests, and two integration tests that discharge
SC #2 (atomic 3-save rollback) and SC #7 (regenerate: Note overwrites,
Cards append).

## Scope

- **4 SQL repo modules** at `app/infrastructure/repositories/sql_*.py`.
  Each is ≤50 LOC, structural-subtype conformant with its Phase 2
  Protocol (no explicit inheritance), and imports only from
  `app.domain.*` + `app.infrastructure.db.*` + `app.logging_config`.
- **4 contract test files** at `tests/contract/test_*_repository_contract.py`
  following the `test_llm_provider_contract.py` template; each
  parametrized on `[fake, sql]`. The fake leg reuses the hand-written
  `tests.fakes.Fake*Repository`; the sql leg instantiates the real
  adapter against the SAVEPOINT-isolated `session` fixture.
- **2 integration tests** at
  `tests/integration/test_sql_repositories_{atomic,regenerate}.py`
  discharging SC #2 and SC #7.

## Decisions Discharged (CONTEXT)

| Decision | Status | Evidence |
|----------|--------|----------|
| **D-01** Use case owns transaction; repos never commit | discharged | `grep` across the four repos returns zero hits for `session.commit`, `session.rollback`, `session.begin`. |
| **D-01a** Phase 3 delivers shape; Phase 4 exercises it | discharged | SC #2 test uses the exact `begin_nested()` + `raise` pattern Phase 4's `SaveDraft.execute()` will use with `session.begin()`. |
| **D-01b** Repos receive `Session` at construction | discharged | `__init__(self, session: Session)` on all four classes; no per-method session arg. |
| **D-02 + save-primitive matrix** | discharged | `SqlSourceRepository` + `SqlNoteRepository` use `session.merge`; `SqlCardRepository` + `SqlCardReviewRepository` use `session.add`. `grep -c "self._session.merge" sql_card_repository.py` == 0 (forbidden). |
| **D-02a** Domain stays stdlib-pure | discharged | `uv run lint-imports` returns `3 kept, 0 broken`. |
| **D-02b** No ORM relationships | discharged | Repos query flat rows; no `relationship()` added in `models.py`. |
| **D-07** Contract harness extended without env gate for SQL | discharged | Four contract tests parametrize on `[fake, sql]`; sql leg runs on every `make check` via the session fixture. |

## Success Criteria (ROADMAP Phase 3)

| SC | Description | Discharged by |
|----|-------------|---------------|
| **SC #1** | Repo round-trip (no `MissingGreenlet`) | `test_save_then_get_roundtrips` on the sql leg of all four contract tests. Sync SQLAlchemy + `expire_on_commit=False` + flat repos per D-02b means `MissingGreenlet` is structurally unreachable. |
| **SC #2** | 3-insert forced-fail rolls back all three rows | `test_third_save_failure_rolls_back_all_three` — Source + Note + Card-A + Card-B duplicate-id triggers `IntegrityError` at flush; `session.begin_nested()` SAVEPOINT rolls back; three `session.get(*Row, ...)` assertions confirm absence. |
| **SC #7** | Regenerate: Note overwrites, Cards append | `test_regenerate_note_overwrites_same_id` (save v1 title="t1" → save v2 title="t2" same id → get returns "t2") + `test_regenerate_cards_append_not_overwrite` (3-card batch × 2 with new ids → 6 rows, originals preserved). |

## TDD Log

RED → GREEN per task:

- **Task 1 (RED):** wrote four contract tests first; `uv run pytest
  tests/contract/test_{source,note,card,card_review}_repository_contract.py`
  showed 8 fake-leg tests passing and 8 sql-leg tests erroring on
  `ModuleNotFoundError: No module named
  'app.infrastructure.repositories.sql_*_repository'`.
- **Task 1 (GREEN):** implemented the four SQL repo modules; all 16
  contract tests passed (8 fake + 8 sql).
- **Task 2 (RED→GREEN in one commit):** integration tests written and
  run; all 3 tests passed first shot (the save-primitive matrix and
  mapper plumbing were already verified in Task 1).

Per the Dojo TDD convention (pytest in pre-commit blocks RED-only
commits), RED + GREEN are merged per commit; evidence lives in this
log, not commit granularity.

## Validation

- `uv run pytest tests/contract/test_*_repository_contract.py
  tests/integration/test_sql_repositories_*.py -x` → **19 passed**.
- `uv run lint-imports` → **3 contracts kept, 0 broken**.
- `uv run make check` → **153 passed, 1 skipped** (the skip is
  `tests/contract/test_llm_provider_contract.py[anthropic]` — opt-in
  via `RUN_LLM_TESTS=1`, expected per Phase 2 D-11).
- **100% coverage** on all four new repo modules plus 100% on the
  four contract tests and two integration tests.

## Deviations from Plan

**One cosmetic deviation — automatically applied:**

1. `[Rule 3 - Linter]` Ruff SIM117 flagged nested `with pytest.raises(...)`
   and `with session.begin_nested():` in the atomic test. Combined into
   a single parenthesized `with` statement
   (`with pytest.raises(IntegrityError), session.begin_nested():`).
   Semantically equivalent — `pytest.raises` still captures the
   `IntegrityError` raised on exit from the nested SAVEPOINT context.
   File modified: `tests/integration/test_sql_repositories_atomic.py`.
   Caught on first `make check`, fixed inline in Task 2's working copy
   before the commit.

**Auth gates:** none.
**Architectural changes:** none.
**Plan executed as written** apart from the one linter fix above.

## Threat Flags

None. Every new file lands in `app.infrastructure.repositories.*`;
no new network endpoints, auth paths, or cross-boundary schema
changes introduced by this plan. The threat model section of the plan
was fully mitigated as predicted (T-03-03-01 through T-03-03-05).

## Follow-ups / Plan 05 Unblocks

- **Plan 05 (composition root + DraftStore wiring):** depends on this
  plan plus Plan 04 (Anthropic LLM provider). With all four SQL repos
  live, Plan 05 can now factory-construct them against a
  `Depends(get_session)` pattern in `app/main.py`.
- **Phase 4 (SaveDraft use case):** will open
  `with session.begin():` inside its `execute()` method, invoke all
  three relevant repos, and rely on the same rollback-on-exception
  semantic that SC #2 proves here.

## Self-Check: PASSED

**Created files verified on disk:**
- `app/infrastructure/repositories/__init__.py` — FOUND
- `app/infrastructure/repositories/sql_source_repository.py` — FOUND
- `app/infrastructure/repositories/sql_note_repository.py` — FOUND
- `app/infrastructure/repositories/sql_card_repository.py` — FOUND
- `app/infrastructure/repositories/sql_card_review_repository.py` — FOUND
- `tests/contract/test_source_repository_contract.py` — FOUND
- `tests/contract/test_note_repository_contract.py` — FOUND
- `tests/contract/test_card_repository_contract.py` — FOUND
- `tests/contract/test_card_review_repository_contract.py` — FOUND
- `tests/integration/test_sql_repositories_atomic.py` — FOUND
- `tests/integration/test_sql_repositories_regenerate.py` — FOUND

**Commits verified in git log:**
- `5188717` — FOUND (feat(03-03): add 4 SQL repositories + parametrized contract tests)
- `21604d9` — FOUND (test(03-03): add SC #2 atomic-save + SC #7 regenerate integration tests)
