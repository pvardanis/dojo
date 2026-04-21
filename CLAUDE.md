# Dojo

<!-- GSD:project-start source:PROJECT.md -->
## Project

Dojo is a local-first tech interview-prep study app. It turns source
material (local markdown/text files, URLs, or topic prompts) into
studyable notes and Q&A cards using Anthropic Claude, then drills those
cards with a Bumble/Tinder-style swipe UX (arrow keys or on-screen
buttons).

**Authoritative context**: `.planning/PROJECT.md` (living summary) and
`docs/superpowers/specs/2026-04-18-dojo-design.md` (full design spec —
the source of truth for architecture and implementation detail).

**Core value**: generate → review → drill → learn. That loop must work.

**How to run**: `make install && make run` (spec §8.1). See `Makefile`
for the full target list once Plan 01-06 lands.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Python 3.12, async at the web tier, sync at the DB layer. See
`.planning/research/STACK.md` for version pins and known issues.

- **Web**: FastAPI (async) + Jinja2 + HTMX + Pico.css
- **DB**: SQLAlchemy 2.0 (sync) + SQLite (stdlib sqlite3) +
  Alembic (sync migrations)
- **LLM**: `anthropic` SDK, `tenacity` for retries
- **Content**: `trafilatura` + `httpx` (async URL extraction),
  `markdown-it-py` + `nh3` (markdown → sanitized HTML)
- **Config**: `pydantic-settings` (loads `ANTHROPIC_API_KEY` from `.env`)
- **Logging**: `structlog` (wraps stdlib logging)
- **Dev**: `uv`, `ruff` (79-char), `ty` (Astral), `interrogate` (100%)
- **Tests**: `pytest`, `pytest-asyncio` (route tests only), `respx`,
  Playwright (E2E)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Follows `~/Documents/Black Lodge/knowledge-base/wiki/python-project-setup.md`:

- File names snake_case. Files ≤100 lines (split if >150)
- Organize by domain/concern; one main function per file
- Every public module/class/function/method has a sphinx-style docstring
- `dataclasses` for containers; `Pydantic` only at validation boundaries
- `logging` with `log = logging.getLogger(__name__)` per module
  (structlog wraps this)
- Every Python file starts with two `# ABOUTME:` lines
- Custom exceptions live in a central `exceptions.py` per layer

**On Protocol vs function (project-local clarifier):** The wiki rule
"prefer Protocol over ABC" assumes you've already decided you need a
class-like abstraction. If a port is stateless and exposes one
operation, use a typed `Callable` alias (e.g.
`UrlFetcher = Callable[[str], str]`). Reach for `typing.Protocol` only
when the abstraction has state, multiple related methods, or clear
growth pressure. In Dojo: `LLMProvider` + all repositories + `DraftStore`
are Protocols; `UrlFetcher` and `SourceReader` are Callables.

**TDD is mandatory.** Red → green → refactor. Tests use hand-written
fakes at every DIP boundary; no `Mock()` for behavior testing. Test
output must be pristine.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Four layers, dependencies flow inward only:

```
Presentation (FastAPI + Jinja + HTMX)  ──▶
Application  (use cases + ports)        ──▶
Domain       (entities + VOs + rules)   ◀──
Infrastructure (SQLAlchemy + Anthropic + httpx + fs) ──▶
```

- **Domain** — pure Python, stdlib only
- **Application** — use cases and Protocol/Callable ports (DIP lives
  in `app/application/ports.py`)
- **Infrastructure** — SQL repos, Anthropic provider, file/URL adapters,
  `InMemoryDraftStore`
- **Presentation** — FastAPI routes, Jinja templates, HTMX partials

**Composition root**: `app/main.py` (the only module that wires all
layers). Swapping LLM provider = new class + one line in the root.

**Full details**: `docs/architecture/` (Mermaid diagrams — layers, domain
model, flows, ports↔adapters) and `docs/superpowers/specs/2026-04-18-dojo-design.md`.

**Ports summary**:
- Protocols: `LLMProvider`, `SourceRepository`, `NoteRepository`,
  `CardRepository`, `CardReviewRepository`, `DraftStore`
- Callable aliases: `UrlFetcher`, `SourceReader`
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to `.claude/skills/<name>/SKILL.md`
if domain-specific guidance emerges during implementation.
<!-- GSD:skills-end -->

## PR Shape

**Every change to `main` goes through a pull request.** No direct
pushes, regardless of category (code / docs / tooling / rebrand /
housekeeping). Enforced by GitHub branch protection on `origin/main` —
`git push origin main` will fail; the path is branch → push → PR →
merge.

**During phase execution: one PR per plan, not per phase.**
- Branch name: `phase-{X}-plan-{YY}-{slug}`
  (e.g. `phase-02-plan-01-domain-entities`)
- Scope: the commits for that plan + its `SUMMARY.md`
- Open the PR when the plan's `SUMMARY.md` is committed
- Wait for CI + merge before starting the next plan
- **Exception**: if two plans in the same wave can only ship together
  (tight coupling that would break CI mid-wave), bundle them into one
  PR and name the branch `phase-{X}-wave-{N}-{slug}`

**Outside phase execution** (docs updates, one-off fixes, rebrand,
housekeeping): per-topic PRs.
- Branch name: `topic/{slug}` or `chore/{slug}` or `fix/{slug}`
- One coherent change per PR
- Same rule: no direct pushes regardless of how trivial the change
  seems

**Rationale**: Dojo is public + showcase. PRs 200-400 LOC are the
review sweet spot; 2000+ LOC bundles (like Phase 1) get rubber-stamped
in practice. Per-plan granularity lands most plans at 70-300 LOC of
real code. Every PR also triggers CI, forces a "why" in the PR body,
and gives a rollback handle — direct pushes skip all of that.

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work
through a GSD command so planning artifacts and execution context stay
in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user
explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate the
> developer profile. This section is managed by
> `generate-claude-profile` — do not edit manually.
<!-- GSD:profile-end -->
