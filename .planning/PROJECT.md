# Dojo

## What This Is

A local web app for MLOps interview prep. It turns source material
(Black Lodge wiki docs, URLs, raw text, or a topic prompt alone) into
studyable notes and Q&A cards, then drills those cards with a
dating-app-style swipe UX (arrow keys or on-screen buttons).

## Core Value

Generate Q&A cards from user-supplied source material, drill them
interactively, retain knowledge. If everything else fails, that loop —
generate → drill → learn — must work.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can generate notes + Q&A cards from a single FILE source
      (e.g. a Black Lodge `.md` wiki doc or raw pasted text)
- [ ] User can generate notes + Q&A cards from a URL (fetched, main
      content extracted)
- [ ] User can generate notes + Q&A cards from a TOPIC prompt alone
      (LLM's own knowledge, no source)
- [ ] Every generation is driven by a user prompt
      (e.g. _"give me basic intro notes for k8s, skip RBAC"_); LLM
      augments beyond the source
- [ ] User can review generated cards: edit, reject individually,
      approve — nothing persists until user saves
- [ ] Saved Source + Note + approved Cards are committed atomically
- [ ] User can drill saved cards: Space reveals, → correct, ← wrong,
      on-screen buttons mirror the arrows, card animates off on commit
- [ ] User can filter drill sessions by source or tag
- [ ] User can read saved notes rendered as markdown on a source-detail
      page, with linked cards and a "Drill these" button
- [ ] Free-form tags on cards; default-copied from source, editable per
      card
- [ ] User can edit or delete any saved card (not just during pre-save
      review) with confirmation on delete
- [ ] Card question and answer content rendered as markdown in drill
      mode (code blocks, YAML, commands); HTML output sanitized with
      `nh3`
- [ ] Drill start page lets user cap session length (e.g. 10 / 25 / all)
      before starting
- [ ] Card-review history persisted (append-only `CardReview` log)
- [ ] LLM provider abstracted via port; Anthropic is the one shipped
      concrete. Swapping = new class + one composition-root line
- [ ] API key via `.env` + pydantic-settings (env var only; no key in
      DB or UI)
- [ ] Test pyramid with hand-written fakes at DIP boundaries (no
      `Mock()` behavior-testing), >90% coverage, pristine test output
- [ ] `make check` passes: ruff + ty + interrogate (100%) + pytest
- [ ] Pre-commit hook runs `make check`; GitHub Actions CI runs
      `make check` on push/PR
- [ ] Four Mermaid architecture diagrams in `docs/architecture/`
      (layers, domain model, flows, ports↔adapters); render natively in
      GitHub and Obsidian
- [ ] Repo root `CLAUDE.md` explains layout and DIP boundaries

### Out of Scope

- **Folder-as-source + RAG** — deferred to Phase 2. The MVP
  single-file / URL / topic paths cover the core studying loop; RAG is
  a separate learning exercise in its own right (embeddings, chunking,
  vector store, retrieval quality evals).
- **Mock interview mode** (paste job ad → typed-answer drill with LLM
  as judge) — Phase 2.
- **Spaced repetition scheduling** (SRS: SM-2 / FSRS) — Phase 3.
  Review log exists from MVP so Phase 3 can backfill without schema
  pain.
- **Duolingo-style streaks, daily stats, heatmaps** — Phase 3. All
  computable from `CardReview`; pure view layer.
- **Multiple LLM providers shipped simultaneously** — Phase 4 if
  earned. Port designed for it; only Anthropic implemented in MVP.
- **Local LLM support (Ollama)** — Phase 4.
- **Multi-user, authentication** — local single-user app, not planned.
- **Full-text search across notes/cards** — Phase 4+.
- **Anki export** — Phase 4+.
- **Card versioning on regenerate** — not planned; regeneration
  overwrites notes and appends cards (user prunes in review step).
- **Server deployment / cloud hosting** — localhost-only, not planned.
- **No `make db-reset` target** — deliberate foot-gun avoidance; manual
  `rm dojo.db && make migrate` when needed.

## Context

- Built as both a study tool and a build exercise — design decisions
  favor interview-relevant patterns (DDD layering, DIP with
  Protocols/Callables, FastAPI async + sync DB via threadpool,
  structured LLM output) over
  shortcuts that ship faster but teach less.
- Content spine comes from an existing Black Lodge knowledge base at
  `~/Documents/Black Lodge/knowledge-base/` — already contains wiki
  docs on `kubernetes-patterns`, `docker-patterns`,
  `ml-systems-architecture`, `distributed-ml-patterns`,
  `ai-engineering`, `vllm-internals`, and more. App reads these as
  single-file sources in MVP.
- Development follows Python conventions from Black Lodge's
  `python-project-setup.md` wiki: `uv` package management, `ruff`
  formatting at 79-char line length, `ty` (Astral) type checking,
  `interrogate` at 100% docstring coverage, file sizes ≤100 lines
  (split if >150), dataclasses for containers, Protocols preferred over
  ABCs.
- Full design spec already written and committed at
  `docs/superpowers/specs/2026-04-18-dojo-design.md` (660 lines with
  Mermaid diagrams). PROJECT.md is a distilled view; the spec is
  authoritative on implementation details.
- TDD mandatory per global CLAUDE.md. Tests use hand-written fakes at
  DIP boundaries, never `Mock()` for behavior testing.

## Constraints

- **Tech stack**: Python 3.12, FastAPI (async), SQLAlchemy 2.0 (sync)
  + SQLite, Alembic (sync), Jinja2 + HTMX, Pico.css, anthropic SDK,
  trafilatura, httpx, markdown-it-py — locked per spec §4.2.
  DB layer intentionally sync: local-first single-user workload; the
  async-throughout call was reversed in Phase 1 review as overkill.
- **Dev tooling**: uv, ruff (79-char), ty (Astral), interrogate (100%),
  pytest + pytest-asyncio + respx, Playwright for E2E.
- **Secrets**: `ANTHROPIC_API_KEY` via env var loaded by
  pydantic-settings; never in DB or UI; `.env.example` checked in,
  `.env` gitignored.
- **Deployment**: localhost only. Single-user. No auth.
- **Architecture**: four layers with dependencies flowing inward only;
  each layer owns its own types (no cross-layer type imports); LLM
  provider and repositories behind Protocol ports, stateless I/O
  adapters behind `Callable` type aliases.
- **Quality gates**: `make check` must pass locally (pre-commit) and in
  CI (GitHub Actions) before merge.
- **Test discipline**: TDD (red-green-refactor), hand-written fakes at
  DIP boundaries, no mocks testing mock behavior, pristine test output,
  >90% coverage with quality over count.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Name: Dojo | Training-ground metaphor; short; non-Twin-Peaks so it doesn't overlap with Black Lodge knowledge base | — Pending |
| Stack: Python + FastAPI + HTMX + Pico | Matches the primary MLOps language; exercises real service patterns without drowning in frontend work | — Pending |
| Sync SQLAlchemy (reversed from async) | Originally async for learning-goal parity; Phase 1 review found it was overkill for a single-user SQLite app. Async stays at the web tier (FastAPI routes, httpx URL fetching, LLM client) — enough async surface for MLOps interview-relevance without the threadpool tax. | Reversed in Phase 1 |
| Pico.css (not Tailwind) | Classless, zero-build; UI is not a focus for MVP | — Pending |
| API key via env + `.env` via pydantic-settings | Industry-standard; keeps secrets out of domain/app layers; swappable to OS keychain later | — Pending |
| One LLM provider in MVP, port abstraction built in | Ship one concrete, design carefully; abstractions built without a second implementation often leak | — Pending |
| Drafts in-memory, DB writes only on user save | Avoids orphan rows; acceptable to lose drafts on backend restart | — Pending |
| Notes overwrite, cards append on regenerate | Notes are generated material (safe to lose); cards carry review history (safe to keep) | — Pending |
| Drill UX: Bumble/Tinder web pattern | Space reveals, ← wrong, → right (or click ✗/✓ buttons); card slides off on commit. No mouse-drag in MVP | — Pending |
| Stateless ports = `Callable` alias, stateful/multi-method = `Protocol` | Protocol-vs-function is separate from Protocol-vs-ABC; matches global CLAUDE.md functional-first rule | — Pending |
| Fakes, not mocks | Behavior-testing via hand-written fakes implementing the port — assertable state, not call patterns | — Pending |
| No `make db-reset` target | Foot-gun at the exact spot the DB-safety instinct says avoid; manual reset is sufficient | — Pending |
| DB-safety rule: Claude confirms before destructive ops during dev chats | Not a product UI rule; about Claude's actions during implementation | — Pending |
| Single-source-of-truth for design: spec at `docs/superpowers/specs/2026-04-18-dojo-design.md` | PROJECT.md is a distilled view; the spec is authoritative on implementation | — Pending |
| `DraftStore` is a first-class Protocol port (not an ad-hoc dict in a use case) | Research flagged the spec referenced drafts without a declared port; explicit port enables testing + future Redis/SQLite-backed swap | — Pending |
| `tenacity` for retry/backoff on LLM calls | Replaces hand-rolled exponential backoff with a battle-tested lib; matches spec §6.1 intent | — Pending |
| `structlog` for structured logging | Cheap to add up front; pays off in debugging and future observability; matches `python-project-setup.md` logging convention | — Pending |
| `nh3` for HTML sanitization of LLM-generated markdown | Required whenever we render LLM output as HTML (Read mode, drill markdown); security flag, not a nice-to-have | — Pending |
| Post-save card edit/delete in MVP | Table-stakes for flashcard apps; small code cost; avoids "why can't I fix my own cards" hole | — Pending |
| Markdown in drill Q&A (not just plain text) | MLOps questions include code/YAML/commands; `markdown-it-py` already a dep for notes; `nh3` sanitizes | — Pending |
| Session size cap on drill start | Prevents overwhelming 100+ card sessions; simple dropdown; aligns with daily-study UX | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-18 after initialization*
