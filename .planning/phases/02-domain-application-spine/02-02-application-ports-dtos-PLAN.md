---
phase: 02-domain-application-spine
plan: 02
type: tdd
wave: 2
depends_on:
  - "02-01"
files_modified:
  - app/application/__init__.py
  - app/application/ports.py
  - app/application/dtos.py
  - app/application/exceptions.py
  - tests/unit/application/__init__.py
  - tests/unit/application/test_dtos.py
  - tests/unit/application/test_exceptions.py
  - tests/unit/application/test_ports.py
autonomous: true
requirements:
  - DRAFT-01
  - TEST-01
tags:
  - application
  - ports
  - dtos
  - protocol
  - pydantic
  - tdd
must_haves:
  truths:
    - "`app/application/ports.py` declares `LLMProvider`, `SourceRepository`, `NoteRepository`, `CardRepository`, `CardReviewRepository`, and `DraftStore` as `typing.Protocol`s (no `@runtime_checkable`) — closes DRAFT-01's port declaration."
    - "`app/application/ports.py` declares `UrlFetcher` and `SourceReader` as `typing.TypeAlias` on `Callable[[...], ...]` per CLAUDE.md Protocol-vs-function clarifier."
    - "`app/application/ports.py` declares `DraftToken = NewType(\"DraftToken\", uuid.UUID)`."
    - "`DraftStore` Protocol exposes exactly two methods: `put(token, bundle) -> None` and `pop(token) -> DraftBundle | None`. No `get`, no TTL API, no clock injection (per CONTEXT D-04/D-05)."
    - "`NoteDTO` and `CardDTO` are Pydantic `BaseModel` with `model_config = ConfigDict(extra=\"ignore\")` and `min_length=1` on required string fields."
    - "`GenerateRequest`, `GenerateResponse`, `DraftBundle` are `@dataclass(frozen=True)` — plain stdlib, no Pydantic."
    - "`UnsupportedSourceKind`, `DraftExpired`, `LLMOutputMalformed` are declared in `app/application/exceptions.py` and inherit from `app.domain.exceptions.DojoError`."
    - "`app/application/` imports only from stdlib, Pydantic, and `app.domain` — never from `app.infrastructure` or `app.web`."
  artifacts:
    - path: "app/application/__init__.py"
      provides: "Application package marker (ABOUTME + module docstring)."
    - path: "app/application/ports.py"
      provides: "Six Protocol ports + two Callable aliases + `DraftToken` NewType."
    - path: "app/application/dtos.py"
      provides: "Pydantic `NoteDTO`/`CardDTO` for LLM I/O boundary; stdlib frozen dataclasses `GenerateRequest`, `GenerateResponse`, `DraftBundle` for internal use-case types."
    - path: "app/application/exceptions.py"
      provides: "Application-layer exception hierarchy inheriting from `DojoError`."
    - path: "tests/unit/application/__init__.py"
      provides: "Application-layer unit-test package marker."
    - path: "tests/unit/application/test_dtos.py"
      provides: "Pydantic DTO validation tests + stdlib dataclass frozenness tests."
    - path: "tests/unit/application/test_exceptions.py"
      provides: "Application exception hierarchy smoke tests (inherit from `DojoError`, carry message)."
  key_links:
    - from: "app/application/ports.py"
      to: "app/domain/entities.py + app/domain/value_objects.py"
      via: "imports entity classes and typed-ID aliases for Protocol method signatures"
      pattern: "from app\\.domain\\."
    - from: "app/application/dtos.py"
      to: "app/domain/value_objects.py"
      via: "`GenerateRequest.kind: SourceKind` imports from domain"
      pattern: "from app\\.domain\\.value_objects import"
    - from: "app/application/exceptions.py"
      to: "app/domain/exceptions.py"
      via: "every application exception inherits from `DojoError`"
      pattern: "from app\\.domain\\.exceptions import DojoError"
---

<objective>
Deliver Phase 2's application-layer spine: the six Protocol ports + two
Callable aliases + `DraftToken` NewType, the Pydantic+dataclass DTOs, and
the application-layer exception hierarchy. After this plan lands, every
port shape Dojo will use for the rest of the project is frozen, and the
import contract from `app.application` inward is one-way (domain-only).

This plan contributes to ROADMAP Phase 2 Success Criterion #2 (ports
declared as Protocols without `@runtime_checkable`; aliases as Callables)
and partially discharges DRAFT-01 (DraftStore is a first-class Protocol
port; the in-memory concrete implementation is Phase 3's
`InMemoryDraftStore`). TEST-01's "hand-written fakes at every port
boundary" is unblocked — Plan 03 picks up the fakes once the Protocol
shapes are frozen here.

TDD applies per DTO and per exception class. Ports themselves are type
definitions with no runtime behavior beyond what the type-checker
validates, so their "test" is import-plus-ty-check: the test asserts the
ports module imports clean, every Protocol is `issubclass`-compatible
with `typing.Protocol`, and `FakeLLMProvider`-shape structural subtypes
pass a type-check smoke (the real structural-subtype exercise comes in
Plan 03).

File-size ceiling is 100 lines per CLAUDE.md. If `ports.py` exceeds it
with interrogate-compliant one-line docstrings, split per RESEARCH §2.2
into `ports/repositories.py` + `ports/llm.py` + `ports/draft_store.py` +
`ports/aliases.py` with an `app/application/ports/__init__.py`
re-exporting every name.
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

# Plan 01 output (required for imports)
@.planning/phases/02-domain-application-spine/02-01-SUMMARY.md
@app/domain/value_objects.py
@app/domain/entities.py
@app/domain/exceptions.py

# Phase 1 analog files
@app/settings.py
@app/logging_config.py
@app/infrastructure/__init__.py
@tests/unit/test_settings.py

<interfaces>
<!-- Inputs from Plan 01 (already merged at execution time). -->

From `app/domain/value_objects.py`:
```python
class SourceKind(Enum):
    FILE = "file"
    URL = "url"
    TOPIC = "topic"

class Rating(Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"

SourceId = NewType("SourceId", uuid.UUID)
NoteId = NewType("NoteId", uuid.UUID)
CardId = NewType("CardId", uuid.UUID)
ReviewId = NewType("ReviewId", uuid.UUID)
```

From `app/domain/entities.py`:
```python
@dataclass(frozen=True)
class Source: ...   # kind, user_prompt, input, id: SourceId, created_at
@dataclass(frozen=True)
class Note: ...     # source_id, content, id: NoteId, created_at
@dataclass(frozen=True)
class Card: ...     # source_id, question, answer, tags, id: CardId, created_at
@dataclass(frozen=True)
class CardReview:   # card_id, rating: Rating, id: ReviewId, reviewed_at
    @property
    def is_correct(self) -> bool: ...
```

From `app/domain/exceptions.py`:
```python
class DojoError(Exception):
    """Base class for all Dojo domain and application exceptions."""
```

<!-- Phase 1 Pydantic pattern analog — from app/settings.py lines 22-40 -->
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )
    anthropic_api_key: SecretStr = SecretStr("dev-placeholder")
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Red→Green for `dtos.py` + `exceptions.py`</name>
  <read_first>
    - .planning/phases/02-domain-application-spine/02-CONTEXT.md (D-07, D-08: GenerateRequest/Response shapes; Claude's discretion "Pydantic DTO posture": `ConfigDict(extra="ignore")` + `min_length=1`; "Domain vs application exception split").
    - .planning/phases/02-domain-application-spine/02-RESEARCH.md §2.2 (dtos.py and exceptions.py shapes), §3.7 (DTO return type `tuple[NoteDTO, list[CardDTO]]`).
    - .planning/phases/02-domain-application-spine/02-PATTERNS.md "app/application/dtos.py" + "app/application/exceptions.py" (full skeletons).
    - app/settings.py lines 22-51 (Pydantic v2 `model_config = SettingsConfigDict(...)` pattern + `@field_validator` validator shape).
    - app/domain/exceptions.py (Plan 01 output — `DojoError` base class).
    - tests/unit/test_settings.py lines 36-51 (Pydantic validation-test idiom with `monkeypatch.delenv` + `Settings(_env_file=None)`).
  </read_first>
  <behavior>
    TDD per DTO/exception. **Commit RED and GREEN separately per file.**

    `tests/unit/application/test_dtos.py` must include these failing
    tests first, then pass after implementation:
    - `test_card_dto_rejects_empty_question`: `CardDTO(question="", answer="a.")` raises `pydantic.ValidationError`.
    - `test_card_dto_rejects_empty_answer`: `CardDTO(question="q?", answer="")` raises `pydantic.ValidationError`.
    - `test_card_dto_default_tags_is_empty_tuple`: `CardDTO(question="q?", answer="a.").tags == ()`.
    - `test_card_dto_ignores_extra_fields`: `CardDTO(question="q?", answer="a.", bogus="x")` constructs successfully; `hasattr(card, "bogus")` is False.
    - `test_note_dto_rejects_empty_content`: `NoteDTO(content="")` raises `pydantic.ValidationError`.
    - `test_note_dto_ignores_extra_fields`: `NoteDTO(content="c", bogus="x")` constructs; `bogus` not set.
    - `test_generate_request_is_frozen`: `GenerateRequest` instance cannot have attributes mutated — raises `dataclasses.FrozenInstanceError`.
    - `test_generate_request_allows_none_input_for_topic`: `GenerateRequest(kind=SourceKind.TOPIC, input=None, user_prompt="p")` constructs cleanly.
    - `test_generate_response_holds_token_and_bundle`: `GenerateResponse(token=..., bundle=DraftBundle(note=..., cards=[...]))` — attribute access works.
    - `test_draft_bundle_is_frozen`: `DraftBundle` attribute mutation raises `FrozenInstanceError`.

    `tests/unit/application/test_exceptions.py` must include:
    - `test_unsupported_source_kind_inherits_dojo_error`: `issubclass(UnsupportedSourceKind, DojoError)`.
    - `test_draft_expired_inherits_dojo_error`: `issubclass(DraftExpired, DojoError)`.
    - `test_llm_output_malformed_inherits_dojo_error`: `issubclass(LLMOutputMalformed, DojoError)`.
    - `test_application_exception_carries_message`: raising `UnsupportedSourceKind("x")` → `str(exc) == "x"`.
  </behavior>
  <action>
**Part A — RED: write failing tests.**

1. Create `tests/unit/application/__init__.py` with the ABOUTME pattern
   (two lines) + module docstring:
   ```python
   # ABOUTME: Application-layer unit tests.
   # ABOUTME: Ports, DTOs, exceptions, use cases — fake-driven.
   """Application unit tests."""
   ```

2. Create `tests/unit/application/test_dtos.py`. Header (per PATTERNS.md
   "tests/unit/application/test_dtos.py"):
   ```python
   # ABOUTME: Pydantic DTO validation + frozen-dataclass tests.
   # ABOUTME: Covers NoteDTO, CardDTO, GenerateRequest, Response, Bundle.
   """Application DTO unit tests."""

   from __future__ import annotations

   from dataclasses import FrozenInstanceError

   import pytest
   from pydantic import ValidationError

   from app.application.dtos import (
       CardDTO,
       DraftBundle,
       GenerateRequest,
       GenerateResponse,
       NoteDTO,
   )
   from app.application.ports import DraftToken
   from app.domain.value_objects import SourceKind
   ```
   Add the 10 `def test_*` functions listed in `<behavior>`. Each has a
   one-line docstring. Assertion patterns follow PATTERNS.md examples.
   For `test_generate_response_holds_token_and_bundle`, construct a
   `DraftToken` via `DraftToken(uuid.uuid4())` (import `uuid`).

3. Create `tests/unit/application/test_exceptions.py`. Header:
   ```python
   # ABOUTME: Application-layer exception hierarchy tests.
   # ABOUTME: Every exception inherits from DojoError; messages round-trip.
   """Application exception tests."""

   from __future__ import annotations

   from app.application.exceptions import (
       DraftExpired,
       LLMOutputMalformed,
       UnsupportedSourceKind,
   )
   from app.domain.exceptions import DojoError
   ```
   Add the 4 tests listed in `<behavior>`.

4. Run `uv run pytest tests/unit/application/ --collect-only` — expect
   `ModuleNotFoundError` on `app.application.dtos`, `app.application.ports`,
   and `app.application.exceptions`.

5. Commit. Message:
   `test(02-02): add failing tests for application DTOs and exceptions`

**Part B — GREEN: implement the modules (minimum needed for tests to pass).**

6. Create `app/application/__init__.py`:
   ```python
   # ABOUTME: Application layer — ports, DTOs, use cases.
   # ABOUTME: Depends on app.domain only; no infrastructure / web imports.
   """Application layer package."""
   ```

7. Create `app/application/exceptions.py` (copy PATTERNS.md skeleton
   verbatim):
   ```python
   # ABOUTME: Application-layer exception hierarchy.
   # ABOUTME: Every class inherits from app.domain.exceptions.DojoError.
   """Application-layer exceptions."""

   from __future__ import annotations

   from app.domain.exceptions import DojoError


   class UnsupportedSourceKind(DojoError):
       """Raised when a source kind is not yet supported by the use case."""


   class DraftExpired(DojoError):
       """Raised when a draft token has expired or was already popped."""


   class LLMOutputMalformed(DojoError):
       """Raised when the LLM's structured output fails DTO validation."""
   ```

8. Create **a stub** `app/application/ports.py` with only `DraftToken` +
   a forward-ref to `DraftBundle` so `test_dtos.py` imports resolve. Full
   ports implementation lands in Task 2; here we need just:
   ```python
   # ABOUTME: Application ports — Protocols, Callable aliases, NewTypes.
   # ABOUTME: Full surface lands in 02-02 Task 2; Task 1 declares DraftToken.
   """Application ports (partial — see Task 2 for full surface)."""

   from __future__ import annotations

   import uuid
   from typing import NewType

   DraftToken = NewType("DraftToken", uuid.UUID)
   ```
   (Task 2 expands this file with Protocols and Callable aliases. This
   incremental split keeps Task 1's tests laser-focused on DTOs.)

9. Create `app/application/dtos.py`. Copy PATTERNS.md skeleton and extend
   to include `DraftBundle` (per CONTEXT D-08):
   ```python
   # ABOUTME: Pydantic DTOs for LLM I/O + stdlib dataclasses for use cases.
   # ABOUTME: extra="ignore" + min_length=1 per CONTEXT Pydantic posture.
   """Application DTOs — LLM boundary + internal use-case types."""

   from __future__ import annotations

   from dataclasses import dataclass, field

   from pydantic import BaseModel, ConfigDict, Field

   from app.application.ports import DraftToken
   from app.domain.value_objects import SourceKind


   class NoteDTO(BaseModel):
       """Structured note output from LLM provider."""

       model_config = ConfigDict(extra="ignore")

       content: str = Field(min_length=1)


   class CardDTO(BaseModel):
       """One Q&A card produced by LLM provider."""

       model_config = ConfigDict(extra="ignore")

       question: str = Field(min_length=1)
       answer: str = Field(min_length=1)
       tags: tuple[str, ...] = ()


   @dataclass(frozen=True)
   class DraftBundle:
       """Proposed note + cards held in the draft store pre-save."""

       note: NoteDTO
       cards: list[CardDTO]


   @dataclass(frozen=True)
   class GenerateRequest:
       """Request to `GenerateFromSource.execute`."""

       kind: SourceKind
       input: str | None
       user_prompt: str


   @dataclass(frozen=True)
   class GenerateResponse:
       """Response envelope with draft token + bundle."""

       token: DraftToken
       bundle: DraftBundle
   ```

10. Run `uv run pytest tests/unit/application/test_dtos.py
    tests/unit/application/test_exceptions.py -v` — all 14 tests must
    pass (GREEN).

11. Run `uv run ruff check app/application/ tests/unit/application/` and
    `uv run ty check app` and `uv run interrogate -c pyproject.toml app` —
    all exit 0.

12. Commit. Message:
    `feat(02-02): add application DTOs, exceptions, and DraftToken`

**Sizing contingency:** if `dtos.py` exceeds 100 lines after full skeleton,
split into `dtos/llm_io.py` (`NoteDTO`, `CardDTO`) + `dtos/use_case.py`
(`GenerateRequest`, `GenerateResponse`, `DraftBundle`) with
`dtos/__init__.py` re-exporting. Task plan estimate: 60-80 LOC (under
limit).
  </action>
  <verify>
    <automated>uv run pytest tests/unit/application/test_dtos.py tests/unit/application/test_exceptions.py -v && uv run ruff check app/application/ tests/unit/application/ && uv run ty check app && uv run interrogate -c pyproject.toml app</automated>
  </verify>
  <acceptance_criteria>
    - `app/application/__init__.py` exists with two `# ABOUTME:` lines.
    - `app/application/exceptions.py` contains `class UnsupportedSourceKind(DojoError):`, `class DraftExpired(DojoError):`, `class LLMOutputMalformed(DojoError):`.
    - `app/application/dtos.py` contains: `class NoteDTO(BaseModel):`, `class CardDTO(BaseModel):`, `model_config = ConfigDict(extra="ignore")`, `question: str = Field(min_length=1)`, `answer: str = Field(min_length=1)`, `tags: tuple[str, ...] = ()`, `class DraftBundle:`, `class GenerateRequest:`, `class GenerateResponse:`, `@dataclass(frozen=True)` (appears ≥3 times).
    - `app/application/ports.py` contains `DraftToken = NewType("DraftToken", uuid.UUID)` (full Protocol surface lands in Task 2 of this plan).
    - `grep -E "^(from|import) " app/application/dtos.py app/application/exceptions.py` shows only stdlib, `pydantic`, `app.application`, and `app.domain` imports — no `app.infrastructure`, no `app.web`.
    - `uv run pytest tests/unit/application/test_dtos.py tests/unit/application/test_exceptions.py -v` exits 0 with exactly 14 tests passed.
    - `uv run ruff check app/application/ tests/unit/application/` exits 0.
    - `uv run ty check app` exits 0.
    - `uv run interrogate -c pyproject.toml app` exits 0 with `100.0%`.
    - Two commits exist with messages matching `^test\(02-02\):` and `^feat\(02-02\):`.
  </acceptance_criteria>
  <done>14 DTO + exception tests pass. `app/application/` contains 4 files. `ports.py` has `DraftToken` stub only; full surface comes in Task 2.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Expand `ports.py` — full Protocol surface + Callable aliases</name>
  <read_first>
    - .planning/phases/02-domain-application-spine/02-CONTEXT.md (D-04: `DraftStore` Protocol with exactly `put` + atomic `pop`; D-05: TTL in docstring only; D-10: `LLMProvider.generate_note_and_cards(source_text, user_prompt)`; Claude's discretion "Protocol method docstrings").
    - .planning/phases/02-domain-application-spine/02-RESEARCH.md §2.2 (ports.py sizing flag + split criteria), §3.5-3.7 (DraftStore / SourceRepository / LLMProvider shapes).
    - .planning/phases/02-domain-application-spine/02-PATTERNS.md "app/application/ports.py" (full module skeleton + TypeAlias pattern + no-`@runtime_checkable` rule).
    - app/application/dtos.py (Task 1 output — Protocol signatures reference `NoteDTO`, `CardDTO`, `DraftBundle`).
    - app/logging_config.py (module-header + `from __future__ import annotations` pattern for single-file spine modules).
    - CLAUDE.md "Protocol vs function" clarifier (project-local rule: stateless one-op = `Callable` alias; stateful/multi-method = `typing.Protocol`).
  </read_first>
  <behavior>
    Expand `app/application/ports.py` from its Task-1 stub (just
    `DraftToken`) to the full Phase 2 port surface per CONTEXT + PATTERNS.
    There are no new runtime tests — Protocols are structural contracts,
    not runtime objects. Instead:

    - Add a `tests/unit/application/test_ports.py` with smoke tests that
      (a) import every port name and (b) assert `DraftStore` is a
      `typing.Protocol` (not `@runtime_checkable`), via
      `typing.get_protocol_members(DraftStore) == {"put", "pop"}` (Python
      3.13+) OR for 3.12 compatibility via `DraftStore.__protocol_attrs__`
      / a behavioral smoke: assert a stub class with matching methods
      passes `isinstance` via a structural helper **written in the test**
      (don't add `@runtime_checkable` to the port itself).

    - Actually — RESEARCH §3.5-3.7 covers DraftStore/SourceRepository/
      LLMProvider behavior via fakes, which Plan 03 adds. In Plan 02 we
      only need to prove the ports **import clean** and expose the
      required names. Keep the port smoke test minimal (name-import +
      module-level presence checks).
  </behavior>
  <action>
**Part A — RED: add port-surface smoke tests.**

1. Create `tests/unit/application/test_ports.py`. Header:
   ```python
   # ABOUTME: Application-ports smoke tests — surface + docstring shape.
   # ABOUTME: Behavioral tests for each port land in fakes (Plan 03).
   """Application ports smoke tests."""

   from __future__ import annotations

   from collections.abc import Callable

   from app.application import ports
   ```

2. Add these failing tests:
   - `test_six_protocols_declared`: assert every name in
     `{"LLMProvider", "SourceRepository", "NoteRepository",
     "CardRepository", "CardReviewRepository", "DraftStore"}` is an
     attribute of `ports` module.
   - `test_two_callable_aliases_declared`: assert `hasattr(ports,
     "UrlFetcher")` and `hasattr(ports, "SourceReader")`.
   - `test_draft_token_is_new_type_over_uuid`: assert
     `ports.DraftToken.__supertype__ is __import__("uuid").UUID` (NewType
     exposes the underlying type via `__supertype__`).
   - `test_draft_store_protocol_methods`: assert `hasattr(ports.DraftStore,
     "put")` and `hasattr(ports.DraftStore, "pop")` and no attribute
     `get` is declared on the Protocol (per CONTEXT D-04: atomic-pop-only).
     Check: `"get" not in {m for m in dir(ports.DraftStore) if not
     m.startswith("_")}`.
   - `test_no_runtime_checkable`: assert `getattr(ports.DraftStore,
     "_is_runtime_protocol", False) is False` (Python runtime flag set
     by `@runtime_checkable`; we explicitly forbid it per CONTEXT).

3. Run `uv run pytest tests/unit/application/test_ports.py -v` → expect
   fails (`LLMProvider`/`SourceRepository`/etc. missing from
   `app.application.ports`).

4. Commit. Message:
   `test(02-02): add failing smoke tests for full ports surface`

**Part B — GREEN: expand `ports.py`.**

5. Replace `app/application/ports.py` with the full Protocol surface.
   Structure (derived from PATTERNS.md + CONTEXT D-04/D-05/D-10):

   ```python
   # ABOUTME: Application ports — Protocols, Callable aliases, NewTypes.
   # ABOUTME: Structural subtyping; no @runtime_checkable (zero runtime cost).
   """Application layer ports (DIP boundary)."""

   from __future__ import annotations

   import uuid
   from collections.abc import Callable
   from pathlib import Path
   from typing import NewType, Protocol, TypeAlias

   from app.application.dtos import CardDTO, DraftBundle, NoteDTO
   from app.domain.entities import Card, CardReview, Note, Source
   from app.domain.value_objects import (
       CardId,
       NoteId,
       ReviewId,
       SourceId,
   )


   DraftToken = NewType("DraftToken", uuid.UUID)


   class LLMProvider(Protocol):
       """Port for note + card generation via a language model."""

       def generate_note_and_cards(
           self,
           source_text: str | None,
           user_prompt: str,
       ) -> tuple[NoteDTO, list[CardDTO]]:
           """Generate a structured note + card list; raise LLMOutputMalformed on invalid shape."""
           ...


   class SourceRepository(Protocol):
       """Port for persisting and retrieving `Source` entities."""

       def save(self, source: Source) -> None:
           """Upsert the source row keyed by `source.id`."""
           ...

       def get(self, source_id: SourceId) -> Source | None:
           """Return the stored source or None if absent."""
           ...


   class NoteRepository(Protocol):
       """Port for persisting `Note` entities (regenerate-overwrites)."""

       def save(self, note: Note) -> None:
           """Upsert; regenerate-overwrite semantics enforced by adapter."""
           ...

       def get(self, note_id: NoteId) -> Note | None:
           """Return the stored note or None if absent."""
           ...


   class CardRepository(Protocol):
       """Port for persisting `Card` entities (regenerate-appends)."""

       def save(self, card: Card) -> None:
           """Insert the card; adapters do not overwrite existing ids."""
           ...

       def get(self, card_id: CardId) -> Card | None:
           """Return the stored card or None if absent."""
           ...


   class CardReviewRepository(Protocol):
       """Port for append-only `CardReview` log."""

       def save(self, review: CardReview) -> None:
           """Append the review to the persistent log."""
           ...


   class DraftStore(Protocol):
       """In-memory holder for pending draft bundles (30-min TTL).

       Concurrency: put/pop are atomic in the adapter; `pop` is
       read-and-delete. There is no `get` — callers commit-or-discard.
       """

       def put(self, token: DraftToken, bundle: DraftBundle) -> None:
           """Store the bundle under the token; TTL starts on write."""
           ...

       def pop(self, token: DraftToken) -> DraftBundle | None:
           """Atomic read-and-delete; returns None if absent or expired."""
           ...


   UrlFetcher: TypeAlias = Callable[[str], str]
   """Async URL → text fetcher (stateless). Phase 3 trafilatura adapter."""

   SourceReader: TypeAlias = Callable[[Path], str]
   """Path → raw-text reader (stateless). Phase 3 filesystem adapter."""
   ```

6. Run `uv run pytest tests/unit/application/test_ports.py -v` — all 5
   tests pass.

7. Run the full application unit-test suite:
   `uv run pytest tests/unit/application/ -v` — all 19 tests pass
   (5 ports + 10 dtos + 4 exceptions).

8. Run `uv run ruff check app/application/` and `uv run ty check app`
   and `uv run interrogate -c pyproject.toml app` — all exit 0.
   Interrogate 100% is the load-bearing gate: every Protocol method has
   a one-line docstring.

9. **Sizing check:** `wc -l app/application/ports.py`. If result >100:
   split per RESEARCH §2.2 into `app/application/ports/__init__.py`,
   `ports/llm.py` (LLMProvider), `ports/repositories.py` (4 repos),
   `ports/draft_store.py` (DraftStore + DraftToken), `ports/aliases.py`
   (UrlFetcher, SourceReader). `ports/__init__.py` must re-export every
   name so external imports stay `from app.application.ports import ...`.
   After split, rerun Task 1 + Task 2 tests + `make check`.

10. Run `make check` end-to-end — must exit 0.

11. Commit. Message:
    `feat(02-02): add full application ports surface (6 Protocols + 2 aliases)`
    Or, if split was required: separate commits for the split, then the
    surface.
  </action>
  <verify>
    <automated>uv run pytest tests/unit/application/ -v && make check</automated>
  </verify>
  <acceptance_criteria>
    - `app/application/ports.py` (or `app/application/ports/__init__.py` if split) exports: `LLMProvider`, `SourceRepository`, `NoteRepository`, `CardRepository`, `CardReviewRepository`, `DraftStore`, `UrlFetcher`, `SourceReader`, `DraftToken`. Verify: `uv run python -c "from app.application.ports import LLMProvider, SourceRepository, NoteRepository, CardRepository, CardReviewRepository, DraftStore, UrlFetcher, SourceReader, DraftToken; print('ok')"` prints `ok` and exits 0.
    - `ports.py` does NOT contain the string `@runtime_checkable` (verify: `grep -c "runtime_checkable" app/application/ports.py 2>/dev/null || grep -rc "runtime_checkable" app/application/ports/ 2>/dev/null` returns `0`).
    - `DraftStore` Protocol has exactly `put` and `pop` public methods — no `get`. Verify: `grep -E "^\s+def " app/application/ports.py | grep -A0 -B3 "DraftStore"` (or in split layout, same grep on `ports/draft_store.py`) lists only `put` and `pop` under that class.
    - Every file in `app/application/ports*` is ≤100 lines (`find app/application -name "ports*" -name "*.py" -exec wc -l {} +` shows no entry >100).
    - `LLMProvider.generate_note_and_cards` signature takes `source_text: str | None` and `user_prompt: str` and returns `tuple[NoteDTO, list[CardDTO]]` per CONTEXT D-10 (`grep -A3 "def generate_note_and_cards" app/application/ports*.py`).
    - `UrlFetcher` and `SourceReader` are declared via `TypeAlias` on `Callable[...]` — NOT as Protocols (`grep -E "UrlFetcher|SourceReader" app/application/ports*.py` shows `TypeAlias = Callable[`).
    - `uv run pytest tests/unit/application/ -v` exits 0 with ≥19 tests passed.
    - `make check` exits 0.
    - `grep -rE "^(from|import) " app/application/` shows only imports from stdlib, `pydantic`, `app.application.*`, and `app.domain.*` — zero infrastructure/web imports (belt-and-braces for the Plan 05 import-linter contract).
    - Commit exists with message matching `^feat\(02-02\): add full application ports surface`.
  </acceptance_criteria>
  <done>All 6 Protocols + 2 Callable aliases + `DraftToken` declared. Port shapes frozen. `make check` green. Port surface ready for Plan 03's fakes to structurally subtype.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

Phase 2 application layer has **no runtime trust boundaries**. Ports are
declarative types; DTOs and exceptions are pure data. No network, no
filesystem, no DB access. The only external surface is Pydantic
validation inside `NoteDTO`/`CardDTO`, which is defensive code for when
Phase 3's `AnthropicLLMProvider` deserialises tool-use output.

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-02-01 | Tampering | Malformed LLM output mutates into a `NoteDTO`/`CardDTO` with empty content and flows into the draft store / DB | mitigate | `model_config = ConfigDict(extra="ignore")` + `Field(min_length=1)` on `CardDTO.question`, `CardDTO.answer`, `NoteDTO.content`. Tests `test_*_dto_rejects_empty_*` assert the validation fires. PITFALL M6 closes the empty-string escape. Phase 3's adapter re-validates with `LLMOutputMalformed` exception wrapping. |
| T-02-02-02 | Tampering | A `DraftStore` adapter author side-steps the atomic-pop contract by adding a `get` method | mitigate | CONTEXT D-04 freezes the Protocol to `put` + `pop` only. Test `test_draft_store_protocol_methods` asserts `get` is not an attribute. Plan 05's `import-linter` + TEST-03 contract harness adds structural-contract enforcement across fake + real implementations. |
| T-02-02-03 | Information Disclosure | `app/application/` accidentally imports `Settings`/`ANTHROPIC_API_KEY` and leaks it across the DIP boundary | mitigate | Import-grep check in acceptance criteria (no `app.infrastructure` / `app.web` imports). Structural enforcement via import-linter contract `Application must not depend on infrastructure or web` lands in Plan 05. |
| T-02-02-04 | Elevation of Privilege | A future port surface-change silently adds a privileged method (e.g., `DraftStore.admin_purge`) without review | accept | Low severity (single-user local app). No mitigation this phase. Future phases re-lint via import-linter and unit tests. |

No high-severity threats.
</threat_model>

<verification>
Phase-level verification (run after both tasks complete):

```bash
# 1. Application unit tests green
uv run pytest tests/unit/application/ -v

# 2. Port imports resolve
uv run python -c "
from app.application.ports import (
    CardRepository,
    CardReviewRepository,
    DraftStore,
    DraftToken,
    LLMProvider,
    NoteRepository,
    SourceReader,
    SourceRepository,
    UrlFetcher,
)
print('all ports importable')
"

# 3. No runtime_checkable
! grep -rE "@runtime_checkable|runtime_checkable" app/application/

# 4. Inward-only imports
grep -rE "^(from|import) " app/application/ | grep -E "(app\.infrastructure|app\.web)" && echo "LEAK!" || echo "inward-only OK"
# Expected: "inward-only OK"

# 5. Full gate
make check

# 6. File sizes
find app/application tests/unit/application -name "*.py" -exec wc -l {} + | awk '$1 > 100 {print "TOO LARGE:", $0}'
# Expected: no output.
```
</verification>

<success_criteria>
Plan 02 is complete when:

1. `app/application/` contains `__init__.py`, `ports.py` (or `ports/`
   subpackage after split), `dtos.py`, `exceptions.py` — every Python
   file ≤100 lines, two `# ABOUTME:` lines, interrogate 100%.
2. `tests/unit/application/` contains `__init__.py`, `test_dtos.py`,
   `test_exceptions.py`, `test_ports.py`.
3. `uv run pytest tests/unit/application/ -v` exits 0 with ≥19 tests
   passed.
4. `make check` exits 0.
5. Port surface: 6 Protocols (`LLMProvider`, `SourceRepository`,
   `NoteRepository`, `CardRepository`, `CardReviewRepository`,
   `DraftStore`), 2 Callable aliases (`UrlFetcher`, `SourceReader`),
   1 NewType (`DraftToken`). None carry `@runtime_checkable`.
6. `DraftStore` has exactly `put` + `pop`; no `get` (closes PITFALL C10's
   read-then-delete race at the port level per CONTEXT D-04).
7. ROADMAP Phase 2 SC #2 satisfied (ports declared, no
   `@runtime_checkable`, Callable aliases present).
8. DRAFT-01 port declaration discharged here; fake + concrete
   implementation in Plan 03 / Phase 3.
</success_criteria>

<output>
After completion, create `.planning/phases/02-domain-application-spine/02-02-SUMMARY.md`
documenting:
- Files created (with line counts).
- Whether `ports.py` required a split (≤100-line contingency).
- Test breakdown (dtos / exceptions / ports).
- Port surface snapshot (6 Protocols + 2 aliases + 1 NewType).
- Commit hashes for each RED/GREEN pair.
- Confirmation that no `@runtime_checkable` decorator appears anywhere.
</output>
