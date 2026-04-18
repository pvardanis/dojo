# Architecture Patterns

**Project:** Dojo — local MLOps interview study app
**Researched:** 2026-04-18
**Scope:** Validate spec's 4-layer DDD + ports/adapters design against 2026 Python/FastAPI practice; surface concrete async-session, Protocol-DIP, and composition-root patterns; flag structural smells; recommend build order.

**Overall confidence: HIGH.** The spec's architecture is idiomatic and aligned with how modern async FastAPI + SQLAlchemy 2.0 services are structured in 2026. One concrete concern and several implementation-detail patterns are flagged below.

---

## TL;DR

- The spec's four-layer DDD + ports/adapters layout is correct and standard. Proceed.
- Use **one `AsyncSession` per request**, provided via FastAPI `Depends(...)` with `yield`, bound to an `async_sessionmaker(expire_on_commit=False)` initialized in the FastAPI `lifespan`.
- Use **`typing.Protocol`** (not `ABC`) for multi-method ports; use a `Callable` type alias for the one-shot ports (`UrlFetcher`, `SourceReader`). Do **not** mark Protocols `@runtime_checkable` — it's not needed and can hide type errors.
- Inject use cases as **thin factory dependencies**: the composition root lives conceptually in `app/main.py` (engine + sessionmaker lifespan) and `app/web/deps.py` (per-request session → repos → use case).
- **Build order: Domain → Application (ports + one use case) → Infrastructure mappers/session → SQL repositories → LLM adapter → Web routes → HTMX templates → E2E.** Details and rationale below.
- **One real structural concern:** the "draft store, in-memory dict keyed by session token" (spec §5.1) sits awkwardly at the application layer but has no declared port, no owning module, and no clear injection path. See [§5.1 below](#51-concern-draft-store-has-no-port-or-home-layer). Fix is small but should be made before the Generate use case is written.

---

## 1. Component Boundaries

The spec's layering (§2) is sound. Refining it with explicit import rules:

### 1.1 Layer Responsibilities (Who Owns What)

| Layer | Owns | Imports From | Never Imports |
|---|---|---|---|
| **Domain** (`app/domain/`) | Entities (`Source`, `Note`, `Card`, `CardReview`), value objects (`SourceKind`, `Rating`), typed IDs, domain exceptions, invariants | stdlib only | Anything outside `app/domain/` |
| **Application** (`app/application/`) | Use cases, port definitions (Protocols + Callable aliases), Pydantic DTOs for external I/O, application exceptions, draft store abstraction | `app.domain.*`, stdlib, `pydantic` | `app.infrastructure.*`, `app.web.*`, `fastapi`, `sqlalchemy`, `anthropic` |
| **Infrastructure** (`app/infrastructure/`) | SQLAlchemy ORM models, mappers (ORM↔domain), repo implementations, Anthropic adapter, `httpx`/`trafilatura` adapters, filesystem adapter, DB session factory | `app.domain.*`, `app.application.ports`, stdlib, third-party SDKs | `app.web.*` |
| **Web** (`app/web/`) | FastAPI routes, Jinja templates, HTMX fragments, `Depends` wiring (`deps.py`), HTTP exception translation | All inner layers | — |
| **Composition root** (`app/main.py` + lifespan) | Engine construction, sessionmaker, LLM client construction, FastAPI app assembly | Everything | — (this is where the rule relaxes; it's the only allowed cross-layer binder) |

### 1.2 Why These Boundaries

- **Domain has zero deps** → fastest tests, no fixture weight, pure logic you can refactor without breaking adapters.
- **Application imports domain only** → use cases are testable with nothing but hand-written fakes implementing the ports. No test needs a DB or a network socket.
- **Infrastructure may import application ports** (to implement them) and domain (to construct entities in mappers) but **never the other way around** — this is the DIP arrow that makes the architecture hexagonal rather than layered-in-name-only.
- **Web imports down, never up.** Routes call application use cases; they never speak SQLAlchemy or anthropic directly.

### 1.3 Concrete Import-Rule Enforcement

Make the rule mechanical, not aspirational. Two options (pick one, document in `CLAUDE.md`):

1. **`import-linter`** — declarative contract in `pyproject.toml`, runs in `make check`. Low-cost, high-signal.
2. **Manual review + `ruff` custom rule** — fine for a small codebase but won't catch drift.

**Recommendation:** add `import-linter` to the stack. The four layers are explicitly enumerated; a 10-line config catches the one kind of bug that silently kills hexagonal architectures (a domain file accidentally importing SQLAlchemy). Worth it.

> **Confidence:** HIGH. Layering rules are directly from spec §2/§4.1 and match global `CLAUDE.md` "Dependencies must only flow inward."

---

## 2. Data Flow

Request → inner → back out. Every flow follows the same shape.

```
HTTP request
  │
  ▼
[Web route]  ── parses HTTP, gets AsyncSession from Depends, constructs use case
  │
  ▼
[Use case]   ── calls ports: LLM, repos, fetcher, reader
  │
  ├──► [LLMProvider port]  ── Anthropic adapter (httpx → anthropic SDK)
  ├──► [Repo port]         ── SQL adapter (AsyncSession → mappers → domain entities)
  ├──► [UrlFetcher port]   ── httpx + trafilatura
  └──► [SourceReader port] ── filesystem read
  │
  ▼
[Domain entities cross back]  ── plain dataclasses, no ORM/Pydantic contamination
  │
  ▼
[Web route]  ── renders Jinja template / JSON / redirect
  │
  ▼
HTTP response
```

### 2.1 Type Crossings (The Important Part)

Each arrow is typed. What moves across each boundary:

| Boundary | Inbound type | Outbound type |
|---|---|---|
| HTTP → Web route | Pydantic (Form/Query/Path models at web layer) | Jinja-rendered `HTMLResponse` |
| Web → Use case | Primitive args or application-layer command dataclass | Domain entities / application DTOs |
| Use case → LLM port | Application DTO (prompt inputs) | Application DTO (`GeneratedContent`) |
| Use case → Repo port | Domain entity or ID | Domain entity / list / `None` |
| Repo impl ↔ ORM | Domain entity | ORM row (mapper converts) |
| Adapter ↔ third-party | Domain-safe params | Third-party types wrapped and re-raised as application exceptions |

**The critical rule** (already in spec §3 "Layer ownership"): **no type defined in an outer layer is imported by an inner layer.** If a use case would benefit from knowing about a Pydantic model the web layer uses, it means the application layer should own its own DTO and the web layer should convert.

### 2.2 Transaction Boundary

One transaction per use case invocation. Concretely: the use case receives a `SessionRepository`-bundle or individual repos that share the same `AsyncSession`; on exception the outer session context manager rolls back, on success it commits. This lives in `app/web/deps.py`. See [§3.2 Pattern A](#32-pattern-a-async-session-per-request-via-lifespan--depends).

**Atomicity required by spec §5.1:** the "save draft" flow writes `Source + Note + approved Cards` in one transaction. This is naturally satisfied by session-per-request with a single commit at the end of the HTTP handler — no explicit Unit of Work class needed at Dojo's scale.

> **Confidence:** HIGH for flow direction (spec §5). MEDIUM for "no UoW class needed" — defensible given MVP scope, but if multi-use-case workflows appear in Phase 2, reconsider.

---

## 3. Patterns to Mirror (Concrete References)

### 3.1 Pattern: Composition Root at App Startup (FastAPI lifespan)

**What:** The engine, `async_sessionmaker`, and LLM client are created once in a FastAPI `lifespan` async context manager and stored on `app.state`. Per-request dependencies pull from `app.state` to construct session-scoped adapters.

**When:** Always, for any resource that's expensive to construct (DB connection pool, HTTP client, LLM SDK client).

**Canonical reference:** FastAPI Lifespan Events — [https://fastapi.tiangolo.com/advanced/events/](https://fastapi.tiangolo.com/advanced/events/) (verified HIGH confidence). Resources set on `app.state` during startup are cleaned up after `yield`.

**Example (sketch matching the spec's layout):**

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from anthropic import AsyncAnthropic

from app.settings import Settings
from app.web.routes import home, sources, cards, drill

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()  # pydantic-settings reads .env
    engine = create_async_engine(settings.db_url, echo=False)
    app.state.sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False
    )
    app.state.llm_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    try:
        yield
    finally:
        await engine.dispose()

app = FastAPI(lifespan=lifespan)
app.include_router(home.router)
app.include_router(sources.router)
app.include_router(cards.router)
app.include_router(drill.router)
```

**Why on `app.state`, not module globals:** keeps the factory callable (testing creates a separate `FastAPI` instance with a fake `state`), keeps import side-effects nil, matches the official "shared resources at startup" pattern.

### 3.2 Pattern A: Async Session Per Request via Lifespan + Depends

**What:** Each HTTP request gets its own `AsyncSession` from the lifespan's `async_sessionmaker`. The session is yielded via a FastAPI dependency, committed on success, rolled back on exception, closed in `finally`.

**When:** Every route that touches the DB. This is *the* 2026-idiomatic pattern for async FastAPI + SQLAlchemy 2.0.

**Canonical reference:** FastAPI Dependencies with Yield — [https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/) (verified HIGH confidence). FastAPI internally wraps yielded dependencies in `asynccontextmanager` and guarantees reverse-order cleanup.

**Example:**

```python
# app/web/deps.py
from typing import Annotated, AsyncIterator
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One AsyncSession per request. Commits on success, rolls back on error."""
    sessionmaker = request.app.state.sessionmaker
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

SessionDep = Annotated[AsyncSession, Depends(get_session)]
```

**Why `expire_on_commit=False`:** default `True` expires all ORM attributes on commit, so reading `obj.id` after `commit()` triggers a fresh lazy-load — which in async is an error (MissingGreenlet). Setting it to `False` is the standard recommendation for async SQLAlchemy (see release notes and async extension docs — sqlalchemy.org was unreachable during research but this is the established convention; **MEDIUM confidence, verify at implementation time**).

**Why commit in the dep, not the use case:** keeps the use case infrastructure-agnostic (the use case doesn't know "commit" exists; the web-side transaction boundary is pulled outward). Alternative: use case calls `await uow.commit()` on a Unit of Work port. For Dojo's scale, the simpler approach wins.

### 3.3 Pattern B: Protocol Ports + Callable Aliases

**What:** Stateful, multi-method ports are `typing.Protocol`. Stateless one-shot ports are `Callable` type aliases. This matches spec §4.3 exactly.

**When:** Always, for every boundary that crosses into infrastructure.

**Canonical reference:** Python `typing.Protocol` — [https://docs.python.org/3/library/typing.html#typing.Protocol](https://docs.python.org/3/library/typing.html#typing.Protocol) (verified HIGH confidence). Protocol gives structural subtyping: the implementer doesn't need to inherit from the Protocol, it just needs to match shape. Ideal for DIP because the application layer defines the Protocol and the infra layer's concrete classes implement it without importing it.

**Wait — do implementers need to import the Protocol?** Strictly for static typing, no. In practice, **yes, infra imports the Protocol** because (a) `ty`/`mypy` can then verify at the class definition site rather than at every construction site, and (b) a quick eyeball of `class SqlSourceRepository(SourceRepository):` makes the relationship obvious. The DIP rule is about *runtime* dependencies and the direction of the *abstraction*; the infra importing the Protocol is fine — the Protocol is in the application layer (the inner circle).

**Example:**

```python
# app/application/ports.py
from pathlib import Path
from typing import Callable, Protocol
from app.domain.entities import Source, SourceId, Card
from app.application.dtos import GeneratedContent

# Stateful, multi-method → Protocol
class SourceRepository(Protocol):
    async def save(self, source: Source) -> None: ...
    async def by_id(self, source_id: SourceId) -> Source | None: ...
    async def list_all(self) -> list[Source]: ...
    async def delete(self, source_id: SourceId) -> None: ...

class LLMProvider(Protocol):
    async def generate_note_and_cards(
        self, source_text: str | None, user_prompt: str
    ) -> GeneratedContent: ...

# Stateless, one-shot → Callable alias
UrlFetcher = Callable[[str], "Awaitable[str]"]  # or use typing.Awaitable
SourceReader = Callable[[Path], str]
```

**Do not use `@runtime_checkable`** unless you genuinely need `isinstance()` checks (you don't — composition root wires concrete types). Runtime checks are weaker than static checks (don't verify signatures, only presence) and can mask bugs. Confirmed by Python docs: "runtime checks are structural only... can pass `isinstance()` despite incompatible types." (HIGH confidence, cited above.)

### 3.4 Pattern C: Dependency-Injected Use Cases

**What:** Use cases are callable classes (or functions) that accept their ports as constructor args (or keyword args). FastAPI `Depends` builds the use case per request, wiring the session-scoped repos and process-scoped LLM client.

**When:** Every route. No route should construct infra adapters inline.

**Example:**

```python
# app/web/deps.py (continued)
from app.application.generate_from_source import GenerateFromSource
from app.infrastructure.repositories.source_repository import SqlSourceRepository
from app.infrastructure.repositories.note_repository import SqlNoteRepository
from app.infrastructure.repositories.card_repository import SqlCardRepository
from app.infrastructure.llm.anthropic_provider import AnthropicLLMProvider
from app.infrastructure.sources.file_reader import read_file
from app.infrastructure.sources.url_fetcher import fetch_url

def get_generate_from_source(
    session: SessionDep,
    request: Request,
) -> GenerateFromSource:
    return GenerateFromSource(
        sources=SqlSourceRepository(session),
        notes=SqlNoteRepository(session),
        cards=SqlCardRepository(session),
        llm=AnthropicLLMProvider(request.app.state.llm_client),
        read_file=read_file,
        fetch_url=fetch_url,
        drafts=request.app.state.draft_store,  # see §5.1 concern below
    )

GenerateDep = Annotated[GenerateFromSource, Depends(get_generate_from_source)]
```

**Why kwargs, not positional:** The application layer uses keyword-only args for ports (recommend `@dataclass(kw_only=True)` or `def __init__(self, *, sources, notes, ...)`). Positional order is an anti-pattern for anything with >3 collaborators — reorder bugs are invisible to type checkers.

### 3.5 Pattern D: ORM↔Domain Mappers (Explicit, Not Inherited)

**What:** SQLAlchemy ORM models live in `app/infrastructure/db/models.py` and are **not** the same classes as domain entities. A pair of mapper functions (`to_domain`, `to_orm`) convert between them at the repository boundary.

**When:** Always, when the domain model has invariants or value objects that shouldn't leak ORM semantics (lazy loading, detached-instance pitfalls, pickle-compatibility issues).

**Why not `registry.map_imperatively` (classical mapping)?** Tempting — it lets the domain entity *be* the ORM class. But:
- It pulls SQLAlchemy types into the domain layer (violates §4.1).
- Lazy-loading attribute access in domain methods becomes a hidden I/O call (especially dangerous in async; triggers MissingGreenlet).
- Serialization (Pydantic, pickle) gets surprising.

Explicit mappers (`to_domain(row: OrmSource) -> Source`) are 10 extra lines and zero surprises. Cosmic Python (Harry Percival / Bob Gregory, *Architecture Patterns with Python*) advocates exactly this boundary and its tradeoffs are well-documented.

> **Confidence:** MEDIUM — couldn't fetch Cosmic Python directly during this session. Pattern is widely known; validate at implementation time if the team wants alternatives.

### 3.6 Pattern E: Hand-Written Fakes at DIP Boundaries

**What:** Every Protocol port gets a `Fake*` implementation (in-memory repos, deterministic LLM) under `tests/fakes/`. Use-case unit tests construct the use case with fakes and assert on fake state.

**When:** Every use-case unit test.

**Example shape:**

```python
# tests/fakes/fake_card_repository.py
from app.application.ports import CardRepository
from app.domain.entities import Card, SourceId

class FakeCardRepository:
    """Implements CardRepository Protocol via in-memory dict."""

    def __init__(self) -> None:
        self.cards: dict[CardId, Card] = {}
        self.save_calls: int = 0  # for assertions about behavior, not call patterns

    async def save(self, card: Card) -> None:
        self.save_calls += 1
        self.cards[card.id] = card

    async def by_source(self, source_id: SourceId) -> list[Card]:
        return [c for c in self.cards.values() if c.source_id == source_id]
```

Test asserts `fake_cards.cards == {...}` rather than `mock.save.assert_called_with(...)`. Matches global CLAUDE.md mandate and spec §7.1.

### 3.7 Pattern F: Route Handler Stays Thin

**What:** Routes parse HTTP, pull the use case via `Depends`, call it, translate the result (domain entity or exception) into a template or status code. No business logic.

**Example:**

```python
# app/web/routes/sources.py
@router.post("/sources/generate")
async def generate(
    kind: Annotated[SourceKind, Form()],
    input_value: Annotated[str | None, Form(alias="input")],
    user_prompt: Annotated[str, Form()],
    use_case: GenerateDep,
    request: Request,
):
    try:
        draft = await use_case.execute(kind, input_value, user_prompt)
    except SourceFetchFailed as e:
        return templates.TemplateResponse(
            "sources/error.html", {"request": request, "message": str(e)},
            status_code=400,
        )
    return templates.TemplateResponse(
        "sources/review.html", {"request": request, "draft": draft}
    )
```

FastAPI "bigger applications" tutorial ([https://fastapi.tiangolo.com/tutorial/bigger-applications/](https://fastapi.tiangolo.com/tutorial/bigger-applications/), HIGH confidence) shows the `APIRouter` pattern and centralized `dependencies.py` module — spec §4.1's `app/web/deps.py` is the same pattern.

---

## 4. Anti-Patterns to Avoid

### 4.1 Anti-Pattern: Engine or Sessionmaker as Module Globals

**What:** `engine = create_async_engine(...)` at module top level in `app/infrastructure/db/session.py`, imported by repos and tests.

**Why bad:**
- Import-time side effects: importing any module triggers engine creation.
- Tests can't substitute the engine without `monkeypatch` gymnastics.
- Breaks the "only the composition root knows about infra" rule.

**Instead:** Construct engine in `lifespan`, store on `app.state`, pass `async_sessionmaker` (or the `AsyncSession` itself) to repos via constructor.

### 4.2 Anti-Pattern: Sharing a Single AsyncSession Across Concurrent Tasks

**What:** Awaiting multiple coroutines in parallel (`asyncio.gather(session.execute(...), session.execute(...))`) on the same session.

**Why bad:** SQLAlchemy's `AsyncSession` is **not** safe for concurrent use — it's an async wrapper around a sync session, and concurrent statements corrupt the connection state. Raises `IllegalStateChangeError` or silently interleaves.

**Instead:** Serialize (`await session.execute(a); await session.execute(b)`), or use two separate sessions if you genuinely need concurrency (rare in a request handler).

> **Confidence:** MEDIUM — established pattern from SQLAlchemy async docs; couldn't re-verify during this research session (sqlalchemy.org unreachable). Flag for confirmation during Infrastructure implementation.

### 4.3 Anti-Pattern: Lazy-Loading Attributes in Async

**What:** Domain code calls `source.cards` on a detached or expired ORM object inside an async context.

**Why bad:** Triggers implicit I/O, raises `MissingGreenlet` in async.

**Instead:** Repositories always eager-load (`selectinload`, `joinedload`) what the use case needs. Mappers convert to plain domain dataclasses before the ORM row leaves the repo. No ORM object escapes `app/infrastructure/`.

### 4.4 Anti-Pattern: `@runtime_checkable` Protocols Everywhere

**What:** Marking every Protocol `@runtime_checkable` "just in case."

**Why bad:** Weaker-than-nominal checks (only presence, not signatures); slower `isinstance` calls; masks real type errors. Python docs explicitly warn about this.

**Instead:** Leave Protocols static-only. The composition root provides concretes; static typing covers the rest.

### 4.5 Anti-Pattern: Use Cases That Accept a Session

**What:** `GenerateFromSource.execute(session: AsyncSession, ...)` — the use case knows about SQLAlchemy.

**Why bad:** Couples application layer to infrastructure. Application tests now need a real session or a fake session object.

**Instead:** Use case accepts repository ports. The repo holds the session. Session management stays in `app/web/deps.py`.

### 4.6 Anti-Pattern: Third-Party Exceptions Leaking to Web

**What:** `anthropic.RateLimitError` or `sqlalchemy.exc.IntegrityError` reaching the route handler.

**Why bad:** Web layer now imports infra. Error translation scatters.

**Instead:** Adapters wrap and re-raise as `LLMRateLimited`, `DuplicateSource`, etc. (spec §6.4 already mandates this; just surfacing it.)

---

## 5. Structural Concerns With the Spec

### 5.1 Concern: Draft Store Has No Port or Home Layer

**Spec text (§5.1):** *"Draft store: in-memory dict keyed by short-lived session token (UUID, 30-minute TTL)."*

**What's missing:** There's no port for it in §4.3, no module in §4.1, and no clear layer-ownership rule. The spec implies it but doesn't define it.

**Why it matters:** If it's just a `dict` instantiated in `app/main.py`, fine for MVP — but then the use case can't be unit-tested without a real dict, the TTL logic has no home, and Phase 2 (if drafts persist to Redis or survive restarts) requires a refactor.

**Fix (small, recommended before Generate use case is written):**

1. Add `DraftStore` as a Protocol port in `app/application/ports.py`:
   ```python
   class DraftStore(Protocol):
       async def put(self, token: str, draft: GeneratedDraft) -> None: ...
       async def get(self, token: str) -> GeneratedDraft | None: ...
       async def pop(self, token: str) -> GeneratedDraft | None: ...
   ```
2. Concrete `InMemoryDraftStore` in `app/infrastructure/drafts/in_memory.py` with TTL eviction (or delegate TTL to `cachetools.TTLCache`).
3. Wire in `lifespan`: `app.state.draft_store = InMemoryDraftStore(ttl_seconds=1800)`.
4. Test with a `FakeDraftStore` that skips TTL for determinism.

**Cost:** ~40 lines across three files. Unlocks Phase 2's RAG retrieval-cache reuse without an architectural refactor.

> **Confidence:** HIGH that this is missing from the spec and should be fixed. Spec is authoritative but underspecified here.

### 5.2 Concern (Minor): Circular-Import Risk Between `application/ports.py` and `application/dtos.py`

**Why it matters:** `ports.py` declares `LLMProvider` whose method returns `GeneratedContent` (a DTO). If `dtos.py` ever imports anything from `ports.py` (e.g., a return-type alias), circular import.

**Fix:** Keep `dtos.py` a leaf module — it imports only from `app.domain.*` and stdlib. `ports.py` imports from `dtos.py` but never the reverse. Document in `app/application/__init__.py` or `CLAUDE.md`.

**Cost:** One discipline rule.

### 5.3 Concern (Minor): "Each Layer Owns Its Own Types" Cross-References Unspecified

**Spec text (§3):** *"Domain entities are plain Python dataclasses... Application uses Pydantic DTOs... Infrastructure has its own SQLAlchemy models..."*

**Not covered:** web-layer forms/requests. FastAPI auto-parses request bodies using Pydantic — the web layer will naturally define its own Pydantic models for forms. That's fine, but worth stating explicitly so Claude sessions don't reuse application DTOs as form models.

**Fix:** Add a one-line rule to `CLAUDE.md`: *"Web-layer Pydantic models for form/request parsing are separate from application-layer DTOs. Map in the route handler."*

**Cost:** One doc line.

### 5.4 Non-Concern: Composition Root in `app/main.py`

Spec §2 says the composition root lives in `app/main.py`. In practice it'll be split: engine/sessionmaker/LLM-client lifespan in `app/main.py`, per-request wiring in `app/web/deps.py`. That's the standard FastAPI composition root pattern (verified HIGH confidence from FastAPI docs). No change needed.

### 5.5 Non-Concern: Four Layers (vs. Three)

Some hexagonal guides collapse "application" and "domain" into one "core" layer. Spec keeps them separate, which is correct for Dojo because (a) DTOs are distinct from entities, (b) use cases have enough behavior to warrant their own module, and (c) it's the conventional DDD split. Proceed as specified.

---

## 6. Build Order Recommendation

**Rationale:** Build inner-to-outer so every layer has real consumers by the time its tests run. The first use case is the "spine" — it exercises every port and surfaces design bugs fast.

### Phase 1a — Spine-First Bottom-Up (Week 1)

1. **Domain entities + value objects + exceptions** (`app/domain/`)
   - Dataclasses, no dependencies. Write with tests.
   - **Why first:** Everything downstream imports it; getting the types right avoids cascading refactors.

2. **Application ports + DTOs** (`app/application/ports.py`, `dtos.py`)
   - Protocols, Callable aliases, Pydantic DTOs.
   - **Why now, before use cases:** Defining the abstractions first forces you to answer "what does the use case need?" separately from "how does infra satisfy it?" — which is the DIP discipline.

3. **One vertical slice use case: `GenerateFromSource` (TOPIC only)** (`app/application/generate_from_source.py`)
   - Simplest variant: no file read, no URL fetch, just LLM + repos.
   - Tests: `FakeLLMProvider`, `FakeSourceRepository`, `FakeNoteRepository`, `FakeCardRepository`, `FakeDraftStore`.
   - **Why now:** Proves the port shapes before you commit to infra implementations. Cheaper to refactor Protocols than SQL schemas.

### Phase 1b — Infrastructure for the Spine (Week 1-2)

4. **DB plumbing** (`app/infrastructure/db/session.py`, `models.py`, `mappers.py`)
   - `async_sessionmaker`, ORM models for `Source`/`Note`/`Card`/`CardReview`, round-trip mappers.
   - Alembic initial migration.
   - Integration tests: real SQLite tmp file, round-trip a `Source`.
   - **Why now:** Repositories need this.

5. **SQL repositories** (`app/infrastructure/repositories/*`)
   - One repo per aggregate, implementing its Protocol.
   - Integration tests against real SQLite.
   - **Why before LLM adapter:** Repos are simpler (deterministic, no network), failing tests here are easier to debug. Also: a broken repo breaks everything; a broken LLM adapter only breaks generation.

6. **Anthropic LLM adapter** (`app/infrastructure/llm/anthropic_provider.py`, `prompts.py`)
   - Uses Anthropic tool-use for structured output (DTO → LLM → DTO).
   - Opt-in integration test against real API (gated by `RUN_LLM_TESTS=1` per spec §7.2).
   - **Why here:** By this point you have domain, ports, repos — the LLM adapter is the last piece the Generate use case needs.

7. **In-memory draft store** (`app/infrastructure/drafts/in_memory.py`) — **per §5.1 concern**
   - TTL eviction; satisfies `DraftStore` Protocol.

8. **File reader + URL fetcher** (`app/infrastructure/sources/*`)
   - `read_file`, `fetch_url` — Callable adapters.
   - Integration tests: real filesystem + `respx`-stubbed HTTP.
   - **Why after LLM adapter:** These extend the spine to FILE and URL kinds, but the minimum viable generate loop works with just TOPIC.

### Phase 1c — Web + UX (Week 2-3)

9. **FastAPI skeleton + lifespan + `deps.py`** (`app/main.py`, `app/web/deps.py`)
   - `lifespan` wires engine/sessionmaker/LLM-client/draft-store onto `app.state`.
   - `deps.py` provides `SessionDep`, `GenerateDep`, other use-case deps.

10. **Routes: Generate → Review → Save** (`app/web/routes/sources.py`, `cards.py`)
    - Forms to submit generation, review cards, save drafts.
    - Jinja templates with HTMX for the review flow.

11. **Routes: Drill** (`app/web/routes/drill.py`)
    - Card sequence, Space/← /→ keybindings (client JS), POST review.
    - `DrillDeck` use case (simple; random order + record review).

12. **Routes: Read** (`app/web/routes/home.py`, source detail view)
    - Markdown rendering via `markdown-it-py`.

### Phase 1d — Polish (Week 3)

13. **E2E tests (Playwright)** — one happy path per flow with `FakeLLMProvider` via `DOJO_LLM=fake` env toggle (spec §7.3).

14. **`make check` tightening** — ruff, ty, interrogate, pytest all green.

15. **Architecture docs + Mermaid diagrams** (`docs/architecture/`) — four diagrams per spec §1 goals.

16. **Pre-commit + CI wiring** — GitHub Actions, `.pre-commit-config.yaml`.

### Why This Order (Key Dependencies)

- **Domain before application:** Application imports domain types.
- **Ports before use cases:** Use cases reference ports by type.
- **Use case before infra:** You learn what the port *needs* from writing the use case against fakes; writing infra first locks in accidental coupling.
- **Repos before LLM adapter:** Repos are deterministic, easier to debug. Also: the LLM adapter interacts with money (API costs); de-risk the free/deterministic parts first.
- **Infra before web:** Web's `deps.py` imports concrete infra. Can't wire what doesn't exist.
- **Drill and Read after Generate:** Generate is the hardest path (three source kinds, LLM structured output, atomic save). Solve it first; Drill and Read reuse its repos with thinner use cases.

### Anti-Pattern in Build Order

**Don't build the web layer first "because that's what users see."** FastAPI routes with zero real adapters become throwaway scaffolding; you'll rewrite them when the use case signatures settle. Build the spine, then thread it through routes.

---

## 7. Scalability Considerations

Dojo is explicitly localhost / single-user / single-process. No horizontal scaling story needed. But the architecture's shape *does* affect two things:

| Concern | Today (MVP) | Phase 2+ (if) |
|---|---|---|
| DB concurrency | SQLite + one `AsyncSession` per request, serialized writes. Fine. | If Dojo grows to multi-user or heavy RAG indexing, move to PostgreSQL — `async_sessionmaker` and repo abstractions are identical, just swap the engine URL. |
| LLM call latency | One generation call per user per minute at most. Fine. | Mock-interview mode (Phase 2) may need streaming responses — `LLMProvider` Protocol gains a `stream_*` method. Port design accommodates this cleanly. |
| Draft store | In-memory dict, lost on restart. Acceptable per spec. | If drafts need to survive restart or span instances, swap `InMemoryDraftStore` for `SqliteDraftStore` — the Protocol is the insurance policy. |

**Implication for architecture:** the ports/adapters split is *already* paying for itself at Phase 2 without any MVP overhead.

---

## 8. Sources

**HIGH confidence (official docs, verified this session):**

- FastAPI Lifespan Events — [https://fastapi.tiangolo.com/advanced/events/](https://fastapi.tiangolo.com/advanced/events/)
- FastAPI Dependencies with yield — [https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/)
- FastAPI Dependencies (Annotated pattern) — [https://fastapi.tiangolo.com/tutorial/dependencies/](https://fastapi.tiangolo.com/tutorial/dependencies/)
- FastAPI Bigger Applications (APIRouter, `deps.py` pattern) — [https://fastapi.tiangolo.com/tutorial/bigger-applications/](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- FastAPI SQL Databases (session-per-request shape; note: docs show sync SQLModel, async pattern is analogous) — [https://fastapi.tiangolo.com/tutorial/sql-databases/](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- FastAPI Async/Await (when to use `async def`, concurrency model) — [https://fastapi.tiangolo.com/async/](https://fastapi.tiangolo.com/async/)
- FastAPI Deployment Concepts (uvicorn workers, single-process semantics) — [https://fastapi.tiangolo.com/deployment/concepts/](https://fastapi.tiangolo.com/deployment/concepts/)
- Python `typing.Protocol` (structural subtyping, `@runtime_checkable` caveats) — [https://docs.python.org/3/library/typing.html#typing.Protocol](https://docs.python.org/3/library/typing.html#typing.Protocol)

**MEDIUM confidence (established patterns from training, not re-verified this session because sqlalchemy.org and several article hosts were unreachable):**

- SQLAlchemy 2.0 `AsyncSession` + `async_sessionmaker` + `expire_on_commit=False` — standard 2.0 async pattern; flag for confirmation at implementation time via `docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html`.
- "AsyncSession not safe for concurrent use" — SQLAlchemy async limitation; flag for verification.
- Cosmic Python (*Architecture Patterns with Python*, Percival & Gregory) — repository pattern, domain model purity, Unit of Work discussion. [https://www.cosmicpython.com/book/](https://www.cosmicpython.com/book/) — was unreachable during this session; widely-cited reference for the pattern stack the spec uses.

**LOW confidence (not verified; flag for validation):**

- None flagged at this level. All architectural claims above are either from HIGH-confidence sources or well-established patterns from training.

**Project docs consulted (ground truth):**

- `/Users/pvardanis/Documents/projects/dojo/.planning/PROJECT.md`
- `/Users/pvardanis/Documents/projects/dojo/docs/superpowers/specs/2026-04-18-dojo-design.md` (§2 Architecture, §3 Domain model, §4.1 Package layout, §4.2 Library picks, §4.3 Ports and adapters, §5 Data flows, §7 Testing strategy)

---

## 9. Quality-Gate Checklist

- [x] Components clearly defined with boundaries (§1)
- [x] Data flow direction explicit (§2)
- [x] Build order implications noted with rationale (§6)
- [x] Concrete pattern references — not generic advice — with canonical URLs (§3, §8)
- [x] Concerns with the spec's architecture explicitly flagged (§5) — one significant (draft store has no port), two minor (circular-import discipline, web-layer Pydantic scope)
- [x] Confidence levels assigned per source
- [x] Dependencies-flow-inward rule verified against spec §2 and global `CLAUDE.md`
- [x] No contradictions with existing spec decisions (§4.3 port typing rule, §3 layer ownership rule)
