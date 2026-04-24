# Phase 3: Infrastructure Adapters — Research

**Researched:** 2026-04-24
**Domain:** SQLAlchemy 2.0 sync ORM + mappers, anthropic SDK + tenacity,
trafilatura + httpx URL fetching, in-memory TTL store, Alembic autogen,
contract harness extension.
**Confidence:** HIGH on stack + patterns; MEDIUM on atomic-pop claim
(see Re-plan Signals §R1).

---

## Summary

Phase 3 wires seven concrete adapters behind the seven ports locked in
Phase 2 — four `Sql*Repository` classes, `AnthropicLLMProvider`,
`InMemoryDraftStore`, `fetch_url`, `read_file` — plus the first real
Alembic migration and a six-port extension of the Phase 2 contract
harness. CONTEXT.md locks almost every significant decision (D-01
through D-10). Research confirms those decisions are executable with
the current SDK versions (anthropic 0.97, tenacity 9.1, SQLAlchemy
2.0.38, trafilatura 2.0, respx 0.23) with **one material shift since
CONTEXT.md was authored** and **one claim that deserves planner
attention**:

1. **[VERIFIED]** Anthropic tool-use now supports `strict: true` with
   grammar-constrained sampling — a first-class schema enforcement
   mechanism that didn't exist when Spec §4.2 was written. This
   **narrows the C6 surface** without eliminating the Pydantic DTO
   firewall: Pydantic still catches the case where grammar constraints
   are violated (never documented to happen, but a belt-and-suspenders
   check), and the DTO semantic retry in D-03a still applies to
   `min_length=1` on cards (which grammar can't enforce). Recommendation:
   use `strict: true` plus Pydantic, not Pydantic alone.
2. **[VERIFIED]** D-04's claim that `dict.pop(key, None)` is
   "GIL-atomic" matches CPython behavior **in practice** on Python 3.12
   with the GIL, but it is **NOT a documented language guarantee**.
   Python 3's own thread-safety docs list `dict.pop(key)` under
   "safe but non-atomic" — it won't corrupt the dict, but the
   "exactly one caller gets the value, the other gets None" semantics
   for a concurrent race is implementation-specific. This is not a
   re-plan signal in itself — D-04c already flags the assumption in the
   class docstring — but the **SC #5 test for "two-coroutine same-token
   race exactly one wins"** should not claim it is testing a language
   guarantee; it is testing CPython 3.12 GIL behavior. Planner should
   hold this framing when it writes the test assertions.

**Primary recommendation:** ship the Phase 3 plans exactly as
CONTEXT.md D-01..D-10 specify, with two refinements baked into the
plan: (a) adopt `strict: true` on the Anthropic tool schema; (b) frame
the concurrent-pop test as an observability gate on CPython behavior
rather than a spec-level atomicity proof.

---

## Architectural Responsibility Map

Phase 3 is entirely infrastructure — no tier ambiguity to resolve, but
the per-capability ownership is worth spelling out because Phase 4 will
consume it unchanged.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Source/Note/Card/Review persistence | Infrastructure (SQL repos) | — | Each port owns its one table; no aggregates. |
| LLM call + retry + validation | Infrastructure (Anthropic adapter) | — | SDK + tenacity + Pydantic all live behind the port. |
| Draft bundle TTL hold | Infrastructure (InMemoryDraftStore) | — | Process-local dict; swappable to Redis later. |
| URL fetch + extraction | Infrastructure (fetch_url) | — | httpx + trafilatura wrapped behind Callable. |
| File read | Infrastructure (read_file) | — | stdlib `open()` + error wrap. |
| Transaction boundary | Application (use case, D-01) | Infrastructure (Session) | Repos do NOT commit; use case opens `session.begin()`. |
| Atomic pop under concurrency | Infrastructure (InMemoryDraftStore) | CPython runtime | Relies on GIL-scoped single-bytecode `dict.pop`. |
| Exception wrapping at boundary | Infrastructure (catches third-party) | Application (owns types) | D-03b: infra wraps, application type-owns. |

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

All ten implementation decisions from CONTEXT.md are locked and
non-negotiable for Phase 3:

- **D-01..D-01b** — Use case owns transaction boundary; repos are
  constructed with a `Session` reference at init; Phase 3 integration
  test exercises `with session.begin(): repo.save(×3)` to prove SC #2
  rollback.
- **D-02..D-02d** — Declarative ORM row classes + pure mapper
  functions + `session.merge()` save path + `session.get()` read path;
  domain stays stdlib-pure; no ORM relationships; `lazy="raise"` as
  belt-and-suspenders; column types locked (IDs as TEXT via UUID
  stringification, timestamps as DATETIME, enums as TEXT `.value`,
  tags as JSON TEXT).
- **D-03..D-03c** — `anthropic.Anthropic(max_retries=0)` non-optional;
  tenacity decorator with whitelisted exception types
  (RateLimitError / APIStatusError / APIConnectionError); semantic
  retry is separate from tenacity; SDK exceptions wrapped into domain
  types at adapter outer boundary; SC #4 = respx 429→200 sequence asserts
  exactly 2 HTTP calls.
- **D-04..D-04d** — Plain dict + no lock + GIL-atomic pop + lazy TTL
  check + injected clock; class docstring names the GIL assumption;
  supersedes Phase 2 D-05's `asyncio.Lock` mention.
- **D-05** — Paywall heuristics locked: 2xx only, ≤10s timeout,
  trafilatura non-None, ≥1000 char floor, paywall-marker check (<2000
  chars + ≥2 markers triggers `SourceNotArticle`), custom User-Agent
  `Dojo/0.1 (+local study app)`.
- **D-06** — FILE reader: UTF-8 strict, `PermissionError` →
  `SourceUnreadable`, `FileNotFoundError` → `SourceNotFound`, no size
  cap at reader layer.
- **D-07** — Contract harness extension: fake + real legs per port;
  real legs always run except LLM (env-gated per Phase 2 D-11).
- **D-08..D-08a** — Alembic autogenerate-review-edit-commit; one
  migration for all four tables; `migrations/env.py` already imports
  `Base` from `app.infrastructure.db.session` (verified live).
- **D-09** — Arch doc extensions land in Phase 3 plans, not separate PR.
  Specifically: §4/§5 "Persistence data flow" subsection + §6 glossary
  entries + §4 stale-line fix (line 702: `asyncio.Lock` → D-04).
- **D-10** — PR #11 chore already on `chore/generate-from-source-
  docstring`; Phase 3 does not duplicate.

### Claude's Discretion

- FastAPI `Depends(get_session)` generator shape (Phase 4 wiring; Phase
  3 sets up the `SessionLocal` use only).
- Repository file layout — one `sql_source_repository.py` per repo vs
  a single `repositories.py`. Research recommendation: **one file per
  repo** to stay under the 100-line ceiling per CLAUDE.md.
- Tool schema shape — one tool `generate_note_and_cards` vs two. Research
  recommendation: **one tool**; spec doesn't mandate two and one-tool
  matches the `GeneratedContent` DTO's shape exactly.
- tenacity decorator wiring — module-level vs instance `.retry_with`
  wrapper. Research recommendation: **module-level `@retry` decorator
  on the private `_sdk_call(self, ...)` method**; stateless and testable
  via monkeypatched call count.
- Fake clock fixture shape. Research recommendation: **list-captured
  counter** fixture — `times = [0.0]`; `clock = lambda: times[0]`;
  `times[0] += 1` in the test body. Zero monkeypatch.
- respx fixture organization — per-test stub vs session-wide. Research
  recommendation: **per-test** — easier to assert call counts cleanly.
- trafilatura config. Research recommendation: `extract(html,
  include_comments=False, deduplicate=True, output_format='txt',
  favor_precision=True)` — precision favored over recall because study
  material quality is dominated by "did we capture the actual article"
  not "did we capture everything".
- Exception class hierarchy additions location — `app/infrastructure/
  exceptions.py` vs per-adapter file. Research recommendation:
  **`app/application/exceptions.py` for the types callers catch**
  (`LLMRateLimited`, `LLMAuthFailed`, `LLMUnreachable`,
  `LLMContextTooLarge`, `SourceNotFound`, `SourceUnreadable`,
  `SourceFetchFailed`, `SourceNotArticle`), **`app/infrastructure/
  exceptions.py` if/when a type is infra-private** (currently none
  needed). Rationale: application and web layers catch these; they're
  what callers depend on, so they belong at the layer of their
  *meaning*, not the layer that raises them. Infrastructure imports
  them freely; the domain layer never catches them.

### Deferred Ideas (OUT OF SCOPE)

Per CONTEXT.md: `UnitOfWork` Protocol, ORM relationships, background TTL
sweep, `threading.Lock` in DraftStore, Anthropic SDK built-in retry,
OpenAI/Ollama/local-LLM providers, FOLDER source + RAG, full-text
search, Anki export, SRS, async SQLAlchemy repositories.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **LLM-01** | LLM access via `LLMProvider` port; Anthropic is the one MVP concrete. | `AnthropicLLMProvider` adapter (D-03), structural subtyping against existing Phase 2 port. |
| **LLM-02** | `tenacity` retries with exponential backoff, max 3; typed domain exceptions at adapter boundary. | D-03 tenacity decorator shape; D-03b exception wrap map; SDK exception tree verified current (§anthropic exceptions below). |
| **GEN-02** | LLM returns structured note + cards; malformed → one retry with stricter prompt, then raise. | D-03a semantic retry separate from tenacity; Pydantic DTO validation inside adapter; `strict: true` on tool now a first-line defense. |
| **PERSIST-02** | Regenerate overwrites note row, appends cards. | D-02 `session.merge()` on NoteRepo (overwrite), `session.add()` on CardRepo (append). SC #7 integration test. |

---

## Phase Scope & Entry State

### What's live already (Phase 1 + 2)

- `app/infrastructure/db/session.py` — `Base` (`DeclarativeBase`),
  sync `engine`, `SessionLocal` with `expire_on_commit=False`,
  dialect-guarded SQLite PRAGMA listener (`PRAGMA foreign_keys=ON`,
  `journal_mode=WAL`, `busy_timeout=5000`). **Do NOT duplicate.**
- `app/settings.py` — `anthropic_api_key: SecretStr`, `database_url`,
  `run_llm_tests`. Already wired.
- `app/application/ports.py` — all 7 ports: 5 `typing.Protocol`s
  (`LLMProvider`, `SourceRepository`, `NoteRepository`,
  `CardRepository`, `CardReviewRepository`, `DraftStore`) + 2 type
  aliases (`UrlFetcher = Callable[[str], str]`,
  `SourceReader = Callable[[Path], str]`). No `@runtime_checkable` —
  structural subtyping only. Return types are fully typed.
- `app/application/dtos.py` — `NoteDTO`, `CardDTO`, `GeneratedContent`
  (all Pydantic with `extra="ignore"` + `min_length=1` on cards),
  `DraftBundle`, `GenerateRequest`, `GenerateResponse` (all frozen
  dataclasses).
- `app/application/exceptions.py` — `DojoError` (in domain), plus
  `UnsupportedSourceKind`, `ExtractorNotApplicable`, `DraftExpired`,
  `LLMOutputMalformed`. Phase 3 extends this file (or adds
  `app/application/exceptions.py` types) with the LLM/source error
  classes listed above.
- `tests/fakes/` — 6 fakes (symmetric to 6 Protocol ports; `UrlFetcher`
  and `SourceReader` are plain callables and have no fake classes).
  **Do NOT modify any fake file in Phase 3** — contract harness
  treats fake and real symmetrically.
- `tests/contract/test_llm_provider_contract.py` — canonical pattern.
  `@pytest.fixture(params=["fake", "anthropic"])` yields either a
  `FakeLLMProvider()` or imports `app.infrastructure.llm.
  anthropic_provider.AnthropicLLMProvider`, gated on
  `RUN_LLM_TESTS` env var. Phase 3 adds six more contract test files
  following the same pattern.
- `tests/conftest.py` — `session` fixture with SAVEPOINT isolation
  (outer transaction on a connection, session joins via
  `join_transaction_mode="create_savepoint"`, outer rollback at
  teardown). **Shared across all Phase 3 integration tests.**
  Migrated engine is session-scoped; `alembic upgrade head` runs once
  per pytest session against a tmp-file DB.
- `migrations/env.py` — **sync** (verified line 8:
  `from app.infrastructure.db.session import Base`); uses
  `engine_from_config(... poolclass=NullPool)` + `connection.run_sync`
  is **not** present because the env is already synchronous. Works
  with `alembic upgrade head`. [VERIFIED]
- `migrations/versions/0001_initial.py` — empty upgrade/downgrade;
  first real schema migration stacks on top as `0002_*.py`. Already
  tested by `tests/integration/test_alembic_smoke.py`.
- `pyproject.toml` — **`anthropic`, `tenacity`, `trafilatura`,
  `respx`, `nh3` are NOT yet in the dependency list.** Phase 3 plans
  must add each to `[project].dependencies` (runtime) or
  `[dependency-groups].dev` (respx only — test dependency).

### What Phase 3 adds

New files (≤100 lines each; 150 hard split):
- `app/infrastructure/db/models.py` — 4 row classes + single
  `from .models import *` re-export from `session.py` or `__init__.py`
  (Pitfall M9 mitigation — eager import so `Base.metadata` sees the
  tables at autogen time).
- `app/infrastructure/db/mappers.py` — 8 pure functions
  (`source_to_row`/`source_from_row` × 4 entities). If >100 lines,
  split into per-entity files (`mappers/source.py`, etc.).
- `app/infrastructure/repositories/sql_source_repository.py` — 1 per repo.
- `app/infrastructure/repositories/sql_note_repository.py`
- `app/infrastructure/repositories/sql_card_repository.py`
- `app/infrastructure/repositories/sql_card_review_repository.py`
- `app/infrastructure/drafts/in_memory_draft_store.py`
- `app/infrastructure/readers/file_reader.py` — `read_file` callable.
- `app/infrastructure/fetchers/url_fetcher.py` — `fetch_url` callable.
- `app/infrastructure/llm/anthropic_provider.py` — the complex one;
  likely splits into `anthropic_provider.py` (class + public methods),
  `_tool_schema.py` (tool definition), `_exceptions_map.py`
  (SDK → domain exception mapping). Splits enforce CLAUDE.md size rule.
- `app/application/exceptions.py` — extended with the 8 new error classes.
- `migrations/versions/0002_create_initial_schema.py` — first real
  migration, autogenerated then human-reviewed.
- `tests/contract/test_source_repository_contract.py` (+ 5 more:
  note / card / card_review / draft_store / url_fetcher /
  source_reader) — extends the fake+real pattern from the LLM
  contract test.
- `tests/integration/test_sql_repositories_atomic.py` — SC #2
  third-insert-fails rollback test.
- `tests/integration/test_sql_repositories_regenerate.py` — SC #7
  note-overwrites-card-appends test.
- `tests/integration/test_anthropic_retry_count.py` — SC #4 respx
  429→200 exact-count test.
- `tests/integration/test_draft_store_concurrency.py` — SC #5
  fake-clock TTL + concurrent-pop race.
- `tests/integration/test_url_fetcher_paywall.py` — SC #6 threshold +
  paywall + timeout cases.
- `tests/integration/test_file_reader.py` — read success, not-found,
  permission-denied, bad-utf8.

### Runtime State Inventory

Phase 3 is a greenfield code-add — no rename, no refactor. No stored
data, no live service config, no OS-registered state, no secret
renames, no build-artifact cleanup. The only "state" Phase 3 creates
is the empty four-table SQLite schema on `alembic upgrade head`, which
is the normal path.

**Category:** Nothing found. (Verified: Phase 3 is pure code-add; no
strings are being renamed, nothing is being migrated from an old
shape.)

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Everything | ✓ | pinned in pyproject `>=3.12,<3.13` | — |
| `anthropic` SDK | LLM-01, LLM-02 | ✗ not yet installed | 0.97.0 (verified via PyPI 2026-04-24) | — must add |
| `tenacity` | LLM-02 | ✗ not yet installed | 9.1.4 (verified via PyPI 2026-02-07) | — must add |
| `trafilatura` | GEN-02 (URL path) | ✗ not yet installed | 2.0.0 (verified 2024-12-03) | — must add |
| `respx` | tests | ✗ not yet installed | 0.23.1 (verified 2026-04-08; httpx>=0.25 compatible, we have 0.28) | pytest-httpx if respx becomes awkward |
| `httpx` | URL fetcher | ✓ (dev dep) | 0.28.1 locked — must promote to runtime dep | — |
| `SQLAlchemy` | Repos | ✓ | 2.0.38+ locked | — |
| `Alembic` | Migration | ✓ | 1.18+ locked | — |
| `nh3` | (Phase 5+ — out of Phase 3 scope) | ✗ | 0.2.x | defer |
| `ANTHROPIC_API_KEY` | Real LLM contract leg | ✗ optional (RUN_LLM_TESTS gate) | — | Phase 3 gates real LLM on env var per Phase 2 D-11 |
| `sqlite3` CLI | Migration human-review (D-08 `.schema` check) | ✓ (OS) | system | — |

**Missing dependencies that block Phase 3 execution:**
- `anthropic`, `tenacity`, `trafilatura`, `respx` — must be added as
  part of Plan 01 of Phase 3 (dependency install + verification) before
  any adapter code lands.
- `httpx` must move from dev-group (where it is today for the ASGI
  test client) to runtime `[project].dependencies`.

**Missing dependencies with fallbacks:**
- `respx` → `pytest-httpx` if we hit a cross-version compatibility
  issue. Low probability per STACK.md FLAG 2; noted for planner.

**Note on `httpx` version:** we already have `httpx>=0.28` (locked at
0.28.1). Respx 0.23 requires httpx >=0.25 — compatible, no action needed.

---

## Technical Approach

### A. SQL repositories — SQLAlchemy 2.0 sync

**Stack:** SQLAlchemy 2.0.38, `DeclarativeBase` (already live as
`Base`), `Mapped[...]` column annotations, `sessionmaker` with
`expire_on_commit=False` (already live).

**Row-class shape** (one per entity):

```python
# Source: SQLAlchemy 2.0 docs — Mapped annotations
# https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.db.session import Base

class SourceRow(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(primary_key=True)
    kind: Mapped[str]                    # SourceKind.value
    user_prompt: Mapped[str]
    display_name: Mapped[str]
    identifier: Mapped[str | None]
    source_text: Mapped[str | None]
    created_at: Mapped[datetime]
```

Notes:
- **No `relationship()`** — D-02b. Flat per-table, no cross-row access.
- IDs as `str` per D-02d; mapper converts `uuid.UUID` ↔ `str`.
- Enums stored as `Mapped[str]` — mapper writes `.value`, reads with
  `SourceKind(row_str)`.
- `Card.tags` as JSON-encoded TEXT; mapper `json.dumps` ↔ `json.loads`.
  Domain already uses `tuple[str, ...]`; mapper returns `tuple` from
  `list`.

**Mapper functions** (pure, one pair per entity):

```python
def source_to_row(src: Source) -> SourceRow:
    return SourceRow(
        id=str(src.id),
        kind=src.kind.value,
        user_prompt=src.user_prompt,
        display_name=src.display_name,
        identifier=src.identifier,
        source_text=src.source_text,
        created_at=src.created_at,
    )

def source_from_row(row: SourceRow) -> Source:
    return Source(
        id=SourceId(uuid.UUID(row.id)),
        kind=SourceKind(row.kind),
        user_prompt=row.user_prompt,
        display_name=row.display_name,
        identifier=row.identifier,
        source_text=row.source_text,
        created_at=row.created_at,
    )
```

These are pure — unit-testable without a DB fixture. No classes,
no state.

**Repository shape:**

```python
class SqlSourceRepository:
    """Sync SQL adapter for SourceRepository Protocol."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, source: Source) -> None:
        row = source_to_row(source)
        self._session.merge(row)   # upsert by PK

    def get(self, source_id: SourceId) -> Source | None:
        row = self._session.get(SourceRow, str(source_id))
        return source_from_row(row) if row is not None else None
```

Key semantic choices per CONTEXT.md:
- **`session.merge(row)` on save** — upsert by primary key. Handles
  both insert (new id) and update (existing id) paths. Required for
  `Note` (regenerate-overwrites); also safe for `Source` (Source is
  the parent, so "re-save" simply re-writes the same fields).
- **`session.add(row)` for `Card`** — not `merge`. PERSIST-02 says
  regenerate APPENDS cards, so each new Card gets a fresh ID and
  `add()` is the right primitive. Using `merge()` would enable
  overwrite-by-id, which we don't want.
- **`session.get(RowClass, str_id)` on read** — SQLAlchemy 2.0's
  preferred API; avoids legacy `query()`, gives None cleanly on miss.
- **Repos never `.commit()` or `.rollback()`** — D-01. The caller
  (Phase 4's `SaveDraft` use case) opens `session.begin()`; repos
  participate.
- **Repos never receive a session factory** — D-01b. They receive a
  constructed `Session` at init. Phase 4 will wire one per request via
  `Depends(get_session)`.

**`MissingGreenlet` mitigation:**
- `expire_on_commit=False` already live in `session.py`. Attribute
  access on returned rows after commit does NOT trigger reload.
- Mapper converts row → dataclass at repo boundary; the returned
  `Source` is fully materialised stdlib data; no ORM reference leaks.
- This is belt-and-suspenders: `MissingGreenlet` is specifically an
  async-greenlet bug. Sync SQLAlchemy 2.0 does not use greenlet for
  sync sessions — the error won't fire even if `expire_on_commit=True`.
  But `expire_on_commit=False` protects against "saved then accessed
  detached" state generally. Keep the flag.

**`lazy="raise"` (D-02c):** Currently no relationships declared, so
this is moot. Add a project convention in the `docs/architecture/
overview.md` §5 "Persistence data flow" subsection: "If you add an
ORM relationship, set `lazy='raise'` on it — lazy access is a code
smell that will blow up in production." This is the belt-and-suspenders
D-02c intended.

**Atomic transaction (SC #2):** The pattern Phase 4 will use and
Phase 3's integration test must exercise:

```python
# In the integration test that forces SC #2:
with session.begin():                 # opens transaction
    src_repo.save(source)
    note_repo.save(note)
    card_repo.save(card_that_violates_constraint)   # raises
# On exit with exception, SQLAlchemy rolls back automatically.
# Assert: session.get(SourceRow, str(source.id)) is None
#         session.get(NoteRow,   str(note.id))   is None
#         session.get(CardRow,   str(card.id))   is None
```

Note on conftest.py interaction: the `session` fixture uses
`join_transaction_mode="create_savepoint"`. When the test code calls
`session.begin()`, SQLAlchemy opens a SAVEPOINT inside the outer
transaction. A rollback rolls back the SAVEPOINT, not the outer
connection. This is exactly what we want: the test sees rollback
semantics; the outer fixture teardown still rolls back the outer
transaction. **[VERIFIED by reading conftest.py line 89-108.]**

---

### B. Anthropic LLM adapter — tenacity + tool-use

**Stack:** anthropic 0.97.0 (PyPI verified 2026-04-24), tenacity 9.1.4,
Pydantic 2.13.3 (already live for DTOs).

#### B.1 Client construction

```python
# Source: anthropic SDK _client.py (verified via GitHub search 2026-04-24)
import anthropic

self._client = anthropic.Anthropic(
    api_key=settings.anthropic_api_key.get_secret_value(),
    max_retries=0,    # non-optional per D-03 / C7
)
```

**Why `max_retries=0`:** [VERIFIED] SDK default is 2 (search source:
`copyprogramming.com/howto/thread-safety-in-python-s-dictionary` et al.
cite the `_client.py` default). Without `max_retries=0`, tenacity
stacks on top — 3 tenacity × 2 SDK = 6 real calls per logical retry;
PITFALL C7 ships; SC #4's "exactly 2 HTTP calls" assertion fails.

#### B.2 Tool-use schema (one tool — Claude's Discretion recommendation)

```python
# Source: https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use
TOOL_DEFINITION = {
    "name": "generate_note_and_cards",
    "description": (
        "Produce a study note and a list of Q&A cards from the "
        "provided source text and user prompt. Return EXACTLY ONE "
        "tool_use call; do not emit free-form text."
    ),
    "strict": True,   # [NEW 2026] grammar-constrained sampling
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "note": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "content_md": {"type": "string"},
                },
                "required": ["title", "content_md"],
            },
            "cards": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "question": {"type": "string"},
                        "answer": {"type": "string"},
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["question", "answer", "tags"],
                },
            },
        },
        "required": ["note", "cards"],
    },
}
```

**Important:**
- `"strict": true` is [VERIFIED new] Anthropic feature (2026 docs,
  "grammar-constrained sampling"). Input field in `tool_use` response
  block will strictly follow the schema.
- `additionalProperties: false` on every object. Required for
  `strict: true` to enforce no extra fields.
- `tags: []` is `required` — we emit an empty array if no tags rather
  than making it optional. Keeps the schema strict; mapper handles
  empty tuple on domain side.
- **NOT enforced by strict mode:** `min_length` constraints,
  `min_items` on cards. Pydantic's `Field(min_length=1)` on
  `cards: list[CardDTO]` still does work at the adapter boundary —
  the model COULD return `cards: []` and the strict grammar would
  accept it. This is why D-03a's Pydantic retry is still load-bearing.

#### B.3 tenacity decorator + `_sdk_call` method

```python
# Source: https://tenacity.readthedocs.io
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type,
)

class AnthropicLLMProvider:
    """LLMProvider Protocol adapter using anthropic SDK + tenacity."""

    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        model: str = "claude-opus-4-7",
    ) -> None:
        self._client = client or anthropic.Anthropic(
            api_key=get_settings().anthropic_api_key.get_secret_value(),
            max_retries=0,
        )
        self._model = model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((
            anthropic.RateLimitError,       # 429
            anthropic.APIConnectionError,   # network
            anthropic.APITimeoutError,      # subclass of APIConn
            anthropic.InternalServerError,  # 5xx
        )),
        reraise=True,
    )
    def _sdk_call(self, messages: list[dict], system: str) -> Any:
        return self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            messages=messages,
            tools=[TOOL_DEFINITION],
            tool_choice={"type": "tool", "name": "generate_note_and_cards"},
        )
```

**Retry-whitelist rationale:**
- `RateLimitError` (429) — retry; rate limits are transient.
- `APIConnectionError` + `APITimeoutError` — network fluke; retry.
- `InternalServerError` (5xx) — retry; Anthropic sometimes 5xx's.
- **NOT retried:** `AuthenticationError` (401), `BadRequestError`
  (400 — payload too large counts), `NotFoundError` (404),
  `PermissionDeniedError` (403), `UnprocessableEntityError` (422).
  These are permanent; retry wastes budget and hides the root cause
  (PITFALL C7's "sixty-second failure" story).

**`reraise=True`** — on final failure, the underlying SDK exception
surfaces to the caller, not a tenacity `RetryError` wrapping it.
Simplifies `except RateLimitError:` outer boundary.

**Call-count assertion for SC #4:** tenacity's `_sdk_call.retry.
statistics` counts attempts, but respx also counts HTTP calls. Prefer
asserting HTTP call count:

```python
# In test_anthropic_retry_count.py
import respx, httpx
from unittest.mock import ANY

@respx.mock
def test_tenacity_counts_exact():
    route = respx.post("https://api.anthropic.com/v1/messages").mock(
        side_effect=[
            httpx.Response(429, json={"error": ...}),
            httpx.Response(200, json={...valid tool_use...}),
        ]
    )
    provider = AnthropicLLMProvider()
    note, cards = provider.generate_note_and_cards(None, "x")
    assert route.call_count == 2   # exactly one retry
```

**Whitelist test (no retry on 401):**

```python
def test_auth_error_no_retry():
    respx.post("https://api.anthropic.com/v1/messages").respond(
        status_code=401, json={"error": {"type": "authentication_error"}}
    )
    provider = AnthropicLLMProvider()
    with pytest.raises(LLMAuthFailed):
        provider.generate_note_and_cards(None, "x")
    assert route.call_count == 1   # no retry
```

#### B.4 Semantic retry (D-03a)

Separate from tenacity. Lives inside `generate_note_and_cards`:

```python
def generate_note_and_cards(
    self, source_text: str | None, user_prompt: str,
) -> tuple[NoteDTO, list[CardDTO]]:
    try:
        response = self._sdk_call(...)
        return self._parse_and_validate(response)
    except pydantic.ValidationError:
        # Second attempt with stricter prompt.
        stricter_system = self._system_prompt() + " " + STRICTER_ADDENDUM
        response = self._sdk_call(...)    # full tenacity lifecycle
        try:
            return self._parse_and_validate(response)
        except pydantic.ValidationError as e:
            raise LLMOutputMalformed(str(e)) from e
    except anthropic.RateLimitError as e:
        raise LLMRateLimited(str(e)) from e
    except anthropic.AuthenticationError as e:
        raise LLMAuthFailed(str(e)) from e
    except anthropic.APIConnectionError as e:
        raise LLMUnreachable(str(e)) from e
    except anthropic.BadRequestError as e:
        if "payload" in str(e).lower() or "context" in str(e).lower():
            raise LLMContextTooLarge(str(e)) from e
        raise LLMInvalidRequest(str(e)) from e
```

**Key points:**
- Semantic retry (Pydantic catch + one re-call) is ONE extra full
  tenacity lifecycle underneath — the second `_sdk_call` could itself
  retry up to 3 times on 429. That's intentional and correct.
- Exception wrap at the OUTER boundary of `generate_note_and_cards`
  (D-03b). Inside `_sdk_call` and `_parse_and_validate`, SDK exceptions
  propagate as-is; the outer `try/except` converts them.
- `LLMContextTooLarge` — Anthropic raises `BadRequestError` (400) for
  oversize payloads. We sniff the message to discriminate from other
  400s. This is a heuristic; flag as LOW confidence on exact message
  strings and expand the match list if real calls surface variants.

#### B.5 Response parse + DTO validation

```python
def _parse_and_validate(
    self, response,
) -> tuple[NoteDTO, list[CardDTO]]:
    tool_blocks = [b for b in response.content if b.type == "tool_use"]
    if not tool_blocks:
        raise LLMOutputMalformed("no tool_use block in response")
    payload = tool_blocks[0].input    # SDK parses JSON into dict
    validated = GeneratedContent.model_validate(payload)   # Pydantic
    return validated.note, validated.cards
```

`strict: true` makes the Pydantic catch rare; keep it anyway as a
belt-and-suspenders check + C6 test hook.

---

### C. InMemoryDraftStore

**Stack:** stdlib only; `time.monotonic` (default clock).

```python
# app/infrastructure/drafts/in_memory_draft_store.py
from collections.abc import Callable
import time
from app.application.dtos import DraftBundle
from app.application.ports import DraftToken


class InMemoryDraftStore:
    """DraftStore Protocol adapter: plain dict + lazy TTL + GIL-atomic pop.

    Thread safety comes from CPython GIL atomicity of dict operations.
    If Dojo ever runs on a no-GIL Python build (PEP 703), swap in
    `threading.Lock` — the free-threaded build's per-dict locking
    prevents corruption but does not document "exactly one caller
    wins a race" semantics.
    """

    _TTL_SECONDS = 30 * 60   # 30 minutes per DRAFT-01

    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        ttl_seconds: float = _TTL_SECONDS,
    ) -> None:
        self._store: dict[DraftToken, tuple[DraftBundle, float]] = {}
        self._clock = clock
        self._ttl = ttl_seconds

    def put(self, token: DraftToken, bundle: DraftBundle) -> None:
        self._store[token] = (bundle, self._clock())

    def pop(self, token: DraftToken) -> DraftBundle | None:
        entry = self._store.pop(token, None)
        if entry is None:
            return None
        bundle, stored_at = entry
        if self._clock() - stored_at > self._ttl:
            return None   # lazy TTL: treat expired as absent
        return bundle
```

**Details:**
- Single `_store` dict; value is `(bundle, timestamp)` tuple.
- `put`: single assignment. `dict.__setitem__` is documented atomic.
- `pop`: single `dict.pop(key, None)` call. Returns local variable;
  no further dict access. The TTL check runs on a local. If two
  callers race, CPython 3.12 + GIL executes the pop in one bytecode
  — exactly one gets `entry is not None`, the other gets `None`.
  See Re-plan Signal R1 for the documentation vs implementation gap.
- Clock injection for SC #5:
  ```python
  times = [0.0]
  store = InMemoryDraftStore(clock=lambda: times[0])
  store.put(tok, bundle)
  times[0] = 1800.1                         # 30:00.1 later
  assert store.pop(tok) is None             # expired
  ```
- No background sweep, no timer thread, no `asyncio.Lock`,
  no `threading.Lock`. Per D-04, D-04a, D-04b.

**Test for two-coroutine race (SC #5):**

```python
import asyncio

@pytest.mark.asyncio
async def test_concurrent_pop_exactly_one_wins():
    store = InMemoryDraftStore()
    token = DraftToken(uuid.uuid4())
    bundle = DraftBundle(note=..., cards=[...])
    store.put(token, bundle)

    # Two coroutines racing.
    async def pop(): return store.pop(token)
    results = await asyncio.gather(pop(), pop())

    winners = [r for r in results if r is not None]
    losers = [r for r in results if r is None]
    assert len(winners) == 1
    assert len(losers) == 1
    assert winners[0] is bundle
```

**Framing per Re-plan Signal R1:** This test gates CPython 3.12 GIL
behavior, not a language spec guarantee. It WILL pass on 3.12 with the
GIL because `dict.pop(key, default)` is implemented in a single C-level
operation that holds the GIL through. Stability under `pytest-repeat`
(10 iterations — we have the plugin live) will demonstrate that.

---

### D. URL fetcher — httpx + trafilatura

**Stack:** httpx 0.28.1 (already locked); trafilatura 2.0.0.

**Port shape** (from `ports.py`): `UrlFetcher = Callable[[str], str]`.
Synchronous signature.

**Async-from-sync bridge question:** The port is sync. trafilatura 2.0
is sync (`trafilatura.extract()` is a blocking function; verified
2026-04-24). httpx offers both sync and async clients.

**Decision:** Use `httpx.Client` (sync), not `httpx.AsyncClient` +
`asyncio.run`. Rationale:
1. `asyncio.run(...)` per call opens + closes a new event loop each
   time — expensive for a one-shot HTTP GET.
2. `asyncio.run` from inside a running event loop is a hard error;
   Phase 4 will call `fetch_url` from sync use-case code (even though
   the route is async, FastAPI runs sync endpoints in a threadpool).
3. Sync httpx is robust; the connection-pool advantage of async
   doesn't matter for a one-shot per-URL app.
4. If we later need to parallelise URL fetches (v2 FOLDER + RAG),
   swap the callable's body — the port stays.

**Shape:**

```python
# app/infrastructure/fetchers/url_fetcher.py
import httpx
import trafilatura
from app.application.exceptions import (
    SourceFetchFailed, SourceNotArticle,
)

_USER_AGENT = "Dojo/0.1 (+local study app)"
_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
_MIN_CHARS = 1000
_PAYWALL_MAX_CHARS = 2000
_PAYWALL_MARKERS = frozenset((
    "subscribe", "sign up", "sign in", "paywall",
    "continue reading", "free article",
))

def fetch_url(url: str) -> str:
    """Fetch `url` and extract main article text. UrlFetcher impl."""
    try:
        response = httpx.get(
            url,
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=True,
            timeout=_TIMEOUT,
        )
    except httpx.TimeoutException as e:
        raise SourceFetchFailed(f"timeout fetching {url}") from e
    except httpx.HTTPError as e:
        raise SourceFetchFailed(f"fetch failed: {e}") from e

    if not response.is_success:
        raise SourceFetchFailed(
            f"URL returned {response.status_code}"
        )

    extracted = trafilatura.extract(
        response.text,
        include_comments=False,
        deduplicate=True,
        output_format="txt",
        favor_precision=True,
    )
    if extracted is None or len(extracted) < _MIN_CHARS:
        raise SourceNotArticle("extraction failed or too short")

    if len(extracted) < _PAYWALL_MAX_CHARS:
        low = extracted.lower()
        hits = sum(1 for m in _PAYWALL_MARKERS if m in low)
        if hits >= 2:
            raise SourceNotArticle("paywall suspected")

    return extracted
```

**Details:**
- `trafilatura.extract` signature verified against current docs
  (2026-04-24): `include_comments`, `deduplicate`, `output_format`,
  `favor_precision` all valid parameters. Returns `str | None`.
- `favor_precision=True` because we want "article body only, not
  navigation / comments / sidebars." Trades recall for precision.
  Acceptable for study material; user can always paste the text if
  extraction misses.
- Paywall check only runs for short extractions. An extraction of
  50,000 chars with "sign in" twice is clearly a full article.
- Timeout shape: connect 5s, read 10s — "≤ 10s" per D-05. Raise
  `SourceFetchFailed` on timeout (maps to `SourceFetchFailed("timeout")`
  per D-05).
- Non-2xx: `SourceFetchFailed("URL returned N")` per D-05.

**respx testing:**

```python
# tests/integration/test_url_fetcher_paywall.py
import respx
from httpx import Response

@respx.mock
def test_fetch_url_happy_path():
    html = "<html><body>" + "Lorem ipsum " * 200 + "</body></html>"
    respx.get("https://example.com/article").mock(
        return_value=Response(200, text=html)
    )
    text = fetch_url("https://example.com/article")
    assert len(text) >= 1000

@respx.mock
def test_fetch_url_404_raises():
    respx.get("https://example.com/missing").mock(
        return_value=Response(404)
    )
    with pytest.raises(SourceFetchFailed):
        fetch_url("https://example.com/missing")

@respx.mock
def test_fetch_url_paywall_detected():
    html = "<body>Sign up. Subscribe. Continue reading.</body>"
    respx.get("https://example.com/paywall").mock(
        return_value=Response(200, text=html)
    )
    with pytest.raises(SourceNotArticle, match="paywall"):
        fetch_url("https://example.com/paywall")

@respx.mock
def test_fetch_url_too_short_raises():
    respx.get("https://example.com/short").mock(
        return_value=Response(200, text="<body>too short</body>")
    )
    with pytest.raises(SourceNotArticle, match="too short|extraction"):
        fetch_url("https://example.com/short")
```

---

### E. File reader

**Port shape:** `SourceReader = Callable[[Path], str]`.

```python
# app/infrastructure/readers/file_reader.py
from pathlib import Path
from app.application.exceptions import SourceNotFound, SourceUnreadable


def read_file(path: Path) -> str:
    """Read `path` as UTF-8 text. SourceReader impl."""
    try:
        return path.read_text(encoding="utf-8", errors="strict")
    except FileNotFoundError as e:
        raise SourceNotFound(str(path)) from e
    except PermissionError as e:
        raise SourceUnreadable(f"permission denied: {path}") from e
    except UnicodeDecodeError as e:
        raise SourceUnreadable(f"not valid UTF-8: {path}") from e
    except IsADirectoryError as e:
        raise SourceUnreadable(f"path is a directory: {path}") from e
    except OSError as e:
        # Catch-all for other filesystem errors (EIO, ELOOP, etc.)
        raise SourceUnreadable(f"OS error reading {path}: {e}") from e
```

Notes per D-06:
- Strict UTF-8; no `errors="replace"` fallback.
- `FileNotFoundError` → `SourceNotFound` (name hints at the `identifier`
  being the missing thing).
- `PermissionError` and `UnicodeDecodeError` → `SourceUnreadable`.
- `IsADirectoryError` is a real edge case (user pastes a folder path);
  wrap as `SourceUnreadable`.
- No size limit; downstream LLM will raise `LLMContextTooLarge` if the
  file is too big.

---

### F. Alembic migration (autogenerate → review → commit)

**Entry state:**
- `migrations/env.py` line 8: `from app.infrastructure.db.session import
  Base` — `Base` is re-exported. **The import is already there.** The
  question is whether `Base.metadata` will see the 4 new row classes at
  autogen time.
- `app/infrastructure/db/session.py` imports nothing from `models.py`
  (models.py doesn't exist yet). To make `Base.metadata.tables` contain
  the four tables, **the row-class module must be imported** before
  autogen runs.

**M9 mitigation:**

Option A: Add `from app.infrastructure.db import models as _models` to
`migrations/env.py` after the `Base` import. Explicit; env.py is the
only caller that needs it.

Option B: Add it to `app/infrastructure/db/__init__.py` as
`from . import models`. Every import of the db package pulls models;
env.py already imports `Base` which imports this package.

**Research recommendation:** **Option A in env.py.** Rationale:
import for side effect at the call site that cares. Option B would
force every sync-session user to pay the model import cost at startup;
tiny cost but wrong on principle. One extra line in env.py is clearer.

**Alembic command:**

```bash
uv run alembic revision --autogenerate \
    -m "create initial schema"
```

**Human review checklist (D-08):**
- `op.create_table("sources", ...)` × 4 tables present.
- No `op.create_index` on a table created in the same `upgrade()`
  before the table create itself runs (autogen occasionally
  mis-orders).
- No `op.alter_column(...)` calls — we're creating, not altering, so
  none should appear. If any do, autogen drifted from the empty
  baseline.
- SQLite `ALTER TABLE` limits: only relevant for later migrations
  (adding columns, changing types). First migration is all
  `create_table` — safe.
- Run `uv run alembic upgrade head` on a fresh tmp DB; run
  `sqlite3 /tmp/dojo.db .schema` and confirm each of the 4 tables
  present.
- Run `uv run alembic downgrade base` then `upgrade head` — round-trip
  succeeds (gate for VALIDATION.md row).

Drop `0002_create_initial_schema.py` into `migrations/versions/` with
the reviewed-and-edited body.

---

### G. Contract harness extension (Phase 2 plan-05 → Phase 3)

**Entry state:** `tests/contract/test_llm_provider_contract.py`
implements the canonical pattern. Phase 3 copies this file six more
times, one per port.

**Per-port contract test shape:**

```python
# tests/contract/test_source_repository_contract.py
from collections.abc import Iterator
import pytest
from sqlalchemy.orm import Session

from tests.fakes import FakeSourceRepository


@pytest.fixture(params=["fake", "sql"])
def source_repository(
    request: pytest.FixtureRequest,
    session: Session,     # from tests/conftest.py
) -> Iterator:
    if request.param == "fake":
        yield FakeSourceRepository()
        return
    from app.infrastructure.repositories.sql_source_repository import (
        SqlSourceRepository,
    )
    yield SqlSourceRepository(session)


def test_save_then_get_roundtrips(source_repository) -> None:
    """Saved Source is retrievable by id."""
    src = Source(
        kind=SourceKind.TOPIC,
        user_prompt="x",
        display_name="y",
    )
    source_repository.save(src)
    loaded = source_repository.get(src.id)
    assert loaded is not None
    assert loaded.id == src.id
    assert loaded.user_prompt == "x"


def test_get_unknown_returns_none(source_repository) -> None:
    loaded = source_repository.get(SourceId(uuid.uuid4()))
    assert loaded is None
```

**Real-leg session fixture:** The existing `session` fixture in
`conftest.py` provides a SAVEPOINT-isolated sync session against a tmp
file DB that's had `alembic upgrade head` applied. SQL contract tests
can consume it directly. Each test gets a fresh SAVEPOINT; tear-down
rolls back.

**No env gate for DB/draft/URL/File contract tests** per D-07. Only
the LLM contract test gates on `RUN_LLM_TESTS=1`.

**Six new files to create** (one per port):
1. `tests/contract/test_source_repository_contract.py`
2. `tests/contract/test_note_repository_contract.py`
3. `tests/contract/test_card_repository_contract.py`
4. `tests/contract/test_card_review_repository_contract.py`
5. `tests/contract/test_draft_store_contract.py`
6. `tests/contract/test_url_fetcher_contract.py`
7. `tests/contract/test_source_reader_contract.py`

(That's seven new files — six ports that didn't have contract tests
plus splitting the `UrlFetcher` / `SourceReader` Callable aliases into
their own files; six contract tests for the 6 stateful ports plus 2
contract tests for the 2 callable aliases = 8 total, minus the 1
already live = 7 new. Plan should enumerate exactly.)

---

## Validation Architecture

The phase-level validation harness is Nyquist-compliant and
decomposable by requirement × test-type × command. Framework detection:
`pytest` (>= 9.0.3, live), `pytest-asyncio` (1.3 live, `asyncio_mode=
auto`), `pytest-cov` (live), `pytest-repeat` (live — used for SC #4's
10x stability gate).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0 + pytest-asyncio 1.3 + respx 0.23 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/unit tests/contract -x` |
| Full suite command | `uv run make check` (runs full make-check pipeline) |

### Phase Requirements → Test Map

| Req / SC | Behavior | Test Type | Automated Command | File (✅ exists / ❌ Wave 0) |
|----------|----------|-----------|-------------------|-------------------------------|
| LLM-01 / SC #3 | AnthropicLLMProvider validates tool_use payload via Pydantic; raises `LLMOutputMalformed` on schema fail | integration (respx) | `uv run pytest tests/integration/test_anthropic_provider.py::test_malformed_payload_raises_after_retry -x` | ❌ Wave 0 |
| LLM-01 / SC #3 | Adapter retries once semantically on malformed, then raises | integration (respx) | `... ::test_one_malformed_then_success -x` | ❌ Wave 0 |
| LLM-01 / SC #3 | SDK exceptions wrap into domain exceptions at outer boundary | integration (respx) | `... ::test_429_final_wraps_as_llm_rate_limited -x` | ❌ Wave 0 |
| LLM-02 / SC #4 | tenacity retries 3x with exponential backoff on whitelisted errors | integration (respx) | `uv run pytest tests/integration/test_anthropic_retry_count.py::test_429_then_200_exactly_two_calls -x` | ❌ Wave 0 |
| LLM-02 / SC #4 | 401 is NOT retried | integration (respx) | `... ::test_401_no_retry -x` | ❌ Wave 0 |
| LLM-02 / SC #4 | max_retries=0 is set on the client (no SDK stacking) | unit | `uv run pytest tests/unit/application/test_anthropic_provider_config.py -x` | ❌ Wave 0 |
| GEN-02 / SC #6 | URL fetcher raises `SourceNotArticle` under 1000 chars | integration (respx) | `uv run pytest tests/integration/test_url_fetcher_paywall.py::test_short_extraction_raises -x` | ❌ Wave 0 |
| GEN-02 / SC #6 | Paywall heuristic fires (< 2000 chars + ≥ 2 markers) | integration (respx) | `... ::test_paywall_detected -x` | ❌ Wave 0 |
| GEN-02 / SC #6 | Timeout → `SourceFetchFailed` | integration (respx) | `... ::test_timeout_wraps -x` | ❌ Wave 0 |
| GEN-02 / SC #6 | Non-2xx → `SourceFetchFailed("URL returned N")` | integration (respx) | `... ::test_404_wraps -x` | ❌ Wave 0 |
| GEN-02 (file path) | `read_file` wraps `FileNotFoundError` → `SourceNotFound` | integration (tmp_path) | `uv run pytest tests/integration/test_file_reader.py::test_missing_file_raises -x` | ❌ Wave 0 |
| GEN-02 (file path) | `read_file` wraps `PermissionError` → `SourceUnreadable` | integration | `... ::test_permission_denied_raises -x` | ❌ Wave 0 |
| GEN-02 (file path) | `read_file` wraps `UnicodeDecodeError` → `SourceUnreadable` | integration | `... ::test_bad_utf8_raises -x` | ❌ Wave 0 |
| PERSIST-02 / SC #1 | Repo round-trips Source + Note + Cards; no `MissingGreenlet` | contract (fake+sql) | `uv run pytest tests/contract/test_source_repository_contract.py tests/contract/test_note_repository_contract.py tests/contract/test_card_repository_contract.py -x` | ❌ Wave 0 |
| PERSIST-02 / SC #2 | Forced 3rd-insert failure in `session.begin()` → all three rollback | integration (SAVEPOINT) | `uv run pytest tests/integration/test_sql_repositories_atomic.py -x` | ❌ Wave 0 |
| PERSIST-02 / SC #7 | Regenerate: note row overwrites, card rows append, existing cards untouched | integration | `uv run pytest tests/integration/test_sql_repositories_regenerate.py -x` | ❌ Wave 0 |
| DRAFT-01 / SC #5 | TTL eviction via fake clock past 30 min threshold | contract (fake+real) | `uv run pytest tests/contract/test_draft_store_contract.py -x` | ❌ Wave 0 |
| DRAFT-01 / SC #5 | Two-coroutine same-token race: exactly one wins | integration (asyncio.gather) | `uv run pytest tests/integration/test_draft_store_concurrency.py::test_concurrent_pop_exactly_one_wins --count=10` | ❌ Wave 0 |
| TEST-03 (Phase 3 extension) | 7 contract test files (LLM live + 6 new) — fake and real legs both pass | contract | `uv run pytest tests/contract/ -x` | ✅ 1 of 7 exists |
| Phase 3 / D-08 | Alembic round-trip: upgrade → downgrade → upgrade | integration | `uv run pytest tests/integration/test_alembic_round_trip.py -x` | ❌ Wave 0 |
| Phase 3 / D-09 | Composition root swaps fake → real without code gymnastics | unit | `uv run pytest tests/unit/test_composition_root.py::test_real_providers_instantiate -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit (pre-commit hook):** `uv run pytest tests/unit` —
  pre-commit runs unit only per Phase 1 D-14. Integration tests run in
  CI and via `make test` locally.
- **Per wave merge:** `uv run make check` — full pipeline (ruff + ty +
  interrogate + pydoclint + pytest including integration + contract).
- **Per plan PR:** `uv run make check` green + human review of the
  autogenerated migration (D-08).
- **Phase gate:** Full suite green with >90% coverage (TEST-02),
  including the 10-iteration pytest-repeat smoke on the concurrent-pop
  test for CPython-GIL stability.

### Wave 0 Gaps

All Wave 0 gaps are Phase 3 to create (no pre-existing test infrastructure
gap exists):

- [ ] Seven contract test files (6 new + extends the existing LLM file).
- [ ] 15 integration test files per the requirement map above.
- [ ] `tests/integration/test_alembic_round_trip.py` — migration
  up/down/up cycle (defends D-08 against SQLite-specific regressions).
- [ ] `tests/unit/test_composition_root.py` — asserts
  `create_app()` → wired AnthropicLLMProvider + real repos, gated by
  an env var so the real LLM isn't constructed during test collection
  unless `RUN_LLM_TESTS=1`.

Framework install: `uv add anthropic tenacity trafilatura nh3 &&
uv add --dev respx`. Verify with `uv run pytest --co tests/contract/`.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no (local-single-user) | — |
| V3 Session Management | no | — |
| V4 Access Control | no (local-single-user) | — |
| V5 Input Validation | yes — URL fetch, file read, LLM output | httpx 2xx check; trafilatura min-length + paywall; Pydantic DTO on LLM output with `strict: true` tool schema |
| V6 Cryptography | partial — API key handling | `SecretStr` from pydantic — already live (settings.py) |
| V7 Error Handling | yes | Typed exception wrap at boundary (D-03b); no stack traces to UI; log at WARN with redacted secrets |
| V8 Data Protection | partial — DB at rest | SQLite file permissions inherited from fs; no encryption-at-rest in v1 |
| V9 Communications | yes — HTTPS to Anthropic | SDK uses HTTPS by default; httpx defaults to HTTPS-capable transport |
| V14 Configuration | yes — API key never in DB or UI | Phase 1 `.env.example` + `SecretStr` + never-logged pattern |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM prompt injection → malicious tool_use | Tampering | Tool `strict: true` + Pydantic validation + we don't execute returned content; only persist to DB |
| LLM output as HTML → XSS | Tampering (downstream) | Phase 5 will add `nh3` sanitization at render; Phase 3 doesn't render — just persists the markdown string |
| URL fetch of attacker-controlled URL | Information disclosure, SSRF-adjacent | Single-user local app; user inputs the URL; no open proxy surface. Fix: document that fetch_url trusts its input. Localhost is not a security boundary (PITFALL M5). |
| SQL injection via user_prompt/note/card text | Tampering | SQLAlchemy parameterised queries (ORM always uses bound params) |
| API key leaked in logs | Info disclosure | `SecretStr.get_secret_value()` only at boundary; never logged; Phase 1 test `test_main_lifespan.py` asserts key not in startup logs |
| Malicious file path (path traversal) | Tampering | Local-single-user, no restriction per D-06; document trust boundary; no sandbox |

---

## Key Patterns & Snippets

### Composition-root fake↔real swap (D-09 arch doc goal)

```python
# app/main.py (Phase 4 will wire fully; Phase 3 prepares the shape)
def build_llm() -> LLMProvider:
    """Pick the LLM provider based on env. Dev override uses fake."""
    if os.getenv("DOJO_LLM") == "fake":
        from tests.fakes import FakeLLMProvider   # only in test env
        return FakeLLMProvider()
    from app.infrastructure.llm.anthropic_provider import (
        AnthropicLLMProvider,
    )
    return AnthropicLLMProvider()
```

**Important:** Phase 3 does NOT import `tests.fakes` from `app/main.py`
— that would leak test packages into production imports. Instead
Phase 7's E2E will inject the fake via its own test harness. Phase 3
just provides the `AnthropicLLMProvider` side of the switch.

### Repo dependency injection shape

```python
# Phase 4 will use this via Depends(get_session); Phase 3 tests wire
# the session from conftest.py directly.
def build_source_repo(session: Session) -> SourceRepository:
    return SqlSourceRepository(session)
```

### Exception wrap map (D-03b — reference)

| SDK exception | HTTP | Domain exception | Retryable? |
|--------------|------|------------------|------------|
| `anthropic.RateLimitError` | 429 | `LLMRateLimited` | yes |
| `anthropic.APIConnectionError` | — | `LLMUnreachable` | yes |
| `anthropic.APITimeoutError` | — | `LLMUnreachable` | yes |
| `anthropic.InternalServerError` | 5xx | `LLMUnreachable` | yes |
| `anthropic.AuthenticationError` | 401 | `LLMAuthFailed` | **no** |
| `anthropic.PermissionDeniedError` | 403 | `LLMAuthFailed` | **no** |
| `anthropic.NotFoundError` | 404 | `LLMInvalidRequest` | **no** |
| `anthropic.BadRequestError` (payload_too_large) | 400 | `LLMContextTooLarge` | **no** |
| `anthropic.BadRequestError` (other) | 400 | `LLMInvalidRequest` | **no** |
| `anthropic.UnprocessableEntityError` | 422 | `LLMInvalidRequest` | **no** |
| `anthropic.APIResponseValidationError` | — | `LLMOutputMalformed` | **no** |
| `pydantic.ValidationError` inside adapter | — | `LLMOutputMalformed` (after semantic retry) | semantic retry once, then raise |

---

## Pitfall Coverage Map

| Pitfall | Entry gate? | Mitigation location in plan | Residual risk |
|---------|-------------|-----------------------------|----------------|
| **C1** `MissingGreenlet` on post-commit attribute | yes | D-02b flat repos (no relationships); mapper converts at boundary; `expire_on_commit=False` already live | **Zero** — sync sessions don't use greenlet. Cat-and-mouse proof via SC #1 integration test. |
| **C2** selectinload vs joinedload | yes (moot) | D-02b: no relationships → no `*load` calls | Zero — revisit only if Phase 4/5 adds a relationship |
| **C3** `expire_on_commit=True` refetch trap | yes | Phase 1 already sets `expire_on_commit=False` in `session.py` (verified line 32) | Zero. |
| **C5** Atomic save session management | yes | D-01: use case owns `session.begin()`. SC #2 integration test exercises 3-save rollback | **Planner MUST verify** the integration test uses `session.begin()` without nested commits; fixture is SAVEPOINT-isolated (conftest.py line 104) |
| **C6** Anthropic tool-use not strict JSON | yes | Pydantic DTO validation inside adapter; **UPGRADED** — add `strict: true` to tool definition (first-line grammar enforcement); D-03a semantic retry handles residual | Very low — strict mode + Pydantic is belt-and-suspenders. |
| **C7** SDK + tenacity stacked retry | yes | D-03: `max_retries=0` on client; SC #4 asserts exact call count via respx | Zero — SC #4 is an explicit test gate. |
| **C8** Anthropic context-size limits | informs | `LLMContextTooLarge` wrap on `BadRequestError` with message sniff (D-03b) | **Low-medium** — message sniff is heuristic; flag for review if Anthropic changes the error text |
| **C9** URL extraction quality / paywall | yes | D-05 locked heuristics: 1000-char floor + paywall marker + User-Agent + timeout | Low — heuristics are directional; add a phase-exit note to tune from real usage |
| **C10** DraftStore races | yes | D-04 atomic pop + SC #5 concurrent-pop test | **Low** — see Re-plan Signal R1 about documented vs implementation guarantees |
| **M6** Pydantic `extra="ignore"` | yes (Phase 2 settled) | DTOs already have `ConfigDict(extra="ignore")` + `Field(min_length=1)` on cards (verified `app/application/dtos.py` line 21-43) | Zero. |
| **M7** fake drift | yes | D-07: 7 contract tests × [fake, real]. Every real adapter in Phase 3 runs against the same contract as its fake | Low — contract harness is the firewall. |
| **M9** `uv` + Alembic stale metadata | yes | Plan adds `from app.infrastructure.db import models` to `migrations/env.py` so autogen sees tables; smoke test asserts `Base.metadata.tables` has all 4 | Low. |

---

## Code Examples

See the per-section snippets above for: `SourceRow` column shape, mapper
functions, `SqlSourceRepository.save/get`, Anthropic tool schema,
`_sdk_call` with tenacity decorator, `generate_note_and_cards` outer
wrap, `InMemoryDraftStore` full class, `fetch_url` full function,
`read_file` full function, contract-test fixture, respx retry-count
test. All reference-quality, copy-editable.

---

## State of the Art

| Old approach (pre-2026) | Current approach | When changed | Impact on Dojo |
|-------------------------|------------------|--------------|----------------|
| Tool-use schema as permissive JSON shim | `strict: true` grammar-constrained sampling | 2025-2026 Anthropic feature | Narrows C6 surface; adopt in Phase 3 tool def |
| `alembic init -t async` template | Dojo uses sync env.py (post-Phase-1 reversal) | Phase 1 review 2026-04-22 | No Phase 3 impact — env.py is correct |
| `async_sessionmaker` + `AsyncSession` | Sync `sessionmaker` + `Session` | Phase 1 review | Phase 3 repos are sync; matches the stack |
| `asyncio.Lock` around dict ops | Plain dict + GIL atomicity | Phase 3 D-04 | Simpler code; R1 signal on documentation |
| `instructor` library for Pydantic-in/out | Direct SDK + Pydantic post-parse | Remains direct (per STACK.md FLAG 5) | No change — instructor optional, Phase 3 stays direct |

**Deprecated/outdated signals (none for Phase 3 scope):** N/A — all
Phase 3 libs are actively maintained and current.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `anthropic.BadRequestError` message for context-size contains "payload" or "context" substring (case insensitive) | B.4 — `LLMContextTooLarge` discrimination | Low. If strings are different, the catch falls through to `LLMInvalidRequest`; user sees a confusing error. Fix: expand match list if integration tests surface a variant string. **[ASSUMED]** |
| A2 | `anthropic.APITimeoutError` is a subclass of `APIConnectionError` per SDK exception tree | B.3 whitelist ordering | Very low. Verified via WebFetch of `_exceptions.py` GitHub docs (2026-04-24) — confirmed. **[VERIFIED]** |
| A3 | CPython 3.12 GIL implementation guarantees `dict.pop(key, default)` completes in one atomic C-level step | C — InMemoryDraftStore SC #5 | Medium — see Re-plan Signal R1. Not documented as language guarantee, but observed behavior. **[ASSUMED — CPython 3.12 impl detail]** |
| A4 | trafilatura 2.0's `extract()` returns `None` (not empty string) on extraction failure | D — URL fetcher | Low. Docs state null return (doc-confirmed 2026-04-24). Defense-in-depth: `is None or len(extracted) < _MIN_CHARS` handles both. **[VERIFIED]** |
| A5 | `anthropic.Anthropic(max_retries=0)` is a supported client constructor arg in SDK 0.97 | B.1 non-optional flag | Zero — verified via WebFetch of SDK README + DeepWiki (2026-04-24). **[VERIFIED]** |
| A6 | `strict: true` on tool definition guarantees `input_schema` conformance via grammar-constrained sampling | B.2 tool schema | Very low — verified via WebFetch of docs.claude.com strict-tool-use page (2026-04-24); explicit guarantee in docs. **[VERIFIED]** |
| A7 | `session.merge()` on an attached row performs upsert by primary key, not just "insert or fail" | A.3 `SqlSourceRepository.save` | Low — SQLAlchemy 2.0 documented behavior. PK-keyed upsert has been merge semantics since 1.x. **[CITED: SQLAlchemy docs /orm/session_basics.html]** |
| A8 | `sqlalchemy.orm.Session.get(Model, pk)` returns `None` on miss (not raises) | A.3 `SqlSourceRepository.get` | Zero — documented 2.0 behavior. **[CITED: SQLAlchemy docs]** |
| A9 | pytest-asyncio's `asyncio.gather(pop(), pop())` in an `async def test_...` with `asyncio_mode=auto` will schedule both coroutines on the same event loop in interleaved fashion | C concurrent-pop test | Low. pytest-asyncio 1.x + `asyncio_mode=auto` handles the fixture shape. Stability-check via pytest-repeat @ 10x. **[ASSUMED behavior of cooperative scheduling]** |

**Assumptions that require user confirmation before execution:** A1,
A3, A9. All three have fallback recovery paths documented in-table;
none are blockers.

---

## Open Questions / Re-plan Signals

### R1 — `dict.pop` atomicity documentation gap

CONTEXT.md D-04 claims `dict.pop(token, None)` is "GIL-atomic" and
treats this as a load-bearing mitigation for C10. Python 3's thread
safety docs (verified 2026-04-24 at `docs.python.org/3/library/
threadsafety.html`) explicitly list `d.pop(key)` as "safe but NOT
atomic" — it won't corrupt the dict, but "other threads can observe
intermediate states during the operation."

**What it means for Phase 3:**
- The D-04 claim is correct **in practice** on CPython 3.12 with the
  GIL enabled — `dict.pop(key, default)` compiles to a single
  `CALL_FUNCTION_KW`-style bytecode that executes atomically under
  the GIL.
- The claim is **not a language-spec guarantee**. A future CPython
  bytecode change, PEP 703 free-threaded build, or alternate runtime
  (PyPy, etc.) could technically allow a race where both callers get
  `None`.
- D-04c already flags this ("If Dojo ever runs on a no-GIL Python
  build, swap in `threading.Lock`").

**Recommended framing in the plan:**
- SC #5's concurrent-pop test is a **CPython 3.12 GIL observability
  gate**, not a spec-level atomicity proof.
- Use `pytest-repeat --count=10` on the concurrent-pop test to gain
  confidence without claiming guarantee.
- Keep D-04c's class-docstring warning as the load-bearing contract
  marker.

This is **NOT a re-plan signal** — CONTEXT.md already baked the
right escape hatch. But the planner should write the test comments
and SUMMARY.md wording to frame CPython behavior, not language spec.

### R2 — `strict: true` adoption changes C6 framing (not the plan)

CONTEXT.md D-03a and C6 both assume Anthropic tool-use is "permissive
about the schema." 2026 Anthropic `strict: true` narrows this
materially (grammar-constrained sampling guarantees
`input_schema`-conformant inputs). **This is a plan refinement, not a
re-plan signal.** D-03a's Pydantic DTO firewall + semantic retry
remain correct — they catch `min_length=1` on cards (which grammar
doesn't enforce) and defend against the (documented-impossible-but-
you-never-know) case of a strict-mode bypass.

Recommended plan edit: when the plan lands the tool schema, include
`"strict": True` and document in a comment that it's the first-line
defense; Pydantic catches residual schema issues including the
length invariant. Update CONTEXT.md C6 mitigation note accordingly
on phase close.

### R3 — `httpx` must be promoted from dev to runtime dependency

`httpx` is currently in `[dependency-groups].dev` (test client for
ASGI). The URL fetcher imports `httpx` at runtime. Phase 3 plan
must move it to `[project].dependencies`. One-line pyproject edit;
flagged here so planner enumerates it as a separate task in the
dependency-setup plan.

### R4 — Exception type ownership (Claude's Discretion resolution)

CONTEXT.md defers this to the planner. Research recommendation is
**`app/application/exceptions.py` for all domain-visible LLM and
Source exception types**, on the DDD principle that exception types
belong to the layer that defines their *meaning*. Infrastructure
raises them; application and web catch them. If the planner disagrees
(e.g. wants to split: `LLMOutputMalformed` already lives in
application — add the others there too; infra-private errors go in
`app/infrastructure/exceptions.py` if ever needed), the specific
file chosen must be consistent across all 8 new types.

### R5 — Does `env.py` need the models eager-import?

CONTEXT.md D-08 references PITFALL M9 ("`uv` + editable install +
Alembic: stale metadata"). Current `migrations/env.py` line 10:
`from app.infrastructure.db.session import Base  # noqa: F401 (M9)`
— but that only imports `Base`, not `models.py` (which doesn't exist
yet). Phase 3 plan MUST:
1. Create `app/infrastructure/db/models.py` with row classes.
2. Add `from app.infrastructure.db import models as _models  # noqa:
   F401` to `env.py` so `Base.metadata.tables` sees the tables at
   autogen time.
3. Add a smoke test (`tests/integration/test_alembic_metadata.py`)
   asserting `Base.metadata.tables` contains all four expected table
   names. 5-line test, catches the M9 "empty migration" bug.

No open question — just enumerate these three steps in the plan.

---

## References

### Primary (HIGH confidence) — verified 2026-04-24

- **PyPI JSON APIs** — verified current versions:
  - `anthropic` 0.97.0 ([pypi.org/pypi/anthropic/json](https://pypi.org/pypi/anthropic/json))
  - `tenacity` 9.1.4 ([pypi.org/pypi/tenacity/json](https://pypi.org/pypi/tenacity/json))
  - `trafilatura` 2.0.0 ([pypi.org/pypi/trafilatura/json](https://pypi.org/pypi/trafilatura/json))
  - `respx` 0.23.1 ([pypi.org/pypi/respx/json](https://pypi.org/pypi/respx/json))
- **Anthropic docs — Strict tool use** ([platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use)) — grammar-constrained sampling, schema limitations, supported models.
- **Anthropic docs — Tool use overview** ([platform.claude.com/docs/en/agents-and-tools/tool-use/overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)) — `tool_use` block shape, `tool_choice`, pricing.
- **Anthropic SDK `_exceptions.py`** ([github.com/anthropics/anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python)) — complete exception tree with HTTP status mapping.
- **Anthropic SDK README** (DeepWiki mirror at [deepwiki.com/anthropics/anthropic-sdk-python/4.5-request-lifecycle-and-error-handling](https://deepwiki.com/anthropics/anthropic-sdk-python/4.5-request-lifecycle-and-error-handling)) — `max_retries` default is 2.
- **tenacity docs** ([tenacity.readthedocs.io](https://tenacity.readthedocs.io/en/latest/)) — `@retry`, `stop_after_attempt`, `wait_exponential`, `reraise=True`, `.retry.statistics`.
- **Python 3 Thread Safety docs** ([docs.python.org/3/library/threadsafety.html](https://docs.python.org/3/library/threadsafety.html)) — `dict.pop` classified safe-but-not-atomic.
- **Python 3.12 FAQ — atomic dict ops** ([docs.python.org/3.12/faq/library.html](https://docs.python.org/3.12/faq/library.html)) — `D[x] = y` atomic list.
- **trafilatura docs** ([trafilatura.readthedocs.io/en/latest/corefunctions.html](https://trafilatura.readthedocs.io/en/latest/corefunctions.html)) — `extract()` full signature with `deduplicate`, `favor_precision`, `output_format`, `include_comments`.
- **Alembic autogenerate docs** ([alembic.sqlalchemy.org/en/latest/autogenerate.html](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)) — limitations, `batch_alter_table` for SQLite, human-review requirement.

### Secondary (MEDIUM confidence)

- WebSearch result: anthropic SDK default `max_retries=2` (cross-referenced with DeepWiki — agrees).
- WebSearch result: CPython 3.13 per-object dict locks (free-threaded builds) — relevant to R1 framing.

### Tertiary (internal project artifacts)

- `.planning/phases/03-infrastructure-adapters/03-CONTEXT.md` — user decisions D-01..D-10.
- `.planning/research/PITFALLS.md` — C1..C10, M6, M7, M9.
- `.planning/research/STACK.md` — version floors + known-issue flags.
- `.planning/phases/02-domain-application-spine/02-CONTEXT.md` — port shapes, D-11 env gate, fake design rules.
- `CLAUDE.md` (project root) — file size ≤100, ABOUTME headers, Protocol-vs-Callable rule, PR discipline.
- `docs/superpowers/specs/2026-04-18-dojo-design.md` §4.2, §4.3, §5.1, §6, §7.2.
- `app/infrastructure/db/session.py` (live; reused).
- `app/application/ports.py` (live; implemented against).
- `app/application/dtos.py` (live; `GeneratedContent` is the Anthropic adapter's validated type).
- `tests/contract/test_llm_provider_contract.py` (live; pattern for 6 new contract files).
- `tests/conftest.py` (live; `session` fixture reused by all SQL contract + integration tests).
- `migrations/env.py` (live; verified sync-shaped, imports `Base`, needs models-eager-import added).
- `migrations/versions/0001_initial.py` (empty baseline; Phase 3 stacks 0002 on top).

---

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — all versions verified against PyPI live 2026-04-24.
- Architecture per-adapter patterns: **HIGH** — each pattern verified against official docs; code snippets compile-ready.
- Anthropic tool-use + strict mode: **HIGH** — docs.claude.com explicit guarantee, tested syntax.
- tenacity + retry count semantics: **HIGH** — docs + respx call-count assertion is standard.
- `dict.pop` atomicity claim: **MEDIUM** — implementation-correct on CPython 3.12 GIL; language-spec-weaker; R1 flag.
- Alembic autogen + SQLite: **MEDIUM-HIGH** — M9 mitigation is the critical path; documented gotcha.
- Pitfalls coverage: **HIGH** — CONTEXT.md already baked mitigations; research confirmed.
- Contract harness extension: **HIGH** — copy-edit the existing LLM pattern across 6 more files.
- URL fetcher paywall heuristics: **MEDIUM** — directional; real usage will tune thresholds.

**Research date:** 2026-04-24
**Valid until:** 2026-05-24 (30 days — stack is stable; Anthropic API is
the fastest-moving dep, minor SDK versions weekly).

---

## RESEARCH COMPLETE
