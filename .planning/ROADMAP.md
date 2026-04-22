# Roadmap: Dojo

## Overview

Dojo ships a local tech interview-prep study app whose core loop is
generate → review → drill → learn. The roadmap is ordered spine-first
bottom-up per ARCHITECTURE.md §6: a grounded tooling scaffold, then the
pure domain + application spine against fakes, then the infrastructure
adapters that satisfy the ports, then the three user-facing flows
(Generate/Review/Save, Drill, Read/Manage) stacked outside-to-inside in
user-value order, then a closing docs + E2E phase that locks the
architecture story and the regression net in place. Every phase-entry
gate from PITFALLS.md (async Alembic, pytest-asyncio event loop, fake
drift contract tests, draft-store concurrency, drill animation timing)
is baked into the phase it belongs to rather than deferred to a
generic "polish" bucket.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Project Scaffold & Tooling** (completed 2026-04-21) - Boring-but-correct Python project foundation: uv, ruff, ty, interrogate, pytest-asyncio, async Alembic, pre-commit, GitHub Actions CI, structlog, settings
- [ ] **Phase 2: Domain & Application Spine** - Pure domain entities, application ports (incl. DraftStore Protocol), DTOs, and GenerateFromSource use case (TOPIC kind) driven end-to-end by hand-written fakes
- [ ] **Phase 3: Infrastructure Adapters** - Real adapters behind every port: SQLAlchemy repos with mappers, Anthropic provider with tenacity retries and DTO validation, InMemoryDraftStore with TTL + lock, FILE reader, URL fetcher with paywall guards
- [ ] **Phase 4: Generate → Review → Save Flow** - FastAPI skeleton + lifespan + deps.py wired to real infra; Generate/Review/Save routes for FILE, URL, and TOPIC sources with atomic persistence
- [ ] **Phase 5: Drill Mode** - Drill start page with session cap, card-by-card keyboard/click UX with sanitized markdown rendering and swipe animation, CardReview log, end-of-session summary
- [ ] **Phase 6: Read Mode & Card Management** - Source list with tag filter, Source detail page with rendered note and linked cards, post-save card edit/delete flows
- [ ] **Phase 7: Documentation & End-to-End Coverage** - Four Mermaid architecture diagrams, repo root CLAUDE.md, Playwright happy-path E2E tests with FakeLLMProvider, make check green at >90% coverage with pristine output

## Phase Details

### Phase 1: Project Scaffold & Tooling
**Goal**: A freshly-cloned Dojo repo boots end-to-end through `make install && make check && make run` with every quality gate configured, CI green on the empty skeleton, and the async-infrastructure footguns (async Alembic template, pytest-asyncio event-loop config, import-linter boundaries, structlog, pydantic-settings) verified before any business code exists.
**Depends on**: Nothing (first phase)
**Requirements**: OPS-01, OPS-02, OPS-03, OPS-04, TEST-02, LLM-03
**Success Criteria** (what must be TRUE):
  1. `make install && make check` exits zero on a clean clone, with ruff clean, ty clean, interrogate at 100%, and an empty-but-running pytest suite with pristine output
  2. `make run` starts uvicorn on localhost:8000 and serves a minimal health/home route rendered through Jinja
  3. `alembic upgrade head` (run via `make migrate`) applies an async migration to a fresh aiosqlite DB and `sqlite3 dojo.db .schema` shows the expected tables
  4. A first pytest-asyncio integration test that opens a real async SQLite session runs 10 times in a row without event-loop flakes
  5. `pre-commit install` is wired into `make install`; a commit that violates ruff/ty/interrogate is blocked by the hook
  6. GitHub Actions CI runs `make check` on push/PR against Python 3.12 and goes green on the scaffold
  7. `ANTHROPIC_API_KEY` loads through pydantic-settings from `.env`; `.env.example` is checked in, `.env` is gitignored, and the key never leaves settings
  8. `structlog` is configured at app startup and every module obtains its logger via a shared `get_logger(__name__)` helper
**Plans**: 6 plans
  - [x] 01-01-project-bootstrap-PLAN.md — pyproject.toml + .gitignore + .env.example + CLAUDE.md reconcile
  - [x] 01-02-settings-logging-PLAN.md — app/settings.py (pydantic-settings + SecretStr) + app/logging_config.py (structlog)
  - [x] 01-03-database-alembic-PLAN.md — async SQLAlchemy session.py + async Alembic env.py + empty initial revision
  - [x] 01-04-web-routes-PLAN.md — app/main.py composition root + home/health routes + Jinja templates
  - [x] 01-05-test-infrastructure-PLAN.md — tests/conftest.py async fixtures + 4 Phase 1 tests (db_smoke, home, logging_smoke, settings)
  - [x] 01-06-tooling-ci-PLAN.md — Makefile + .pre-commit-config.yaml + .github/workflows/ci.yml

### Phase 2: Domain & Application Spine
**Goal**: The pure inner core of the app — domain entities, value objects, domain exceptions, application ports (Protocols + Callable aliases, including the DraftStore Protocol), Pydantic DTOs, and the GenerateFromSource use case for the TOPIC kind — exists and is fully driven by hand-written fakes at every DIP boundary, so the port shapes are locked before any adapter is written.
**Depends on**: Phase 1
**Requirements**: DRAFT-01, TEST-01, TEST-03
**Success Criteria** (what must be TRUE):
  1. `app/domain/` contains `Source`, `Note`, `Card`, `CardReview` dataclasses with `SourceKind` and `Rating` value objects, typed IDs, and domain exceptions — all importing only stdlib
  2. `app/application/ports.py` declares `LLMProvider`, `SourceRepository`, `NoteRepository`, `CardRepository`, `CardReviewRepository`, and `DraftStore` as `typing.Protocol`s, plus `UrlFetcher` and `SourceReader` as `Callable` aliases; none use `@runtime_checkable`
  3. The `GenerateFromSource` use case runs end-to-end for the TOPIC kind against `FakeLLMProvider`, `FakeDraftStore`, and fake repositories, producing a draft bundle that round-trips through the draft-store fake
  4. Hand-written fakes live under `tests/fakes/`, implement each Protocol by structural subtyping, expose assertable state (not call patterns), and are exercised by unit tests that use no `Mock()` behavior-testing
  5. A contract-test harness parameterised over `[FakeLLMProvider, AnthropicLLMProvider]` exists and is gated on `RUN_LLM_TESTS=1`; the Anthropic variant skips cleanly when the env var is unset, and the Fake variant runs on every `make check`
  6. `import-linter` (or equivalent) is configured so a test asserts that `app/domain/` and `app/application/` never import from `app/infrastructure/` or `app/web/`
**Plans**: 5 plans
  - [x] 02-01-domain-entities-PLAN.md — Domain entities, value objects, typed IDs, DojoError (stdlib-only; TDD per entity)
  - [x] 02-02-application-ports-dtos-PLAN.md — 6 Protocol ports + 2 Callable aliases + DraftToken + Pydantic/dataclass DTOs + app exceptions
  - [ ] 02-03-hand-written-fakes-PLAN.md — Seven hand-written fakes under tests/fakes/ (structural subtyping, no Mock())
  - [ ] 02-04-generate-from-source-use-case-PLAN.md — GenerateFromSource use case (TOPIC wired; FILE/URL raise UnsupportedSourceKind)
  - [ ] 02-05-contract-harness-import-linter-PLAN.md — TEST-03 parametrised harness + import-linter DIP boundary enforcement

### Phase 3: Infrastructure Adapters
**Goal**: Every port declared in Phase 2 has a real concrete adapter that passes both its own integration tests and the Phase 2 contract tests: SQLAlchemy ORM models + mappers + repositories (with eager loading and `expire_on_commit=False`), `AnthropicLLMProvider` (tenacity retries, DTO-validated tool-use output, wrapped exceptions), `InMemoryDraftStore` (TTL + `asyncio.Lock` + atomic `pop`), filesystem reader, and URL fetcher (trafilatura + paywall heuristics).
**Depends on**: Phase 2
**Requirements**: LLM-01, LLM-02, GEN-02, PERSIST-02
**Success Criteria** (what must be TRUE):
  1. Each repository implements its Protocol against a real aiosqlite tmp file; integration tests round-trip a `Source` with its `Note` and `Cards` and assert no `MissingGreenlet` on post-commit attribute access
  2. An integration test that forces the third insert in an atomic `Source + Note + Cards` transaction to fail asserts that none of the three persisted
  3. `AnthropicLLMProvider` validates tool-use output against a Pydantic DTO inside the adapter, raises `LLMOutputMalformed` on schema mismatch, retries once with a stricter prompt, and wraps SDK-specific exceptions (`RateLimitError`, etc.) into domain exception types
  4. `tenacity` is configured for exponential backoff up to 3 attempts on 429/5xx; a `respx`-stubbed test that returns 429 once then 200 observes exactly one retry and no SDK-level retry stacking
  5. `InMemoryDraftStore` satisfies its contract tests for 30-minute TTL eviction (via a fake clock), atomic `pop` under concurrent-save simulation, and two-coroutine same-token races where exactly one succeeds
  6. URL fetcher raises `SourceNotArticle` when extraction returns under the minimum-length threshold or matches the paywall heuristic; timeouts and non-2xx statuses surface as `SourceFetchFailed`
  7. Regenerating against an existing Source overwrites its Note row and appends new Card rows without touching existing Cards, verified by an integration test
**Plans**: TBD

### Phase 4: Generate → Review → Save Flow
**Goal**: Users can drive the full generation funnel through the web UI — pick FILE / URL / TOPIC, provide a user prompt, land on a review screen with editable note and per-card edit/reject controls, approve, and save — with everything persisted atomically only on explicit save, and nothing escaping the draft store without user action.
**Depends on**: Phase 3
**Requirements**: INGEST-01, INGEST-02, INGEST-03, GEN-01, GEN-03, PERSIST-01, CARD-01
**Success Criteria** (what must be TRUE):
  1. User can enter a local markdown/text file path, submit a generation form, and reach a review screen where the generated note and card candidates are visible and editable
  2. User can paste a URL, submit, and reach the same review screen with source text extracted via trafilatura (or see a readable error for paywalled/short extractions)
  3. User can type a topic and a user prompt with no source at all, submit, and reach the review screen with LLM-generated content
  4. The user prompt entered on generation is stored on the Source and echoed back in the review UI for reproducibility
  5. On the review screen, user can edit the note markdown, edit any card's question/answer/tags, reject individual cards, and click Save; nothing appears in the DB until Save is clicked
  6. On Save, Source + Note + approved Cards commit in a single async transaction; on any persistence failure, none of the three appear in the DB and the user lands back on a retry-capable review screen
  7. Each generated card inherits a default source-level tag that the user can override per card before saving
**Plans**: TBD
**UI hint**: yes

### Phase 5: Drill Mode
**Goal**: Users can start a drill session from a Source or a Tag with an optional session-size cap, reveal and rate cards keyboard-first (Space / ← / →) with mirroring on-screen buttons, watch each committed card animate off the deck on the correct side, and land on a summary screen — with every rating persisted to the `CardReview` log and all rendered Q&A content sanitized.
**Depends on**: Phase 4
**Requirements**: DRILL-01, DRILL-02, DRILL-03, DRILL-04, DRILL-05
**Success Criteria** (what must be TRUE):
  1. User can open a drill start page, filter by Source or Tag, choose a session size (10 / 25 / all), and start a drill whose deck reflects those choices
  2. During drill, each card displays the question rendered as sanitized markdown (code blocks, YAML, inline code); pressing Space (or tapping Show) reveals the answer, also sanitized markdown
  3. Pressing → or tapping ✓ commits a correct rating; pressing ← or tapping ✗ commits an incorrect rating; the card visibly slides off in the rated direction, and the next card appears in place without keyboard listeners double-firing
  4. Every rating appends a `CardReview` row with `is_correct` and `reviewed_at`; no existing card data is mutated
  5. After the last card, a summary screen shows correct/total and session duration computed from the review log
**Plans**: TBD
**UI hint**: yes

### Phase 6: Read Mode & Card Management
**Goal**: Users can navigate a saved Source library, open any Source's detail page to read its generated note as rendered markdown with linked cards and a "Drill these" entry point, and directly edit or delete any saved card (with delete confirmation) outside the pre-save review flow.
**Depends on**: Phase 5
**Requirements**: READ-01, READ-02, CARD-02, CARD-03
**Success Criteria** (what must be TRUE):
  1. User can list all saved Sources on a home/library page and filter the list by tag
  2. User can click a Source and land on a detail page that renders the note as sanitized HTML markdown, shows the original user prompt, lists linked cards, and offers a "Drill these" button that starts a drill scoped to that Source
  3. User can edit a saved card's question, answer, and tags from the Source detail page or a dedicated card view, and the edit persists
  4. User can delete a saved card from the same views; the action requires a confirmation step and is permanent, and the deleted card no longer appears in drill or detail views
**Plans**: TBD
**UI hint**: yes

### Phase 7: Documentation & End-to-End Coverage
**Goal**: The repo ships with the architecture story documented in Mermaid diagrams that render natively in GitHub and Obsidian, a concise `CLAUDE.md` that orients future Claude sessions in under 150 lines, and a Playwright E2E suite that exercises each flow end-to-end with a `FakeLLMProvider` so regressions on any user-visible path fail CI.
**Depends on**: Phase 6
**Requirements**: DOCS-01, DOCS-02
**Success Criteria** (what must be TRUE):
  1. `docs/architecture/` contains four Mermaid diagrams — layers, domain model, flows, ports↔adapters — and each renders cleanly on GitHub and in Obsidian without extra tooling
  2. Repo root `CLAUDE.md` is present, under 150 lines, and covers project purpose, layout pointer, run instructions, DIP boundary location, Protocol-vs-function rule, and test strategy summary
  3. Playwright E2E tests cover one happy path per flow (Generate → Review → Save, Drill, Read, Edit/Delete Card) with `FakeLLMProvider` injected via env var, and run green in CI
  4. Final `make check` passes with >90% coverage, pristine test output, ruff clean, ty clean, interrogate 100%
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Scaffold & Tooling | 0/6 | Not started | - |
| 2. Domain & Application Spine | 2/5 | In progress | - |
| 3. Infrastructure Adapters | 0/TBD | Not started | - |
| 4. Generate → Review → Save Flow | 0/TBD | Not started | - |
| 5. Drill Mode | 0/TBD | Not started | - |
| 6. Read Mode & Card Management | 0/TBD | Not started | - |
| 7. Documentation & End-to-End Coverage | 0/TBD | Not started | - |
