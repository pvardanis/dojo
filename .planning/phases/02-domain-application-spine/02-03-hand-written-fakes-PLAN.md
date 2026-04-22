---
phase: 02-domain-application-spine
plan: 03
type: tdd
wave: 3
depends_on:
  - "02-01"
  - "02-02"
files_modified:
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
autonomous: true
requirements:
  - DRAFT-01
  - TEST-01
tags:
  - fakes
  - test-infrastructure
  - tdd
must_haves:
  truths:
    - "Every application port declared in Plan 02 has a hand-written fake under `tests/fakes/`."
    - "No fake uses `unittest.mock.Mock`, `MagicMock`, or `AsyncMock` — hand-written fakes only (TEST-01)."
    - "Every fake exposes its state as a public attribute (e.g. `fake.saved`, `fake.puts`, `fake.calls_with`) — no `.calls` lists, no `assert_called_with` idioms (CONTEXT Claude's-discretion: fake assertion style)."
    - "`FakeDraftStore` supports `put` + atomic `pop` + a `force_expire(token)` test hook (per CONTEXT D-06)."
    - "`FakeLLMProvider` records calls on `calls_with: list[tuple[str | None, str]]` and exposes a mutable `next_response` so tests can override the canned return (per PATTERNS.md)."
    - "Fakes implement Protocols by structural subtyping — NO inheritance from the Protocol, NO `@runtime_checkable`."
  artifacts:
    - path: "tests/fakes/__init__.py"
      provides: "Re-exports for every fake: `from tests.fakes import FakeLLMProvider, FakeSourceRepository, ...`."
    - path: "tests/fakes/fake_llm_provider.py"
      provides: "Hand-written fake of `LLMProvider` — deterministic canned `(NoteDTO, list[CardDTO])` response + call log."
    - path: "tests/fakes/fake_source_repository.py"
      provides: "Dict-backed fake of `SourceRepository`."
    - path: "tests/fakes/fake_note_repository.py"
      provides: "Dict-backed fake of `NoteRepository` with regenerate-overwrite semantic."
    - path: "tests/fakes/fake_card_repository.py"
      provides: "Dict-backed fake of `CardRepository` with append-only regeneration."
    - path: "tests/fakes/fake_card_review_repository.py"
      provides: "List-backed fake of `CardReviewRepository`."
    - path: "tests/fakes/fake_draft_store.py"
      provides: "Dict-backed fake of `DraftStore` with atomic `pop` and `force_expire` test hook."
    - path: "tests/unit/fakes/"
      provides: "One unit test file per fake, exercising its contract (seven files total)."
  key_links:
    - from: "tests/fakes/fake_llm_provider.py"
      to: "app/application/dtos.py"
      via: "imports `NoteDTO`, `CardDTO` for canned response type"
      pattern: "from app\\.application\\.dtos import"
    - from: "tests/fakes/fake_draft_store.py"
      to: "app/application/ports.py + dtos.py"
      via: "imports `DraftToken` and `DraftBundle`"
      pattern: "from app\\.application\\."
    - from: "tests/fakes/fake_*_repository.py"
      to: "app/domain/entities.py + app/domain/value_objects.py"
      via: "imports the domain entity + its typed ID"
      pattern: "from app\\.domain\\."
---

<objective>
Deliver seven hand-written fakes — one per application port — plus
accompanying unit tests that exercise each fake's contract via public
state. These fakes are the backbone of TEST-01 ("hand-written fakes at
every port boundary, no Mock() behavior-testing") and DRAFT-01 (the
`FakeDraftStore` is the Phase-2 implementation of the DraftStore port;
Phase 3's `InMemoryDraftStore` adds TTL + `asyncio.Lock`).

Each fake is a plain Python class with structural subtyping against its
Protocol — no inheritance, no `@runtime_checkable`, no metaclass magic.
State is exposed on public attributes so tests assert on `.saved`,
`.puts`, `.calls_with` rather than on mock call patterns. When Plan 04
wires the `GenerateFromSource` use case against these fakes, the use-
case test reads post-state from the fakes the same way a Phase-3
integration test would read post-state from a real SQLite DB.

RED→GREEN per fake: each fake's unit test lands as a failing test first,
then the fake is implemented minimally to pass. No orphan fakes — every
fake file has a corresponding test file with ≥3 assertions on its public
state.

This plan is the single biggest one in Phase 2 (7 source files + 7 test
files = ~14 files, RESEARCH estimates 300-400 LOC). If the PR exceeds
400 LOC against `main`, flag to Danny for mid-plan review; the plan
itself stays single-PR because the fakes form one cohesive surface and
splitting them would force two PRs to stabilise a single Wave-3
landmark.
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

# Plans 01 + 02 outputs (required)
@.planning/phases/02-domain-application-spine/02-01-SUMMARY.md
@.planning/phases/02-domain-application-spine/02-02-SUMMARY.md
@app/domain/entities.py
@app/domain/value_objects.py
@app/application/ports.py
@app/application/dtos.py
@app/application/exceptions.py

# Phase 1 analog
@tests/__init__.py
@tests/unit/__init__.py

<interfaces>
<!-- All Protocol signatures the fakes must structurally match. -->
<!-- Copied verbatim from Plan 02's ports.py output. -->

```python
class LLMProvider(Protocol):
    def generate_note_and_cards(
        self,
        source_text: str | None,
        user_prompt: str,
    ) -> tuple[NoteDTO, list[CardDTO]]: ...

class SourceRepository(Protocol):
    def save(self, source: Source) -> None: ...
    def get(self, source_id: SourceId) -> Source | None: ...

class NoteRepository(Protocol):
    def save(self, note: Note) -> None: ...
    def get(self, note_id: NoteId) -> Note | None: ...

class CardRepository(Protocol):
    def save(self, card: Card) -> None: ...
    def get(self, card_id: CardId) -> Card | None: ...

class CardReviewRepository(Protocol):
    def save(self, review: CardReview) -> None: ...

class DraftStore(Protocol):
    def put(self, token: DraftToken, bundle: DraftBundle) -> None: ...
    def pop(self, token: DraftToken) -> DraftBundle | None: ...

DraftToken = NewType("DraftToken", uuid.UUID)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Red→Green for `FakeDraftStore` + `FakeLLMProvider`</name>
  <read_first>
    - .planning/phases/02-domain-application-spine/02-CONTEXT.md D-04 (DraftStore surface), D-06 (`FakeDraftStore.force_expire` hook); Claude's-discretion "Fakes file layout" (one file per fake, re-exported via `tests/fakes/__init__.py`); "Fake assertion style" (public-attribute state).
    - .planning/phases/02-domain-application-spine/02-RESEARCH.md §3.5 (DraftStore RED/GREEN), §3.7 (LLMProvider RED/GREEN + `calls_with` + `next_response`).
    - .planning/phases/02-domain-application-spine/02-PATTERNS.md "tests/fakes/fake_llm_provider.py" + "tests/fakes/fake_draft_store.py" + "tests/fakes/__init__.py" (full skeletons).
    - app/application/ports.py (Plan 02 output — `LLMProvider` and `DraftStore` Protocol shapes).
    - app/application/dtos.py (Plan 02 output — `NoteDTO`, `CardDTO`, `DraftBundle`).
  </read_first>
  <behavior>
    Two fakes in this task (the highest-surface ones). Each is preceded by
    its RED tests. Commit RED + GREEN per fake.

    `tests/unit/fakes/test_fake_draft_store.py`:
    - `test_put_then_pop_returns_bundle`
    - `test_pop_is_atomic_read_and_delete` (second `pop(token)` → `None`)
    - `test_pop_missing_returns_none`
    - `test_puts_log_records_every_write`
    - `test_force_expire_removes_token` (subsequent `pop` → `None`)

    `tests/unit/fakes/test_fake_llm_provider.py`:
    - `test_returns_default_canned_note_and_cards`
    - `test_calls_with_logs_every_call`
    - `test_next_response_override_changes_return` (mutate
      `fake.next_response`, call, assert new return)
    - `test_returns_tuple_of_note_dto_and_card_list` (type assertion:
      `isinstance(note, NoteDTO)`, `isinstance(cards, list)`, each
      `isinstance(c, CardDTO)`).
  </behavior>
  <action>
**Part A — Test-package markers + RED tests for two fakes.**

1. Create `tests/fakes/__init__.py` — **but leave the re-export list
   EMPTY for now**. Only the ABOUTME + docstring, no imports. The
   re-export list gets filled in Task 3 after all seven fakes exist
   (prevents import-order flakes during RED→GREEN cycles).
   ```python
   # ABOUTME: Hand-written fakes for every application port.
   # ABOUTME: No Mock(); tests import `from tests.fakes import Fake*`.
   """Hand-written fake adapters (one per port)."""
   ```

2. Create `tests/unit/fakes/__init__.py`:
   ```python
   # ABOUTME: Unit tests for hand-written fakes.
   # ABOUTME: Each fake test exercises the fake's contract via public state.
   """Unit tests for hand-written fakes."""
   ```

3. Create `tests/unit/fakes/test_fake_draft_store.py` with the 5 tests
   listed in `<behavior>`. Header:
   ```python
   # ABOUTME: FakeDraftStore contract tests — put/pop atomicity, expiry.
   # ABOUTME: Proves the fake's state is exposed via .puts public attribute.
   """FakeDraftStore unit tests."""

   from __future__ import annotations

   import uuid

   from app.application.dtos import CardDTO, DraftBundle, NoteDTO
   from app.application.ports import DraftToken
   from tests.fakes.fake_draft_store import FakeDraftStore
   ```
   Test body examples:
   ```python
   def _sample_bundle() -> DraftBundle:
       """Build a minimal DraftBundle for tests."""
       return DraftBundle(
           note=NoteDTO(content="n"),
           cards=[CardDTO(question="q?", answer="a.")],
       )


   def test_put_then_pop_returns_bundle() -> None:
       """put stores the bundle; pop returns it exactly once."""
       store = FakeDraftStore()
       token = DraftToken(uuid.uuid4())
       bundle = _sample_bundle()
       store.put(token, bundle)
       assert store.pop(token) == bundle


   def test_pop_is_atomic_read_and_delete() -> None:
       """After a successful pop, a second pop returns None."""
       store = FakeDraftStore()
       token = DraftToken(uuid.uuid4())
       store.put(token, _sample_bundle())
       _first = store.pop(token)
       assert store.pop(token) is None


   def test_force_expire_removes_token() -> None:
       """force_expire drops the token as if the TTL had fired."""
       store = FakeDraftStore()
       token = DraftToken(uuid.uuid4())
       store.put(token, _sample_bundle())
       store.force_expire(token)
       assert store.pop(token) is None
   ```

4. Create `tests/unit/fakes/test_fake_llm_provider.py`. Header:
   ```python
   # ABOUTME: FakeLLMProvider contract tests — call log + canned response.
   # ABOUTME: Proves public .calls_with and .next_response attributes work.
   """FakeLLMProvider unit tests."""

   from __future__ import annotations

   from app.application.dtos import CardDTO, NoteDTO
   from tests.fakes.fake_llm_provider import FakeLLMProvider
   ```
   Test body example:
   ```python
   def test_calls_with_logs_every_call() -> None:
       """Every call is recorded on .calls_with in order."""
       fake = FakeLLMProvider()
       fake.generate_note_and_cards(source_text=None, user_prompt="a")
       fake.generate_note_and_cards(source_text="src", user_prompt="b")
       assert fake.calls_with == [(None, "a"), ("src", "b")]


   def test_next_response_override_changes_return() -> None:
       """Mutating .next_response changes subsequent return values."""
       fake = FakeLLMProvider()
       fake.next_response = (
           NoteDTO(content="override"),
           [CardDTO(question="Q", answer="A")],
       )
       note, cards = fake.generate_note_and_cards(
           source_text=None, user_prompt="p"
       )
       assert note.content == "override"
       assert cards[0].question == "Q"
   ```

5. Run `uv run pytest tests/unit/fakes/test_fake_draft_store.py
   tests/unit/fakes/test_fake_llm_provider.py --collect-only` → expect
   `ModuleNotFoundError` on `tests.fakes.fake_draft_store` and
   `tests.fakes.fake_llm_provider`.

6. Commit. Message:
   `test(02-03): add failing tests for FakeDraftStore and FakeLLMProvider`

**Part B — GREEN: implement the two fakes.**

7. Create `tests/fakes/fake_draft_store.py` (verbatim from PATTERNS.md):
   ```python
   # ABOUTME: FakeDraftStore — dict wrapper with force_expire test hook.
   # ABOUTME: put writes; pop is atomic read-and-delete (dict.pop).
   """FakeDraftStore — hand-written fake for DraftStore port."""

   from __future__ import annotations

   from app.application.dtos import DraftBundle
   from app.application.ports import DraftToken


   class FakeDraftStore:
       """In-memory dict with an atomic pop and a force_expire hook."""

       def __init__(self) -> None:
           """Start with empty store + empty put log."""
           self._store: dict[DraftToken, DraftBundle] = {}
           self.puts: list[tuple[DraftToken, DraftBundle]] = []

       def put(self, token: DraftToken, bundle: DraftBundle) -> None:
           """Store the bundle and record the call."""
           self._store[token] = bundle
           self.puts.append((token, bundle))

       def pop(self, token: DraftToken) -> DraftBundle | None:
           """Atomic read-and-delete; returns None if missing or expired."""
           return self._store.pop(token, None)

       def force_expire(self, token: DraftToken) -> None:
           """Test hook: drop token as if its TTL had expired."""
           self._store.pop(token, None)
   ```

8. Create `tests/fakes/fake_llm_provider.py` (verbatim from PATTERNS.md):
   ```python
   # ABOUTME: Hand-written fake LLMProvider for Phase 2 use-case tests.
   # ABOUTME: Records calls on .calls_with; canned response overridable.
   """FakeLLMProvider — structural subtype of LLMProvider."""

   from __future__ import annotations

   from app.application.dtos import CardDTO, NoteDTO


   class FakeLLMProvider:
       """Records calls and returns a canned NoteDTO + cards list."""

       def __init__(self) -> None:
           """Start with empty call log + default canned response."""
           self.calls_with: list[tuple[str | None, str]] = []
           self.next_response: tuple[NoteDTO, list[CardDTO]] = (
               NoteDTO(content="fake note"),
               [CardDTO(question="q?", answer="a.")],
           )

       def generate_note_and_cards(
           self, source_text: str | None, user_prompt: str
       ) -> tuple[NoteDTO, list[CardDTO]]:
           """Record the call and return the current canned response."""
           self.calls_with.append((source_text, user_prompt))
           return self.next_response
   ```

9. Run `uv run pytest tests/unit/fakes/test_fake_draft_store.py
   tests/unit/fakes/test_fake_llm_provider.py -v` — all 9 tests pass.

10. `uv run ruff check tests/fakes/ tests/unit/fakes/` exits 0.
    `uv run ty check app` exits 0 (fakes are not in the ty scope yet;
    that is fine — structural subtyping is exercised in Plan 04's
    use-case test).

11. Commit. Message:
    `feat(02-03): add FakeDraftStore and FakeLLMProvider`
  </action>
  <verify>
    <automated>uv run pytest tests/unit/fakes/test_fake_draft_store.py tests/unit/fakes/test_fake_llm_provider.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `tests/fakes/__init__.py` exists with exactly two `# ABOUTME:` lines + module docstring + NO `from tests.fakes.*` imports yet (filled in Task 3).
    - `tests/unit/fakes/__init__.py` exists with two `# ABOUTME:` lines.
    - `tests/fakes/fake_draft_store.py` contains literal `class FakeDraftStore:`, method `def put(`, method `def pop(`, method `def force_expire(`, and the public attribute `self.puts: list[tuple[DraftToken, DraftBundle]]`.
    - `tests/fakes/fake_draft_store.py` does NOT inherit from `DraftStore` (structural subtyping only) — `grep "class FakeDraftStore" tests/fakes/fake_draft_store.py` shows `class FakeDraftStore:` without parentheses-inherited base.
    - `tests/fakes/fake_llm_provider.py` contains `class FakeLLMProvider:`, method `def generate_note_and_cards(`, public `self.calls_with: list[tuple[str | None, str]]`, public `self.next_response: tuple[NoteDTO, list[CardDTO]]`.
    - No use of `unittest.mock`, `Mock`, `MagicMock`, or `AsyncMock` anywhere under `tests/fakes/` or `tests/unit/fakes/`. Verify: `grep -rE "(unittest\.mock|Mock\(|MagicMock|AsyncMock)" tests/fakes/ tests/unit/fakes/` returns zero matches.
    - `uv run pytest tests/unit/fakes/test_fake_draft_store.py tests/unit/fakes/test_fake_llm_provider.py -v` exits 0 with 9 tests passed.
    - Both fake files are ≤100 lines (`wc -l`).
    - Two commits exist: `^test\(02-03\): add failing tests for FakeDraftStore and FakeLLMProvider` and `^feat\(02-03\): add FakeDraftStore and FakeLLMProvider`.
  </acceptance_criteria>
  <done>FakeDraftStore + FakeLLMProvider implemented, 9 tests green, no Mock anywhere. `tests/fakes/__init__.py` exists as a marker-only file.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Red→Green for four repository fakes</name>
  <read_first>
    - .planning/phases/02-domain-application-spine/02-CONTEXT.md (Claude's-discretion "Fake assertion style" — `.saved: dict[...]` or `.saved: list[...]`).
    - .planning/phases/02-domain-application-spine/02-RESEARCH.md §2.3 (dict-backed + list-backed fake shapes; per-port variations: note overwrite vs card append vs review list).
    - .planning/phases/02-domain-application-spine/02-PATTERNS.md "tests/fakes/fake_source_repository.py + fake_note_repository.py + fake_card_repository.py" and "tests/fakes/fake_card_review_repository.py" (full skeletons + variation notes).
    - app/application/ports.py (Protocol surfaces for the four repos).
    - app/domain/entities.py + value_objects.py (entity + typed-ID imports).
  </read_first>
  <behavior>
    Four fakes, each with its own RED→GREEN cycle. Commit RED + GREEN
    per repository. Tests exercise the contract via public `.saved` state.

    `tests/unit/fakes/test_fake_source_repository.py`:
    - `test_save_then_get_round_trips`: save a `Source`, `get(source.id) == source`.
    - `test_get_missing_returns_none`.
    - `test_saved_dict_exposes_state`: `fake.saved[source.id] is source`.
    - `test_save_overwrites_same_id`: save a `Source` with id X twice — `.saved` has one entry, latest wins.

    `tests/unit/fakes/test_fake_note_repository.py`:
    - `test_save_then_get_round_trips`.
    - `test_get_missing_returns_none`.
    - `test_save_overwrites_by_note_id`: two `Note`s with same id — latest wins.

    `tests/unit/fakes/test_fake_card_repository.py`:
    - `test_save_then_get_round_trips`.
    - `test_get_missing_returns_none`.
    - `test_save_overwrites_same_card_id`: same as note (dict-by-id semantics).
    - (Note: the "append-only regenerate" behavior lives in the
      use-case dispatcher in Phase 4, not inside the repo fake. Fake
      just stores by `card.id`.)

    `tests/unit/fakes/test_fake_card_review_repository.py`:
    - `test_save_appends_to_list`: three `save()` calls → `fake.saved`
      has three entries in insertion order.
    - `test_saved_is_list_not_dict`: `isinstance(fake.saved, list)`.
  </behavior>
  <action>
**Four Red→Green cycles. One per repository. Each cycle = 1 RED commit + 1 GREEN commit.**

**Cycle A — `FakeSourceRepository`:**

1. **RED**: Create `tests/unit/fakes/test_fake_source_repository.py`.
   Header:
   ```python
   # ABOUTME: FakeSourceRepository contract tests — dict-by-id semantics.
   # ABOUTME: Proves .saved exposes state assertable by round-trip tests.
   """FakeSourceRepository unit tests."""

   from __future__ import annotations

   from app.domain.entities import Source
   from app.domain.value_objects import SourceKind
   from tests.fakes.fake_source_repository import FakeSourceRepository
   ```
   Implement 4 tests per `<behavior>`. Example:
   ```python
   def test_save_then_get_round_trips() -> None:
       """save then get by id returns the same Source."""
       repo = FakeSourceRepository()
       src = Source(kind=SourceKind.TOPIC, user_prompt="p")
       repo.save(src)
       assert repo.get(src.id) == src
   ```
   Run tests → `ModuleNotFoundError`. Commit:
   `test(02-03): add failing tests for FakeSourceRepository`

2. **GREEN**: Create `tests/fakes/fake_source_repository.py` verbatim from
   PATTERNS.md "tests/fakes/fake_source_repository.py":
   ```python
   # ABOUTME: Dict-backed fake SourceRepository — exposes .saved state.
   # ABOUTME: Tests assert against repo.saved[source_id], no call tracking.
   """FakeSourceRepository — dict-backed in-memory fake."""

   from __future__ import annotations

   from app.domain.entities import Source
   from app.domain.value_objects import SourceId


   class FakeSourceRepository:
       """In-memory dict of Source entities keyed by SourceId."""

       def __init__(self) -> None:
           """Start with empty store."""
           self.saved: dict[SourceId, Source] = {}

       def save(self, source: Source) -> None:
           """Insert or overwrite the source entry."""
           self.saved[source.id] = source

       def get(self, source_id: SourceId) -> Source | None:
           """Return the stored source or None if missing."""
           return self.saved.get(source_id)
   ```
   Run tests → green. Commit:
   `feat(02-03): add FakeSourceRepository`

**Cycle B — `FakeNoteRepository`:**

3. RED: Create `tests/unit/fakes/test_fake_note_repository.py` with the
   three tests. Note: to build a `Note`, use
   `Note(source_id=Source(...).id, content="body")`. Import `Note` and
   `NoteId` from domain. Commit:
   `test(02-03): add failing tests for FakeNoteRepository`

4. GREEN: Create `tests/fakes/fake_note_repository.py`. Same pattern as
   `FakeSourceRepository` — dict keyed by `NoteId`. Per RESEARCH §2.3,
   regenerate-overwrite is the default dict-upsert semantic — no
   special-case logic in the fake. Commit:
   `feat(02-03): add FakeNoteRepository`

**Cycle C — `FakeCardRepository`:**

5. RED: Create `tests/unit/fakes/test_fake_card_repository.py`. Build a
   `Card` via `Card(source_id=src.id, question="q?", answer="a.")`. Three
   tests. Commit:
   `test(02-03): add failing tests for FakeCardRepository`

6. GREEN: Create `tests/fakes/fake_card_repository.py`. Dict keyed by
   `CardId`. The "append-only on regenerate" semantic is enforced by
   the Phase-4 use-case dispatcher checking `card.id` uniqueness before
   calling `save`; the fake itself is a plain dict upsert. Commit:
   `feat(02-03): add FakeCardRepository`

**Cycle D — `FakeCardReviewRepository`:**

7. RED: Create `tests/unit/fakes/test_fake_card_review_repository.py`.
   Build a `CardReview` via `CardReview(card_id=card.id, rating=Rating.CORRECT)`.
   Two tests. Commit:
   `test(02-03): add failing tests for FakeCardReviewRepository`

8. GREEN: Create `tests/fakes/fake_card_review_repository.py`. List-backed
   (per PATTERNS.md):
   ```python
   # ABOUTME: List-backed fake CardReviewRepository — append-only log.
   # ABOUTME: Tests assert on the list order of `.saved`.
   """FakeCardReviewRepository — hand-written list-backed fake."""

   from __future__ import annotations

   from app.domain.entities import CardReview


   class FakeCardReviewRepository:
       """Append-only list of CardReview entries."""

       def __init__(self) -> None:
           """Start with empty review log."""
           self.saved: list[CardReview] = []

       def save(self, review: CardReview) -> None:
           """Append the review to the log."""
           self.saved.append(review)
   ```
   Commit: `feat(02-03): add FakeCardReviewRepository`

**Verification after all four cycles:**

9. Run the full fake test suite so far:
   `uv run pytest tests/unit/fakes/ -v` — ≥20 tests pass (5 DraftStore +
   4 LLM + 4 Source + 3 Note + 3 Card + 2 CardReview = 21).

10. `uv run ruff check tests/fakes/ tests/unit/fakes/` exits 0.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/fakes/ -v</automated>
  </verify>
  <acceptance_criteria>
    - Six fake source files exist: `tests/fakes/fake_{source,note,card,card_review}_repository.py`, `tests/fakes/fake_draft_store.py`, `tests/fakes/fake_llm_provider.py`. All ≤100 lines.
    - `FakeSourceRepository`, `FakeNoteRepository`, `FakeCardRepository` each expose `self.saved: dict[...]` — verified by `grep "self.saved: dict\[" tests/fakes/fake_source_repository.py tests/fakes/fake_note_repository.py tests/fakes/fake_card_repository.py` returning 3 matches.
    - `FakeCardReviewRepository` exposes `self.saved: list[CardReview]` — verified by `grep "self.saved: list\[CardReview\]" tests/fakes/fake_card_review_repository.py`.
    - No fake inherits from its Protocol — `grep -E "class Fake[A-Z][a-zA-Z]+\(" tests/fakes/*.py` returns zero matches (classes declared without bases; structural subtyping).
    - No use of `Mock`/`MagicMock`/`AsyncMock` anywhere under `tests/fakes/` or `tests/unit/fakes/` (re-verify: `grep -rE "(unittest\.mock|Mock\(|MagicMock|AsyncMock)" tests/fakes/ tests/unit/fakes/` returns zero).
    - Six test files exist in `tests/unit/fakes/` covering each fake; `uv run pytest tests/unit/fakes/ -v` exits 0 with ≥21 tests passed.
    - `uv run ruff check tests/fakes/ tests/unit/fakes/` exits 0.
    - Git log shows 8 commits matching `^(test|feat)\(02-03\):` for cycles A through D (4 RED + 4 GREEN), plus the 2 from Task 1 (total ≥10 02-03 commits).
  </acceptance_criteria>
  <done>All four repository fakes implemented, 21 total fake tests passing. No Mock. No Protocol inheritance.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Wire re-exports + structural-subtype smoke test + `make check`</name>
  <read_first>
    - .planning/phases/02-domain-application-spine/02-PATTERNS.md "tests/fakes/__init__.py" (exact re-export list + `__all__`).
    - .planning/phases/02-domain-application-spine/02-CONTEXT.md Claude's-discretion "Fakes file layout" (re-export is the consumer API).
    - tests/fakes/__init__.py (Task 1 stub) and every tests/fakes/fake_*.py (Tasks 1-2 output).
    - Makefile `check:` target.
  </read_first>
  <behavior>
    - `tests/fakes/__init__.py` re-exports all six fakes with a complete
      `__all__` list — so use-case tests (Plan 04) can `from tests.fakes
      import FakeLLMProvider, FakeDraftStore, ...`.
    - One structural-subtype smoke test proves every fake matches its
      port's method signature. This test imports the Protocols at
      type-check time and the fakes at runtime, then asserts via
      annotated variables — the real assertion is that `ty` passes.

    New test file:

    `tests/unit/fakes/test_structural_subtype.py`:
    - `test_fakes_match_their_protocols`: for each (port, fake) pair,
      construct a variable annotated as the Protocol and assigned the
      fake instance. If shapes mismatch, `ty check` fails. Runtime
      assertion: `hasattr(fake, method_name)` for each Protocol method.
  </behavior>
  <action>
**Part A — Re-exports in `tests/fakes/__init__.py`.**

1. Replace `tests/fakes/__init__.py` (currently marker-only) with the
   full re-export version from PATTERNS.md:
   ```python
   # ABOUTME: Hand-written fakes for every application port.
   # ABOUTME: No Mock(); tests import `from tests.fakes import Fake*`.
   """Hand-written fake adapters (one per port)."""

   from tests.fakes.fake_card_repository import FakeCardRepository
   from tests.fakes.fake_card_review_repository import (
       FakeCardReviewRepository,
   )
   from tests.fakes.fake_draft_store import FakeDraftStore
   from tests.fakes.fake_llm_provider import FakeLLMProvider
   from tests.fakes.fake_note_repository import FakeNoteRepository
   from tests.fakes.fake_source_repository import FakeSourceRepository

   __all__ = [
       "FakeCardRepository",
       "FakeCardReviewRepository",
       "FakeDraftStore",
       "FakeLLMProvider",
       "FakeNoteRepository",
       "FakeSourceRepository",
   ]
   ```

2. Run `uv run python -c "from tests.fakes import FakeLLMProvider,
   FakeSourceRepository, FakeNoteRepository, FakeCardRepository,
   FakeCardReviewRepository, FakeDraftStore; print('ok')"` — prints `ok`.

**Part B — RED: structural-subtype smoke test.**

3. Create `tests/unit/fakes/test_structural_subtype.py`. This test
   exercises the structural-subtype contract at runtime and adds an
   `# type: ignore`-free block that ty type-checks. Header:
   ```python
   # ABOUTME: Proves every fake structurally subtypes its Protocol.
   # ABOUTME: Runtime: hasattr checks. Typecheck: annotated assignments.
   """Structural-subtype smoke tests for hand-written fakes."""

   from __future__ import annotations

   from app.application.ports import (
       CardRepository,
       CardReviewRepository,
       DraftStore,
       LLMProvider,
       NoteRepository,
       SourceRepository,
   )
   from tests.fakes import (
       FakeCardRepository,
       FakeCardReviewRepository,
       FakeDraftStore,
       FakeLLMProvider,
       FakeNoteRepository,
       FakeSourceRepository,
   )
   ```
   Body (one test asserts runtime shape, one exercises the type-check
   boundary via annotated assignment):
   ```python
   def test_fakes_have_required_public_methods() -> None:
       """Each fake exposes the public methods its Protocol declares."""
       assert hasattr(FakeLLMProvider(), "generate_note_and_cards")
       assert hasattr(FakeSourceRepository(), "save")
       assert hasattr(FakeSourceRepository(), "get")
       assert hasattr(FakeNoteRepository(), "save")
       assert hasattr(FakeNoteRepository(), "get")
       assert hasattr(FakeCardRepository(), "save")
       assert hasattr(FakeCardRepository(), "get")
       assert hasattr(FakeCardReviewRepository(), "save")
       assert hasattr(FakeDraftStore(), "put")
       assert hasattr(FakeDraftStore(), "pop")


   def test_fakes_are_assignable_to_their_protocols() -> None:
       """Structural-subtype check — ty validates the annotated vars."""
       llm: LLMProvider = FakeLLMProvider()
       sources: SourceRepository = FakeSourceRepository()
       notes: NoteRepository = FakeNoteRepository()
       cards: CardRepository = FakeCardRepository()
       reviews: CardReviewRepository = FakeCardReviewRepository()
       drafts: DraftStore = FakeDraftStore()
       assert llm is not None
       assert sources is not None
       assert notes is not None
       assert cards is not None
       assert reviews is not None
       assert drafts is not None
   ```

4. Run `uv run pytest tests/unit/fakes/test_structural_subtype.py -v`
   — both tests must pass. Commit:
   `test(02-03): add structural-subtype smoke tests for fakes`
   (no separate GREEN commit — the fakes already satisfy the contract
   from Tasks 1 and 2; this test is a backstop that catches a later
   drift).

**Part C — Final gates.**

5. Run `make check` end-to-end. Must exit 0. If `ty check` fails on any
   annotated-assignment line, the fake has drifted from the Protocol —
   fix the fake (not the Protocol — Phase 2 shapes are frozen per
   CONTEXT). Re-run `make check`.

6. Commit any formatter fixes if applied. Message:
   `chore(02-03): apply make check fixes`
   (skip if clean).
  </action>
  <verify>
    <automated>uv run pytest tests/unit/fakes/ -v && make check</automated>
  </verify>
  <acceptance_criteria>
    - `tests/fakes/__init__.py` contains the literal string `__all__` and exactly 6 `from tests.fakes.fake_*` imports (one per fake). Verify: `grep -c "^from tests.fakes.fake_" tests/fakes/__init__.py` returns `6` (module re-exports may be reformatted by ruff — also accept continuation-line imports, so the line count might differ; the `__all__` list must contain all six fake names).
    - `uv run python -c "from tests.fakes import FakeCardRepository, FakeCardReviewRepository, FakeDraftStore, FakeLLMProvider, FakeNoteRepository, FakeSourceRepository; print('ok')"` exits 0 and prints `ok`.
    - `tests/unit/fakes/test_structural_subtype.py` exists with ≥2 `def test_` functions.
    - `uv run pytest tests/unit/fakes/ -v` exits 0 with ≥23 tests passed (21 from Tasks 1-2 + 2 from Task 3).
    - `uv run ty check app tests/unit/fakes/test_structural_subtype.py` exits 0 — the annotated-assignment structural-subtype checks are load-bearing.
    - `make check` exits 0 — the full gate including format, lint, typecheck, docstrings, pytest.
    - Final `grep -rE "(unittest\.mock|Mock\(|MagicMock|AsyncMock)" tests/fakes/ tests/unit/fakes/` returns zero matches — the "no Mock" discipline for Plan 03 is load-bearing.
    - Commit exists with message matching `^test\(02-03\): add structural-subtype smoke tests for fakes`.
  </acceptance_criteria>
  <done>All seven fakes re-exported. Structural-subtype smoke test green. `make check` clean. Plan 03 closes Phase 2 SC #4 (fakes live under tests/fakes/, implement each Protocol by structural subtyping, expose assertable state, no Mock() behavior-testing).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

Fakes run only in tests. They consume domain entities (Plan 01) and
application DTOs (Plan 02) constructed by test code, and they never
cross a process boundary, network, filesystem, or DB. There is no
runtime trust boundary in this plan's production surface — the fakes
are test-only code that never ships in `app/`.

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-03-01 | Tampering | A fake silently drifts from its Protocol when a port signature changes, and a test passes against the fake but the real adapter fails | mitigate | Task 3's `test_fakes_are_assignable_to_their_protocols` is the type-check-time structural-subtype assertion. Plan 05's TEST-03 contract harness is the runtime backstop: fake + real impls exercise the same tests. Together these close PITFALL M7. |
| T-02-03-02 | Tampering | A fake re-implements a Protocol by inheritance (e.g., `class FakeDraftStore(DraftStore):`), which would mask a Protocol change by hiding the signature drift behind inheritance semantics | mitigate | Acceptance criteria `grep -E "class Fake[A-Z][a-zA-Z]+\("` explicitly forbids inheritance. Structural subtyping is the contract. |
| T-02-03-03 | Repudiation | A test author uses `unittest.mock.Mock` inside a fake or in a fake-unit-test, undermining TEST-01 | mitigate | Acceptance criteria `grep -rE "unittest\.mock\|Mock\("` returns zero. This gate is checked in every task in this plan. A CI grep belt-and-braces could be added later (flagged to Plan 05 / Phase 7). |
| T-02-03-04 | Information Disclosure | Fakes leak to production bundle | accept | Fakes live under `tests/` which is excluded from `hatch wheel` via `[tool.hatch.build.targets.wheel] packages = ["app"]` in `pyproject.toml`. `tests/` is not part of the package surface. |

No high-severity threats.
</threat_model>

<verification>
Phase-level verification (run after all three tasks complete):

```bash
# 1. All fake unit tests green
uv run pytest tests/unit/fakes/ -v
# Expected: ≥23 tests passed.

# 2. Re-export sanity check
uv run python -c "
from tests.fakes import (
    FakeCardRepository,
    FakeCardReviewRepository,
    FakeDraftStore,
    FakeLLMProvider,
    FakeNoteRepository,
    FakeSourceRepository,
)
print('all fakes importable')
"

# 3. No Mock anywhere
! grep -rE "(unittest\.mock|Mock\(|MagicMock|AsyncMock)" tests/fakes/ tests/unit/fakes/

# 4. No Protocol inheritance
! grep -E "class Fake[A-Z][a-zA-Z]+\(" tests/fakes/*.py

# 5. Public-state assertion style (sanity check — grep for .saved / .puts / .calls_with)
grep -rE "\.(saved|puts|calls_with|next_response)" tests/fakes/ tests/unit/fakes/ | wc -l
# Expected: ≥20 hits — proves the public-attribute style is used throughout.

# 6. Full gate
make check
```
</verification>

<success_criteria>
Plan 03 is complete when:

1. `tests/fakes/` contains 7 Python files: `__init__.py` (with
   `__all__` re-exports), 6 `fake_*.py` (one per port).
2. `tests/unit/fakes/` contains 7 test files covering each fake.
3. `uv run pytest tests/unit/fakes/ -v` exits 0 with ≥23 tests passed.
4. `make check` exits 0.
5. No fake inherits from its Protocol (structural subtyping only).
6. No `Mock()`/`MagicMock`/`AsyncMock` anywhere under `tests/fakes/` or
   `tests/unit/fakes/` (closes TEST-01's "no Mock() behavior-testing").
7. Every fake exposes `.saved` or `.puts` + `.calls_with` /
   `.next_response` as public attributes.
8. `FakeDraftStore` exposes `put` + `pop` + `force_expire` (TTL test hook
   per CONTEXT D-06) — discharges DRAFT-01's Phase-2 port-implementation.
9. ROADMAP Phase 2 SC #4 is satisfied:
   - Fakes live under `tests/fakes/` ✓
   - Implement each Protocol by structural subtyping ✓
   - Expose assertable state (not call patterns) ✓
   - Exercised by unit tests that use no `Mock()` behavior-testing ✓
</success_criteria>

<output>
After completion, create `.planning/phases/02-domain-application-spine/02-03-SUMMARY.md`
documenting:
- Seven fake files (with line counts).
- Seven unit-test files (with test counts per file).
- Commit list: per-cycle RED + GREEN pairs (≥8 commits for Tasks 1-2 +
  ≥1 for Task 3).
- Confirmation: zero `Mock()` usage; zero Protocol inheritance.
- Public-attribute style summary (which fake exposes what).
- Any deviations from the plan (expected: none).
</output>
