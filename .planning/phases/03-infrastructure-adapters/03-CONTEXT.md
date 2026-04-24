# Phase 3: Infrastructure Adapters - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 delivers real concrete adapters behind every port declared in
Phase 2:

- `Sql{Source,Note,Card,CardReview}Repository` — sync SQLAlchemy
  repositories with declarative ORM row classes + pure mapper
  functions; `expire_on_commit=False` already live in `session.py`
- `AnthropicLLMProvider` — tool-use structured output, `tenacity`
  transport retries, Pydantic DTO validation, SDK exceptions wrapped
  into domain types
- `InMemoryDraftStore` — plain dict + lazy TTL + GIL-atomic `pop`
- `read_file` (`SourceReader`) — filesystem adapter for FILE kind
- `fetch_url` (`UrlFetcher`) — `httpx` + `trafilatura` + paywall
  heuristics for URL kind
- First real Alembic migration creating `sources`, `notes`, `cards`,
  `card_reviews` tables on top of Phase 1's empty baseline
- Each adapter passes its own integration tests plus the Phase 2
  contract harness (extended from one port to seven)

**Nothing in this phase touches FastAPI routes or composes a full
request-path flow.** No `SaveDraft` use case (Phase 4). No
Generate-Review-Save HTTP routes (Phase 4). The composition root
(`app/main.py`) gets its fake → real adapter swap here, but the
flow that exercises that wiring end-to-end through the browser is
Phase 4's success criterion.

Phase 3 is the phase where Phase 2's port shapes get their first
real test. If a Protocol needs to change, that's evidence Phase 2's
contract harness missed something — re-plan signal, not routine
update.

</domain>

<decisions>
## Implementation Decisions

### Transaction Boundary & Session Lifecycle

- **D-01:** **Use case owns the transaction boundary.** Phase 4's
  `SaveDraft` use case will receive a `Session` via composition-root
  injection and open `with session.begin():` inside `execute()`.
  Repositories are constructed with that same request-scoped
  `Session` and participate in the transaction. No `UnitOfWork`
  Protocol — the SQLAlchemy `Session` already is one, and introducing
  a parallel abstraction with a single implementation violates
  YAGNI-vs-scheduled-variants (no second UoW impl is on any roadmap).

- **D-01a:** **Phase 3 delivers the shape, Phase 4 exercises it.**
  The Phase 3 integration tests for SC #2 (force the 3rd insert to
  fail, assert rollback) directly exercise the `with session.begin():
  repo.save(...); repo.save(...); repo.save(...)` pattern so Phase 4
  inherits a proven flow.

- **D-01b:** **Repos receive `Session` at construction, not per
  method.** Phase 2 port signatures (`save(self, source: Source) ->
  None`) preclude per-method session args. Each repo holds a single
  Session reference for its lifetime. The Session's lifetime equals
  the request's (Phase 4 wires this via `Depends(get_session)` —
  standard FastAPI pattern).

### ORM ↔ Domain Mapping

- **D-02:** **Declarative ORM + pure mapper functions.** Layout:
  - `app/infrastructure/db/models.py` — `SourceRow`, `NoteRow`,
    `CardRow`, `CardReviewRow`, each inheriting from the existing
    `Base` (`DeclarativeBase` in `session.py`). Columns use
    `Mapped[...]` annotations. Each row class maps 1:1 to its table.
  - `app/infrastructure/db/mappers.py` — pure functions:
    `source_to_row(Source) -> SourceRow`,
    `source_from_row(SourceRow) -> Source`; one pair per entity.
    No classes, no state, no DB access — unit-testable without a
    fixture.
  - `app/infrastructure/repositories/sql_*.py` — one file per repo,
    each implementing its Phase 2 Protocol. The `save()` path calls
    `source_to_row(entity)` then `session.merge(row)`. The `get()`
    path calls `session.get(SourceRow, str(id))` then
    `source_from_row(row)` if non-None.

- **D-02a:** **Domain stays stdlib-pure.** The import-linter contract
  from Plan 02-05 (`app.domain` must not import from
  `app.infrastructure`) holds unchanged. No SQLAlchemy types leak
  into domain.

- **D-02b:** **No ORM relationships.** Phase 2 ports are flat —
  `SourceRepository.get(source_id) -> Source | None`, not
  `get_aggregate(source_id) -> (Source, Note, list[Card])`. Phase 3
  repos query flat per entity. The SC #1 "Source + Note + Cards
  round-trip" integration test exercises three separate repo calls,
  not a traversal. This sidesteps PITFALLS C1 (`MissingGreenlet` on
  lazy access) and C2 (selectinload vs joinedload pitfalls) by not
  growing a relationship surface at all.

- **D-02c:** **`lazy="raise"` as belt-and-suspenders.** Even without
  declared relationships in the ORM layer, set `lazy="raise"` at the
  mapper registry level if SQLAlchemy 2.0 supports a default —
  otherwise it's a no-op. If a future reader adds a relationship,
  lazy access fails loudly instead of limping silently.

- **D-02d:** **Column types (locked).**
  - IDs: `Mapped[str]` (UUID converted via `str(uuid)` / `uuid.UUID(s)`
    at mapper boundary). SQLite doesn't have a native UUID type; text
    is portable and readable in `sqlite3 .schema` dumps.
  - Timestamps: `Mapped[datetime]` → native `DATETIME` (SQLAlchemy
    handles the conversion).
  - `SourceKind` / `Rating` enums: stored as `Mapped[str]` with the
    enum `.value` at the mapper boundary. Avoids SQLAlchemy's
    `Enum` type, which has pitfalls on rename/reorder across
    migrations.
  - `Card.tags` (list of strings): stored as JSON-encoded TEXT (SQLite
    has no array type; JSON works and is portable to Postgres' `JSONB`
    later). Mapper handles `json.dumps`/`json.loads`.

### Anthropic Retry & Error Wrapping

- **D-03:** **Tenacity owns transport retries, SDK muzzled.**
  - Client construction: `anthropic.Anthropic(api_key=..., max_retries=0)`.
    The `max_retries=0` is non-optional — without it, PITFALL C7
    ships.
  - Retry decorator on the single SDK call:
    ```python
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((
            anthropic.RateLimitError,
            anthropic.InternalServerError,  # 5xx
            anthropic.APIConnectionError,  # network
        )),
        reraise=True,
    )
    ```
  - Whitelisted exception types only. `AuthenticationError` (401),
    `BadRequestError` (400), `NotFoundError` (404), etc. propagate
    immediately — they're permanent failures, retrying burns budget.
    `InternalServerError` is the SDK's 5xx subclass; `APIStatusError` is
    the non-2xx base and would over-include 4xx.

- **D-03a:** **Semantic retry is separate from tenacity.** Per spec
  §6.1, one retry on malformed-JSON with stricter prompt, then raise
  `LLMOutputMalformed`. This lives as an explicit `try/except
  pydantic.ValidationError` inside `generate_note_and_cards`, NOT as
  a tenacity predicate. Each semantic attempt triggers a full
  tenacity lifecycle underneath.

- **D-03b:** **SDK exceptions wrapped into domain types at the
  adapter's outer boundary** (spec §6.4). Adapter catches
  `anthropic.RateLimitError` after tenacity gives up and raises our
  `LLMRateLimited`. Same for `AuthenticationError → LLMAuthFailed`,
  `APIConnectionError → LLMUnreachable`, etc. The application layer
  never imports `anthropic`.

- **D-03c:** **SC #4 test pattern (locked).** `respx` stubs the HTTP
  layer, first response is 429, second is 200 with a valid tool-use
  block. Assert exactly 2 HTTP calls (one original + one retry).
  Also: assert 0 retries when the stub returns 401 immediately
  (whitelist check).

### DraftStore Concurrency

- **D-04:** **Plain dict, no lock, GIL-atomic pop.** The only
  contended operation is `dict.pop(token, None)`, which CPython
  implements as a single atomic bytecode. Two callers racing on the
  same token: exactly one wins, one gets `None`. No `threading.Lock`,
  no `asyncio.Lock`.

- **D-04a:** **Lazy TTL check on access.** Expired entries are
  removed when someone happens to pop them — no background sweep, no
  timer thread. The TTL check runs after the atomic pop on a local
  variable, not on the dict.

- **D-04b:** **Clock is injected.** `InMemoryDraftStore.__init__`
  takes `clock: Callable[[], float] = time.monotonic`. SC #5's
  "fake clock" TTL test advances a list-captured counter; no sleep,
  no monkeypatch.

- **D-04c:** **Class docstring names the GIL assumption.** "Thread
  safety comes from CPython GIL atomicity of `dict.pop`. If dojo
  ever runs on a no-GIL Python build (PEP 703), swap in
  `threading.Lock`." Prevents a future reader from shipping on
  no-GIL Python and getting mysterious bugs.

- **D-04d:** **Supersedes Phase 2 CONTEXT.md §D-05.** Phase 2 noted
  "TTL + lazy TTL check on access, `asyncio.Lock` around writes" —
  that `asyncio.Lock` line came from the pre-Phase-1-review
  async-throughout assumption. With sync `DraftStore` Protocol and
  single-event-loop FastAPI deployment, no lock is needed.

### URL Fetcher & FILE Reader

- **D-05:** **Paywall / low-quality fetch heuristics** (PITFALL C9,
  locked). The `fetch_url` callable returns extracted text iff:
  - HTTP 2xx status (else raise `SourceFetchFailed("URL returned N")`)
  - `httpx` timeout ≤ 10s (else raise `SourceFetchFailed("timeout")`)
  - `trafilatura.extract(...)` returns non-None (else raise
    `SourceNotArticle("extraction failed")`)
  - Extracted text length ≥ 1000 chars (below that, raise
    `SourceNotArticle("too short")`)
  - Paywall-marker check: if text length < 2000 chars AND contains
    ≥ 2 of {"subscribe", "sign up", "sign in", "paywall",
    "continue reading", "free article"} (case-insensitive), raise
    `SourceNotArticle("paywall suspected")`
  - Custom `User-Agent: Dojo/0.1 (+local study app)` to avoid the
    default `python-httpx/...` which triggers some anti-bot filters.
  - Follow redirects (`httpx` default is true) — fine for article URLs.

- **D-06:** **FILE reader** (`read_file`):
  - Accept any filesystem path — single-user local app, no root
    restriction.
  - UTF-8 strict decode; `UnicodeDecodeError` wraps into
    `SourceUnreadable`.
  - `FileNotFoundError` wraps into `SourceNotFound`.
  - `PermissionError` wraps into `SourceUnreadable`.
  - No size limit at the reader layer — if a user points at a 10MB
    file, that's on them; the LLM will refuse via `LLMContextTooLarge`
    downstream, which is a readable error.

### Contract Harness Extension

- **D-07:** **Extend Phase 2's single-port harness to all seven
  ports.** Each port gets a `test_{port}_contract.py` in
  `tests/contract/` following the same `fixture(params=["fake",
  "real"])` pattern. The "real" leg activates when:
  - `LLMProvider`: `RUN_LLM_TESTS=1` set AND `AnthropicLLMProvider`
    importable (already live from Plan 02-05)
  - `SourceRepository` / `NoteRepository` / `CardRepository` /
    `CardReviewRepository`: always run against a tmp SQLite file
    (no env gate — real adapter is cheap)
  - `DraftStore`: always run against `InMemoryDraftStore` (same —
    cheap, in-process)
  - `UrlFetcher`: always run against `fetch_url` with `respx` stub;
    no env gate, no real network
  - `SourceReader`: always run against `read_file` with `tmp_path`
    fixture; no env gate

  Each "real" leg runs on every `make check`. The Anthropic leg
  stays opt-in per Phase 2 D-11.

### Migration Authoring

- **D-08:** **Autogenerate → review → edit → commit.**
  - Create `app/infrastructure/db/models.py` first (the declarative
    classes per D-02).
  - Wire `app.infrastructure.db.models:Base.metadata` into
    `migrations/env.py` for autogenerate.
  - Run `alembic revision --autogenerate -m "create initial schema"`.
  - Human-review the generated revision file for SQLite-specific
    weirdness (e.g. `op.create_index` on tables not yet created,
    `ALTER TABLE` patterns SQLite doesn't support).
  - Edit as needed; commit the revision.
  - `alembic upgrade head` on a fresh DB → apply → `sqlite3 dojo.db
    .schema` → verify four tables present.

- **D-08a:** **One migration, all four tables.** No per-entity
  migrations. The atomic schema delivery is one revision so Phase 3
  lands a coherent DB shape.

### Phase 3 Deliverables Beyond Code

- **D-09:** **Arch doc extensions.** The following additions to
  `docs/architecture/overview.md` land as part of Phase 3 plans (not
  a separate chore PR), because they describe patterns the Phase 3
  code implements:
  - §4 or §5: "Persistence data flow" subsection — the who-sees-what
    matrix (route / use case / repo / mapper / ORM / SQL), the
    save-side trace showing use case opens `session.begin()` and
    repos translate at the boundary, a `SaveDraft` sequence diagram
    (Phase 4 pattern as Phase 3's contract)
  - §6 (glossary): explain Session as transaction handle, not SQL
    surface; explain mapper functions
  - §4 stale-line fix: `InMemoryDraftStore with asyncio.Lock` →
    update to match D-04 (plain dict + GIL atomicity + lazy TTL)

- **D-10:** **PR #11 chore lands independently.** `GenerateFromSource`
  docstring clarification already on `chore/generate-from-source-
  docstring` → PR #11. Phase 3 plans do not duplicate this edit.

### Claude's Discretion

- Per-request `Session` via FastAPI `Depends(get_session)` in
  `app/web/deps.py` — exact generator function shape
- Repository file layout — one `sql_source_repository.py` per repo
  vs a single `repositories.py` with all four (lean one-file-per-repo
  for 100-line ceiling)
- `Anthropic` tool schema shape — one tool `generate_note_and_cards`
  returning `{note: {...}, cards: [{...}]}` vs two separate tools
  (one-tool is simpler; spec doesn't mandate)
- Exact `tenacity` decorator wiring — module-level decorator vs
  instance-method `.retry_with` wrapper (latter is cleaner for
  testing retry counts)
- Fake clock fixture shape — `monkeypatch`-free, list-captured
  counter injected into `InMemoryDraftStore(clock=...)`
- respx fixture organization — per-test stub vs session-wide
  `httpx.MockRouter`
- `trafilatura` config options (`include_comments=False`,
  `deduplicate=True`, etc.) — pick the sensible-default combination
  and lock in the URL fetcher module
- Exception class hierarchy additions in
  `app/infrastructure/exceptions.py` or a per-adapter exceptions
  file — planner's call based on which grows more

### Folded Todos

None — pending todos list empty at discussion time.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level (authoritative)

- `.planning/PROJECT.md` — vision, constraints, Key Decisions table
  (sync SQLAlchemy reversal, tenacity for retries, DraftStore
  Protocol, fakes-not-mocks, notes-overwrite / cards-append on
  regenerate)
- `.planning/REQUIREMENTS.md` — owns LLM-01, LLM-02, GEN-02,
  PERSIST-02 for this phase. Cross-cutting notes at the end:
  "TEST-03 contract tests scaffolded in Phase 2, extended in
  Phase 3"; "C10 draft-store race conditions are Phase 3's concern".
- `.planning/ROADMAP.md` §"Phase 3: Infrastructure Adapters" —
  Goal, Depends on, Requirements, 7 Success Criteria
- `CLAUDE.md` (project root) — stack pins, conventions,
  Protocol-vs-function clarifier, PR discipline

### Design spec (authoritative on implementation detail)

- `docs/superpowers/specs/2026-04-18-dojo-design.md`
  - §4.2 Library picks — locked libraries (SQLAlchemy 2.0 sync,
    anthropic SDK, tenacity, trafilatura, httpx, respx)
  - §4.3 Ports and adapters — adapter table; four `Sql*Repository`
    + `AnthropicLLMProvider` + `fetch_url` + `read_file`
  - §5.1 Generate flow — sequence diagram; Phase 3 adapters plug
    into the existing `GenerateFromSource` use case behind their
    ports
  - §6 Error handling — §6.1 LLM failures (3 retries; one
    malformed-JSON retry; typed exceptions),
    §6.2 Network failures (timeout / non-2xx / non-HTML),
    §6.3 Filesystem failures,
    §6.4 Rules (infra wraps third-party errors; no silent fallbacks)
  - §7.2 Integration tests — real SQLite tmp file; file reader
    real fs; URL fetcher respx-stubbed; LLM provider opt-in via
    `RUN_LLM_TESTS=1`

### Research (Phase 3 entry gates)

- `.planning/research/PITFALLS.md` — entry gates driving Phase 3
  decisions:
  - **C1** (`MissingGreenlet` on post-commit attribute access) —
    driver for D-02b (flat repos, no ORM relationships)
  - **C2** (selectinload vs joinedload) — moot given D-02b
  - **C3** (`expire_on_commit=True` refetch trap) — mitigated by
    Phase 1 `session.py` already setting `expire_on_commit=False`
  - **C5** (atomic save session management) — driver for D-01 /
    D-01a
  - **C6** (Anthropic tool-use is not strict JSON schema) —
    driver for D-03a semantic retry
  - **C7** (SDK + tenacity stacked retry trap) — driver for
    D-03 SDK muzzling
  - **C8** (Anthropic context-size limits) — informs the
    `LLMContextTooLarge` wrap in D-03b
  - **C9** (URL extraction quality / paywall) — driver for D-05
  - **C10** (DraftStore races) — **superseded** for the
    single-user sync-DraftStore case; driver for D-04 atomic pop
  - **M6** (Pydantic DTO `extra="ignore"` posture) — locked in
    Phase 2; Anthropic adapter DTO validation inherits
  - **M7** (fake drift) — driver for D-07 contract harness
    extension
- `.planning/research/STACK.md` — version pins, known-issue flags
  (SQLAlchemy 2.0 sync, tenacity floor, trafilatura flags,
  respx pattern)

### Prior phase context

- `.planning/phases/01-project-scaffold-tooling/01-CONTEXT.md`
  - **D-01 through D-03** — portable-by-construction DB posture;
    Phase 3 inherits the `DATABASE_URL` setting, dialect-guarded
    PRAGMA listener, settings-backed Alembic env
  - **D-06** — tmp-file SQLite test DB pattern; Phase 3
    integration tests extend this
  - **D-08 through D-10** — empty initial revision in Phase 1 is
    the baseline Phase 3's first real migration stacks on top of
  - **D-14** — pre-commit pytest runs unit only; Phase 3
    integration tests land in `make check` + CI, not the hook
  - **D-15** — interrogate 100% on Protocol methods; Phase 3
    adapter methods get one-line semantic docstrings
- `.planning/phases/01-project-scaffold-tooling/LEARNINGS.md` —
  Phase-2-boundary-lint open item (closed by Plan 02-05);
  integration fixture template lives in `tests/conftest.py`
- `.planning/phases/02-domain-application-spine/02-CONTEXT.md`
  - **D-04 / D-05** — DraftStore Protocol shape (put + atomic pop,
    no get); Phase 3 `InMemoryDraftStore` implements this.
    D-05's `asyncio.Lock` note is **superseded** by Phase 3 D-04.
  - **D-07 / D-08** — `GenerateRequest` / `GenerateResponse` /
    `DraftBundle` dataclass shapes; Phase 3 adapters consume
    these unchanged
  - **D-10** — `LLMProvider.generate_note_and_cards(source_text,
    user_prompt)` signature; Phase 3 Anthropic adapter implements
    this literally
  - **D-11** — TEST-03 contract harness pattern; Phase 3 extends
    from 1 port to 7
  - **D-12** — import-linter boundaries (now live via Plan 02-05);
    Phase 3 must not introduce `app.domain`→`app.infrastructure`
    or `app.application`→`app.infrastructure` imports
  - Claude's Discretion "Fake assertion style" — real adapters
    are tested against the same contract tests, so the assertion
    style (public-attribute inspection, not `.calls` lists)
    applies symmetrically

### External conventions

- `~/Documents/Black Lodge/knowledge-base/wiki/python-project-setup.md`
  — file size ≤100 lines (split at 150), ABOUTME headers,
  exceptions-per-layer in central `exceptions.py`, dataclasses for
  containers, Pydantic at validation boundaries,
  `get_logger(__name__)` per module
- **SQLAlchemy 2.0 docs** — `Mapped[...]` annotations, `session.merge`
  vs `session.add`, `expire_on_commit` semantics. Referenced during
  mapper / repo implementation in plans.
- **anthropic SDK docs** — `max_retries` client arg, `messages.create`
  with `tools` parameter for structured output, exception hierarchy
  (`RateLimitError`, `APIStatusError`, `APIConnectionError`,
  `AuthenticationError`, `BadRequestError`, `NotFoundError`).
  Referenced during adapter implementation.
- **tenacity docs** — `@retry` decorator, `stop_after_attempt`,
  `wait_exponential`, `retry_if_exception_type`, `reraise=True`.
- **trafilatura docs** — `extract()` options, known flags for
  paywalled / SPA sites.
- **respx docs** — `MockRouter` usage for `httpx` stubbing.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (Phase 1 + Phase 2 spine)

- `app/infrastructure/db/session.py` — **live**. `Base`
  (`DeclarativeBase`), `engine`, `SessionLocal` with
  `expire_on_commit=False`, dialect-guarded SQLite PRAGMA listener
  (FK ON, WAL, busy_timeout). Phase 3 adds ORM row classes that
  inherit from this `Base`. Phase 3 repos construct from
  `SessionLocal()` (during integration tests) or receive a
  dep-injected `Session` (Phase 4 wiring).
- `app/settings.py` — `DATABASE_URL`, `ANTHROPIC_API_KEY` (as
  `SecretStr`), `RUN_LLM_TESTS`. Phase 3 `AnthropicLLMProvider`
  reads the key via `get_settings()`. Composition root in
  `app/main.py` instantiates the provider with settings.
- `app/logging_config.py` — `get_logger(__name__)` helper. Every
  Phase 3 adapter module obtains its logger through this.
- `app/application/ports.py` — seven ports locked in Phase 2.
  Phase 3 supplies the concrete that satisfies each, via
  structural subtyping (no `@runtime_checkable`, no explicit
  `class ...(LLMProvider):` inheritance — implementing the method
  signatures is enough).
- `app/application/dtos.py` — `GenerateRequest`, `GenerateResponse`,
  `DraftBundle`, `NoteDTO`, `CardDTO`. `NoteDTO` / `CardDTO` are
  what the LLM adapter returns; Pydantic validation happens there
  (spec §6.1 + Phase 2 Claude's discretion M6 posture:
  `extra="ignore"`, `min_length=1` on cards).
- `app/application/extractor_registry.py` — live registry. Phase 3
  registers `FileExtractor` and `UrlExtractor` implementations
  (thin wrappers around `read_file` / `fetch_url` that accept a
  `GenerateRequest` and extract the text).
- `tests/fakes/` — six fakes (`FakeLLMProvider`, `Fake*Repository`
  × 4, `FakeDraftStore`). Phase 3 does NOT touch these — they
  continue to power unit tests. Real adapters run in contract +
  integration tests only.
- `tests/contract/test_llm_provider_contract.py` — live harness for
  `LLMProvider`. Phase 3 extends this pattern file-by-file to each
  new port.
- `tests/conftest.py` — async DB fixtures and pristine-log fixture
  already live from Phase 1. Phase 3 integration tests reuse the
  tmp-file SQLite fixture unchanged.
- `migrations/env.py` + `migrations/versions/0001_initial.py` —
  Phase 1 async Alembic baseline. Phase 3 stacks its real schema
  migration on top. (Note: the project reversed to sync SQLAlchemy
  post-Phase 1; verify the Alembic env.py is still async-shaped or
  was flipped. Researcher step should confirm.)

### Established Patterns

- Two-line `# ABOUTME:` header on every Python file.
- Module docstring + one-liner docstrings on public methods.
  Sphinx `:param:` / `:returns:` / `:raises:` format enforced by
  `pydoclint` (added in PR #9; `skip-checking-raises=true`).
- `interrogate` at 100% — Phase 3 adapter methods get semantic
  one-liners (what-it-does + what-it-raises), not restatements of
  the method name (Phase 1 D-15).
- File size ≤100 lines, split at 150 — one file per repository,
  one per extractor, one per adapter module.
- Frozen dataclasses for containers; Pydantic only at validation
  boundaries (Anthropic DTO validation is one such boundary).
- Structural-subtype implementation of Protocols — no explicit
  `class SqlSourceRepository(SourceRepository):` inheritance; ty
  verifies conformance.
- `make check` gate: format + lint + typecheck + docstrings +
  pydoclint + pytest. Pre-commit runs unit-only pytest (Phase 1
  D-14); integration tests run in `make test` / CI.
- Import-linter contracts (live via Plan 02-05): `app.domain` and
  `app.application` must not import from `app.infrastructure`;
  `app.domain` must not import from `app.application`. Every
  Phase 3 file lands in `app.infrastructure.*` and is therefore
  unrestricted in what it imports — but it must never be imported
  *by* the inner layers.

### Integration Points

- **`app/main.py` composition root** — Phase 3 swaps fakes for
  real adapters. The wiring pattern is a single function that
  reads `get_settings()`, constructs the `AnthropicLLMProvider`,
  constructs `InMemoryDraftStore`, constructs four
  `Sql*Repository` instances (but these need a per-request
  `Session`, so they're factory'd rather than singleton'd),
  registers FILE + URL extractors with the
  `SourceTextExtractorRegistry`, and returns the wired
  `GenerateFromSource` use case. Phase 4 extends this with
  FastAPI `Depends(...)` wiring.
- **`Base.metadata` ↔ Alembic** — `migrations/env.py` imports
  `Base` from `app.infrastructure.db.session`; Phase 3 creates
  `app/infrastructure/db/models.py` and ensures `env.py` imports
  it (or that `session.py` eagerly imports models.py) so
  autogenerate sees the tables. PITFALL M9 mitigation.
- **Contract harness ↔ real adapters** — each contract test file
  parameterizes on `[fake, real]`. The `real` fixture is factory'd
  per-test (e.g. real repo gets a fresh tmp-SQLite engine + migrated
  schema + new session). Fake fixture is fresh instance.
- **respx + httpx** — URL fetcher integration tests use respx to
  stub. The Anthropic adapter integration tests also use respx for
  the SDK's underlying httpx client (see SDK docs for the mock
  pattern).

### Phase 4 contract (do not foreclose)

- `SaveDraft` use case will receive `Session` + repos + DraftStore;
  must open `session.begin()` exactly once per save.
- FastAPI routes will translate domain exceptions into HTTP
  responses. Phase 3 exception types must carry human-readable
  messages, not structured codes.
- E2E tests (Phase 7) will run with `DOJO_LLM=fake` env var or
  equivalent — composition root must honor a switch between
  real and fake LLM provider. Phase 3 sets up the branch; Phase 4
  wires it into the web layer.

</code_context>

<specifics>
## Specific Ideas

- **"Adapters are boring."** A real adapter should not be clever.
  Every Phase 3 file reads like a glue layer between a third-party
  library and our Protocol. If a file grows a state machine, a
  caching layer, or a retry loop with custom logic, question it —
  that complexity belongs behind a further abstraction or is
  over-engineering.
- **"The contract harness is the firewall."** Each new adapter
  adds a contract test that both the fake and the real must pass.
  If the real adapter is the only place behavior changes (e.g.
  actual SQL semantics), that's a sign the port's Protocol is
  under-specified — surface as a Phase 2-revisit signal, don't
  silently add conditional logic to the fake.
- **"Sync at the DB, async at the web."** The dojo stack is
  deliberately asymmetric. Phase 3 adapters are sync (DB, filesystem,
  LLM SDK). The URL fetcher is async (`httpx`), but it's a one-shot
  `Callable[[str], str]` — internal async is implementation detail,
  the port shape is sync-returning. The async-from-sync bridge
  (`asyncio.run` or equivalent) lives inside the URL fetcher, not
  at any higher level.
- **"GIL-atomic pop is a load-bearing assumption."** D-04 rests on
  it. The class docstring names it explicitly. Any future "let's
  run on PyPy / no-GIL / Jython" consideration re-opens that
  decision.
- **"Phase 3 is the last phase before the web surface."** Phase 4
  will add FastAPI routes that exercise the Phase 3 adapters. Every
  integration test in Phase 3 should answer the question: "can a
  route built on top of this adapter be atomic, observable, and
  error-handled correctly?" If an adapter is hard to integration-test
  here, it'll be harder to route-test in Phase 4.

</specifics>

<deferred>
## Deferred Ideas

- **`UnitOfWork` Protocol** — rejected for MVP in favor of
  "`Session` is the UoW" (D-01). Revisit if/when a second
  persistence backend lands (e.g. async Postgres, or a
  file-based repo for tests).
- **ORM relationships between Source / Note / Card** — rejected
  (D-02b) in favor of flat repos matching Phase 2 port shape.
  Revisit only if the aggregate-load pattern becomes the dominant
  access shape (unlikely at dojo's scale).
- **Background TTL sweep / expiration event** — rejected (D-04a)
  in favor of lazy on-access TTL check. Revisit only if memory
  pressure from abandoned drafts becomes measurable.
- **`threading.Lock` in `InMemoryDraftStore`** — rejected (D-04).
  Revisit if dojo ever adds a sync FastAPI route touching the
  DraftStore, or moves to no-GIL Python.
- **Anthropic SDK built-in retry** — rejected (D-03). Revisit if
  tenacity proves awkward (unlikely; it's the canonical tool).
- **OpenAI / Ollama / local-LLM providers** — v1 out-of-scope per
  PROJECT.md; port is shaped for it.
- **FOLDER source kind + RAG** — v2 roadmap per spec §10.
- **Full-text search / Anki export / SRS** — v2+ roadmap.
- **SQLAlchemy async repositories** — rejected project-wide in the
  Phase 1 review (sync is sufficient for local-first single-user).

### Reviewed Todos (not folded)

None — pending todos list empty.

</deferred>

---

*Phase: 03-infrastructure-adapters*
*Context gathered: 2026-04-24*
