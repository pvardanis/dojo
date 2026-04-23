# Dojo — v1 Requirements

Full design context: `docs/superpowers/specs/2026-04-18-dojo-design.md`.
Project reference: `.planning/PROJECT.md`.

Each requirement is user-centric, atomic, and testable. Design-level
decisions (stack, layering, port shapes, prompt templates) live in the
spec — requirements here are what the user can do with Dojo v1.

---

## v1 Requirements

### Source ingestion

- [ ] **INGEST-01**: User can generate notes and cards from a single
      local file (markdown or text) by entering its path and a user
      prompt.
- [ ] **INGEST-02**: User can generate notes and cards from a URL; Dojo
      fetches the page, extracts the main article content via
      `trafilatura`, and uses that as source text.
- [ ] **INGEST-03**: User can generate notes and cards from a topic
      prompt alone (no source); the LLM draws on its own knowledge to
      produce the note and cards.

### Generation flow

- [ ] **GEN-01**: Every generation takes a user prompt describing what
      to learn (_"basic intro to k8s, skip RBAC and operators"_); the
      prompt is stored on the Source for reproducibility.
- [ ] **GEN-02**: The LLM returns a structured response producing both
      a note (markdown) and a list of Q&A card candidates; malformed
      output retries once with a stricter prompt, then surfaces the raw
      response with a readable error.
- [ ] **GEN-03**: Generation surfaces a review UI where the user can
      edit the note, edit each card's question/answer/tags, reject
      individual cards, then save; nothing persists to the DB until
      the user explicitly saves.

### Persistence and drafts

- [x] **DRAFT-01**: In-flight generated content lives in a `DraftStore`
      (Protocol port, in-memory concrete for MVP) keyed by a session
      token with a 30-minute TTL; expired or abandoned drafts are
      garbage-collected.
- [ ] **PERSIST-01**: On user save, Source + Note + approved Cards are
      committed in a single async transaction; failure rolls all three
      back.
- [ ] **PERSIST-02**: Regenerating notes for an existing Source
      overwrites the previous note; regenerating cards appends new
      candidates to the review UI without touching existing cards.

### Drill mode

- [ ] **DRILL-01**: User can start a drill session by choosing a Source
      (all its cards) or a Tag (cards with that tag across all
      Sources); before the session starts, they can cap its length
      (e.g. 10, 25, all).
- [ ] **DRILL-02**: During drill, the current card shows question only;
      pressing Space (or the "Show" button) reveals the answer.
- [ ] **DRILL-03**: User rates the answer with `→` (or the ✓ button)
      for correct and `←` (or the ✗ button) for incorrect; the card
      animates sliding off in the chosen direction and the next card
      appears. Each rating appends a `CardReview` row.
- [ ] **DRILL-04**: Card question and answer are rendered as markdown
      (code blocks, YAML, inline code); HTML output from markdown is
      sanitized with `nh3` before being injected into the DOM.
- [ ] **DRILL-05**: At the end of a drill session, a summary screen
      shows correct/total and session duration.

### Card management

- [ ] **CARD-01**: Cards carry a free-form list of tag strings;
      generation copies a default source-level tag onto each card, and
      the user can edit tags per card during pre-save review.
- [ ] **CARD-02**: User can edit a saved card's question, answer, and
      tags from the Source detail page or a dedicated card view.
- [ ] **CARD-03**: User can delete a saved card; deletion requires
      confirmation and is permanent.

### Read mode (notes and source detail)

- [ ] **READ-01**: User can navigate to a Source detail page that
      renders the note as HTML markdown (via `markdown-it-py` +
      `nh3`), shows the user prompt used to generate it, and lists all
      linked cards with a "Drill these" button.
- [ ] **READ-02**: User can list all saved Sources, filter by tag, and
      click through to any Source's detail page.

### LLM provider

- [ ] **LLM-01**: LLM access goes through a `LLMProvider` Protocol
      port; the MVP ships one concrete, `AnthropicLLMProvider`, using
      the official SDK. Swapping to another provider = adding a new
      class and changing one line in the composition root.
- [ ] **LLM-02**: The Anthropic provider uses `tenacity` for
      exponential-backoff retries on rate-limit and transient errors
      (max 3), and surfaces terminal failures as typed domain
      exceptions with actionable error messages.
- [ ] **LLM-03**: The Anthropic API key is loaded from the
      `ANTHROPIC_API_KEY` environment variable via
      `pydantic-settings`; it never touches the DB or the UI. The repo
      ships a `.env.example`; `.env` is gitignored.

### Operations and dev tooling

- [ ] **OPS-01**: Repo includes a Makefile with `install`, `format`,
      `lint`, `typecheck`, `docstrings`, `test`, `check`, `run`, and
      `migrate` targets. `make check` runs `format + lint + typecheck
      + docstrings + test`. No `db-reset` target.
- [ ] **OPS-02**: `pre-commit` runs `make check` on every commit;
      `pre-commit install` is part of `make install`.
- [ ] **OPS-03**: GitHub Actions CI runs `make check` on push and PR;
      single job on Python 3.12.
- [ ] **OPS-04**: Structured logging via `structlog` is configured at
      app startup; every module gets a logger via the standard
      `get_logger(__name__)` pattern.

### Tests

- [x] **TEST-01**: Test pyramid with hand-written fakes at every port
      boundary: unit tests (domain + use cases, fakes only),
      integration tests (real SQLite tmp + real filesystem +
      `respx`-stubbed HTTP), E2E tests (Playwright with a
      `FakeLLMProvider` injected so E2E doesn't burn tokens).
- [ ] **TEST-02**: `make check` exits zero with `ruff` clean, `ty`
      clean, `interrogate` at 100%, and `pytest` passing at >90%
      coverage; test output is pristine (no stray warnings or logs).
- [x] **TEST-03**: Contract tests parameterised over
      `[FakeLLMProvider, AnthropicLLMProvider]` guard against fake
      drift on every CI run; the AnthropicLLMProvider variant is
      opt-in via env var so CI doesn't hit the API by default.

### Documentation and project guide

- [ ] **DOCS-01**: `docs/architecture/` contains four Mermaid diagrams
      — layers, domain model, flows, ports↔adapters — each renders in
      GitHub and Obsidian without extra tooling.
- [ ] **DOCS-02**: Repo root `CLAUDE.md` explains project purpose,
      layout pointer (to `docs/architecture/` and `app/`), how to run
      (`make install && make run`), where the DIP boundaries are (at
      `app/application/ports.py`), the Protocol-vs-function clarifier
      (project-local copy), and the test strategy summary. ≤150 lines.

---

## v2 (Deferred)

Scoped and designed-for, but not shipping in v1.

- **RAG + Folder source (Phase 2)**: FOLDER source kind, `Retriever`
  and `EmbeddingProvider` ports, local `sentence-transformers`
  embeddings, SQLite + `sqlite-vec` vector store, folder indexer with
  mtime-based reindex, retrieval-quality evals.
- **Mock interview mode (Phase 2)**: paste job-ad → LLM generates
  tailored interview plan; drill mode with typed answers + LLM-as-judge
  grading.
- **Spaced repetition scheduling (Phase 3)**: SM-2 or FSRS; `Card`
  gains `ease_factor`, `interval`, `repetitions`, `next_review_at`;
  drill switches from "all filtered cards" to "cards due today"; data
  backfilled from the existing `CardReview` log.
- **Streaks, daily stats, heatmap (Phase 3)**: view-layer only, built
  on `CardReview`.
- **Additional LLM providers (Phase 4)**: OpenAI or Ollama to validate
  the port abstraction didn't leak.
- **Local LLM support via Ollama (Phase 4)**.
- **Full-text search via SQLite FTS5 (Phase 4+)**.
- **Anki export (Phase 4+)**.

---

## Out of Scope (explicit exclusions)

- **Multi-user / authentication** — Dojo is single-user local.
- **Server or cloud deployment** — localhost-only runtime.
- **Card versioning on regenerate** — overwrite notes, append cards;
  user prunes manually. Schema supports adding versioning later without
  migration pain.
- **Simultaneous multi-provider LLM shipping in v1** — port designed
  for it, but only Anthropic implemented.
- **`make db-reset` target** — deliberate foot-gun avoidance; `rm
  dojo.db && make migrate` is the manual reset path.
- **Real mouse-drag gesture on drill cards** — the Bumble/Tinder-style
  swipe feel is delivered via the commit animation, not an actual drag
  interaction. Phase 3 may revisit.
- **Image, LaTeX, or audio cards** — markdown-only cards; no rich
  media.
- **AI tutor free-form chat mode** — "just use Claude" is the
  fallback; Dojo's value is structured drill, not chat.

---

## Traceability

Requirements → phases, set by `ROADMAP.md`. Each v1 requirement maps
to exactly one phase.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGEST-01 | Phase 4 — Generate → Review → Save Flow | Pending |
| INGEST-02 | Phase 4 — Generate → Review → Save Flow | Pending |
| INGEST-03 | Phase 4 — Generate → Review → Save Flow | Pending |
| GEN-01 | Phase 4 — Generate → Review → Save Flow | Pending |
| GEN-02 | Phase 3 — Infrastructure Adapters | Pending |
| GEN-03 | Phase 4 — Generate → Review → Save Flow | Pending |
| DRAFT-01 | Phase 2 — Domain & Application Spine | Complete (Plan 02-03) |
| PERSIST-01 | Phase 4 — Generate → Review → Save Flow | Pending |
| PERSIST-02 | Phase 3 — Infrastructure Adapters | Pending |
| DRILL-01 | Phase 5 — Drill Mode | Pending |
| DRILL-02 | Phase 5 — Drill Mode | Pending |
| DRILL-03 | Phase 5 — Drill Mode | Pending |
| DRILL-04 | Phase 5 — Drill Mode | Pending |
| DRILL-05 | Phase 5 — Drill Mode | Pending |
| CARD-01 | Phase 4 — Generate → Review → Save Flow | Pending |
| CARD-02 | Phase 6 — Read Mode & Card Management | Pending |
| CARD-03 | Phase 6 — Read Mode & Card Management | Pending |
| READ-01 | Phase 6 — Read Mode & Card Management | Pending |
| READ-02 | Phase 6 — Read Mode & Card Management | Pending |
| LLM-01 | Phase 3 — Infrastructure Adapters | Pending |
| LLM-02 | Phase 3 — Infrastructure Adapters | Pending |
| LLM-03 | Phase 1 — Project Scaffold & Tooling | Pending |
| OPS-01 | Phase 1 — Project Scaffold & Tooling | Pending |
| OPS-02 | Phase 1 — Project Scaffold & Tooling | Pending |
| OPS-03 | Phase 1 — Project Scaffold & Tooling | Pending |
| OPS-04 | Phase 1 — Project Scaffold & Tooling | Pending |
| TEST-01 | Phase 2 — Domain & Application Spine | Complete (Plan 02-03) |
| TEST-02 | Phase 1 — Project Scaffold & Tooling | Pending |
| TEST-03 | Phase 2 — Domain & Application Spine | Complete (Plan 02-05) |
| DOCS-01 | Phase 7 — Documentation & End-to-End Coverage | Pending |
| DOCS-02 | Phase 7 — Documentation & End-to-End Coverage | Pending |

**Coverage:** 31 / 31 requirements mapped.

**Cross-cutting notes (tracked in the assigned phase's success criteria, not re-assigned):**
- TEST-03 contract tests are scaffolded in Phase 2 (where every port is first declared) and extended in Phase 3 as each new real adapter is introduced.
- M3 drill animation timing is a Phase 5 success-criterion concern (prototype early in the phase, not at the end).
- C10 draft-store race conditions are a Phase 3 success-criterion concern (atomic `pop`, `asyncio.Lock`, lazy TTL) even though DRAFT-01 (the Protocol port) is owned by Phase 2.
