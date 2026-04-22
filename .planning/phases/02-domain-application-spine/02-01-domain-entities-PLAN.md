---
phase: 02-domain-application-spine
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - app/domain/__init__.py
  - app/domain/value_objects.py
  - app/domain/entities.py
  - app/domain/exceptions.py
  - tests/unit/domain/__init__.py
  - tests/unit/domain/test_source.py
  - tests/unit/domain/test_note.py
  - tests/unit/domain/test_card.py
  - tests/unit/domain/test_card_review.py
  - tests/unit/domain/test_value_objects.py
  - tests/unit/domain/test_exceptions.py
autonomous: true
requirements:
  - TEST-01
tags:
  - domain
  - dataclasses
  - tdd
must_haves:
  truths:
    - "`Source`, `Note`, `Card`, `CardReview` can be constructed directly from stdlib types and carry unique `SourceId`/`NoteId`/`CardId`/`ReviewId` at construction time."
    - "Entity constructors raise `ValueError` when required string fields (`user_prompt`, `content`, `question`, `answer`) are empty or whitespace-only."
    - "`SourceKind` enum has exactly `{FILE, URL, TOPIC}`; `Rating` enum has exactly `{CORRECT, INCORRECT}`."
    - "`DojoError` is the base exception class for every Dojo exception hierarchy."
    - "`app/domain/` imports only stdlib modules (`dataclasses`, `enum`, `typing`, `uuid`, `datetime`) — zero third-party imports."
  artifacts:
    - path: "app/domain/__init__.py"
      provides: "Domain package marker (ABOUTME + module docstring; no re-exports per Phase 1 D-11)."
    - path: "app/domain/value_objects.py"
      provides: "`SourceKind`, `Rating` enums; `SourceId`, `NoteId`, `CardId`, `ReviewId` `NewType` aliases over `uuid.UUID`."
    - path: "app/domain/entities.py"
      provides: "Frozen dataclasses `Source`, `Note`, `Card`, `CardReview` with `default_factory` ID minting and `__post_init__` invariants."
    - path: "app/domain/exceptions.py"
      provides: "`DojoError` base class (+ `InvalidEntity` subclass if a real case surfaces — MVP may ship with just the base)."
    - path: "tests/unit/domain/test_source.py"
      provides: "Source entity invariant tests (empty prompt → `ValueError`; IDs unique per instance)."
    - path: "tests/unit/domain/test_note.py"
      provides: "Note entity invariant tests (empty content → `ValueError`; `source_id` association)."
    - path: "tests/unit/domain/test_card.py"
      provides: "Card entity invariant tests (empty question/answer → `ValueError`; `tags` defaults to empty tuple)."
    - path: "tests/unit/domain/test_card_review.py"
      provides: "CardReview entity tests (rating + `reviewed_at`; `is_correct` derived from `Rating`)."
    - path: "tests/unit/domain/test_value_objects.py"
      provides: "Enum membership tests for `SourceKind` and `Rating`; NewType-ID smoke assertion."
    - path: "tests/unit/domain/test_exceptions.py"
      provides: "`DojoError` hierarchy smoke test."
  key_links:
    - from: "app/domain/entities.py"
      to: "app/domain/value_objects.py"
      via: "imports `SourceKind`, `Rating`, and the four `*Id` NewType aliases"
      pattern: "from app.domain.value_objects import"
    - from: "app/domain/exceptions.py"
      to: "(stdlib `Exception`)"
      via: "`DojoError(Exception)` subclass; no cross-layer import"
      pattern: "class DojoError\\(Exception\\):"
    - from: "tests/unit/domain/*.py"
      to: "app/domain/*"
      via: "every domain test imports only from `app.domain.*` and stdlib/pytest"
      pattern: "from app\\.domain\\."
---

<objective>
Deliver the pure-stdlib inner core of Dojo's domain layer: four frozen
dataclass entities (`Source`, `Note`, `Card`, `CardReview`), their value
objects (`SourceKind`, `Rating`) and typed IDs (`SourceId`, `NoteId`,
`CardId`, `ReviewId`), and a minimal `DojoError` exception hierarchy —
all driven test-first, all importing only stdlib.

This plan contributes to ROADMAP Phase 2 Success Criterion #1: `app/domain/`
contains the entities, value objects, typed IDs, and domain exceptions with
stdlib-only imports. Requirement TEST-01 (hand-written fakes at every port
boundary, no `Mock()`) is partially discharged here because these entity
tests use no fakes at all — they are pure-stdlib unit tests exercising
`__post_init__` invariants and thus set the "no Mock()" precedent for the
phase.

No I/O, no Pydantic, no ORM, no logging. Every file ≤100 lines (wiki rule).
Every file starts with two `# ABOUTME:` lines and one module docstring.
Every public symbol has a one-line docstring (interrogate 100% per Phase 1
D-15). Red→Green→Refactor on every entity — no source code lands before
its failing test.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/02-domain-application-spine/02-CONTEXT.md
@.planning/phases/02-domain-application-spine/02-RESEARCH.md
@.planning/phases/02-domain-application-spine/02-PATTERNS.md
@CLAUDE.md

# Phase 1 analog files (copy-skeleton references)
@app/settings.py
@app/infrastructure/db/__init__.py
@tests/__init__.py
@tests/unit/__init__.py
@tests/unit/test_settings.py

<interfaces>
<!-- Phase 1 analog signatures the executor copies. No existing domain code. -->

From `app/settings.py` (ABOUTME + module-docstring + `from __future__` header pattern):
```python
# ABOUTME: App settings loaded from .env via pydantic-settings.
# ABOUTME: Single source of truth for config, including DB + API key.
"""Application settings loaded from .env via pydantic-settings."""

from __future__ import annotations
```

From `app/infrastructure/db/__init__.py` (package-marker pattern):
```python
# ABOUTME: DB-infrastructure subpackage (engine, session, repos).
# ABOUTME: Phase 1 provides Base + session; Phase 3 adds repositories.
"""Database infrastructure subpackage."""
```

From `tests/unit/test_settings.py` (unit-test idiom — `pytest`, `MonkeyPatch`, typed signature, docstring):
```python
def test_anthropic_key_loaded_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`ANTHROPIC_API_KEY` env var takes precedence over default."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    settings = get_settings()
    assert settings.anthropic_api_key.get_secret_value() == "sk-ant-test"
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Red — failing tests for value objects + `DojoError`</name>
  <read_first>
    - .planning/phases/02-domain-application-spine/02-CONTEXT.md (D-01: NewType-IDs; Claude's discretion "Entity construction invariants")
    - .planning/phases/02-domain-application-spine/02-RESEARCH.md §2.4 (test file list + sizes), §3.1–3.4 (RED/GREEN bullets per entity)
    - .planning/phases/02-domain-application-spine/02-PATTERNS.md "tests/unit/domain/test_source.py" (full test-file skeleton + adapted invariant-test pattern)
    - tests/unit/test_settings.py (Phase 1 unit-test idiom — pytest, typed sig, docstring, one-line)
    - tests/unit/__init__.py (ABOUTME two-line pattern for `tests/unit/domain/__init__.py`)
  </read_first>
  <behavior>
    - `tests/unit/domain/test_value_objects.py` contains `test_source_kind_members`: `set(m.name for m in SourceKind) == {"FILE", "URL", "TOPIC"}`.
    - `tests/unit/domain/test_value_objects.py` contains `test_rating_members`: `set(m.name for m in Rating) == {"CORRECT", "INCORRECT"}`.
    - `tests/unit/domain/test_value_objects.py` contains `test_new_type_ids_wrap_uuid`: `SourceId(uuid.uuid4())` is an instance of `uuid.UUID` at runtime (NewType has zero runtime cost); every ID alias (`SourceId`, `NoteId`, `CardId`, `ReviewId`) is importable from `app.domain.value_objects`.
    - `tests/unit/domain/test_exceptions.py` contains `test_dojo_error_is_exception`: `DojoError` subclasses `Exception` and can be raised with a string message.
    - Tests fail with `ModuleNotFoundError` on `app.domain.value_objects` and `app.domain.exceptions` (modules do not exist yet).
  </behavior>
  <action>
**RED phase — write the failing tests first, with NO implementation.**

1. Create `tests/unit/domain/__init__.py` with the exact two-line ABOUTME
   pattern from `tests/unit/__init__.py` (copy-adapt per PATTERNS.md
   "tests/unit/domain/__init__.py" block):
   ```python
   # ABOUTME: Domain-layer unit tests.
   # ABOUTME: Entities, value objects, exceptions — stdlib only.
   """Domain unit tests."""
   ```

2. Create `tests/unit/domain/test_value_objects.py` with three test functions
   (`test_source_kind_members`, `test_rating_members`, `test_new_type_ids_wrap_uuid`).
   File header must follow the exact PATTERNS.md "tests/unit/domain/test_source.py"
   template (ABOUTME lines tailored to this file's role) + `from __future__ import annotations`.
   Imports will be `import uuid`, `import pytest` (or omit if unused), and
   `from app.domain.value_objects import SourceKind, Rating, SourceId, NoteId, CardId, ReviewId`.
   Each test has a one-line docstring; each uses plain assertions (no fixtures).
   Example test body for `test_source_kind_members`:
   ```python
   def test_source_kind_members() -> None:
       """SourceKind contains exactly FILE, URL, TOPIC."""
       assert {m.name for m in SourceKind} == {"FILE", "URL", "TOPIC"}
   ```

3. Create `tests/unit/domain/test_exceptions.py` with one test function
   `test_dojo_error_is_exception` asserting `issubclass(DojoError, Exception)`
   and that `raise DojoError("boom")` round-trips the message (`str(exc)`).
   Import: `from app.domain.exceptions import DojoError`.

4. Run `uv run pytest tests/unit/domain/test_value_objects.py
   tests/unit/domain/test_exceptions.py -v` and confirm both files fail
   with `ModuleNotFoundError` (the expected RED state — modules don't exist).

5. Commit the failing tests **without implementation**. Commit message:
   `test(02-01): add failing tests for domain value objects and DojoError`

**Do NOT** create `app/domain/value_objects.py` or `app/domain/exceptions.py`
in this task. Only tests + test-package marker.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/domain/test_value_objects.py tests/unit/domain/test_exceptions.py -v 2>&1 | grep -E "ModuleNotFoundError|ERRORS" | head -5</automated>
  </verify>
  <acceptance_criteria>
    - File `tests/unit/domain/__init__.py` exists and starts with exactly two lines that begin `# ABOUTME: `.
    - File `tests/unit/domain/test_value_objects.py` exists; `grep -c "^def test_" tests/unit/domain/test_value_objects.py` returns `3`.
    - File `tests/unit/domain/test_exceptions.py` exists; contains `from app.domain.exceptions import DojoError` and a `def test_dojo_error_is_exception`.
    - `uv run pytest tests/unit/domain/test_value_objects.py tests/unit/domain/test_exceptions.py --collect-only 2>&1` exits non-zero AND output contains `ModuleNotFoundError: No module named 'app.domain'` (or `app.domain.value_objects`).
    - No file under `app/domain/` exists yet (this task is RED only). Verify with `ls app/domain/ 2>&1` returns "No such file or directory" or an empty listing.
    - A commit exists with message matching `^test\(02-01\): add failing tests for domain value objects and DojoError` (`git log --oneline -1`).
  </acceptance_criteria>
  <done>Two test files + one package marker committed. `pytest --collect-only` fails with `ModuleNotFoundError` on `app.domain.*`. No `app/domain/` source exists.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Green — implement `value_objects.py` + `exceptions.py` + `app/domain/__init__.py`</name>
  <read_first>
    - Task 1's committed test files (the tests this task must make pass).
    - .planning/phases/02-domain-application-spine/02-CONTEXT.md D-01 (NewType-IDs, literal code block); Claude's discretion "Domain vs application exception split".
    - .planning/phases/02-domain-application-spine/02-PATTERNS.md "app/domain/value_objects.py" and "app/domain/exceptions.py" and "app/domain/__init__.py" (full skeletons).
    - app/infrastructure/db/__init__.py (Phase 1 package-marker analog).
    - app/settings.py (module-header + `from __future__` pattern).
    - pyproject.toml [tool.interrogate] (fail-under=100 — one-line docstrings required).
  </read_first>
  <action>
**GREEN phase — write the minimum code to make Task 1's tests pass.**

1. Create `app/domain/__init__.py` with exactly this content (per PATTERNS.md):
   ```python
   # ABOUTME: Domain layer — pure entities, value objects, exceptions.
   # ABOUTME: stdlib-only; no I/O, no Pydantic, no ORM imports.
   """Dojo domain layer."""
   ```

2. Create `app/domain/value_objects.py` with exactly this structure (per
   PATTERNS.md + CONTEXT D-01). Use these literal symbol definitions:
   ```python
   # ABOUTME: Domain value objects — SourceKind, Rating enums + typed IDs.
   # ABOUTME: NewType aliases over uuid.UUID; zero runtime cost.
   """Domain value objects and typed IDs."""

   from __future__ import annotations

   import uuid
   from enum import Enum
   from typing import NewType


   class SourceKind(Enum):
       """Kind of source material a generation request targets."""

       FILE = "file"
       URL = "url"
       TOPIC = "topic"


   class Rating(Enum):
       """User rating applied to a drilled card."""

       CORRECT = "correct"
       INCORRECT = "incorrect"


   SourceId = NewType("SourceId", uuid.UUID)
   NoteId = NewType("NoteId", uuid.UUID)
   CardId = NewType("CardId", uuid.UUID)
   ReviewId = NewType("ReviewId", uuid.UUID)
   ```

3. Create `app/domain/exceptions.py` with the `DojoError` base class only
   (per CONTEXT Claude's-discretion: "MVP may start with just the base
   class"):
   ```python
   # ABOUTME: Domain-layer exception hierarchy rooted at DojoError.
   # ABOUTME: Application + infrastructure exceptions inherit from DojoError.
   """Domain-layer exceptions."""

   from __future__ import annotations


   class DojoError(Exception):
       """Base class for all Dojo domain and application exceptions."""
   ```
   Do NOT add `InvalidEntity` unless Task 3 produces a real call-site need
   (YAGNI; CONTEXT rule).

4. Run `uv run pytest tests/unit/domain/test_value_objects.py
   tests/unit/domain/test_exceptions.py -v` — all 4 tests must pass (GREEN).

5. Run `uv run ruff check app/domain/ tests/unit/domain/` and
   `uv run ty check app/domain` — both must exit zero.

6. Run `uv run interrogate -c pyproject.toml app` — must report 100%
   (no docstring regression).

7. Commit the three source files. Commit message:
   `feat(02-01): add domain value objects, IDs, and DojoError base`
  </action>
  <verify>
    <automated>uv run pytest tests/unit/domain/test_value_objects.py tests/unit/domain/test_exceptions.py -v && uv run ruff check app/domain/ && uv run ty check app/domain && uv run interrogate -c pyproject.toml app</automated>
  </verify>
  <acceptance_criteria>
    - `app/domain/__init__.py` exists with exactly two `# ABOUTME:` lines followed by `"""Dojo domain layer."""`.
    - `app/domain/value_objects.py` file size ≤100 lines (`wc -l` output) AND contains the literal strings `class SourceKind(Enum):`, `class Rating(Enum):`, `SourceId = NewType("SourceId", uuid.UUID)`, `NoteId = NewType("NoteId", uuid.UUID)`, `CardId = NewType("CardId", uuid.UUID)`, `ReviewId = NewType("ReviewId", uuid.UUID)`.
    - `app/domain/exceptions.py` contains the literal string `class DojoError(Exception):` and a one-line docstring immediately below the class statement.
    - `grep -E "^(from|import) " app/domain/value_objects.py app/domain/exceptions.py` shows only stdlib imports (`uuid`, `enum`, `typing`, `__future__`) — zero third-party modules.
    - `uv run pytest tests/unit/domain/test_value_objects.py tests/unit/domain/test_exceptions.py -v` exits 0 with 4 tests passed.
    - `uv run ruff check app/domain/` exits 0.
    - `uv run ty check app/domain` exits 0.
    - `uv run interrogate -c pyproject.toml app` exits 0 AND output contains `actual: 100.0%` (or equivalent 100% line).
    - Commit exists with message matching `^feat\(02-01\): add domain value objects, IDs, and DojoError base`.
  </acceptance_criteria>
  <done>4 domain tests pass. `ruff`, `ty`, `interrogate` all clean. `app/domain/` contains 3 files, stdlib imports only.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Red→Green for all four entities + final `make check`</name>
  <read_first>
    - .planning/phases/02-domain-application-spine/02-CONTEXT.md (D-02: `default_factory=lambda: SourceId(uuid.uuid4())` pattern; Claude's-discretion "Entity mutability" → `frozen=True`; "Entity construction invariants" → `__post_init__` + bare `ValueError`).
    - .planning/phases/02-domain-application-spine/02-RESEARCH.md §3.1–3.4 (RED/GREEN bullets per entity).
    - .planning/phases/02-domain-application-spine/02-PATTERNS.md "app/domain/entities.py" (full `Source` skeleton + `_require_nonempty` refactor hint).
    - app/domain/value_objects.py (Task 2 output — entities import `SourceKind`, `Rating`, the 4 `*Id` aliases from here).
    - Makefile (target `check:` runs `format + lint + typecheck + docstrings + test` — this task must leave `make check` green).
  </read_first>
  <behavior>
    TDD loop per entity (`Source`, `Note`, `Card`, `CardReview`), in that order:
    - **Source**: `test_source_construction_rejects_empty_user_prompt`, `test_source_id_is_unique_per_instance`, `test_source_defaults_input_to_none`, `test_source_is_frozen`.
    - **Note**: `test_note_construction_rejects_empty_content`, `test_note_carries_source_id_association`, `test_note_id_is_unique`, `test_note_is_frozen`.
    - **Card**: `test_card_rejects_empty_question`, `test_card_rejects_empty_answer`, `test_card_default_tags_is_empty_tuple`, `test_card_carries_source_id_association`, `test_card_is_frozen`.
    - **CardReview**: `test_card_review_records_rating_and_time`, `test_card_review_is_correct_matches_rating` (CORRECT → True; INCORRECT → False), `test_card_review_carries_card_id_association`, `test_card_review_is_frozen`.
    Commit per RED (failing) + per GREEN (passing) pair.
  </behavior>
  <action>
**Four Red→Green cycles, one per entity. Each cycle = one failing-test
commit + one implementation commit.**

For each entity, follow this exact loop:

**Cycle A — `Source`:**
1. **RED:** Create `tests/unit/domain/test_source.py` with ABOUTME header
   per PATTERNS.md and four tests listed in `<behavior>`. Use the literal
   pattern shown in PATTERNS.md "tests/unit/domain/test_source.py":
   ```python
   def test_source_construction_rejects_empty_user_prompt() -> None:
       """`Source(user_prompt='')` raises ValueError."""
       with pytest.raises(ValueError, match="non-empty"):
           Source(kind=SourceKind.TOPIC, user_prompt="")
   ```
   `test_source_is_frozen` asserts `dataclasses.FrozenInstanceError` on
   attribute mutation. Import: `from app.domain.entities import Source`
   and `from app.domain.value_objects import SourceKind`.
   Run `uv run pytest tests/unit/domain/test_source.py` → expect
   `ImportError: cannot import name 'Source'`.
   Commit: `test(02-01): add failing tests for Source entity`

2. **GREEN:** Create `app/domain/entities.py` with `Source` only:
   ```python
   # ABOUTME: Domain entities — Source, Note, Card, CardReview dataclasses.
   # ABOUTME: Frozen, stdlib-only; IDs minted via default_factory on construction.
   """Domain entities."""

   from __future__ import annotations

   import uuid
   from dataclasses import dataclass, field
   from datetime import datetime

   from app.domain.value_objects import (
       CardId,
       NoteId,
       Rating,
       ReviewId,
       SourceId,
       SourceKind,
   )


   @dataclass(frozen=True)
   class Source:
       """A source of study material."""

       kind: SourceKind
       user_prompt: str
       input: str | None = None
       id: SourceId = field(
           default_factory=lambda: SourceId(uuid.uuid4())
       )
       created_at: datetime = field(default_factory=datetime.now)

       def __post_init__(self) -> None:
           """Reject empty user_prompt after whitespace strip."""
           if not self.user_prompt.strip():
               raise ValueError("user_prompt must be non-empty")
   ```
   Run the Source tests → all green. Commit:
   `feat(02-01): add Source entity`

**Cycles B–D — repeat for `Note`, `Card`, `CardReview`.**

   - `Note` fields: `source_id: SourceId`, `content: str`, `id: NoteId =
     field(default_factory=lambda: NoteId(uuid.uuid4()))`, `created_at:
     datetime = field(default_factory=datetime.now)`. `__post_init__`
     rejects empty `content`.
   - `Card` fields: `source_id: SourceId`, `question: str`, `answer: str`,
     `tags: tuple[str, ...] = ()`, `id: CardId = field(default_factory=
     lambda: CardId(uuid.uuid4()))`, `created_at: datetime = field(
     default_factory=datetime.now)`. `__post_init__` rejects empty
     `question` AND empty `answer` (two separate `ValueError` raises,
     message includes the field name).
   - `CardReview` fields: `card_id: CardId`, `rating: Rating`, `id:
     ReviewId = field(default_factory=lambda: ReviewId(uuid.uuid4()))`,
     `reviewed_at: datetime = field(default_factory=datetime.now)`.
     `is_correct` is a `@property` returning `self.rating ==
     Rating.CORRECT` (per RESEARCH §3.4).

**Refactor pass (after all four entities GREEN):**
If `Source`/`Note`/`Card` each duplicated a 3-line empty-string check in
`__post_init__`, and `entities.py` is at risk of exceeding 100 lines,
extract a module-level helper (per RESEARCH §3.1 refactor hint):
```python
def _require_nonempty(value: str, field_name: str) -> None:
    """Raise ValueError if `value` is empty or whitespace-only."""
    if not value.strip():
        raise ValueError(f"{field_name} must be non-empty")
```
Helper is module-private (underscore-prefixed). Interrogate does not
require docstrings on private symbols, but include one anyway (team
convention). After refactor, run the full domain test suite — must stay
green. Commit:
`refactor(02-01): extract _require_nonempty helper in entities.py`

**Final gates:**
- Confirm `app/domain/entities.py` is ≤100 lines (`wc -l`). If it exceeds,
  split into `entities/source.py`, `entities/note.py`, `entities/card.py`,
  `entities/card_review.py` with an `entities/__init__.py` that re-exports
  all four names (flagged in PATTERNS.md as a contingency).
- Run `make check` end-to-end (`format + lint + typecheck + docstrings +
  test`). Must exit 0 with all domain tests (and all pre-existing Phase 1
  tests) passing.
- Commit the final state if any formatter/linter fix was applied (e.g.
  trailing whitespace). Commit message: `chore(02-01): apply make check fixes`
  (skip this commit if `make check` was already clean).

**Do NOT touch:** `app/application/`, `tests/fakes/`, `tests/contract/`,
`pyproject.toml`, `Makefile`. Those are later plans.
  </action>
  <verify>
    <automated>make check</automated>
  </verify>
  <acceptance_criteria>
    - Four test files exist: `tests/unit/domain/test_source.py`, `test_note.py`, `test_card.py`, `test_card_review.py`. Each has ≥4 `def test_` functions.
    - `app/domain/entities.py` exists and is ≤100 lines (`wc -l app/domain/entities.py` ≤ 100). If split, `app/domain/entities/__init__.py` re-exports all four entity names.
    - `app/domain/entities.py` contains the literal strings `@dataclass(frozen=True)`, `class Source:`, `class Note:`, `class Card:`, `class CardReview:`, `default_factory=lambda: SourceId(uuid.uuid4())` (or the equivalent pattern for each ID), and `def __post_init__(self) -> None:` at least once.
    - `grep -E "^(from|import) " app/domain/entities.py` shows only stdlib (`__future__`, `uuid`, `dataclasses`, `datetime`) and `from app.domain.value_objects import ...` — zero third-party.
    - `CardReview` has an `is_correct` property returning a `bool`, verified by `grep -A1 "@property" app/domain/entities.py | grep "is_correct"`.
    - `make check` exits 0 (covers format + lint + typecheck + docstrings + pytest at 100% interrogate, zero ruff errors, zero ty errors, all domain tests green, all Phase 1 tests still green).
    - `uv run pytest tests/unit/domain/ -v` exits 0 AND reports ≥20 passed tests across the six domain test files (4 entity files + value_objects + exceptions).
    - `git log --oneline -15` contains at least 8 commits matching `^(test|feat|refactor|chore)\(02-01\):` (four RED + four GREEN at minimum).
  </acceptance_criteria>
  <done>All four entities green. `make check` clean. Domain layer ≤4 Python files, all stdlib-only, all ≤100 lines, 100% interrogate.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

Phase 2's domain layer has **no trust boundaries**. It is pure-stdlib
Python with no I/O, no external inputs, no serialisation, and no
network/filesystem access. Data enters and exits the layer only via
in-process Python function calls from the application layer (Plan 04)
and tests (this plan + Plan 03).

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-01-01 | Tampering | Domain entity invariants bypassed via field mutation | mitigate | All entities are `@dataclass(frozen=True)`; mutation raises `FrozenInstanceError`. Verified by `test_*_is_frozen` in each entity test file. |
| T-02-01-02 | Information Disclosure | Domain layer accidentally imports infrastructure and leaks secrets (e.g., `Settings.anthropic_api_key`) into domain types | accept | Mitigated structurally in Plan 05 via `import-linter` contract `Domain must not depend on infrastructure or web`. In Plan 01, enforced by grep-verified stdlib-only imports in `app/domain/*.py` (see acceptance criteria on Task 2 + Task 3). |
| T-02-01-03 | Elevation of Privilege | A later phase adds an `is_admin`/privilege field to `Source` via monkeypatch | accept | Low severity; Dojo is single-user local. Frozen dataclasses make runtime monkey-patch harder to hit; CI would catch via domain tests + `make check`. No additional mitigation this phase. |

No high-severity threats. All mitigations live in test assertions on Task
1-3 and in the stdlib-only import grep.
</threat_model>

<verification>
Phase-level verification commands (run after all three tasks complete):

```bash
# 1. Domain tests green
uv run pytest tests/unit/domain/ -v

# 2. Stdlib-only imports (manual import-linter comes in Plan 05;
#    Plan 01 belt-and-braces via grep)
grep -rE "^(from|import)" app/domain/ | grep -vE "(__future__|uuid|dataclasses|datetime|enum|typing|app\.domain)"
# Expected: zero lines.

# 3. Full repo gate
make check

# 4. File sizes
find app/domain/ tests/unit/domain/ -name "*.py" -exec wc -l {} + | awk '$1 > 100 {print "TOO LARGE:", $0}'
# Expected: no "TOO LARGE" output.

# 5. Interrogate 100%
uv run interrogate -c pyproject.toml app
# Expected: 100.0% (no regression).
```
</verification>

<success_criteria>
Plan 01 is complete when:

1. `app/domain/` contains `__init__.py`, `value_objects.py`, `entities.py`,
   `exceptions.py` — all ≤100 lines, all starting with two `# ABOUTME:`
   lines, all stdlib-only imports.
2. `tests/unit/domain/` contains `__init__.py` + 6 test files (`test_source`,
   `test_note`, `test_card`, `test_card_review`, `test_value_objects`,
   `test_exceptions`), all ≤100 lines.
3. `uv run pytest tests/unit/domain/` exits 0 with ≥20 tests passed.
4. `make check` exits 0 (ruff, ty, interrogate 100%, all tests including
   Phase 1 tests).
5. Git history shows RED→GREEN commit pairs per entity (at minimum 4
   `test(02-01):` commits preceding 4 `feat(02-01):` commits in the log).
6. ROADMAP Phase 2 SC #1 partial: `app/domain/` entities, value objects,
   typed IDs, and domain exceptions exist with stdlib-only imports.
   (The `import-linter` proof of "never imports from infrastructure/web"
   ships in Plan 05.)
</success_criteria>

<output>
After completion, create `.planning/phases/02-domain-application-spine/02-01-SUMMARY.md`
documenting:
- Files created/modified (with line counts).
- Test count (per-file breakdown).
- RED→GREEN commit hashes per entity.
- Whether `entities.py` required a split (≤100-line contingency).
- Whether `_require_nonempty` helper was extracted.
- Any deviations from the plan (expected: none).
</output>
