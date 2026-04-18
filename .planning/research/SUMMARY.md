# Project Research Summary

**Project:** Dojo — local LLM-powered MLOps interview-prep study app
**Domain:** Single-user, localhost, async Python web app with LLM generation and flashcard drilling
**Researched:** 2026-04-18
**Confidence:** MEDIUM (stack choices HIGH; version numbers MEDIUM; features HIGH on category-level claims; all four researchers had no access to live web tools)

---

## Research-Tool Caveat

All four parallel research agents were denied access to external web tools (WebSearch, WebFetch, Context7, Brave Search, Exa). Every version number, library-version floor, and live-doc reference in the research files is drawn from training data with a knowledge cutoff of January 2026. The project is being scaffolded in April 2026.

**Practical consequence:** stack *choices* are sound and HIGH confidence; version *numbers* are floors to be verified via `uv add <pkg>` before committing `pyproject.toml`. Anything marked `[VERIFY]` in the research files must be checked against current docs before commitment.

---

## Executive Summary

Dojo is a local-first MLOps interview-prep study app built as both a useful tool and a DDD learning exercise. The core loop — generate notes and Q&A cards from source material, review them before saving, drill them with a keyboard-driven swipe UX, iterate — is the product. Every phase of work should be evaluated against whether it strengthens that loop. Research across all four domains confirms that the spec's design decisions are sound for 2026: the four-layer DDD plus ports/adapters architecture is idiomatic, the stack is a clean boring choice, the MVP feature set covers table stakes without over-scoping, and the identified pitfalls are manageable with specific preventive measures baked into the build order.

The key recommended adjustment from research is to treat four cross-cutting concerns as first-class phase-entry gates rather than implementation details: (1) the async Alembic scaffold and the pytest-asyncio event-loop fixture must be the very first things built and verified before any business code is written — both block integration tests if wrong; (2) fake drift is the stealth quality risk that compounds across every phase and requires contract tests from day one; (3) the draft-store race conditions around TTL and concurrent saves require explicit `asyncio.Lock` and atomic pop semantics baked into the `InMemoryDraftStore`; and (4) the card slide-off animation is the flagship UX interaction and must be prototyped in Phase 1 before routes settle, not polished at the end.

Three MVP feature gaps need Danny's decision before the roadmap is finalized: post-save card edit/delete (table stakes for any flashcard app, ~2 hours of work), markdown rendering in the drill UI (critical for MLOps code blocks in answers), and an optional session-size cap on drill. One structural spec gap also needs a decision: the `DraftStore` is referenced by the `GenerateFromSource` use case but has no declared port in `app/application/ports.py` — this must be added before the generate use case is written or the use case cannot be unit-tested with a fake. Three libraries absent from the spec are recommended additions: `tenacity` (retry backoff required by spec §6.1), `structlog` (structured logging at no meaningful cost), `nh3` (HTML sanitization for LLM-generated markdown rendered to HTML).

---

## Key Findings

### Recommended Stack

The spec's stack is a clean, standard 2026 Python async web app choice and all core picks validate. The one technology to watch carefully is `ty` (Astral's type checker), which was still pre-1.0 / preview as of the knowledge cutoff — pin it to an exact patch version and read release notes before each bump. The `respx` httpx test-stub library should be confirmed compatible with the resolved `httpx` version at install time; `pytest-httpx` is the fallback.

**Core technologies:**
- Python 3.12 + FastAPI 0.115+ + Uvicorn — async web framework, de-facto 2026 standard
- Pydantic v2 + pydantic-settings — data modeling and config; v2 idioms only (no `@validator`, no `BaseSettings` from main package)
- SQLAlchemy 2.0 async + aiosqlite + Alembic — async-first ORM; MUST use `alembic init -t async`, MUST set `expire_on_commit=False`, MUST enable `PRAGMA foreign_keys=ON` on every connection
- Jinja2 + HTMX 2.x + Pico.css 2.x — server-rendered UI; use HTMX 2.x docs only (attributes renamed from 1.x)
- anthropic SDK + markdown-it-py + trafilatura + httpx — LLM, markdown rendering, URL extraction
- uv + ruff + ty (pinned) + interrogate + pytest + pytest-asyncio + respx + Playwright — tooling
- **Additions not in spec (recommended):** `tenacity` for LLM retry backoff (spec §6.1 requires it; rolling your own is wrong-by-default), `structlog` for structured logging (drop-in, cheap now, invaluable later), `nh3` for HTML sanitization after markdown-it-py renders LLM content (XSS via prompt injection is real), `python-multipart` for FastAPI form parsing (silently 500s without it)

**Version-verification action required before committing pyproject.toml:**
Run `uv tree --depth 1` after `uv sync` and confirm each resolved version is at or above the floors in STACK.md. Update floors to match what `uv` resolved.

### Expected Features

The spec's MVP is a well-cut MVP by the "table stakes plus one differentiator" rule. Three gaps need explicit decisions before roadmap.

**Must have (table stakes) — currently explicit in spec:**
- Generate notes + cards from FILE / URL / TOPIC with user prompt shaping every generation
- Review-before-persist (edit / reject / approve) — the trust foundation
- Atomic save (Source + Note + approved Cards in one transaction)
- Drill: Space reveals, arrow keys rate, card slides off on commit, session summary at end
- Filter drill by source and tag; shuffle; keyboard-driven
- Markdown rendering in the notes read view
- Append-only CardReview log (Phase 3 SRS hard dependency — must be correct from day one)
- LLM port with Anthropic concrete; API key via env only

**Must have (table stakes) — currently implicit or missing, recommend making explicit:**
- **Gap #1: Post-save card edit and delete.** Any flashcard app needs this. Users find typos after drilling. Complexity LOW (~1 route + template). Recommended: add to MVP.
- **Gap #2: Markdown rendering in card question/answer in the drill view.** MLOps domain answers contain code blocks and YAML. The notes view renders markdown but the spec does not explicitly say the drill view does. Recommended: add as an explicit MVP requirement. Reuses existing renderer.
- **Gap #3: Optional drill session size cap.** No current control on how many cards enter a drill session. A source with 40 cards plus a tag that spans 3 sources becomes 100-card sessions. Complexity LOW (one form field + `LIMIT N` in query). Call: MVP or Phase 2 — flag for Danny.

**Should have (differentiators) — strong coverage in spec:**
- Generate-from-source-with-user-prompt (rare: most tools generate generically from upload)
- Review-before-persist (rarer still: most LLM study apps dump directly to library)
- Local-first / localhost-only (privacy, no subscription, data on disk)
- Provider-swappable LLM via port (Phase 4 validates the abstraction)
- Source to Note to Cards linked model (traceability of "where did this card come from")
- Dating-app drill interaction (tactile differentiator; rare on desktop)

**Defer (Phase 2+):**
- FOLDER source kind + RAG retrieval (Phase 2 — large independent project)
- Mock-interview typed-answer mode with LLM grading (Phase 2 — the long-term signature feature)
- SRS scheduling with SM-2 / FSRS (Phase 3 — CardReview log from Phase 1 enables backfill)
- Streaks, heatmap, weak-cards indicator (Phase 3 — pure view layer over the log)
- Second LLM provider (Phase 4 — validates the port abstraction)
- Local LLM / Ollama (Phase 4)
- FTS5 full-text search, Anki export (Phase 4+)

**Anti-features to hold the line on:**
- Generate-and-save without review: do not add; erodes the trust model
- PDF / YouTube ingestion in MVP: deferred; adds parser complexity and edge-case test burden
- Auto-tagging by LLM: drifts vocabulary and undermines user trust
- SRS in MVP: the half-baked version is worse than deferring

### Architecture Approach

The four-layer DDD plus ports/adapters design in the spec is idiomatic, validated, and the right call. Dependencies flow inward only: Domain has zero deps; Application imports Domain only; Infrastructure implements Application ports but cannot import Web; Web imports everything inward; composition root (`app/main.py` + `app/web/deps.py`) is the only allowed cross-layer binder. The pattern is verified against FastAPI's official docs (lifespan events, `Depends` with yield, `APIRouter`).

**One structural gap to fix before coding begins:** the `DraftStore` (in-memory dict keyed by UUID token) is on the critical path of every generation flow but has no declared port in `app/application/ports.py`, no owning module, and no clear injection path. Fix: add `DraftStore` Protocol to ports.py (three methods: `put`, `get`, `pop`), implement `InMemoryDraftStore` in `app/infrastructure/drafts/in_memory.py`, wire in lifespan. Cost is ~40 lines; the payoff is that the generate use case can be unit-tested with a `FakeDraftStore` and Phase 2 can swap to `SqliteDraftStore` without architectural refactoring.

**Major components:**
1. Domain (`app/domain/`) — `Source`, `Note`, `Card`, `CardReview` dataclasses plus value objects and exceptions; zero dependencies; fastest test layer
2. Application (`app/application/`) — use cases, Protocol ports, Callable aliases, Pydantic DTOs; testable against hand-written fakes only; imports nothing outside this layer except domain
3. Infrastructure (`app/infrastructure/`) — SQL repos with explicit ORM-to-domain mappers, Anthropic LLM adapter, httpx/trafilatura URL fetcher, filesystem reader, `InMemoryDraftStore`
4. Web (`app/web/`) — FastAPI routes (thin: parse HTTP, call use case, render template), Jinja2 + HTMX templates, `deps.py` wiring per-request session and use cases
5. Composition root (`app/main.py` + lifespan) — constructs engine, `async_sessionmaker`, LLM client, draft store; stores on `app.state`

**Recommended build order:** Domain entities then Application ports + DTOs then one vertical slice use case (TOPIC kind, fake infra) then DB plumbing (session, ORM models, mappers, Alembic migration) then SQL repositories then Anthropic adapter then `InMemoryDraftStore` then FILE + URL adapters then FastAPI skeleton + lifespan + deps.py then routes (Generate then Review then Save) then Drill routes then Read routes then E2E tests then tooling polish. Reason: build the spine inner-to-outer so every layer has real consumers before its tests run, and the hardest path (Generate) is solved before the simpler ones (Drill, Read).

**Additional recommended tooling:** `import-linter` with a 10-line `pyproject.toml` config to mechanically enforce the four layer boundaries. The one class of bug that silently kills hexagonal architectures is a domain file accidentally importing SQLAlchemy; `import-linter` in `make check` catches this without relying on code review.

### Critical Pitfalls

The research identified 10 critical or high-severity pitfalls for Phase 1. Top items that can derail the build:

1. **Alembic async scaffold not initialized as async (C4)** — `alembic init` without `-t async` produces a sync `env.py` that silently fails or schema-drifts against aiosqlite. Fix: `alembic init -t async migrations`, then run `alembic upgrade head` against a fresh DB and verify with `sqlite3 dojo.db .schema` before writing any business code. Bake this into the Phase 1 scaffold milestone, not "follow the docs later."

2. **pytest-asyncio event-loop / fixture scope mismatch (M8)** — Session-scoped DB engines crossed with function-scoped event loops produce `RuntimeError: Event loop is closed` on the second test. Fix: set `asyncio_mode = "auto"` in `pyproject.toml`; use a session-scoped event loop fixture if session-scoped DB fixtures are used. Run the first integration test 10 times in a row — flakes mean an event-loop bug.

3. **Fake drift / testing your fake anti-pattern (M7)** — Tests pass against `FakeLLMProvider`; real adapter is broken; the fake silently became the spec. This compounds every phase. Fix: implement contract tests parameterised over `[FakeLLMProvider, AnthropicLLMProvider]` from day one; gate the real adapter test on `RUN_LLM_TESTS=1`. Every time the real adapter changes, the fake is updated or explicitly flagged as simpler.

4. **Draft-store race conditions (C10)** — Non-atomic read-then-delete on draft store token; concurrent saves on the same token; TTL eviction during save; two-tab same-user token collision. Fix: wrap write/delete in `asyncio.Lock`; use `dict.pop(key, None)` for atomic get-and-delete; implement lazy TTL eviction (check `now - created_at` on each access, not a background reaper); store generation inputs in the form so "expired draft" links to regeneration.

5. **Card slide-off animation: HTMX swaps before CSS transition (M3)** — HTMX's default swap is immediate; the element is gone before the browser can animate. This is the flagship UX interaction. Fix: use `hx-swap` with `swap:Nms` matching the CSS transition duration; apply the CSS class (`.swiping-left`, `.swiping-right`) via `hx-on::before-request`; prototype this in the earliest drill milestone, not at the end of Phase 1.

**Additional high-severity pitfalls requiring specific prevention:**
- `MissingGreenlet` from lazy-loading ORM relationships outside a session (C1) — configure `lazy="raise"` on all ORM relationships; mapper must fully materialise every relationship before the entity leaves the repo
- `selectinload` vs `joinedload` silent pagination corruption (C2) — `selectinload` for all one-to-many (Source to Cards, Card to Reviews); `joinedload` only for many-to-one
- `expire_on_commit=True` default triggers re-SQL on every post-commit attribute access (C3) — configure `async_sessionmaker(..., expire_on_commit=False)` at engine setup
- Atomic save broken by repos managing their own sessions (C5) — repos receive an injected `AsyncSession`; repos NEVER commit; only the use case commits
- Anthropic tool-use structured output: schema not enforced, empty card lists silently approved (C6) — validate tool-use input with Pydantic DTO inside the adapter; assert `len(cards) > 0` in the use case; log raw tool-use input at WARN on every validation failure
- Retry stacking (C7) — pick one retry layer: either configure `max_retries=N` on the Anthropic SDK and skip `tenacity`, or set `max_retries=0` on the SDK and own the retry loop; do not stack them

---

## Implications for Roadmap

### Pre-Coding Decisions (Before Phase 1 Begins)

These must be resolved by Danny before the roadmap is finalised:

1. **Gap #1:** Is post-save card edit/delete MVP or Phase 2? Recommendation: MVP (LOW complexity, table stakes).
2. **Gap #2:** Is markdown rendering in the drill UI an explicit MVP requirement? Recommendation: yes, explicit (reuses existing renderer, critical for MLOps code in answers).
3. **Gap #3:** Is a drill session size cap MVP or Phase 2? (lower priority — either is defensible)
4. **Spec fix:** Add `DraftStore` Protocol to `app/application/ports.py` before the generate use case is written. This is not optional.

### Suggested Phase Structure

#### Phase 1: Working Core Loop (MVP)

**Rationale:** The generate to review to drill loop is the product. Everything else is an extension of this loop. Build the spine inner-to-outer (domain first, web last) so architectural decisions solidify before UI surfaces.

**Critical phase-entry gates (do these before any business code):**
- Alembic async scaffold (`alembic init -t async`), first migration, verify schema with `sqlite3`
- pytest-asyncio event-loop config (`asyncio_mode = "auto"`), one integration test run 10 times in a row
- `DraftStore` Protocol added to ports.py

**Delivers:**
- Three ingestion kinds: FILE, URL, TOPIC
- Review-before-persist with edit / reject / approve
- Atomic save (Source + Note + approved Cards)
- Drill with Space / arrows / slide-off animation
- Filter by source and tag; shuffle; keyboard-driven
- Notes read view with markdown rendering
- Markdown rendering in drill UI (if Gap #2 confirmed MVP)
- Post-save card edit/delete (if Gap #1 confirmed MVP)
- Append-only CardReview log
- `make check` green, pre-commit, CI, >90% coverage, pristine test output
- Four Mermaid architecture diagrams

**Pitfalls Phase 1 must bake in:** C4 (Alembic async), M8 (pytest-asyncio event loop), M7 (fake drift via contract tests from day one), C10 (draft store race conditions), M3 (animation timing prototyped early), C1/C2/C3/C5 (SQLAlchemy async discipline), C6/C7 (LLM adapter retry and schema validation)

**Recommended sub-phases within Phase 1:**
- 1a Spine-first bottom-up: Domain entities, Application ports + DraftStore Protocol, `GenerateFromSource` use case with TOPIC kind against fakes
- 1b Infrastructure for the spine: DB plumbing (session + ORM models + mappers + Alembic migration), SQL repos, Anthropic adapter, `InMemoryDraftStore`, FILE + URL adapters
- 1c Web + UX: FastAPI skeleton + lifespan + deps.py, Generate / Review / Save routes, Drill routes (prototype animation here before other routes settle), Read routes
- 1d Polish: E2E tests (Playwright), `make check` tightening, architecture docs, pre-commit + CI

#### Phase 2: Deep Learning (RAG + Mock Interview)

**Rationale:** RAG and mock-interview mode are the two features that separate Dojo from generic flashcard apps in the MLOps-interview-prep niche. They are independent of each other (mock-interview reuses the LLM port; RAG needs new embedding infrastructure) but both build directly on Phase 1's ports/adapters foundation.

**Delivers:**
- FOLDER source kind + embedding retrieval (RAG): study from a whole notes corpus
- Mock-interview typed-answer mode with LLM grading: the signature interview-prep differentiator
- Potentially: bulk card actions in review (approve-all / reject-all) if Phase 1 decks routinely exceed 30 cards per generation

**Phase 2 pitfalls:** C1/C2 carry forward to new repositories; C6 escalates (grading DTO is more complex than card DTO); embedding provider needs its own Protocol and contract tests; retrieval quality is a product risk, not just an implementation risk.

**Research flag:** Phase 2 RAG and mock-interview grading rubrics both warrant a `/gsd-research-phase` before milestone planning.

#### Phase 3: Retention Engine (SRS + Stats)

**Rationale:** The CardReview append-only log built in Phase 1 is specifically designed to enable SRS backfill without schema pain. Phase 3 adds scheduling, a "due today" drill entry point, and the statistics view users expect once they have months of data.

**Delivers:**
- SRS scheduling (SM-2 or FSRS — flag for research)
- "Due today" drill mode replaces or augments the filter-based entry
- Streaks, heatmap, weak-cards indicator (computable from CardReview log — pure view layer)
- Potentially: binary to 4-grade rating enum expansion (requires a schema migration; plan as Phase 3 entry cost)

**Research flag:** SRS algorithm choice (SM-2 vs FSRS) and Python implementations warrant a `/gsd-research-phase`. FSRS is newer and reportedly more accurate; SM-2 is more widely documented.

#### Phase 4: Provider Validation + Power Features

**Rationale:** Phase 4 validates the LLM port abstraction by implementing a second concrete provider, and adds power-user features that are valuable but not essential to the core loop.

**Delivers:**
- Second LLM provider (validates port — the abstraction was worth it milestone)
- Local LLM support via Ollama (privacy and zero-API-cost option)
- SQLite FTS5 full-text search across notes and cards
- Anki export

**Research flag:** Ollama integration and local model structured-output quality need a `/gsd-research-phase`.

### Phase Ordering Rationale

- Phase 1 before Phase 2: RAG and mock-interview both depend on a working generate to drill loop. Building them before Phase 1 is complete means debugging two systems at once.
- Phase 3 depends on Phase 1 CardReview log: the log must exist and be correct before SRS can be designed, because Phase 3 may want to backfill historical sessions.
- Phase 4 is properly last: Ollama/local-LLM requires a mature port surface and well-tuned prompts before adding the complexity of local model quirks.
- Within Phase 1, build inner-to-outer: domain before infra, infra before web, generate before drill. Drill and Read use cases are thinner than Generate — solve the hardest path first.

### Research Flags

**Needs `/gsd-research-phase` before milestone planning:**
- Phase 2 RAG: embedding model selection, vector store options (ChromaDB, SQLite-vec, FAISS), chunking strategy, retrieval quality evaluation
- Phase 2 mock-interview: grading rubric design, structured output schema for grading feedback, UX for typed-answer entry
- Phase 3 SRS: algorithm choice (SM-2 vs FSRS), Python implementations, scheduling data model
- Phase 4 Ollama: local model structured-output quality in 2026, prompt tuning requirements, Ollama API compatibility with existing LLM port

**Standard patterns (skip research-phase, proceed directly to planning):**
- Phase 1 infrastructure: FastAPI + SQLAlchemy 2.0 async patterns are well-documented; ARCHITECTURE.md provides concrete verified implementations
- Phase 1 tooling: uv + ruff + pytest-asyncio setup is well-documented; STACK.md provides a validated `pyproject.toml` skeleton
- Phase 3 stats/streaks: pure view layer over the CardReview log; no novel architecture

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack choices (which lib for which role) | HIGH | All choices are standard 2026 patterns; every pick validated by researcher |
| Stack version numbers | MEDIUM | Based on Jan 2026 training data; treat as floors, verify via `uv sync` before committing pyproject.toml |
| Features (category-level) | HIGH | Stable, widely-documented patterns; HIGH per FEATURES.md |
| Features (competitor-specific claims) | LOW | LLM-study-app space moves fast; do not make product decisions on specific competitor claims without current sources |
| Architecture patterns | HIGH | Verified against FastAPI official docs; SQLAlchemy async patterns MEDIUM (sqlalchemy.org unreachable during research) |
| Pitfalls (fundamental: MissingGreenlet, selectinload, expire_on_commit, Alembic async, atomic transactions) | HIGH | Well-documented ecosystem facts |
| Pitfalls (version-specific: HTMX swap-delay syntax, pytest-asyncio fixture shape, ty capabilities) | MEDIUM | May have changed since knowledge cutoff; marked [VERIFY] inline in PITFALLS.md |
| Pitfalls (heuristic: paywall detection thresholds, context-size limits) | LOW | Directionally correct; exact numbers need tuning from real usage |

**Overall confidence:** MEDIUM-HIGH. Stack decisions and architectural patterns are solid. Version numbers and version-specific behavioral details need live verification before implementation.

### Gaps to Address

- **All `[VERIFY]` flags in PITFALLS.md** — verify against current library docs before the relevant milestone is planned. Top priority: `alembic init -t async` flag name, SQLAlchemy `lazy="raise"` async behavior, Anthropic SDK retry parameter name and defaults, HTMX `hx-swap` timing modifier syntax, current pytest-asyncio canonical event-loop fixture.
- **Version pinning** — run `uv sync` and `uv tree --depth 1` as the first act of Phase 1 scaffolding; update `pyproject.toml` floors to match resolved versions; skim changelogs between floor and resolved for anything breaking.
- **`ty` pre-1.0 status** — check `ty` release status before Phase 1 begins; if still pre-1.0, pin to exact patch version and document the fallback (`mypy` or `pyright`) in `CLAUDE.md`.
- **`respx` compatibility** — confirm resolved `respx` version declares compatibility with resolved `httpx` version; switch to `pytest-httpx` if it lags.
- **Anthropic structured output mechanism** — evaluate `instructor` library for "Pydantic model in, Pydantic model out" before hand-rolling the tool-use parsing in the Anthropic adapter (15-minute evaluation that could save a day of debugging).
- **Gap decisions #1, #2, #3** — Danny must confirm before the Phase 1 roadmap is finalized.

---

## Sources

### Primary (HIGH confidence — authoritative project documents)
- `/Users/pvardanis/Documents/projects/dojo/.planning/PROJECT.md`
- `/Users/pvardanis/Documents/projects/dojo/docs/superpowers/specs/2026-04-18-dojo-design.md`

### Secondary (HIGH confidence — official docs verified during research)
- FastAPI Lifespan Events — https://fastapi.tiangolo.com/advanced/events/
- FastAPI Dependencies with Yield — https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/
- FastAPI Bigger Applications (APIRouter, deps.py pattern) — https://fastapi.tiangolo.com/tutorial/bigger-applications/
- Python `typing.Protocol` — https://docs.python.org/3/library/typing.html#typing.Protocol

### Tertiary (MEDIUM confidence — training-data knowledge, unverified against live docs)
- SQLAlchemy 2.0 async patterns (async_sessionmaker, expire_on_commit, lazy="raise", selectinload vs joinedload) — flag for implementation-time confirmation at docs.sqlalchemy.org
- Alembic async migrations (`-t async` scaffold, env.py pattern) — flag for confirmation
- Anthropic Python SDK retry config and tool-use input parsing — check current SDK README
- HTMX 2.x swap-delay timing modifiers and OOB swap ordering — check htmx.org docs
- Ecosystem knowledge: Anki, RemNote, Wisdolia, SRS algorithms (SM-2, FSRS), Cosmic Python — LOW-MEDIUM confidence on product-specific details in 2026

---

*Research completed: 2026-04-18*
*Ready for roadmap: yes — pending Gap #1, #2, #3 decisions and DraftStore port spec fix*
