# Dojo v1 — Architecture Overview

**Last updated:** 2026-04-23
**Snapshot point:** Phase 2 (Plans 01–04 locked; Plan 05 pending)
**Scope:** Full v1 architecture. Locked layers rendered green; pending
layers (Phase 3 infrastructure, Phase 4+ web) rendered yellow.

This document is a **living v1 architecture overview**, updated as
each phase lands. It consolidates what spec §DOCS-01 will eventually
split into four canonical files under this folder (`layers.md`,
`domain-model.md`, `flows.md`, `ports-and-adapters.md`). Phase 7
refines + splits; until then, this single file carries the mental
model.

Five sections:

1. **Layered dependency direction** — which layer may import which
2. **Class diagram — domain layer** — entities + value objects
3. **Class diagram — application layer** — DTOs, ports, use case
4. **Implementor diagram** — fakes (now) + Phase 3 adapters (planned)
5. **Sequence diagram — GenerateFromSource TOPIC flow** — how the
   pieces collaborate on a single request

Plus a file-to-plan map and a Phase-2-out-of-scope section at the end.

---

## 1. Layered dependency direction

```mermaid
flowchart TD
    subgraph Web["Web — Phase 4+"]
        routes["FastAPI routes<br/>Jinja templates"]
    end

    subgraph Infrastructure["Infrastructure — Phase 3+"]
        adapters["AnthropicLLMProvider<br/>Sql*Repository × 4<br/>InMemoryDraftStore<br/>fetch_url, read_file"]
    end

    subgraph Application["Application — Plans 02-04"]
        ports["ports.py<br/>6 Protocols + 2 Callable aliases"]
        dtos["dtos.py<br/>Pydantic (LLM boundary)<br/>+ dataclass (internal)"]
        usecase["GenerateFromSource<br/>(Plan 04)"]
        appexc["exceptions.py<br/>UnsupportedSourceKind, …"]
    end

    subgraph Domain["Domain — Plan 01"]
        entities["entities.py<br/>Source, Note, Card, CardReview"]
        vos["value_objects.py<br/>SourceKind, Rating<br/>Typed IDs (NewType over UUID)"]
        domexc["exceptions.py<br/>DojoError (base)"]
    end

    Web -->|imports| Application
    Infrastructure -->|implements Protocols<br/>maps ORM to/from| Application
    Infrastructure -->|maps ORM to/from| Domain
    Application -->|imports| Domain
    Web -.->|may import<br/>for rendering| Domain

    classDef locked fill:#d4f4dd,stroke:#2d7a3f,color:#1a1a1a
    classDef pending fill:#fef3c7,stroke:#b45309,color:#1a1a1a
    classDef node fill:#ffffff,stroke:#94a3b8,color:#1a1a1a
    class Domain,Application locked
    class Web,Infrastructure pending
    class routes,adapters,ports,dtos,usecase,appexc,entities,vos,domexc node
```

**Dependency rule:** arrows only flow inward. Domain imports nothing
outside stdlib. Application imports Domain + Pydantic (at the DTO
boundary). Infrastructure imports both and implements the Protocols.
Web imports Application (and reads Domain types for rendering).

**Plan 05 closes this** with `import-linter` contracts that fail
`make lint` if any of these rules are violated.

---

## 2. Class diagram — domain layer

The domain is **pure typed data**. No `__post_init__` validation,
no Pydantic, no ORM. Frozen dataclasses with typed IDs minted via
`default_factory`, tz-aware timestamps by construction.

```mermaid
classDiagram
    %% Value objects
    class SourceKind {
        <<StrEnum>>
        FILE
        URL
        TOPIC
    }
    class Rating {
        <<StrEnum>>
        CORRECT
        INCORRECT
    }
    class SourceId {
        <<NewType over UUID>>
    }
    class NoteId {
        <<NewType over UUID>>
    }
    class CardId {
        <<NewType over UUID>>
    }
    class ReviewId {
        <<NewType over UUID>>
    }

    %% Entities (frozen dataclasses)
    class Source {
        <<frozen dataclass>>
        kind: SourceKind
        user_prompt: str
        display_name: str
        identifier: str | None
        source_text: str | None
        id: SourceId
        created_at: datetime
    }
    class Note {
        <<frozen dataclass>>
        source_id: SourceId
        title: str
        content_md: str
        id: NoteId
        generated_at: datetime
    }
    class Card {
        <<frozen dataclass>>
        source_id: SourceId
        question: str
        answer: str
        tags: tuple[str, ...]
        id: CardId
        created_at: datetime
    }
    class CardReview {
        <<frozen dataclass>>
        card_id: CardId
        rating: Rating
        id: ReviewId
        reviewed_at: datetime
        is_correct: bool
    }

    %% Exception root
    class DojoError {
        <<Exception base>>
    }

    %% Relationships — entity composition
    Source *-- SourceKind : kind
    Source *-- SourceId : id
    Note *-- NoteId : id
    Note ..> SourceId : source_id ref
    Card *-- CardId : id
    Card ..> SourceId : source_id ref
    CardReview *-- ReviewId : id
    CardReview *-- Rating : rating
    CardReview ..> CardId : card_id ref
```

**Reading this:**
- `*--` = composition (Source owns its SourceId, its SourceKind)
- `..>` = reference-only (Note holds a SourceId but doesn't own it —
  the Source is the owner of its identity)
- `<<StrEnum>>` values serialize natively as strings
  (`SourceKind.FILE == "file"`)
- `<<NewType over UUID>>` — zero runtime cost; `ty` catches passing
  a `SourceId` where a `NoteId` is expected

**What's intentionally NOT here:**
- No base entity class (dataclasses all the way down; no inheritance)
- No invariant methods (validation lives at boundary layers — see
  `02-01-SUMMARY.md` + STATE.md decision log)
- No domain services (none needed for Phase 2 scope)

---

## 3. Class diagram — application layer

The application layer declares **contracts** (Protocols + Callable
aliases) and **DTOs** (Pydantic for untrusted LLM I/O; stdlib dataclass
for internal shapes), plus the first **use case**. Structural subtyping
means implementors (fakes, future adapters) don't need to inherit from
the Protocols.

```mermaid
classDiagram
    direction LR

    %% DTOs at the LLM boundary (Pydantic)
    class NoteDTO {
        <<Pydantic>>
        title: str
        content_md: str
    }
    class CardDTO {
        <<Pydantic>>
        question: str
        answer: str
        tags: tuple[str, ...]
    }
    class GeneratedContent {
        <<Pydantic>>
        cards: list[CardDTO]
    }

    %% Internal app DTOs (stdlib dataclass)
    class GenerateRequest {
        <<frozen dataclass>>
        kind: SourceKind
        input: str | None
        user_prompt: str
    }
    class GenerateResponse {
        <<frozen dataclass>>
        token: DraftToken
        bundle: DraftBundle
    }
    class DraftBundle {
        <<frozen dataclass>>
        note: Note
        cards: list[Card]
    }
    class DraftToken {
        <<NewType over UUID>>
    }

    %% Ports (Protocols — no @runtime_checkable)
    class LLMProvider {
        <<Protocol>>
        generate_note_and_cards(source_text: str | None, user_prompt: str) -> tuple[NoteDTO, list[CardDTO]]
    }
    class SourceRepository {
        <<Protocol>>
        save(source: Source) -> None
        get(source_id: SourceId) -> Source | None
    }
    class NoteRepository {
        <<Protocol>>
        save(note: Note) -> None
        get(note_id: NoteId) -> Note | None
    }
    class CardRepository {
        <<Protocol>>
        save(card: Card) -> None
        get(card_id: CardId) -> Card | None
    }
    class CardReviewRepository {
        <<Protocol>>
        save(review: CardReview) -> None
    }
    class DraftStore {
        <<Protocol>>
        put(token: DraftToken, bundle: DraftBundle) -> None
        pop(token: DraftToken) -> DraftBundle | None
    }

    %% Callable aliases (stateless)
    class UrlFetcher {
        <<type alias>>
        Callable[[str], str]
    }
    class SourceReader {
        <<type alias>>
        Callable[[Path], str]
    }

    %% Use case
    class GenerateFromSource {
        llm: LLMProvider
        draft_store: DraftStore
        execute(request: GenerateRequest) -> GenerateResponse
    }

    %% Application exceptions
    class UnsupportedSourceKind {
        <<DojoError>>
    }
    class LLMOutputMalformed {
        <<DojoError>>
    }
    class DraftExpired {
        <<DojoError>>
    }

    %% DTO composition
    GeneratedContent *-- CardDTO
    GenerateRequest *-- SourceKind
    GenerateResponse *-- DraftToken
    GenerateResponse *-- DraftBundle

    %% Use case depends on Protocols (DIP)
    GenerateFromSource ..> LLMProvider : depends on
    GenerateFromSource ..> DraftStore : depends on
    GenerateFromSource ..> GenerateRequest : accepts
    GenerateFromSource ..> GenerateResponse : produces
    GenerateFromSource ..> UnsupportedSourceKind : raises
```

**Reading this:**
- Protocols are **not base classes** — implementors satisfy them
  structurally (duck typing verified at type-check time by `ty`)
- `GenerateFromSource` holds **Protocols**, not concrete adapters
  (DIP). Composition root in `app/main.py` (Phase 4+) will wire real
  adapters or fakes into this use case
- DTO layer is split by trust boundary:
  - **Pydantic DTOs** (`NoteDTO`, `CardDTO`, `GeneratedContent`)
    validate untrusted LLM tool-use output
  - **Internal dataclass DTOs** (`GenerateRequest`, `GenerateResponse`,
    `DraftBundle`) are shaped by our code — stdlib is enough

---

## 4. Implementors — fakes (now) and adapters (Phase 3)

Each Protocol has a fake today and will have a real adapter later.
Structural subtyping means neither inherits from the Protocol — they
just match the shape.

```mermaid
classDiagram
    direction TB

    %% Protocols (abbreviated)
    class LLMProvider {
        <<Protocol>>
    }
    class SourceRepository {
        <<Protocol>>
    }
    class NoteRepository {
        <<Protocol>>
    }
    class CardRepository {
        <<Protocol>>
    }
    class CardReviewRepository {
        <<Protocol>>
    }
    class DraftStore {
        <<Protocol>>
    }

    %% Fakes — Plan 03 (committed)
    class FakeLLMProvider {
        <<fake — tests/fakes>>
        returns: list
        raises: list
        calls: list
    }
    class FakeSourceRepository {
        <<fake>>
        saved: dict
    }
    class FakeNoteRepository {
        <<fake>>
        saved: dict
    }
    class FakeCardRepository {
        <<fake>>
        saved: dict
    }
    class FakeCardReviewRepository {
        <<fake>>
        log: list
    }
    class FakeDraftStore {
        <<fake>>
        puts: list
        force_expire(token: DraftToken) -> None
    }

    %% Real adapters — Phase 3 (planned)
    class AnthropicLLMProvider {
        <<Phase 3>>
    }
    class SqlSourceRepository {
        <<Phase 3>>
    }
    class SqlNoteRepository {
        <<Phase 3>>
    }
    class SqlCardRepository {
        <<Phase 3>>
    }
    class SqlCardReviewRepository {
        <<Phase 3>>
    }
    class InMemoryDraftStore {
        <<Phase 3>>
    }

    %% Structural subtype relationships (dashed — not inheritance)
    FakeLLMProvider ..|> LLMProvider : structural
    FakeSourceRepository ..|> SourceRepository : structural
    FakeNoteRepository ..|> NoteRepository : structural
    FakeCardRepository ..|> CardRepository : structural
    FakeCardReviewRepository ..|> CardReviewRepository : structural
    FakeDraftStore ..|> DraftStore : structural

    AnthropicLLMProvider ..|> LLMProvider : structural
    SqlSourceRepository ..|> SourceRepository : structural
    SqlNoteRepository ..|> NoteRepository : structural
    SqlCardRepository ..|> CardRepository : structural
    SqlCardReviewRepository ..|> CardReviewRepository : structural
    InMemoryDraftStore ..|> DraftStore : structural
```

**Reading this:**
- `..|>` = structural realization (the dashed arrow = duck typing).
  Neither fakes nor adapters inherit from the Protocol — they just
  satisfy its shape
- Both columns (fakes + adapters) satisfy the **same** Protocol. That's
  what makes the Plan 05 TEST-03 contract-test harness possible:
  one suite, parametrized over `[FakeLLMProvider, AnthropicLLMProvider]`
- When you add a new concrete adapter (Phase 3+), no Protocol changes
  are needed. That's the value of "add a class + one line in the
  composition root"

---

## 5. Sequence diagram — GenerateFromSource TOPIC flow

The one orchestration that exists today. Phase 4 adds FILE / URL flows
on top, and a separate Save use case that drains the draft store into
the repositories atomically.

```mermaid
sequenceDiagram
    autonumber

    participant User as Caller<br/>(test or Phase 4 route)
    participant UC as GenerateFromSource
    participant LLM as LLMProvider<br/>(Protocol)
    participant Store as DraftStore<br/>(Protocol)

    User->>+UC: execute(GenerateRequest)<br/>kind=TOPIC<br/>user_prompt="intro to k8s"

    alt kind == TOPIC
        UC->>+LLM: generate_note_and_cards(<br/>source_text=None,<br/>user_prompt="intro to k8s")
        LLM-->>-UC: (NoteDTO, list~CardDTO~)

        UC->>UC: mint DraftToken (uuid4)
        UC->>UC: construct Note(title, content_md, source_id)
        UC->>UC: construct list~Card~ (one per CardDTO)
        UC->>UC: build DraftBundle(note, cards)

        UC->>+Store: put(token, bundle)
        Store-->>-UC: (ok)

        UC-->>-User: GenerateResponse(token, bundle)

    else kind in {FILE, URL}
        UC-->>User: raise UnsupportedSourceKind
    end

    Note over User, Store: Later (Phase 4):<br/>User → SaveDraft use case<br/>→ DraftStore.pop(token)<br/>→ atomic save Source+Note+Cards via repos
```

**Reading this:**
- LLM is called with `source_text=None` for TOPIC (no external source
  snapshot; LLM draws on its own knowledge)
- `DraftToken` is minted by the use case, not passed in (server owns
  the key per PITFALL C10)
- `DraftStore.put` is the one-shot write; later pickup is `pop` which
  is atomic read-and-delete (no race with a concurrent save)
- FILE / URL branches raise before any expensive side effect —
  unsupported kinds fail fast

---

## 6. Where the pieces live (file map)

| Concept | File | Plan |
|---------|------|------|
| Domain entities | `app/domain/entities.py` | 01 |
| Value objects + IDs | `app/domain/value_objects.py` | 01 |
| Domain exception root | `app/domain/exceptions.py` | 01 |
| Protocols + Callables + DraftToken | `app/application/ports.py` | 02 |
| Pydantic + dataclass DTOs | `app/application/dtos.py` | 02 |
| App exceptions | `app/application/exceptions.py` | 02 |
| `GenerateFromSource` use case | `app/application/use_cases/generate_from_source.py` | 04 |
| Hand-written fakes | `tests/fakes/fake_*.py` | 03 |
| Unit tests per fake | `tests/unit/fakes/test_fake_*.py` | 03 |
| Unit tests per entity | `tests/unit/domain/test_*.py` | 01 |
| Unit tests per DTO / port / exception | `tests/unit/application/test_*.py` | 02 |
| Use-case orchestration tests | `tests/unit/application/test_generate_*.py` | 04 |
| Contract-test harness + import-linter | `tests/contract/`, `.importlinter` | 05 (pending) |

---

## 7. What Phase 2 does NOT deliver

Explicitly out of scope — these are Phase 3 (and later) concerns.
Knowing what the Protocols expect from them is important:

- **Real LLM calls** — `AnthropicLLMProvider` lands in Phase 3 with
  tenacity retries, Pydantic DTO validation, typed-exception wrapping.
- **Persistence** — `Sql*Repository` adapters + mappers, async-free
  sessionmaker, `expire_on_commit=False`. ORM-to-domain conversion at
  the mapper boundary.
- **Draft store concurrency** — `InMemoryDraftStore` with `asyncio.Lock`
  + lazy TTL eviction + 30-min expiry. Port contract documents the
  semantics; the adapter enforces them.
- **URL + file source reading** — `fetch_url` (httpx + trafilatura)
  and `read_file` (stdlib Path). Wired into the use case in Phase 4
  when FILE / URL branches light up.
- **Atomic save** — separate `SaveDraft` use case that pops from the
  draft store and writes Source + Note + Cards in one transaction.
  Phase 4.

---

*Last updated: 2026-04-23. Snapshot point: Phase 2 (Plans 01–04
locked; Plan 05 pending). Refresh per phase as new layers land.*

*Relationship to spec §DOCS-01: Phase 7 will split this overview into
four canonical files (`layers.md`, `domain-model.md`, `flows.md`,
`ports-and-adapters.md`). Until then, this single file carries the
mental model.*
