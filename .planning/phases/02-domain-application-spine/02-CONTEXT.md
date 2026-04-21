# Phase 2: Domain & Application Spine - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 delivers the pure inner core of Dojo: domain entities, value
objects, typed IDs, domain + application exceptions, application ports
(Protocols + Callable aliases including the `DraftStore` port),
Pydantic DTOs for LLM I/O, and the `GenerateFromSource` use case driven
end-to-end for the TOPIC kind by hand-written fakes at every DIP
boundary.

**Nothing in this phase touches a database, the LLM, the filesystem, or
the web.** No SQLAlchemy models (Phase 3). No AnthropicLLMProvider
(Phase 3). No FastAPI routes (Phase 4). The artifact is code that runs
only through fakes — plus the lint rule that proves domain/application
never import from infrastructure/web.

Phase 2 is the last phase where port shapes are cheap to change.
Every subsequent phase hardens them.

</domain>

<decisions>
## Implementation Decisions

### Typed IDs & Entity Identity

- **D-01:** Typed IDs use `NewType` over `uuid.UUID`:
  ```python
  SourceId = NewType("SourceId", uuid.UUID)
  NoteId   = NewType("NoteId",   uuid.UUID)
  CardId   = NewType("CardId",   uuid.UUID)
  ReviewId = NewType("ReviewId", uuid.UUID)
  ```
  Declared in `app/domain/value_objects.py`. Zero runtime cost, ty/mypy
  catches `save_note(note_id=source.id)` at type-check time, domain
  stays stdlib-only (`uuid` is stdlib).
- **D-02:** IDs are minted by the **domain constructor** via
  `default_factory`:
  ```python
  id: SourceId = field(default_factory=lambda: SourceId(uuid.uuid4()))
  ```
  Every entity is fully identified at construction — no
  `Optional[SourceId]`, no "unsaved" state. The Phase 3 mapper passes
  stored UUIDs explicitly when loading (`Source(id=SourceId(row.id),
  ...)`). Tests that care about determinism override `id=` at the call
  site.
- **D-03:** `DraftToken` is a `NewType` over `uuid.UUID` too, declared
  in `app/application/ports.py` (it's an application concept, not a
  domain one). Same minting pattern: `default_factory` where created,
  explicit pass-through where re-hydrating.

### DraftStore Port Contract

- **D-04:** `DraftStore` Protocol exposes exactly two methods:
  ```python
  class DraftStore(Protocol):
      def put(self, token: DraftToken, bundle: DraftBundle) -> None: ...
      def pop(self, token: DraftToken) -> DraftBundle | None: ...
  ```
  `pop` is atomic read-and-delete — the save flow calls `pop` once,
  persists, and discards. There is intentionally **no `get`** on the
  port. Forcing callers to commit-or-discard closes PITFALL C10's
  read-then-delete race before it can be written.
- **D-05:** TTL (30 min per DRAFT-01) and concurrency semantics (lazy
  TTL check on access, `asyncio.Lock` around writes) live in the
  Protocol **docstring only**. Enforcement is Phase 3's
  `InMemoryDraftStore` concern. The port does not expose `evict_expired()`
  or a `Clock` injection.
- **D-06:** `FakeDraftStore` (Phase 2, in `tests/fakes/`) is a plain
  dict wrapper with a `force_expire(token)` test hook. No real time
  logic. Tests that need to exercise the expiry path call
  `force_expire` instead of advancing wall-clock.

### GenerateFromSource Use Case Shape

- **D-07:** Request is a typed dataclass in `app/application/dtos.py`:
  ```python
  @dataclass(frozen=True)
  class GenerateRequest:
      kind: SourceKind
      input: str | None   # None for TOPIC
      user_prompt: str
  ```
  Plain stdlib dataclass, not Pydantic — the Pydantic boundary is
  reserved for LLM I/O per spec §3.
- **D-08:** Response is:
  ```python
  @dataclass(frozen=True)
  class GenerateResponse:
      token: DraftToken
      bundle: DraftBundle
  ```
  `DraftBundle` is an application-layer dataclass (not a domain entity
  — nothing is a `Source`/`Note`/`Card` until the user saves) containing
  the proposed note + list of proposed card drafts. The web layer in
  Phase 4 renders review directly from the bundle; the draft-store
  still holds a copy so a reload works.
- **D-09:** Phase 2 wires **TOPIC only** end-to-end. FILE and URL
  branches inside `execute()` raise `UnsupportedSourceKind` (app-layer
  exception). A unit test covers the raise path. Phase 4 replaces the
  raise with real `SourceReader`/`UrlFetcher` calls.
- **D-10:** `LLMProvider.generate_note_and_cards(source_text, user_prompt)`
  signature matches spec §5.1: `source_text: str | None` — `None` for
  TOPIC kind passes through. No kind-specific LLM methods; the prompt
  shaping for TOPIC lives in Phase 3's `prompts.py`.

### Tests & Boundary Enforcement

- **D-11:** TEST-03 contract harness lives in
  `tests/contract/test_llm_provider_contract.py`. Pattern:
  ```python
  @pytest.fixture(params=["fake", "anthropic"])
  def llm_provider(request): ...
  ```
  The `"fake"` branch always yields `FakeLLMProvider`. The
  `"anthropic"` branch skips unless **both** `RUN_LLM_TESTS=1` is set
  **and** `from app.infrastructure.llm.anthropic_provider import
  AnthropicLLMProvider` succeeds. In Phase 2 the import fails → clean
  auto-skip without requiring a stub module. Phase 3 creates the real
  adapter → the variant activates automatically.
- **D-12:** Layer-boundary enforcement via **import-linter**. Add
  `import-linter` to the dev dependency group. Create `.importlinter`
  with two forbidden contracts:
  - `app.domain` must not import from `app.infrastructure` or `app.web`
  - `app.application` must not import from `app.infrastructure` or
    `app.web`

  Wire into `make lint` (`lint-imports` appended after `ruff check`) so
  violations fail `make check` and therefore pre-commit + CI. Closes
  the Phase 1 LEARNINGS open item.

### Claude's Discretion

These micro-decisions follow from the locked choices above. Planner /
executor has authority; surface to Danny only if implementation reveals
a conflict.

- **Entity mutability** — domain dataclasses are `frozen=True`. Edits
  (Phase 4+) construct a new instance via `dataclasses.replace()`.
- **Pydantic DTO posture** — `model_config = ConfigDict(extra="ignore")`
  + `min_length=1` on the cards list (per PITFALL M6). Note/Card DTOs
  are strict on required fields, permissive on extras.
- **Fakes file layout** — one file per fake under `tests/fakes/`
  (`fake_llm_provider.py`, `fake_source_repository.py`,
  `fake_note_repository.py`, `fake_card_repository.py`,
  `fake_card_review_repository.py`, `fake_draft_store.py`). Re-export
  via `tests/fakes/__init__.py` so tests import
  `from tests.fakes import FakeLLMProvider, ...`.
- **Fake assertion style** — fakes expose assertable state as public
  attributes (`fake.puts: list[tuple[DraftToken, DraftBundle]]`,
  `fake.saved_cards: list[Card]`), not `.calls` lists or
  `assert_called_with`. Tests assert against the exposed collections
  directly.
- **Domain vs application exception split:**
  - `app/domain/exceptions.py` — `DojoError` (base), entity invariant
    violations (likely rare in MVP — may start with just the base
    class and `InvalidEntity` if a real case shows up).
  - `app/application/exceptions.py` — use-case failures that inherit
    from `DojoError`: `UnsupportedSourceKind`, `DraftExpired`
    (surface from Phase 3+ but declared here), `LLMOutputMalformed`
    (declared here, raised by Phase 3's adapter).
- **Entity construction invariants** — enforce in `__post_init__` with
  bare `ValueError` for basic string-non-empty checks (e.g.
  `Card.question`, `Source.user_prompt`). Lift to a named domain
  exception only if callers need to branch on the error type.
- **Protocol method docstrings** — one-line docstrings that specify
  return/error semantics per PITFALL M11 (not restatements of the
  method name). Example: `"""Save source; raises DuplicateSource if
  identifier exists."""`

### Folded Todos

None — pending todos list was empty at discussion time.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level (authoritative)

- `.planning/PROJECT.md` — vision, constraints, Key Decisions table
  (DraftStore Protocol, fakes-not-mocks, drafts in-memory, notes
  overwrite / cards append)
- `.planning/REQUIREMENTS.md` — owns DRAFT-01, TEST-01, TEST-03 for
  this phase. Cross-cutting notes at the end: "TEST-03 contract tests
  scaffolded in Phase 2, extended in Phase 3"; "C10 draft-store race
  conditions are Phase 3's concern even though the port is Phase 2".
- `.planning/ROADMAP.md` §"Phase 2: Domain & Application Spine" —
  Goal, Depends on, Requirements, 6 Success Criteria
- `CLAUDE.md` (project root) — Protocol-vs-function clarifier
  (project-local), TDD mandatory, layer dependencies flow inward

### Design spec (authoritative on implementation detail)

- `docs/superpowers/specs/2026-04-18-dojo-design.md` — single source
  of truth for architecture and implementation detail
  - §3 Domain model — entity fields (Source, Note, Card, CardReview),
    value objects (SourceKind, Rating), field rationale, regeneration
    policy, **layer ownership** ("Domain entities are plain Python
    dataclasses. No ORM types, no Pydantic, no HTTP types.")
  - §4.1 Package layout — target file layout for `app/domain/`,
    `app/application/`, `tests/unit/`, `tests/contract/`
  - §4.3 Ports and adapters — the port-shape rule ("Stateless one-op
    ports are typed `Callable` aliases. Stateful or multi-method
    ports are `typing.Protocol`.") + table of all six ports + two
    aliases
  - §5.1 Generate flow — sequence diagram showing the TOPIC branch
    (`source_text = None`) and draft-store round-trip
  - §6 Error handling — §6.4 Rules: exceptions live in
    `app/domain/exceptions.py` and `app/application/exceptions.py`;
    infrastructure wraps third-party errors; no silent fallbacks
  - §7 Testing strategy — §7.1 Unit tests (fakes implementing
    Protocols, assertable state, no `Mock()`)
  - §9 Decisions log — non-obvious decisions already resolved

### Research (Phase 2 entry gates)

- `.planning/research/PITFALLS.md` — entry gates relevant to Phase 2:
  - **C5** (atomic save session) — informs the DraftStore contract
    (the port shape must not foreclose Phase 4's `async with
    session.begin()` use-case-level commit)
  - **C6** (Anthropic tool-use DTO validation) — informs the DTO
    strictness posture (locked in Claude's discretion)
  - **C10** (DraftStore concurrency + TTL + atomic pop) — primary
    driver for D-04 / D-05
  - **M6** (Pydantic `extra="ignore"` for DTOs) — locked posture
  - **M7** (fake-drift) — the single biggest Phase 2 risk; driver
    for D-11 contract harness. Also informs the fake design rules in
    Claude's discretion.
  - **M11** (interrogate + Protocol methods) — one-line docstrings
    specify return/error semantics (locked posture)
- `.planning/research/STACK.md` — version floors and flags. Pydantic
  `extra="ignore"` default and `model_config` in v2.

### Prior phase context

- `.planning/phases/01-project-scaffold-tooling/01-CONTEXT.md` —
  - **D-11** Phase 1 scaffold locations; `app/domain/` and
    `app/application/` will be created fresh by Phase 2 (they are
    explicit Phase 2+ creation per D-11's list).
  - **D-15** interrogate + Protocol stance (100% is 100%, accept
    one-line docstrings).
  - **D-20** package mode for uv — `uv run pytest` and `uv run
    alembic` see the current source tree; no PYTHONPATH hacks.
- `.planning/phases/01-project-scaffold-tooling/LEARNINGS.md` —
  - **Open item "Phase-2 boundary lint"** — closed by D-12
    (import-linter).
  - Item #3 "Tests that pass but don't test anything are the most
    dangerous outcome" — motivates the fake-design rules and
    assertion-style discretion.

### External conventions

- `~/Documents/Black Lodge/knowledge-base/wiki/python-project-setup.md` —
  authoritative on file size limits, ABOUTME convention, Protocol vs
  ABC preference, dataclasses-for-containers, Pydantic at validation
  boundaries, `logging` with `get_logger(__name__)`, exceptions per
  layer in a central `exceptions.py`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `app/logging_config.py` — `get_logger(__name__)` helper is
  established. Phase 2 application modules obtain loggers through it;
  domain modules **do not log** (pure dataclasses and exceptions only
  — no I/O, including log I/O).
- `app/settings.py` — pydantic-settings singleton exists. Phase 2
  modules **do not import it**; settings are an infrastructure concern
  and will be wired into use cases via `Depends` in Phase 4. Importing
  it from domain or application would violate D-12's import-linter
  contract.

### Established Patterns (Phase 1)

- Every Python file starts with the two-line `# ABOUTME:` header.
- Module docstring + one-line docstrings on public methods
  (interrogate 100%, D-15 from Phase 1).
- File size ≤100 lines, split at 150 (python-project-setup wiki).
- Each layer owns exceptions in a central `exceptions.py`.
- Frozen dataclasses for value objects (e.g. the Phase 1 `Settings`
  class pattern — though Settings is Pydantic, the ethos is the same).

### Integration Points

- `app/main.py` composition root exists (Phase 1 `create_app()`).
  Phase 2 adds nothing to it — no new adapters to inject yet. Phase 4
  wires the use case + real adapters into `deps.py`.
- `pyproject.toml` gains a new dev dep (`import-linter`) and a new
  `[tool.importlinter]` section (or a separate `.importlinter` file).
  `Makefile`'s `lint` target gains a `lint-imports` step after `ruff
  check`.
- **Phase 3 contract (do not foreclose):** SQLAlchemy ORM models will
  round-trip domain entities via mappers. Phase 2 entity dataclasses
  **must not leak ORM types**; every field must be a stdlib type or a
  NewType over one. Ports must not assume a session / connection (the
  use case layer opens the transaction in Phase 4).
- **Phase 4 contract (do not foreclose):** FastAPI routes will
  translate domain/application exceptions to HTTP responses. Exceptions
  raised in Phase 2 should carry a human-readable message, not
  structured error codes.

</code_context>

<specifics>
## Specific Ideas

- **"Lock shapes with fakes, harden with adapters."** Phase 2's
  product is a set of frozen Protocol contracts plus a use case that
  exercises them end-to-end against hand-written fakes. If Phase 3
  needs to change a port signature, that's evidence Phase 2's
  discussion didn't dig deep enough — treat as a re-plan signal, not a
  routine update.
- **"Boring and obvious" test for domain entities.** If a reader needs
  to learn a new idiom to read `Source`, we've over-designed. The
  domain layer is vanilla dataclasses + NewType + enum + a few
  `ValueError`s in `__post_init__`. Anything fancier earns its place.
- **The contract test is the firewall.** Every port declared in this
  phase gets both a fake and a contract test that the fake passes.
  Without the contract test, the fake encodes assumptions that the
  real adapter won't satisfy (PITFALL M7 — "the fake silently became
  the spec"). The `RUN_LLM_TESTS` env gate exists so CI skips the
  Anthropic leg cleanly when the real adapter or the API key isn't
  available.

</specifics>

<deferred>
## Deferred Ideas

- **`FOLDER` source kind + `Retriever` / `EmbeddingProvider` ports** —
  v2 roadmap, spec §10 Phase 2 (not to be confused with project
  Phase 2).
- **Mock interview mode** — v2 roadmap.
- **SRS scheduling (`Card.ease_factor`, `interval`,
  `next_review_at`)** — v2 Phase 3.
- **`IdGenerator` Protocol port** — explicitly rejected in favor of
  `default_factory=uuid.uuid4`. Revisit only if we need deterministic
  IDs cross-process or ULID/snowflake later.
- **DB-mint-at-insert for IDs** — explicitly rejected; entities are
  always identified at construction.
- **Port-level TTL / Clock injection on DraftStore** — rejected;
  enforcement is Phase 3's `InMemoryDraftStore` concern.
- **Deferred-import stub for AnthropicLLMProvider in Phase 2** —
  rejected in favor of the `fixture(params=...)` + ImportError path
  which skips cleanly without dead-code commits.
- **Custom AST-walking pytest test for boundary enforcement** —
  rejected in favor of import-linter.

### Reviewed Todos (not folded)

None — pending todos list was empty.

</deferred>

---

*Phase: 02-domain-application-spine*
*Context gathered: 2026-04-22*
