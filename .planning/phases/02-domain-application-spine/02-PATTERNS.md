# Phase 2: Domain & Application Spine — Pattern Map

**Mapped:** 2026-04-22
**Files analyzed:** 31 created + 2 modified = 33
**Analogs found:** 22 / 33 (11 files are new-territory — see §"No Analog Found")

---

## File Classification

### Created (31 files)

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `app/domain/__init__.py` | package-marker | n/a | `app/infrastructure/db/__init__.py` | exact |
| `app/domain/value_objects.py` | value-object module (enums + NewType aliases) | transform (type defs) | `app/settings.py` (module shape) | partial (shape only — no VO analog exists) |
| `app/domain/entities.py` | domain entities (frozen dataclasses) | transform | — (no Phase 1 dataclass analog) | none |
| `app/domain/exceptions.py` | exceptions module | n/a | — (first layer exceptions file) | none |
| `app/application/__init__.py` | package-marker | n/a | `app/infrastructure/__init__.py` | exact |
| `app/application/ports.py` | Protocol + Callable port definitions | type defs | `app/settings.py` (module shape only) | partial (Protocol idiom is fresh) |
| `app/application/dtos.py` | Pydantic DTOs + stdlib dataclasses | transform | `app/settings.py` (Pydantic BaseSettings pattern) | role-match (Pydantic idiom transfers) |
| `app/application/exceptions.py` | exceptions module | n/a | — (new) | none |
| `app/application/use_cases/__init__.py` | package-marker | n/a | `app/web/routes/__init__.py` | exact |
| `app/application/use_cases/generate_from_source.py` | use case (small orchestrator) | request-response | `app/web/routes/home.py` (thin orchestrator shape) | role-match (orchestrator shape transfers) |
| `tests/fakes/__init__.py` | package-marker + re-exports | n/a | `app/web/routes/__init__.py` (markers) + `tests/__init__.py` | partial (re-export list is new) |
| `tests/fakes/fake_llm_provider.py` | hand-written fake (port impl) | stateful, call-record | — | none |
| `tests/fakes/fake_source_repository.py` | hand-written fake (dict-backed repo) | CRUD | — | none |
| `tests/fakes/fake_note_repository.py` | hand-written fake (dict-backed repo) | CRUD | — | none |
| `tests/fakes/fake_card_repository.py` | hand-written fake (dict-backed repo) | CRUD | — | none |
| `tests/fakes/fake_card_review_repository.py` | hand-written fake (list-backed repo) | append-only | — | none |
| `tests/fakes/fake_draft_store.py` | hand-written fake (atomic pop) | pub-sub-style one-shot | — | none |
| `tests/unit/domain/__init__.py` | package-marker | n/a | `tests/unit/__init__.py` | exact |
| `tests/unit/domain/test_source.py` | unit test (entity invariants) | pure | `tests/unit/test_settings.py` (unit test idiom) | role-match |
| `tests/unit/domain/test_note.py` | unit test (entity invariants) | pure | `tests/unit/test_settings.py` | role-match |
| `tests/unit/domain/test_card.py` | unit test (entity invariants) | pure | `tests/unit/test_settings.py` | role-match |
| `tests/unit/domain/test_card_review.py` | unit test (entity invariants) | pure | `tests/unit/test_settings.py` | role-match |
| `tests/unit/domain/test_value_objects.py` | unit test (enum + NewType smoke) | pure | `tests/unit/test_settings.py` | role-match |
| `tests/unit/domain/test_exceptions.py` | unit test (exception hierarchy) | pure | `tests/unit/test_settings.py` | role-match |
| `tests/unit/application/__init__.py` | package-marker | n/a | `tests/unit/__init__.py` | exact |
| `tests/unit/application/test_dtos.py` | unit test (Pydantic + dataclass validation) | pure | `tests/unit/test_settings.py` (Pydantic validation test idiom) | role-match |
| `tests/unit/application/test_exceptions.py` | unit test (exception inheritance) | pure | `tests/unit/test_settings.py` | role-match |
| `tests/unit/application/test_generate_from_source.py` | unit test (use-case wiring, fake-driven) | fixture-driven | `tests/integration/test_db_smoke.py` (fixture-consumer idiom) | partial (no Phase 1 use-case test exists) |
| `tests/contract/__init__.py` | package-marker | n/a | `tests/integration/__init__.py` | exact |
| `tests/contract/test_llm_provider_contract.py` | contract test (param fixture + importorskip + env gate) | fixture-driven | — | none (TEST-03 harness is new) |

### Modified (2 files)

| Modified File | What Changes | Analog Pattern |
|---------------|--------------|----------------|
| `pyproject.toml` | Add `import-linter>=2.0` to `[dependency-groups] dev`; append `[tool.importlinter]` + two `[[tool.importlinter.contracts]]` blocks | Existing `[tool.ruff]`, `[tool.pytest.ini_options]`, `[tool.interrogate]` sections are the placement-style guide |
| `Makefile` | Split `lint` target: run `uv run ruff check --fix .` then `uv run lint-imports` | Existing `check:` target's multi-step pattern |

---

## Pattern Assignments

### `app/domain/__init__.py` (package-marker)

**Analog:** `/Users/pvardanis/Documents/projects/dojo/app/infrastructure/db/__init__.py`

**Full pattern to copy** (all 3 content lines — ABOUTME + one-line docstring, no re-exports):
```python
# ABOUTME: DB-infrastructure subpackage (engine, session, repos).
# ABOUTME: Phase 1 provides Base + session; Phase 3 adds repositories.
"""Database infrastructure subpackage."""
```

**Adapt to:**
```python
# ABOUTME: Domain layer — pure entities, value objects, exceptions.
# ABOUTME: stdlib-only; no I/O, no Pydantic, no ORM imports.
"""Dojo domain layer."""
```

**Rule from CONTEXT.md D-11 (Phase 1):** package markers contain ABOUTME + one-line docstring only, no re-exports. Same rule applies here.

---

### `app/domain/value_objects.py` (value-object module)

**Analog for module shape only:** `/Users/pvardanis/Documents/projects/dojo/app/settings.py` lines 1–11

**Header pattern** (lines 1–5):
```python
# ABOUTME: App settings loaded from .env via pydantic-settings.
# ABOUTME: Single source of truth for config, including DB + API key.
"""Application settings loaded from .env via pydantic-settings."""

from __future__ import annotations
```

**Adapt to value_objects.py:** same two-line ABOUTME + module docstring + `from __future__ import annotations`. Imports: `import uuid` / `from enum import Enum` / `from typing import NewType`. No Phase 1 analog exists for `NewType` or `Enum` — the idiom is locked by CONTEXT.md D-01:

```python
SourceId = NewType("SourceId", uuid.UUID)
NoteId   = NewType("NoteId",   uuid.UUID)
CardId   = NewType("CardId",   uuid.UUID)
ReviewId = NewType("ReviewId", uuid.UUID)
```

**Enum idiom** — no project analog; use stdlib `enum.Enum` with `str` mixin if serialization ever matters (YAGNI in Phase 2). CONTEXT D-enum-discretion: plain `Enum` is fine. Members per RESEARCH.md §2.1: `SourceKind` ∈ {FILE, URL, TOPIC}, `Rating` ∈ {CORRECT, INCORRECT}.

---

### `app/domain/entities.py` (frozen dataclasses)

**No direct Phase 1 analog.** Closest reference: `app/settings.py` demonstrates per-field validation via `@field_validator`, but that's Pydantic — domain uses stdlib `dataclasses`.

**Validation pattern — ported from `app/settings.py` lines 42–51** (concept: validator returns value on pass, raises `ValueError` on fail):
```python
@field_validator("database_url")
@classmethod
def _require_supported_scheme(cls, v: str) -> str:
    """Reject DB URLs for drivers we don't ship support for."""
    if not v.startswith(_SUPPORTED_DB_SCHEMES):
        raise ValueError(
            f"database_url must use a supported scheme "
            f"{_SUPPORTED_DB_SCHEMES}; got {v!r}"
        )
    return v
```

**Adapt to entities.py:** use `__post_init__` on frozen dataclasses with bare `ValueError` for empty-string checks (per CONTEXT.md Claude's-discretion "Entity construction invariants"):
```python
@dataclass(frozen=True)
class Source:
    """A source of study material."""

    kind: SourceKind
    user_prompt: str
    input: str | None = None
    id: SourceId = field(default_factory=lambda: SourceId(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Reject empty user_prompt after whitespace strip."""
        if not self.user_prompt.strip():
            raise ValueError("user_prompt must be non-empty")
```

**ID minting pattern** (locked by CONTEXT.md D-02): `field(default_factory=lambda: SourceId(uuid.uuid4()))`. Same shape for `NoteId`, `CardId`, `ReviewId`.

**Refactor hint from RESEARCH §3.1:** extract `_require_nonempty(value, field_name)` helper once duplication shows up across `Source`/`Note`/`Card`.

**Frozen-dataclass file size:** CONTEXT targets ≤100 lines; this file hits the wiki ceiling if all 4 entities land together. Planner may split to `entities/source.py` + `entities/note.py` + `entities/card.py` + `entities/card_review.py` if size warrants — flag, not pre-decision.

---

### `app/domain/exceptions.py` (exceptions module)

**No Phase 1 analog** — this is the first exceptions module in the repo. The pattern is dictated by `python-project-setup` wiki ("Custom exceptions live in a central `exceptions.py` per layer") and CONTEXT.md Claude's-discretion:

```python
# ABOUTME: Domain-layer exception hierarchy rooted at DojoError.
# ABOUTME: Application + infrastructure exceptions inherit from DojoError.
"""Domain-layer exceptions."""

from __future__ import annotations


class DojoError(Exception):
    """Base class for all Dojo domain + application exceptions."""


class InvalidEntity(DojoError):
    """Raised when an entity construction invariant is violated."""
```

**Rule from CONTEXT Claude's-discretion "Domain vs application exception split":** MVP may start with just `DojoError` + `InvalidEntity` if no real case surfaces. Application-layer exceptions inherit from `DojoError`.

---

### `app/application/__init__.py` (package-marker)

**Analog:** `/Users/pvardanis/Documents/projects/dojo/app/infrastructure/__init__.py` (all 3 content lines):
```python
# ABOUTME: Infrastructure layer — adapters for DB, LLM, sources.
# ABOUTME: Imports inward only (from app.application / app.domain).
"""Infrastructure layer package."""
```

**Adapt to:**
```python
# ABOUTME: Application layer — ports, DTOs, use cases.
# ABOUTME: Depends on app.domain only; no infrastructure / web imports.
"""Application layer package."""
```

---

### `app/application/ports.py` (Protocol + Callable aliases)

**No direct analog.** Closest module-shape reference: `app/logging_config.py` (single central spine file, module docstring, helper signatures).

**Module header pattern — from `app/logging_config.py` lines 1–12**:
```python
# ABOUTME: Structlog + stdlib logging configuration.
# ABOUTME: Dev → ConsoleRenderer; prod → JSONRenderer; tests → WARNING.
"""Structlog + stdlib logging configuration for Dojo."""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

import structlog
```

**Adapt to ports.py:** same two-line ABOUTME + module docstring + `from __future__ import annotations`. Imports `uuid`, `typing.Protocol`, `typing.NewType`, `collections.abc.Callable`, plus domain entity types.

**Protocol idiom is fresh for Dojo** — locked by CONTEXT.md D-04, D-05 and CLAUDE.md Protocol-vs-function clarifier:

```python
class DraftStore(Protocol):
    """In-memory holder for pending draft bundles."""

    def put(self, token: DraftToken, bundle: DraftBundle) -> None:
        """Store bundle under token; TTL enforced by impl (30 min)."""
        ...

    def pop(self, token: DraftToken) -> DraftBundle | None:
        """Atomic read-and-delete; returns None if absent or expired."""
        ...
```

**Rule from CONTEXT Claude's-discretion "Protocol method docstrings":** one-line docstrings specify return/error semantics (not restatements of the method name). Required by Phase 1 D-15 (interrogate 100%).

**Callable aliases** (per CLAUDE.md project-local clarifier):
```python
UrlFetcher: TypeAlias = Callable[[str], str]
"""Async URL → text fetcher. Phase 3's trafilatura adapter implements."""

SourceReader: TypeAlias = Callable[[Path], str]
"""Path → raw-text reader. Phase 3's fs adapter implements."""
```

**No `@runtime_checkable`** (locked by RESEARCH.md §2.2 note, Phase 1 D-11 rule about avoiding runtime cost). Structural subtyping is the contract.

**DraftToken NewType** (per CONTEXT D-03):
```python
DraftToken = NewType("DraftToken", uuid.UUID)
```

**Sizing flag from RESEARCH §2.2:** if ports.py exceeds 100 LOC with interrogate-compliant docstrings, split into `ports/repositories.py` + `ports/llm.py` + `ports/draft_store.py` + `ports/aliases.py`. Planner decides at plan time.

---

### `app/application/dtos.py` (Pydantic DTOs + stdlib dataclasses)

**Analog for Pydantic pattern:** `/Users/pvardanis/Documents/projects/dojo/app/settings.py` lines 22–35

**Pydantic class pattern** (lines 22–40):
```python
class Settings(BaseSettings):
    """Application settings.

    Real environment variables take precedence over .env values
    (pydantic-settings default). Keep the surface minimal; add
    fields only when a phase needs them.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    anthropic_api_key: SecretStr = SecretStr("dev-placeholder")
    database_url: str = "sqlite:///dojo.db"
```

**Adapt to dtos.py — `NoteDTO` / `CardDTO`** (locked by CONTEXT Claude's-discretion "Pydantic DTO posture" + PITFALL M6):
```python
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
```

**Stdlib dataclass pattern for `GenerateRequest` / `GenerateResponse` / `DraftBundle`** — no direct analog; locked by CONTEXT D-07 / D-08:
```python
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

**Split rationale:** Pydantic for the LLM I/O boundary (NoteDTO, CardDTO — untrusted input from Anthropic); stdlib dataclass for internal use-case types (GenerateRequest, GenerateResponse, DraftBundle — trusted, frozen, no validation cost).

---

### `app/application/exceptions.py` (exceptions module)

**Analog:** `app/domain/exceptions.py` (same pattern — ABOUTME + module docstring + class hierarchy). The application-layer class hierarchy **inherits from DojoError** (per CONTEXT Claude's-discretion):

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

**Note (Phase 2 contract — do not foreclose Phase 4):** exceptions carry a human-readable message (CONTEXT §code_context "Phase 4 contract"). `__init__` overrides are YAGNI.

---

### `app/application/use_cases/__init__.py` (package-marker)

**Analog:** `/Users/pvardanis/Documents/projects/dojo/app/web/routes/__init__.py` (all 3 content lines):
```python
# ABOUTME: FastAPI route modules — one APIRouter per file.
# ABOUTME: Home + health in Phase 1; generate/drill/read in later phases.
"""FastAPI route modules."""
```

**Adapt to:**
```python
# ABOUTME: Application use cases — one class per file.
# ABOUTME: Each use case takes ports via __init__ and exposes execute().
"""Application use-case modules."""
```

---

### `app/application/use_cases/generate_from_source.py` (use case)

**Analog for orchestrator shape:** `/Users/pvardanis/Documents/projects/dojo/app/web/routes/home.py` (thin handler + typed dependencies + branching).

**Handler shape pattern — from `app/web/routes/home.py` lines 1–19**:
```python
# ABOUTME: Home + health routes — the Phase 1 minimum endpoints.
# ABOUTME: Proves FastAPI + Jinja + autoescape wiring end-to-end.
"""Home and health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Render the minimal Dojo home page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request, name="home.html", context={}
    )
```

**Adapt to `GenerateFromSource` — class-based orchestrator (locked by RESEARCH §3.8):**
```python
# ABOUTME: GenerateFromSource use case — TOPIC branch wired in Phase 2.
# ABOUTME: FILE + URL branches raise UnsupportedSourceKind until Phase 4.
"""GenerateFromSource use case."""

from __future__ import annotations

import uuid

from app.application.dtos import (
    DraftBundle, GenerateRequest, GenerateResponse,
)
from app.application.exceptions import UnsupportedSourceKind
from app.application.ports import DraftStore, DraftToken, LLMProvider
from app.domain.value_objects import SourceKind


class GenerateFromSource:
    """Generate a draft note + cards from a source, store under token."""

    def __init__(
        self,
        llm: LLMProvider,
        draft_store: DraftStore,
    ) -> None:
        """Wire the use case against its ports."""
        self._llm = llm
        self._draft_store = draft_store

    def execute(self, request: GenerateRequest) -> GenerateResponse:
        """Dispatch on kind; TOPIC fully wired, FILE/URL raise."""
        if request.kind is SourceKind.TOPIC:
            note, cards = self._llm.generate_note_and_cards(
                source_text=None,
                user_prompt=request.user_prompt,
            )
            bundle = DraftBundle(note=note, cards=cards)
            token = DraftToken(uuid.uuid4())
            self._draft_store.put(token, bundle)
            return GenerateResponse(token=token, bundle=bundle)

        raise UnsupportedSourceKind(
            f"Source kind {request.kind.value!r} not supported yet"
        )
```

**Rule from RESEARCH §3.8 Refactor:** the per-kind dispatch is a two-branch if for now; Phase 4 adds FILE + URL branches. Pre-designing a strategy table is YAGNI.

**Constructor signature flag:** RESEARCH §3.8 Green says "takes the five dependencies ... if not used by `execute()` they're omitted until needed." Phase 2 `execute()` only touches `llm` + `draft_store`, so the repositories are **omitted** from `__init__`. Planner takes YAGNI stance.

---

### `tests/fakes/__init__.py` (package-marker + re-exports)

**Analog for marker shape:** `tests/__init__.py`:
```python
# ABOUTME: Dojo test package marker.
# ABOUTME: Shared fixtures live in tests/conftest.py.
"""Dojo test suite."""
```

**Re-export list is new — locked by CONTEXT Claude's-discretion "Fakes file layout":**
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

**Note:** this is the **only** `__all__` / re-export in Phase 2 — D-11 forbids re-exports in source-tree `__init__.py`s, but `tests/fakes/` is a consumer API (tests import `from tests.fakes import ...` per CONTEXT Claude's-discretion) so the re-export is the contract.

---

### `tests/fakes/fake_llm_provider.py` (structural-subtype fake)

**No direct analog.** Design rules locked by CONTEXT Claude's-discretion "Fake assertion style" (public-attribute state, not `.calls` + `assert_called_with`) and RESEARCH §3.7.

**Pattern to copy:**
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

**Rule from RESEARCH §3.7 Refactor:** if multiple tests need distinct canned responses, upgrade to `responses: Iterator[tuple[NoteDTO, list[CardDTO]]]` constructor arg. Don't pre-build.

**Structural-subtype note:** `FakeLLMProvider` does NOT inherit from `LLMProvider`. `typing.Protocol` (without `@runtime_checkable`) uses structural matching — the fake passes type-check by having the matching method signature.

---

### `tests/fakes/fake_source_repository.py` + `fake_note_repository.py` + `fake_card_repository.py` (dict-backed CRUD fakes)

**No direct analog.** Shared pattern (per RESEARCH §2.3):

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

**Note-repo variation** — supports regenerate-overwrite (spec §3): `save(note)` overwrites any existing entry with the same `note.source_id` before the ID-keyed write. Port surface still `save(note) -> None` + `get(note_id) -> Note | None`.

**Card-repo variation** — append-only regeneration: `save(card)` inserts only if `card.id` absent; the use-case appends cards rather than overwriting. Port surface `save(card) -> None` + `get(card_id) -> Card | None`.

**Discipline reminder (RESEARCH §3.6 Refactor):** resist adding `list()`, `delete()`, `filter_by_tag()` until Phases 5/6 need them. YAGNI.

---

### `tests/fakes/fake_card_review_repository.py` (list-backed append fake)

**No direct analog.** Per RESEARCH §2.3, exposes `fake.saved: list[CardReview]` (list, not dict — reviews are append-only and naturally ordered):

```python
class FakeCardReviewRepository:
    """Append-only list of CardReview entries."""

    def __init__(self) -> None:
        """Start with empty review log."""
        self.saved: list[CardReview] = []

    def save(self, review: CardReview) -> None:
        """Append the review to the log."""
        self.saved.append(review)
```

---

### `tests/fakes/fake_draft_store.py` (dict-backed atomic pop)

**No direct analog.** Locked by CONTEXT D-04 / D-06 + RESEARCH §3.5:

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

**Rule from CONTEXT D-05:** TTL/concurrency semantics live in the Protocol docstring only. The fake has no clock logic — tests that exercise expiry call `force_expire(token)`.

---

### `tests/unit/domain/__init__.py` (package-marker)

**Analog:** `/Users/pvardanis/Documents/projects/dojo/tests/unit/__init__.py`:
```python
# ABOUTME: Unit-test subpackage marker.
# ABOUTME: Fast, isolated tests with no DB or network IO.
"""Unit tests."""
```

**Adapt to:**
```python
# ABOUTME: Domain-layer unit tests.
# ABOUTME: Entities, value objects, exceptions — stdlib only.
"""Domain unit tests."""
```

---

### `tests/unit/domain/test_source.py` (entity-invariant unit test)

**Analog:** `/Users/pvardanis/Documents/projects/dojo/tests/unit/test_settings.py` lines 1–12 (header + import pattern)

**Header pattern** (lines 1–12):
```python
# ABOUTME: LLM-03 gate — ANTHROPIC_API_KEY loads via pydantic-settings.
# ABOUTME: Exercises lru_cache clear + env override semantics.
"""Settings unit tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.settings import Settings, get_settings
```

**Adapt to test_source.py:**
```python
# ABOUTME: Source entity invariants — non-empty prompt + unique IDs.
# ABOUTME: Exercises __post_init__ ValueError and ID uniqueness.
"""Source entity unit tests."""

from __future__ import annotations

import pytest

from app.domain.entities import Source
from app.domain.value_objects import SourceKind
```

**Test pattern — from `test_settings.py` lines 27–33** (MonkeyPatch-style test, function signature, assertion shape):
```python
def test_anthropic_key_loaded_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`ANTHROPIC_API_KEY` env var takes precedence over default."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    settings = get_settings()
    assert settings.anthropic_api_key.get_secret_value() == "sk-ant-test"
```

**Adapt to entity-invariant test (per RESEARCH §3.1):**
```python
def test_source_construction_rejects_empty_user_prompt() -> None:
    """`Source(user_prompt='')` raises ValueError."""
    with pytest.raises(ValueError, match="non-empty"):
        Source(kind=SourceKind.TOPIC, user_prompt="")


def test_source_id_is_unique_per_instance() -> None:
    """Two `Source()` calls produce distinct SourceIds."""
    a = Source(kind=SourceKind.TOPIC, user_prompt="alpha")
    b = Source(kind=SourceKind.TOPIC, user_prompt="beta")
    assert a.id != b.id
```

**Rule:** same idiom for `test_note.py`, `test_card.py`, `test_card_review.py`, `test_value_objects.py`, `test_exceptions.py` — per RESEARCH §3.1–3.4. Each file ≤100 lines; enforces its entity's invariants only (one entity per file).

---

### `tests/unit/application/__init__.py` (package-marker)

**Analog:** same as `tests/unit/domain/__init__.py` — two-line ABOUTME + one-line docstring.

---

### `tests/unit/application/test_dtos.py` (Pydantic + dataclass validation)

**Analog:** `/Users/pvardanis/Documents/projects/dojo/tests/unit/test_settings.py` lines 36–51 (Pydantic validation test pattern)

**Validation test pattern** (lines 36–51):
```python
def test_defaults_are_present_when_env_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Settings instantiate with defaults when env is empty.

    `Settings(_env_file=None)` bypasses the repo's real `.env` so
    the test is deterministic across local and CI environments.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("RUN_LLM_TESTS", raising=False)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.database_url == "sqlite:///dojo.db"
    assert settings.log_level == "INFO"
    assert settings.run_llm_tests is False
```

**Adapt to test_dtos.py (per RESEARCH §2.5):**
```python
def test_card_dto_rejects_empty_question() -> None:
    """CardDTO raises ValidationError when question is empty."""
    with pytest.raises(ValidationError):
        CardDTO(question="", answer="a.")


def test_card_dto_ignores_extra_fields() -> None:
    """`extra='ignore'` silently drops unknown keys."""
    card = CardDTO(question="q?", answer="a.", bogus="ignored")
    assert not hasattr(card, "bogus")


def test_generate_request_is_frozen() -> None:
    """GenerateRequest is a frozen dataclass."""
    req = GenerateRequest(
        kind=SourceKind.TOPIC, input=None, user_prompt="alpha"
    )
    with pytest.raises(FrozenInstanceError):
        req.user_prompt = "beta"  # type: ignore[misc]
```

---

### `tests/unit/application/test_generate_from_source.py` (use-case end-to-end)

**Analog for fixture-consumer idiom:** `/Users/pvardanis/Documents/projects/dojo/tests/integration/test_db_smoke.py` (single-file fixture consumer, function-scoped setup).

**Fixture-consumer pattern — from `test_db_smoke.py` lines 1–16:**
```python
# ABOUTME: SC #4 canary — sync session + real Alembic migrations.
# ABOUTME: Must pass 10x in a row via `pytest --count=10`.
"""First integration test — proves the fixture stack end-to-end."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def test_session_executes_trivial_query(session: Session) -> None:
    """Open a session, SELECT 1, close cleanly."""
    result = session.execute(text("SELECT 1"))
    value = result.scalar_one()
    assert value == 1
```

**Adapt to test_generate_from_source.py (per RESEARCH §3.8):**
```python
# ABOUTME: GenerateFromSource end-to-end test against hand-written fakes.
# ABOUTME: Covers TOPIC success, draft-store round-trip, FILE/URL raise.
"""GenerateFromSource use-case tests."""

from __future__ import annotations

import pytest

from app.application.dtos import GenerateRequest
from app.application.exceptions import UnsupportedSourceKind
from app.application.use_cases.generate_from_source import (
    GenerateFromSource,
)
from app.domain.value_objects import SourceKind
from tests.fakes import FakeDraftStore, FakeLLMProvider


def test_generate_from_topic_puts_bundle_in_draft_store() -> None:
    """TOPIC path: LLM called with source_text=None, bundle stored."""
    fake_llm = FakeLLMProvider()
    fake_store = FakeDraftStore()
    use_case = GenerateFromSource(llm=fake_llm, draft_store=fake_store)

    response = use_case.execute(
        GenerateRequest(
            kind=SourceKind.TOPIC, input=None, user_prompt="alpha"
        )
    )

    assert fake_llm.calls_with == [(None, "alpha")]
    assert fake_store.pop(response.token) == response.bundle


def test_generate_file_kind_raises_unsupported() -> None:
    """FILE kind raises until Phase 4 wires SourceReader."""
    use_case = GenerateFromSource(
        llm=FakeLLMProvider(), draft_store=FakeDraftStore()
    )
    with pytest.raises(UnsupportedSourceKind):
        use_case.execute(
            GenerateRequest(
                kind=SourceKind.FILE, input="/tmp/x.md", user_prompt="p"
            )
        )
```

**Sizing flag from RESEARCH §2.5:** if file exceeds 100 LOC, split into `test_generate_topic.py` + `test_generate_unsupported.py`. Planner decides.

**Atomic-pop invariant to add** (per RESEARCH §3.5): after the first `pop`, a second `pop(token)` returns `None` — one test asserts this is the fake's behavior, which is what the Protocol contract specifies.

---

### `tests/contract/__init__.py` (package-marker)

**Analog:** `tests/integration/__init__.py`:
```python
# ABOUTME: Integration-test subpackage marker.
# ABOUTME: Tests that hit real DB, ASGI app, filesystem — not mocked.
"""Integration tests."""
```

**Adapt to:**
```python
# ABOUTME: Contract tests — shared-fixture harness across fake + real impls.
# ABOUTME: Real-leg skips unless RUN_LLM_TESTS=1 + adapter module imports.
"""Contract tests."""
```

---

### `tests/contract/test_llm_provider_contract.py` (parametrised fixture + env gate)

**No direct analog.** Pattern locked by CONTEXT D-11 + RESEARCH §2.6.

**Closest Phase 1 reference for `pytest.importorskip` / env-gate idiom:** none in the codebase yet (it's why this harness is the TEST-03 backstop).

**Pattern to copy (full skeleton):**
```python
# ABOUTME: TEST-03 contract harness — asserts Protocol shape for LLM port.
# ABOUTME: Fake leg always runs; anthropic leg auto-skips (import + env).
"""LLMProvider contract tests — shared across fake and real impls."""

from __future__ import annotations

import os

import pytest

from app.application.dtos import CardDTO, NoteDTO
from tests.fakes import FakeLLMProvider


@pytest.fixture(params=["fake", "anthropic"])
def llm_provider(request: pytest.FixtureRequest):
    """Yield a fake or real LLMProvider; real skips without opt-in."""
    if request.param == "fake":
        yield FakeLLMProvider()
        return

    # Double-gate the real leg per CONTEXT D-11.
    if not os.getenv("RUN_LLM_TESTS"):
        pytest.skip("RUN_LLM_TESTS not set")
    adapter_module = pytest.importorskip(
        "app.infrastructure.llm.anthropic_provider"
    )
    yield adapter_module.AnthropicLLMProvider()


def test_generate_returns_note_and_card_list(llm_provider) -> None:
    """Return type is (NoteDTO, list[CardDTO]) with non-empty cards."""
    note, cards = llm_provider.generate_note_and_cards(
        source_text=None, user_prompt="alpha"
    )
    assert isinstance(note, NoteDTO)
    assert isinstance(cards, list)
    assert len(cards) >= 1
    assert all(isinstance(c, CardDTO) for c in cards)
```

**Rule from CONTEXT D-11:** the `"anthropic"` branch skips in Phase 2 because `app.infrastructure.llm.anthropic_provider` does not exist yet; `pytest.importorskip` handles this without a stub module. Phase 3 creates the real adapter → the param activates automatically.

---

### `pyproject.toml` (modified)

**Analog for placement:** existing `[tool.ruff]`, `[tool.pytest.ini_options]`, `[tool.interrogate]` sections. Append the new `[tool.importlinter]` block anywhere after the existing `[tool.*]` sections (TOML is order-free within a table).

**Existing dev-deps shape** (lines 22–33) for the `import-linter` entry:
```toml
[dependency-groups]
dev = [
    "ruff>=0.8",
    "ty==0.0.31",              # D-16: exact pin, still beta
    "interrogate>=1.7",
    "pytest>=8.3",
    "pytest-asyncio>=1.0",     # 1.0+ removed deprecated event_loop
    "pytest-cov>=5.0",
    "pytest-repeat>=0.9.4",    # SC #4 10x smoke stability gate
    "httpx>=0.28",             # ASGITransport client for integration tests
    "pre-commit>=3.7",
]
```

**Add to that list:**
```toml
    "import-linter>=2.0",      # Plan 05: domain/app boundary enforcement
```

**Append new section — from RESEARCH §1.1e (verified against official docs):**
```toml
[tool.importlinter]
root_package = "app"

[[tool.importlinter.contracts]]
name = "Domain must not depend on infrastructure or web"
type = "forbidden"
source_modules = ["app.domain"]
forbidden_modules = ["app.infrastructure", "app.web"]

[[tool.importlinter.contracts]]
name = "Application must not depend on infrastructure or web"
type = "forbidden"
source_modules = ["app.application"]
forbidden_modules = ["app.infrastructure", "app.web"]
```

---

### `Makefile` (modified)

**Analog:** existing `lint:` target (line 14–15) — single-line invocation:
```makefile
lint:
	uv run ruff check --fix .
```

**Replace with two-line version (per RESEARCH §1.1e):**
```makefile
lint:
	uv run ruff check --fix .
	uv run lint-imports
```

**Rule (RESEARCH §1.1e):** ruff first (fast, fixes autofixable style), lint-imports second (slower, builds import graph). If ruff fails, `make` short-circuits and `lint-imports` never runs — standard `make` behavior.

**Wiring note:** `make check` (line 26) invokes `lint`, so `lint-imports` automatically runs in pre-commit + CI once this edit lands.

---

## Shared Patterns

### ABOUTME + module docstring (every Python file)

**Source:** established Phase 1-wide — verified across `app/settings.py`, `app/main.py`, `app/logging_config.py`, `app/infrastructure/db/session.py`, every `__init__.py`, every test file.

**Apply to:** every `.py` file Phase 2 creates (31 new files).

**Exact shape:**
```python
# ABOUTME: <one-line what this file does>.
# ABOUTME: <one-line why/how it fits the layer>.
"""<module docstring — one sentence.>"""

from __future__ import annotations
```

**Rule:** `from __future__ import annotations` is consistent across every non-package-marker Phase 1 file (domain/app use type hints extensively). Skip for the `__init__.py` markers that have no imports.

---

### `from __future__ import annotations` + typed signatures

**Source:** `app/settings.py:5`, `app/main.py:5`, `app/logging_config.py:5`, `app/infrastructure/db/session.py:5`, every test file line 5.

**Apply to:** every non-marker Phase 2 source file. Enables string-annotation evaluation (deferred), which ty relies on for forward-reference resolution in Protocol methods.

---

### One-line docstrings on every public symbol (interrogate 100%)

**Source:** `app/settings.py:42-51` (validator docstring), `app/logging_config.py:53-59` (helper docstring), `app/infrastructure/db/session.py:39` (event-listener docstring), `app/web/routes/home.py:14-15` (route docstring).

**Apply to:** every public class / method / function in Phase 2. Phase 1 D-15 locks 100% interrogate; D-11 CLAUDE.md PR Shape says `app/application/ports.py` is **not** in the interrogate excludes (pyproject.toml:75 confirms — exclude list is `["migrations", "tests", "docs"]` only). So **every Protocol method** needs a one-line docstring.

**Pattern:** specify return/error semantics, not a restatement of the method name (CONTEXT Claude's-discretion). Example: `"""Save source; raises DuplicateSource if identifier exists."""`

---

### Test pristine-output / filterwarnings=error

**Source:** `pyproject.toml:63-64`:
```toml
# Promote warnings to errors (pristine-output rule / TEST-02).
filterwarnings = ["error"]
```

**Apply to:** every Phase 2 test. Tests must produce zero stray warnings. Any Pydantic deprecation warning, dataclass warning, or structlog warning → test failure.

**Support from `tests/unit/conftest.py:12-21`** — Dojo loggers clamped to WARNING for unit tests (already established; Phase 2 tests inherit this).

---

### Test fixture consumer idiom (function-scoped, typed)

**Source:** `tests/integration/test_db_smoke.py:11` (single fixture arg, fully typed).

**Apply to:** every Phase 2 test function. Fakes are constructed **inline** inside the test body (no session-scoped `fake_llm` fixture) — each test owns its own fake instance. This is what CONTEXT's "Fake assertion style" bullet implies: tests assert against per-instance state, so sharing state across tests is forbidden.

**Counter-example to avoid:** do NOT create a `tests/unit/application/conftest.py` with session-scoped fakes. Each test should do `fake = FakeLLMProvider()` inside the test body.

---

## No Analog Found

These 11 Phase 2 files break new ground relative to Phase 1. The planner should use the CONTEXT.md decisions + RESEARCH.md §§3, 4 hints as the pattern source, not a codebase analog.

| File | Role | Reason | Pattern Source |
|------|------|--------|----------------|
| `app/domain/entities.py` | frozen dataclasses | No dataclass analog in Phase 1 (Settings is Pydantic). | CONTEXT D-01, D-02; RESEARCH §3.1–§3.4; wiki `python-project-setup.md` |
| `app/domain/exceptions.py` | exceptions module | First per-layer exceptions file. | wiki "exceptions per layer in a central exceptions.py" |
| `app/application/ports.py` | Protocol + Callable aliases | No Protocol anywhere in Phase 1. | CONTEXT D-04, D-05; CLAUDE.md "Protocol vs function" clarifier; RESEARCH §2.2 |
| `app/application/exceptions.py` | exceptions module | New. | CONTEXT Claude's-discretion "Domain vs application exception split" |
| `tests/fakes/fake_llm_provider.py` | structural-subtype fake | No hand-written fake exists yet. | CONTEXT "Fake assertion style"; RESEARCH §3.7 |
| `tests/fakes/fake_source_repository.py` | dict-backed CRUD fake | Same. | RESEARCH §3.6 |
| `tests/fakes/fake_note_repository.py` | dict-backed CRUD fake | Same; regenerate-overwrite semantic. | RESEARCH §2.3 |
| `tests/fakes/fake_card_repository.py` | dict-backed append fake | Same; append-only regeneration. | RESEARCH §2.3 |
| `tests/fakes/fake_card_review_repository.py` | list-backed append fake | Same. | RESEARCH §2.3 |
| `tests/fakes/fake_draft_store.py` | atomic-pop fake | Same; `force_expire` test hook. | CONTEXT D-04, D-06; RESEARCH §3.5 |
| `tests/contract/test_llm_provider_contract.py` | param + env-gate harness | First contract test in the repo. | CONTEXT D-11; RESEARCH §2.6, §3.9 |

**Planner note:** for these 11 files, the `Pattern Assignments` section above contains a concrete full code skeleton derived from the locked CONTEXT.md decisions. Use those skeletons as the `green` starting point after the `red` test lands (TDD mandatory per CLAUDE.md).

---

## Metadata

**Analog search scope:**
- `/Users/pvardanis/Documents/projects/dojo/app/` (all source files)
- `/Users/pvardanis/Documents/projects/dojo/tests/` (unit + integration)
- `/Users/pvardanis/Documents/projects/dojo/pyproject.toml`
- `/Users/pvardanis/Documents/projects/dojo/Makefile`

**Files scanned:** 16 Phase 1 source files + pyproject.toml + Makefile = 18
**Tool calls used:** 15 (within ≤20 budget)
**Web operations:** 0 (per budget note)

**Key Phase 1 analog files exhaustively read:**
- `app/__init__.py`, `app/infrastructure/__init__.py`, `app/infrastructure/db/__init__.py`, `app/web/__init__.py`, `app/web/routes/__init__.py` (package-marker pattern)
- `app/settings.py` (Pydantic class + validator + `from __future__` + module docstring)
- `app/logging_config.py` (helper-module spine + type-hinted function signatures)
- `app/main.py` (composition root — Phase 2 does not modify this, confirmed by CONTEXT §code_context)
- `app/infrastructure/db/session.py` (module-level state + event listener + dialect guard)
- `app/web/routes/home.py` (small orchestrator + APIRouter + typed handler)
- `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py` (test-package markers)
- `tests/conftest.py`, `tests/unit/conftest.py` (fixture idiom, session-scoped autouse clamps)
- `tests/unit/test_settings.py` (unit test idiom — pytest, MonkeyPatch, typed sig, docstring)
- `tests/integration/test_db_smoke.py` (single-fixture consumer)
- `tests/integration/test_alembic_smoke.py` (multi-step integration fixture + tmp_path)
- `tests/integration/test_logging_smoke.py` (direct call + docstring-as-contract)

---

## PATTERN MAPPING COMPLETE

**Phase:** 2 — Domain & Application Spine
**Files classified:** 33 (31 created + 2 modified)
**Analogs found:** 22 / 33
 - Exact: 5 (all `__init__.py` markers)
 - Role-match: 9 (Pydantic / test-idiom / orchestrator / event-listener)
 - Partial: 8 (module-shape-only for Protocol/dataclass territory)
 - None: 11 (fakes, Protocol ports.py, contract harness — new ground)

**Key Patterns Identified:**
- Every Phase 2 `.py` file inherits the two-line `# ABOUTME:` header + one-line module docstring + `from __future__ import annotations` convention established by Phase 1.
- Domain entities are **frozen stdlib dataclasses** with `__post_init__` raising bare `ValueError` for invariant violations. `field(default_factory=lambda: XId(uuid.uuid4()))` mints IDs at construction per CONTEXT D-02.
- Application `NoteDTO` / `CardDTO` use the `ConfigDict(extra="ignore")` + `Field(min_length=1)` Pydantic v2 pattern (mirrors `Settings` + `SettingsConfigDict` idiom in `app/settings.py`). Use-case DTOs (`GenerateRequest`/`GenerateResponse`/`DraftBundle`) are plain frozen stdlib dataclasses.
- Ports are `typing.Protocol` classes with one-line docstrings on every method (interrogate 100% — ports.py stays out of the excludes). Callable aliases use `TypeAlias`.
- Fakes are plain Python classes with structural subtyping — NO inheritance from the Protocol, NO `@runtime_checkable`. Test state assertions target **public attributes** on the fake (`.saved`, `.puts`, `.calls_with`), never `Mock().assert_called_with`.
- The TEST-03 contract harness uses `pytest.fixture(params=[...])` + `pytest.importorskip` + `RUN_LLM_TESTS` env gate — the `"anthropic"` leg auto-skips when Phase 3's adapter does not exist yet.
- `pyproject.toml` `[tool.importlinter]` block uses the nested-table TOML syntax (verified in RESEARCH §1.1); `Makefile`'s `lint:` target gains a second line `uv run lint-imports` after `ruff check --fix`. No new `check` target — existing `check: format lint typecheck docstrings test` picks up the change transparently.

**File Created:** `/Users/pvardanis/Documents/projects/dojo/.planning/phases/02-domain-application-spine/02-PATTERNS.md`

**Ready for Planning:** gsd-planner can now reference the concrete skeleton per file and the Phase 1 line-number excerpts directly in each plan's action section.
