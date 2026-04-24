# Phase 3: Infrastructure Adapters — Pattern Map

**Mapped:** 2026-04-24
**Files analyzed:** 35 new/modified (18 source/migration/config + 17 test/smoke files)
**Analogs found:** 32 / 35 (remaining 3 have no pre-existing analog; research snippets control)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/infrastructure/db/models.py` | ORM model (declarative rows) | CRUD | `app/domain/entities.py` (shape) + `app/infrastructure/db/session.py` (`Base`) | role-match |
| `app/infrastructure/db/mappers.py` | Pure mapper functions (domain ↔ row) | transform | `app/domain/entities.py` + RESEARCH.md §A | role-match |
| `app/infrastructure/repositories/sql_source_repository.py` | Sync SQL repo (Protocol conformer) | CRUD | `tests/fakes/fake_source_repository.py` (signatures) | exact-signature |
| `app/infrastructure/repositories/sql_note_repository.py` | Sync SQL repo (overwrite on save) | CRUD | `tests/fakes/fake_note_repository.py` | exact-signature |
| `app/infrastructure/repositories/sql_card_repository.py` | Sync SQL repo (append on save) | CRUD | `tests/fakes/fake_card_repository.py` | exact-signature |
| `app/infrastructure/repositories/sql_card_review_repository.py` | Sync SQL repo (append-only log) | CRUD | `tests/fakes/fake_card_review_repository.py` | exact-signature |
| `app/infrastructure/llm/anthropic_provider.py` | LLM adapter (tool-use + retries) | request-response | `tests/fakes/fake_llm_provider.py` (signatures); RESEARCH.md §B (behavior) | signature-match / no-behavior-analog |
| `app/infrastructure/llm/tool_schema.py` | Static tool-schema constant | config/data | RESEARCH.md §B.2 — no codebase analog | **no analog** |
| `app/infrastructure/drafts/in_memory_draft_store.py` | In-memory dict adapter with TTL | CRUD / event | `tests/fakes/fake_draft_store.py` (dict + pop pattern) | exact-signature |
| `app/infrastructure/readers/file_reader.py` | Callable adapter: `Path → str` | file-I/O | — RESEARCH.md §E is the spec; closest structural kin is `app/application/extractor_registry.py._missing_error` (exception wrap shape) | **no analog** (callable, not class) |
| `app/infrastructure/fetchers/url_fetcher.py` | Callable adapter: `str → str` | request-response | — RESEARCH.md §D; no codebase network-adapter analog | **no analog** |
| `app/application/exceptions.py` (extension) | Domain exception classes | type | `app/application/exceptions.py` (existing 4 classes) | exact |
| `migrations/versions/0002_create_initial_schema.py` | Alembic migration (DDL) | batch / schema | `migrations/versions/0001_initial.py` (shape only; logic autogen'd) | shape-match |
| `migrations/env.py` (modify) | Alembic environment wiring | config | `migrations/env.py` (already live — one-line addition) | self |
| `app/main.py` (modify) | Composition root | config | `app/main.py` (existing `create_app` / `lifespan`) | self-extend |
| `pyproject.toml` (modify) | Dependency config | config | current `[project.dependencies]` block | self-extend |
| `docs/architecture/overview.md` (modify) | Doc | doc | existing overview §4/§5/§6 | self-extend |
| `tests/contract/test_source_repository_contract.py` | Contract test (fake + real) | test | `tests/contract/test_llm_provider_contract.py` | exact |
| `tests/contract/test_note_repository_contract.py` | Contract test | test | `tests/contract/test_llm_provider_contract.py` | exact |
| `tests/contract/test_card_repository_contract.py` | Contract test | test | `tests/contract/test_llm_provider_contract.py` | exact |
| `tests/contract/test_card_review_repository_contract.py` | Contract test | test | `tests/contract/test_llm_provider_contract.py` | exact |
| `tests/contract/test_draft_store_contract.py` | Contract test | test | `tests/contract/test_llm_provider_contract.py` | exact |
| `tests/contract/test_source_reader_contract.py` | Contract test (callable port) | test | `tests/contract/test_llm_provider_contract.py` (+ inline test-only "fake" callable) | exact, minor adaptation |
| `tests/contract/test_url_fetcher_contract.py` | Contract test (callable port) | test | `tests/contract/test_llm_provider_contract.py` (+ respx stub for "real" leg) | exact, minor adaptation |
| `tests/integration/test_sql_repositories_atomic.py` | SC #2 rollback test | test | `tests/conftest.py` `session` fixture (SAVEPOINT) | fixture-driven |
| `tests/integration/test_sql_repositories_regenerate.py` | SC #7 regenerate test | test | same fixture | fixture-driven |
| `tests/integration/test_anthropic_retry_count.py` | SC #4 retry-count via respx | test | RESEARCH.md §B.3 snippet; no local respx test yet | **no analog** |
| `tests/integration/test_anthropic_provider.py` | Provider malformed/429/401 wraps | test | RESEARCH.md §B.4 | **no analog** |
| `tests/integration/test_url_fetcher_paywall.py` | Paywall / timeout / 404 | test | RESEARCH.md §D snippet | **no analog** |
| `tests/integration/test_file_reader.py` | File-read happy/error paths | test | `tmp_path` stdlib fixture pattern + RESEARCH.md §E | role-match (pytest tmp_path) |
| `tests/integration/test_draft_store_concurrency.py` | SC #5 TTL + race | test | `tests/fakes/fake_draft_store.py` shape; asyncio.gather from RESEARCH §C | pattern-new |
| `tests/integration/test_alembic_round_trip.py` | upgrade → downgrade → upgrade | test | `tests/conftest.py` `_migrated_engine` fixture (uses `command.upgrade`) | fixture-match |
| `tests/integration/test_alembic_metadata.py` | `Base.metadata.tables` smoke | test | `migrations/env.py` import shape; 5-line M9 guard | pattern-new |
| `tests/unit/test_mappers.py` | Pure-function round-trip | test | RESEARCH.md §A mapper snippet | pattern-new |
| `tests/unit/test_composition_root.py` | Smoke: `create_app()` wires real adapters | test | `app/main.py` `create_app` | self-referential |

---

## Pattern Assignments

### `app/infrastructure/db/models.py` (ORM models; CRUD)

**Analog:** `app/infrastructure/db/session.py` (for `Base` import) + `app/domain/entities.py` (for 1:1 field layout).

**Header / import block — copy exactly (from `app/infrastructure/db/session.py` lines 1–10):**
```python
# ABOUTME: <one-line summary — what this file holds>
# ABOUTME: <one-line qualifier — key behavior/constraint>
"""<Module docstring (single line, domain-flavored).>"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.session import Base
```

**Row-class shape — copy 1:1 from RESEARCH.md §A (lines 325–341), one row per entity. Column types locked by CONTEXT D-02d:** `Mapped[str]` for UUIDs (via `str(uuid)` at mapper boundary), `Mapped[datetime]`, `Mapped[str]` for enums (via `.value`), `Mapped[str]` JSON-encoded for `Card.tags`.

**Domain-entity field map — copy shape from `app/domain/entities.py` (lines 21–64):**
```python
@dataclass(frozen=True)
class Source:
    kind: SourceKind
    user_prompt: str
    display_name: str
    identifier: str | None = None
    source_text: str | None = None
    id: SourceId = field(default_factory=lambda: SourceId(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
```
→ `SourceRow` columns mirror these names 1:1. `NoteRow`, `CardRow`, `CardReviewRow` likewise mirror `Note` / `Card` / `CardReview`. **No `relationship()`** per D-02b.

**Delta from analog:** Row classes are SQLAlchemy `Mapped[...]` annotated, persisted types. Domain dataclasses are frozen, stdlib-only. Never swap them.

---

### `app/infrastructure/db/mappers.py` (pure transforms)

**Analog:** RESEARCH.md §A (lines 354–375). No prior in-codebase pure-mapper module — this is a new pattern, but it matches the project's existing "pure stdlib function" shape (no class, no state).

**Copy exactly (from RESEARCH.md §A lines 354–375):**
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

**Mapper-file docstring pattern (from `app/application/extractor_registry.py` lines 1–3):** one-line ABOUTME × 2 + single-line module docstring.

**Card.tags special case:** `json.dumps(list(card.tags))` on save; `tuple(json.loads(row.tags))` on read (CONTEXT D-02d).

**Delta from analog:** Pure module-level functions. No classes — the "one main function per file" wiki rule is accommodated by splitting into `mappers/source.py`, `mappers/note.py`, etc. if the single file exceeds 100 lines (CLAUDE.md).

---

### `app/infrastructure/repositories/sql_source_repository.py` (and peers)

**Analog:** `tests/fakes/fake_source_repository.py` — this is the authoritative signature source.

**Signature-copy from fake (lines 11–24 of `tests/fakes/fake_source_repository.py`):**
```python
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

**Real-repo shape — copy from RESEARCH.md §A (lines 384–397):**
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

**Per-repo `save` primitive matrix (CONTEXT D-02 + RESEARCH.md §A):**

| Repo | save primitive | Rationale |
|------|----------------|-----------|
| `SqlSourceRepository` | `session.merge(row)` | Upsert by PK (re-save rewrites) |
| `SqlNoteRepository` | `session.merge(row)` | **Regenerate-overwrites** (PERSIST-02) |
| `SqlCardRepository` | `session.add(row)` | **Regenerate-appends** (PERSIST-02; NOT merge) |
| `SqlCardReviewRepository` | `session.add(row)` | Append-only log |

**CardReview has no `get()`** — Protocol in `app/application/ports.py` (lines 110–118) only declares `save`. Mirror that shape; do not add `get`.

**Import idiom — follow `app/infrastructure/db/session.py` lines 1–10:** `from __future__ import annotations` first, stdlib second, third-party next, `app.*` last.

**Logger (every adapter module):**
```python
from app.logging_config import get_logger
log = get_logger(__name__)
```
(Pattern from `app/main.py` line 20 + `app/logging_config.py` line 58–68 docstring: "Every module uses `log = get_logger(__name__)`.")

**Delta from analog (fakes):** No `.saved` public attribute — real repos hold `self._session`, not a dict. No mutation tracking. Persistence is the side-effect of `session.merge/add`. Repos **never commit or rollback** (CONTEXT D-01 — use case owns the transaction).

**Interrogate/docstring convention (from `app/application/ports.py` lines 27–46):** one-line method docstring + `:param:` / `:returns:` / `:raises:` Sphinx blocks. Keep concise — project uses inline one-liners with no Args sections above the `:param:` block.

---

### `app/infrastructure/llm/anthropic_provider.py` (LLM adapter)

**Signature analog:** `tests/fakes/fake_llm_provider.py` — Protocol signature contract.

**Signature to match (from `tests/fakes/fake_llm_provider.py` lines 21–26):**
```python
def generate_note_and_cards(
    self, source_text: str | None, user_prompt: str
) -> tuple[NoteDTO, list[CardDTO]]:
```

**Behavior (no codebase analog; RESEARCH.md §B is the template):**

1. **Client construction (RESEARCH.md §B.1 lines 466–476):**
```python
self._client = anthropic.Anthropic(
    api_key=settings.anthropic_api_key.get_secret_value(),
    max_retries=0,    # non-optional per D-03 / C7
)
```
`get_settings()` import from `app.settings` (pattern from `app/main.py` line 17 + `app/infrastructure/db/session.py` line 10).

2. **`_sdk_call` decorator (RESEARCH.md §B.3 lines 568–588):**
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((
        anthropic.RateLimitError,
        anthropic.APIConnectionError,
        anthropic.APITimeoutError,
        anthropic.InternalServerError,
    )),
    reraise=True,
)
def _sdk_call(self, messages: list[dict], system: str) -> Any:
    return self._client.messages.create(
        model=self._model, max_tokens=4096, system=system,
        messages=messages, tools=[TOOL_DEFINITION],
        tool_choice={"type": "tool", "name": "generate_note_and_cards"},
    )
```

3. **Outer wrap — SDK → domain exception map (RESEARCH.md §B.4 lines 643–668, cross-reference RESEARCH.md Exception-wrap table lines 1243–1258):**
```python
try:
    response = self._sdk_call(...)
    return self._parse_and_validate(response)
except pydantic.ValidationError:
    # one semantic retry with stricter prompt (D-03a)
    ...
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

4. **Response parse (RESEARCH.md §B.5 lines 685–694):**
```python
def _parse_and_validate(self, response) -> tuple[NoteDTO, list[CardDTO]]:
    tool_blocks = [b for b in response.content if b.type == "tool_use"]
    if not tool_blocks:
        raise LLMOutputMalformed("no tool_use block in response")
    payload = tool_blocks[0].input
    validated = GeneratedContent.model_validate(payload)
    return validated.note, validated.cards
```
`GeneratedContent` already lives in `app/application/dtos.py` lines 37–43 (min_length=1 on cards) — **import, do not re-define**.

**Delta from analog (fake):** Fake returns canned `next_response`; real does tool-use call, retries, DTO validation, exception wrap. Both conform to the same Protocol (`app/application/ports.py` lines 27–46) — the contract test proves this.

**File-size gate:** RESEARCH.md §"What Phase 3 adds" lines 245–248 anticipates splitting: `anthropic_provider.py` (class + public methods), `_tool_schema.py` (tool constant), `_exceptions_map.py` (SDK → domain map dict). Planner confirms the exact split when file hits the 100-line soft limit.

---

### `app/infrastructure/llm/tool_schema.py` (static tool-use schema)

**Analog:** None in codebase — pure data constant. RESEARCH.md §B.2 lines 487–527 is the template (copy verbatim). Key invariants:
- `"strict": True` (RESEARCH.md §B.2 line 494 — first-line C6 defense, **[VERIFIED 2026]**).
- `additionalProperties: false` on every object (required by `strict`).
- `tags` is required; emit `[]` when empty (keeps strict schema tight).

**Header shape (standard):**
```python
# ABOUTME: Anthropic tool-use schema for generate_note_and_cards.
# ABOUTME: strict=True + additionalProperties=false enforces shape via grammar.
"""Tool-use schema constant."""
from __future__ import annotations

TOOL_DEFINITION: dict = { ... }
```

---

### `app/infrastructure/drafts/in_memory_draft_store.py`

**Analog:** `tests/fakes/fake_draft_store.py` — same dict-backed, atomic-pop shape. RESEARCH.md §C (lines 705–745) is the full template.

**Signature-copy from `tests/fakes/fake_draft_store.py` lines 11–30:**
```python
class FakeDraftStore:
    """In-memory dict with an atomic pop and a force_expire hook."""

    def __init__(self) -> None:
        self._store: dict[DraftToken, DraftBundle] = {}
        ...

    def put(self, token: DraftToken, bundle: DraftBundle) -> None:
        self._store[token] = bundle
        ...

    def pop(self, token: DraftToken) -> DraftBundle | None:
        return self._store.pop(token, None)
```

**Real-store shape (from RESEARCH.md §C lines 713–744), strip the `force_expire` hook (that's test-only), replace with clock injection + TTL check:**
```python
class InMemoryDraftStore:
    """DraftStore Protocol adapter: plain dict + lazy TTL + GIL-atomic pop.

    Thread safety comes from CPython GIL atomicity of dict operations.
    If Dojo ever runs on a no-GIL Python build (PEP 703), swap in
    threading.Lock.
    """

    _TTL_SECONDS = 30 * 60

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
            return None
        return bundle
```

**Delta from analog (fake):** Entry is `(bundle, timestamp)` tuple; `pop` runs lazy TTL; clock injected. D-04c class-docstring warning is load-bearing — copy verbatim.

---

### `app/infrastructure/readers/file_reader.py` (callable)

**Analog:** No prior codebase file-reader. Exception-wrap style analog = `app/application/extractor_registry.py` `_missing_error` (lines 37–55) — matching pattern of "wrap low-level exception into domain type".

**Copy from RESEARCH.md §E (lines 946–961):**
```python
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
        raise SourceUnreadable(f"OS error reading {path}: {e}") from e
```

**Exception types** live in `app/application/exceptions.py` (see "Shared Patterns — Exceptions" below).

**Delta from analog:** Module-level function only — no class wrapping. Port is `Callable[[Path], str]` (see `app/application/ports.py` line 152), so the file contains the function and nothing else.

---

### `app/infrastructure/fetchers/url_fetcher.py` (callable)

**Analog:** No codebase analog. Copy verbatim from RESEARCH.md §D (lines 822–874). Key constants locked:
- `_USER_AGENT = "Dojo/0.1 (+local study app)"` (D-05)
- `_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)` (D-05 — ≤10s)
- `_MIN_CHARS = 1000` (D-05)
- `_PAYWALL_MAX_CHARS = 2000` (D-05)
- `_PAYWALL_MARKERS = frozenset((...))` (D-05)
- `trafilatura.extract(..., include_comments=False, deduplicate=True, output_format="txt", favor_precision=True)` (Claude's Discretion — favor precision)

**Exception wrap targets:** `SourceFetchFailed` for 2xx/timeout; `SourceNotArticle` for short/paywall/None-extraction.

**Port:** `UrlFetcher = Callable[[str], str]` (from `app/application/ports.py` line 149) — sync, module-level function, no class.

---

### `app/application/exceptions.py` (extend existing file)

**Analog:** the file itself — `app/application/exceptions.py` lines 1–29 already define the pattern.

**Copy class-shape from existing (line 27–28):**
```python
class LLMOutputMalformed(DojoError):
    """Raised when the LLM's structured output fails DTO validation."""
```

**Add (RESEARCH §R4 locks this location, one consistent file — not per-adapter exceptions):**
```python
class LLMRateLimited(DojoError):
    """Raised after all tenacity retries exhaust on a 429."""

class LLMAuthFailed(DojoError):
    """Raised when the provider rejects credentials (401/403)."""

class LLMUnreachable(DojoError):
    """Raised on transport failure after tenacity retries."""

class LLMContextTooLarge(DojoError):
    """Raised when the payload exceeds the model's context window."""

class LLMInvalidRequest(DojoError):
    """Raised on permanent 4xx (non-auth, non-context)."""

class SourceNotFound(DojoError):
    """Raised when a FILE path does not exist."""

class SourceUnreadable(DojoError):
    """Raised when a FILE path cannot be read as UTF-8 text."""

class SourceFetchFailed(DojoError):
    """Raised on URL fetch failure (non-2xx, timeout, transport)."""

class SourceNotArticle(DojoError):
    """Raised when extraction yields no usable article text (incl. paywall)."""
```

**Delta from analog:** None — same DojoError base, same one-line docstring convention. RESEARCH R4 locks this file (not `app/infrastructure/exceptions.py`) on the DDD principle that exception types belong to the layer that defines their *meaning*.

---

### `migrations/versions/0002_create_initial_schema.py`

**Analog:** `migrations/versions/0001_initial.py` lines 1–25 — revision-file shape. The 0002 body itself is **autogenerated** (CONTEXT D-08), not hand-copied.

**Copy header/shape from `0001_initial.py` (lines 1–17):**
```python
# ABOUTME: <Describes what this migration creates — the four tables>.
# ABOUTME: <Second line — e.g. "Depends on 0001 empty baseline.">

"""create initial schema

Revision ID: 0002
Revises: 0001
Create Date: <autogen>

"""

from collections.abc import Sequence

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
```

**Upgrade/downgrade bodies:** Autogen via `uv run alembic revision --autogenerate -m "create initial schema"` (D-08). Human-review checklist (RESEARCH §F lines 1009–1024).

---

### `migrations/env.py` (modify — one line addition)

**Analog:** the file itself (lines 1–62). Existing line 10 already has `from app.infrastructure.db.session import Base  # noqa: F401 (M9)`.

**Required addition (CONTEXT D-08 + RESEARCH §R5, after line 10):**
```python
from app.infrastructure.db.session import Base  # noqa: F401 (M9)
from app.infrastructure.db import models as _models  # noqa: F401 (M9)
```

**Delta from analog:** One-line addition only; all other env.py logic stays. The existing `target_metadata = Base.metadata` (line 28) now sees the four new tables through the imported `models` module.

---

### `app/main.py` (modify — composition root)

**Analog:** `app/main.py` lines 1–77 (existing `create_app` / `lifespan`). RESEARCH §"Composition-root fake↔real swap" lines 1215–1226 is the target shape.

**Existing pattern to preserve (from `app/main.py` lines 64–74):**
```python
def create_app() -> FastAPI:
    """Build the FastAPI app. Called by uvicorn via `app.main:app`."""
    app = FastAPI(title="Dojo", lifespan=lifespan)
    app.state.templates = _TEMPLATES
    app.mount("/static", StaticFiles(directory=_STATIC), name="static")
    app.include_router(home.router)
    return app
```

**Add (RESEARCH snippet lines 1217–1225):**
```python
def build_llm() -> LLMProvider:
    """Pick the LLM provider based on env. Dev override uses fake."""
    from app.infrastructure.llm.anthropic_provider import (
        AnthropicLLMProvider,
    )
    return AnthropicLLMProvider()
```

**Phase 3 boundary:** Phase 3 builds the wired components but does **not** inject them into request handlers (Phase 4 wires `Depends(get_session)`). The fake-vs-real switch per Phase 7 E2E (env var `DOJO_LLM=fake`) is a Phase 3 pre-wire note, not Phase 3 work.

**CRITICAL — per RESEARCH §"Composition-root" lines 1227–1231:** `app/main.py` MUST NOT import `tests.fakes`. The fake-side injection lives in E2E harness, not production wiring.

**Delta from analog:** Small — the file gains provider/repo constructor factories but does not yet dependency-inject into routes.

---

### `pyproject.toml` (modify)

Copy-edit — no code excerpt needed. CONTEXT + RESEARCH §"Environment Availability" lines 286–304 + §R3 mandate:
- Promote `httpx` from `[dependency-groups].dev` to `[project].dependencies`.
- Add to `[project].dependencies`: `anthropic`, `tenacity`, `trafilatura`, `nh3`.
- Add to `[dependency-groups].dev`: `respx`.

---

## Test Patterns

### Contract tests — one canonical template (7 new files)

**Analog:** `tests/contract/test_llm_provider_contract.py` — **the controlling template**. Every Phase 3 contract test copies this shape; only the fixture body and assertions differ per port.

**Controlling template (copy every line except the marked ones):**
```python
# ABOUTME: TEST-03 contract harness — asserts Protocol shape for <PORT>.
# ABOUTME: Fake leg always runs; real leg <runs / skips> per D-07.
"""<Port> contract tests — shared across fake and real impls."""

from __future__ import annotations

import os                                                # LLM only
import pytest
from tests.fakes import <FakePortClass>


@pytest.fixture(params=["fake", "<real>"])
def <port_name>(request: pytest.FixtureRequest, ...):
    """Yield a fake or real <Port>; real <gate>."""
    if request.param == "fake":
        yield <FakePortClass>()
        return
    # real-leg branch — see per-file table below
    ...

def test_<behavior>(<port_name>) -> None:
    """<One-line behavior description.>"""
    ...
```

**Per-file "real leg" branch (seven files):**

| File | `params` 2nd value | Real-leg construction | Env gate |
|------|--------------------|----------------------|----------|
| `test_llm_provider_contract.py` (exists) | `"anthropic"` | `pytest.importorskip` + `AnthropicLLMProvider()` | `RUN_LLM_TESTS=1` |
| `test_source_repository_contract.py` | `"sql"` | `SqlSourceRepository(session)` (consumes `session` fixture from `conftest.py`) | none |
| `test_note_repository_contract.py` | `"sql"` | `SqlNoteRepository(session)` | none |
| `test_card_repository_contract.py` | `"sql"` | `SqlCardRepository(session)` | none |
| `test_card_review_repository_contract.py` | `"sql"` | `SqlCardReviewRepository(session)` | none |
| `test_draft_store_contract.py` | `"in_memory"` | `InMemoryDraftStore()` | none |
| `test_source_reader_contract.py` | `"real"` | bare `read_file` callable + `tmp_path` fixture | none |
| `test_url_fetcher_contract.py` | `"real"` | bare `fetch_url` callable + respx stub fixture | none |

**Fixture-param shape to copy verbatim from `tests/contract/test_llm_provider_contract.py` lines 15–27:**
```python
@pytest.fixture(params=["fake", "anthropic"])
def llm_provider(request: pytest.FixtureRequest):
    """Yield a fake or real LLMProvider; real skips without opt-in."""
    if request.param == "fake":
        yield FakeLLMProvider()
        return

    if os.getenv("RUN_LLM_TESTS", "").lower() not in ("1", "true", "yes"):
        pytest.skip("RUN_LLM_TESTS not set")
    adapter_module = pytest.importorskip(
        "app.infrastructure.llm.anthropic_provider"
    )
    yield adapter_module.AnthropicLLMProvider()
```

**Callable-port adaptation** (`test_source_reader_contract.py`, `test_url_fetcher_contract.py`): No class-based fake exists — inline a trivial fake callable in the test module itself, or rely on the real + a respx/tmp_path fixture. Two params can still be `["real", "fake"]` with the fake leg implemented as `lambda _: "stub text"`.

**Assertion style (from `test_llm_provider_contract.py` lines 30–38):**
```python
def test_generate_returns_note_and_card_list(llm_provider) -> None:
    """Return type is (NoteDTO, list[CardDTO]) with non-empty cards."""
    note, cards = llm_provider.generate_note_and_cards(
        source_text=None, user_prompt="alpha"
    )
    assert isinstance(note, NoteDTO)
    assert isinstance(cards, list)
    assert len(cards) >= 1
```
— public-attribute inspection; no `.calls` list, no Mock; matches Phase 2 D-11 contract style.

---

### Integration tests

**Shared analog:** `tests/conftest.py` `session` fixture (lines 87–108) — SAVEPOINT-isolated tmp-SQLite session, session-scoped migrated engine, function-scoped rollback.

**Session-fixture consumption (copy this pattern into any test that needs a real DB):**
```python
def test_something(session: Session) -> None:
    """Behavior using the SAVEPOINT-isolated session."""
    repo = SqlSourceRepository(session)
    ...
    # Any session.commit() opens/closes a SAVEPOINT; outer rollback
    # at teardown guarantees no state leaks.
```
(Fixture source: `tests/conftest.py` lines 87–108 — `join_transaction_mode="create_savepoint"` is the load-bearing flag.)

**SC #2 atomic-save pattern (from RESEARCH.md §A lines 438–448):**
```python
with session.begin():
    src_repo.save(source)
    note_repo.save(note)
    card_repo.save(card_that_violates_constraint)  # raises
# Exit with exception → rollback (SAVEPOINT).
assert session.get(SourceRow, str(source.id)) is None
assert session.get(NoteRow, str(note.id)) is None
```

**SC #4 respx retry-count pattern (from RESEARCH.md §B.3 lines 608–624):**
```python
@respx.mock
def test_tenacity_counts_exact():
    route = respx.post("https://api.anthropic.com/v1/messages").mock(
        side_effect=[
            httpx.Response(429, json={...}),
            httpx.Response(200, json={...valid tool_use...}),
        ]
    )
    provider = AnthropicLLMProvider()
    note, cards = provider.generate_note_and_cards(None, "x")
    assert route.call_count == 2
```

**SC #5 concurrent-pop pattern (from RESEARCH.md §C lines 769–786):**
```python
@pytest.mark.asyncio
async def test_concurrent_pop_exactly_one_wins():
    store = InMemoryDraftStore()
    token = DraftToken(uuid.uuid4())
    store.put(token, bundle)
    async def pop(): return store.pop(token)
    results = await asyncio.gather(pop(), pop())
    winners = [r for r in results if r is not None]
    assert len(winners) == 1
```
**Framing note (RESEARCH §R1):** comment the test as a *CPython 3.12 GIL observability gate*, not a language-spec proof. Run with `pytest-repeat --count=10`.

**Fake-clock TTL pattern (CONTEXT D-04b + RESEARCH §C lines 755–762):**
```python
times = [0.0]
store = InMemoryDraftStore(clock=lambda: times[0])
store.put(tok, bundle)
times[0] = 1800.1
assert store.pop(tok) is None
```

**SC #6 URL fetcher respx pattern (from RESEARCH.md §D lines 894–932):** four-way test table — happy path, 404, paywall, too-short.

**SC #1 / SC #7 regenerate pattern (CONTEXT D-02 + RESEARCH §A):** Source round-trip + Note merge overwrites same id + Card add appends new ids.

**Alembic round-trip (CONTEXT D-08):** reuse `_alembic_cfg` fixture from `tests/conftest.py` lines 56–66; call `command.upgrade` → `command.downgrade` → `command.upgrade`.

**Alembic metadata smoke (RESEARCH §R5):** 5-line test — `from app.infrastructure.db.session import Base` + `assert set(Base.metadata.tables) == {"sources", "notes", "cards", "card_reviews"}`.

**File-reader integration (from RESEARCH §E lines 940–961):** use `tmp_path` stdlib fixture, create file / unreadable file / bad-utf8 file, assert exception wraps.

---

### Unit tests

**`tests/unit/test_mappers.py`** — pure round-trip, no fixture:
```python
def test_source_round_trip() -> None:
    src = Source(kind=SourceKind.TOPIC, user_prompt="p", display_name="d")
    row = source_to_row(src)
    assert source_from_row(row) == src
```
(Analog: no codebase precedent. Justified by RESEARCH §A "these are pure — unit-testable without a DB fixture.")

**`tests/unit/test_composition_root.py`** — analog `app/main.py create_app` (lines 64–74):
```python
def test_create_app_smoke(monkeypatch) -> None:
    """create_app() returns a wired FastAPI with the real providers."""
    app = create_app()
    assert app.title == "Dojo"
    # Further assertions: provider factories instantiate; env-gated if LLM.
```

---

## Shared Patterns

### ABOUTME header (every new Python file, both source & tests)

**Source:** `app/infrastructure/db/session.py` lines 1–3; `tests/conftest.py` lines 1–3; every other Python file in the repo.

**Pattern:**
```python
# ABOUTME: <One-line purpose, present-tense verb.>
# ABOUTME: <One-line behavior qualifier — key constraint or invariant.>
"""<Module docstring (single line, no trailing period inside the quotes is project convention).>"""
```

**Apply to:** every new file in Phase 3.

---

### Logger (every new non-test Python module)

**Source:** `app/main.py` line 20; `app/logging_config.py` lines 58–68.

**Pattern:**
```python
from app.logging_config import get_logger
log = get_logger(__name__)
```

**Apply to:** every `app/infrastructure/*/*.py` file that might log (adapters, readers, fetchers, providers). Pure mappers + tool-schema constants skip the logger.

---

### Docstring / Sphinx convention

**Source:** `app/application/use_cases/generate_from_source.py` lines 22–70; `app/application/ports.py` lines 30–46.

**Pattern — one-line docstring + Sphinx blocks:**
```python
def save(self, source: Source) -> None:
    """Upsert the source row keyed by `source.id`.

    :param source: The `Source` entity to persist.
    :raises SomeException: When <condition>.
    """
```
- Single backticks (not double) around identifiers (per auto-memory note Apr 23).
- `:param:` / `:returns:` / `:raises:` only for public methods.
- Interrogate enforces 100% (Phase 1 D-15); pydoclint enforces `:param:` shape.

**Apply to:** every public method on Phase 3 adapters. Private methods (`_sdk_call`, `_parse_and_validate`) get one-line docstrings only.

---

### Exception-wrap pattern (infra catches third-party, raises app-layer types)

**Source:** `app/application/extractor_registry.py` lines 37–55 (`_missing_error`) — local precedent for "wrap low-level into domain-meaningful".

**Pattern:**
```python
try:
    ...
except ThirdPartyError as e:
    raise DomainException(f"{context}: {e}") from e
```
- `from e` (preserve cause chain).
- Message carries human-readable context (path, url, status code).
- Domain exception types live in `app/application/exceptions.py`.
- **No silent fallback** (spec §6.4 / CONTEXT canonical_refs).

**Apply to:** `read_file`, `fetch_url`, all `anthropic_provider.generate_*` outer boundary; each SQL repo leaves SQL errors unwrapped (the use case / Phase 4 error boundary handles `session.begin()` rollback).

---

### Protocol conformance (structural subtyping)

**Source:** CONTEXT line 459–461, `tests/fakes/*` — no explicit inheritance, shapes alone satisfy.

**Pattern:**
```python
# NO: class SqlSourceRepository(SourceRepository): ...
# YES:
class SqlSourceRepository:
    """Sync SQL adapter for SourceRepository Protocol."""
    def __init__(self, session: Session) -> None: ...
    def save(self, source: Source) -> None: ...
    def get(self, source_id: SourceId) -> Source | None: ...
```
- `ty` typechecker verifies shape match against `app.application.ports.SourceRepository`.
- **Never import the Protocol into the infra file** except in `if TYPE_CHECKING:` blocks for docstring references.

**Apply to:** all seven Phase 3 adapters.

---

### Import idiom (standard project convention)

**Source:** every file in `app/`. Representative: `app/infrastructure/db/session.py` lines 1–10; `app/domain/entities.py` lines 1–18.

**Order:**
1. Two `# ABOUTME:` lines.
2. Module docstring.
3. `from __future__ import annotations`.
4. Stdlib imports.
5. Third-party imports.
6. `app.*` imports.

**Apply to:** every new Python file.

---

### File-size rule (CLAUDE.md)

**≤ 100 lines preferred; split at 150 hard limit.** Project skill.

**Apply to:** split plans accordingly. Notable candidates for split:
- `mappers.py` → per-entity files if >100 lines.
- `anthropic_provider.py` → `anthropic_provider.py` + `tool_schema.py` + `_exceptions_map.py` (anticipated in RESEARCH line 245–248).

---

### Import-linter boundaries (live via Plan 02-05)

**Source:** CONTEXT line 506–511; project docs.

**Rule:** every Phase 3 file lands in `app.infrastructure.*`. Imports go *into* infra freely; infra is never imported by domain or application. Any new import that crosses these boundaries will be rejected at `make check`.

**Apply to:** sanity-check all new imports; specifically, `app.application.exceptions` is the canonical home for new exception types — infra imports these, not vice versa.

---

## Files with No Analog

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `app/infrastructure/llm/tool_schema.py` | Static JSON schema constant | data | No existing tool-schema / grammar definitions in codebase. RESEARCH.md §B.2 is the verbatim source. |
| `app/infrastructure/fetchers/url_fetcher.py` | HTTP + extraction adapter | request-response | No codebase precedent for outbound HTTP. RESEARCH.md §D is the verbatim source. |
| `tests/integration/test_anthropic_retry_count.py` (+ `test_anthropic_provider.py`) | respx-stubbed LLM integration | test | No prior respx usage in codebase; respx is a new dep. RESEARCH.md §B.3 snippet is the template. |
| `tests/integration/test_url_fetcher_paywall.py` | respx-stubbed HTTP integration | test | Same respx-new-dep reason. |

For these files the **planner falls back to RESEARCH.md snippets**, which are copy-editable. No in-codebase pattern is being violated — they're simply new capabilities.

---

## Pattern Summary

| New File | Analog | Reuse Strategy |
|----------|--------|---------------|
| `db/models.py` | `domain/entities.py` shape + `db/session.py` `Base` | adapt (annotate with `Mapped[...]`) |
| `db/mappers.py` | RESEARCH §A snippet | copy verbatim |
| `repositories/sql_source_repository.py` | `fakes/fake_source_repository.py` signatures + RESEARCH §A body | adapt (replace dict with session.merge/get) |
| `repositories/sql_note_repository.py` | `fakes/fake_note_repository.py` + §A | adapt (merge on save) |
| `repositories/sql_card_repository.py` | `fakes/fake_card_repository.py` + §A | adapt (**add** not merge) |
| `repositories/sql_card_review_repository.py` | `fakes/fake_card_review_repository.py` + §A | adapt (no get method) |
| `llm/anthropic_provider.py` | `fakes/fake_llm_provider.py` signature + RESEARCH §B | new + signature-copy |
| `llm/tool_schema.py` | RESEARCH §B.2 | copy verbatim |
| `drafts/in_memory_draft_store.py` | `fakes/fake_draft_store.py` + RESEARCH §C | adapt (add clock/TTL) |
| `readers/file_reader.py` | RESEARCH §E | copy verbatim |
| `fetchers/url_fetcher.py` | RESEARCH §D | copy verbatim |
| `application/exceptions.py` (extend) | existing file lines 1–29 | extend with same pattern |
| `migrations/versions/0002_*.py` | `0001_initial.py` header | autogen body + header-copy |
| `migrations/env.py` (modify) | self | one-line addition |
| `app/main.py` (modify) | self | extend `create_app` with provider factories |
| `pyproject.toml` | self | dep-list edits |
| 7 × `tests/contract/test_*_contract.py` | `test_llm_provider_contract.py` | copy template, replace fake/real branch |
| `tests/integration/test_sql_repositories_atomic.py` | `conftest.py` session fixture + RESEARCH §A rollback snippet | fixture consume + new test |
| `tests/integration/test_sql_repositories_regenerate.py` | same fixture + `NoteRepository`/`CardRepository` contract | fixture consume |
| `tests/integration/test_anthropic_retry_count.py` | RESEARCH §B.3 snippet | copy verbatim |
| `tests/integration/test_anthropic_provider.py` | RESEARCH §B.4 + exception-wrap table | copy verbatim |
| `tests/integration/test_url_fetcher_paywall.py` | RESEARCH §D snippet | copy verbatim |
| `tests/integration/test_file_reader.py` | `tmp_path` + RESEARCH §E | stdlib-fixture + wrap assertions |
| `tests/integration/test_draft_store_concurrency.py` | RESEARCH §C asyncio.gather snippet | copy verbatim, add pytest-repeat |
| `tests/integration/test_alembic_round_trip.py` | `conftest.py` `_alembic_cfg` + `command.upgrade/downgrade` | fixture consume |
| `tests/integration/test_alembic_metadata.py` | `env.py` import shape | 5-line assertion |
| `tests/unit/test_mappers.py` | RESEARCH §A mapper snippet | pure round-trip |
| `tests/unit/test_composition_root.py` | `app/main.py create_app` | smoke: app title + provider factories instantiate |

---

## Metadata

**Analog search scope:** `app/`, `tests/`, `migrations/`, `.planning/` — all canonical analogs were found in Phase 1 + Phase 2 artifacts.
**Files scanned (Read):** `app/infrastructure/db/session.py`, `app/domain/entities.py`, `app/domain/value_objects.py`, `app/domain/exceptions.py`, `app/application/ports.py`, `app/application/dtos.py`, `app/application/exceptions.py`, `app/application/extractor_registry.py`, `app/application/use_cases/generate_from_source.py`, `app/main.py`, `app/settings.py`, `app/logging_config.py`, `tests/fakes/*.py` (6 files), `tests/contract/test_llm_provider_contract.py`, `tests/conftest.py`, `migrations/env.py`, `migrations/versions/0001_initial.py`, plus the phase's CONTEXT + RESEARCH. No re-reads.
**Pattern extraction date:** 2026-04-24

---

## PATTERN MAPPING COMPLETE
