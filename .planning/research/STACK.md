# Technology Stack

**Project:** Dojo — local LLM-powered MLOps interview study app
**Researched:** 2026-04-18
**Researcher scope:** validate the stack already chosen in
`docs/superpowers/specs/2026-04-18-dojo-design.md` §4.2; flag version risks
and gaps.

---

## Research-tool caveat (read first)

The research agent that produced this file was sandboxed: **Bash,
WebSearch, WebFetch, and Context7 CLI fallback were all denied at
runtime.** That means every version number below is drawn from training
data (knowledge cutoff January 2026) rather than a live check against
PyPI, GitHub Releases, or official changelogs on the research date
(2026-04-18).

**Implication for the implementer:**

- Treat every version in this document as a *floor* (known-good
  minimum), **not** a pin.
- Before committing `pyproject.toml`, run `uv add <pkg>` without a
  version and let `uv` resolve the current stable release, then pin
  what it picked.
- Any finding in the "Known-issue flags" sections marked **LOW**
  confidence MUST be re-validated against the library's current
  issue tracker before you rely on it.

Nothing in the stack *decisions* needs revisiting — the choices are
sound for 2026. The risk is purely in the version numbers.

---

## Overall verdict

The Dojo stack is a clean, boring, 2026-standard choice for a local
async Python web app with LLM integration. **All core picks validate.**
The only items that deserve a second look:

1. **`ty` (Astral's type checker)** — still pre-1.0 / preview as of
   knowledge cutoff. High project risk if it regresses on a breaking
   release. Fallback: swap to `mypy` or `pyright` with one line change.
2. **`respx`** is correct for `httpx`, but sanity-check it's still
   actively maintained — it's been slow-moving and `httpx` has shipped
   minor versions since.
3. **Structured LLM output** — the spec mentions "tool use" as the
   mechanism. As of late 2025, the Anthropic API also offers a
   first-class JSON mode / structured outputs via response schemas
   (available on Messages API). The adapter should prefer that over
   tool-use-as-JSON-shim where supported.
4. **Gaps:** `structlog` (structured logging), `tenacity` (retry logic
   for LLM and HTTP), and `bleach` or `nh3` (HTML sanitization for
   rendered markdown) are idiomatic and not in the spec. Recommend
   adding.

Everything else is correctly chosen. Details below.

---

## Recommended Stack

### Core framework

| Technology | Version floor | Purpose | Why |
|------------|---------------|---------|-----|
| Python | 3.12.x | Language | Spec pins 3.12. 3.13 is stable (released Oct 2024) but 3.12 is the safer default: mature wheels across the whole stack, full type-param syntax, better `asyncio` taskgroups. 3.13's free-threaded mode is still experimental; no gain for a single-user local app. |
| FastAPI | ≥ 0.115 | Web framework | De-facto async Python web standard in 2026. Pydantic v2 native. Stable API. Starlette under the hood (fine). |
| Uvicorn | ≥ 0.30 | ASGI server (dev) | Bundled with FastAPI tutorial; use `uvicorn --reload` for dev. For a single-user local app, no need for Gunicorn/Hypercorn. |
| Pydantic | ≥ 2.8 | Data modelling | FastAPI 0.100+ requires Pydantic v2. v2 is dramatically faster (Rust core). Spec already aligned. |
| pydantic-settings | ≥ 2.4 | Config via env | Split out of Pydantic in v2. Correct choice for `ANTHROPIC_API_KEY`. |

### Database

| Technology | Version floor | Purpose | Why |
|------------|---------------|---------|-----|
| SQLAlchemy | ≥ 2.0.35 | ORM | 2.0 is the modern async-first API (`AsyncSession`, `async_sessionmaker`, `select()` 2.0 style). Don't use 1.x legacy patterns. |
| aiosqlite | ≥ 0.20 | Async SQLite driver | The standard async driver SQLAlchemy uses under `sqlite+aiosqlite://`. Stable, tiny, thin wrapper over `sqlite3`. |
| Alembic | ≥ 1.13 | Migrations | Standard. Supports async env via `context.configure(connection=sync_conn_from_async_engine)` — template in §Known-issue flags. |
| SQLite | ≥ 3.40 (OS) | Database | Ships with Python / OS. For a single-user app, sufficient forever. Enable `PRAGMA foreign_keys=ON` in session setup (SQLite default is OFF — classic pitfall). |

### Web UI

| Technology | Version floor | Purpose | Why |
|------------|---------------|---------|-----|
| Jinja2 | ≥ 3.1 | Server templating | FastAPI-native pairing; `fastapi.templating.Jinja2Templates`. |
| HTMX | 2.x (current) | Client interactivity | HTMX 2.0 (2024) drops IE support and reorganizes attributes; use 2.x, not 1.x. Serve `htmx.min.js` as a static file so you aren't coupled to a CDN. |
| Pico.css | 2.x | Styling | v2 (released 2024) has better dark-mode defaults and CSS variables. Classless mode is the one to use (`<link>` only, no classes). |

### LLM and content

| Technology | Version floor | Purpose | Why |
|------------|---------------|---------|-----|
| anthropic (SDK) | ≥ 0.39 | Claude API client | Official SDK. Supports Messages API, streaming, tool use, and response format / JSON mode. Pin minor + patch. |
| markdown-it-py | ≥ 3.0 | Markdown rendering | CommonMark-compliant, plugin-able (GFM tables, strikethrough via `mdit-py-plugins`). Standard for Python markdown in 2026. |
| mdit-py-plugins | ≥ 0.4 | GFM extensions | If the LLM generates tables or task lists, you'll want `tasklists`, `deflist`, and `tables` enabled. |
| trafilatura | ≥ 1.12 | URL main-content extraction | Best-in-class for prose extraction (benchmarks against goose3, readability-lxml, boilerpipe). Handles weird CMSes well. |
| httpx | ≥ 0.27 | HTTP client (async) | Native async, connection pooling, HTTP/2 available. Standard pairing with `respx` for testing. |

### Dev tooling

| Tool | Version floor | Purpose | Why |
|------|---------------|---------|-----|
| uv | ≥ 0.4 | Package / env manager | Astral's Rust-based resolver. Replaces pip + pip-tools + virtualenv. 2026 standard. |
| ruff | ≥ 0.6 | Linter + formatter | Astral. Replaces black + isort + flake8 + pylint. 79-char line length per spec. |
| ty | **preview** | Type checker | Astral's type checker. See "Known-issue flags" — **this is the one I'd challenge**. |
| interrogate | ≥ 1.7 | Docstring coverage | Spec requires 100%. Standard tool; stable. |
| pytest | ≥ 8.3 | Test runner | Standard. |
| pytest-asyncio | ≥ 0.24 | Async test support | Use `asyncio_mode = "auto"` in `pyproject.toml` so you don't have to decorate every async test. |
| pytest-cov | ≥ 5.0 | Coverage (for >90% gate) | Not in spec but implied by the 90% rule. Add it. |
| respx | ≥ 0.21 | `httpx` test stubs | See "Known-issue flags" — check maintenance. |
| Playwright | ≥ 1.47 | E2E browser tests | Standard in 2026. Install via `playwright install chromium` after `uv sync`. |
| pre-commit | ≥ 3.7 | Git hook runner | Standard. |

### Recommended additions (not in spec)

| Library | Version floor | Purpose | Why add it |
|---------|---------------|---------|-----------|
| tenacity | ≥ 9.0 | Retry / backoff | Spec §6.1 requires "3 retries with exponential backoff" for LLM rate limits. Rolling your own is wrong-by-default (jitter, cap, non-retryable classes). `tenacity` is the idiomatic answer. |
| structlog | ≥ 24.4 | Structured logging | Spec §11 says "no observability beyond standard logging." Fine, but `structlog` with a console renderer is a drop-in replacement that gives you structured fields for free. Cheap now, invaluable later. |
| nh3 | ≥ 0.2 | HTML sanitization | You're rendering LLM-generated markdown into HTML. LLM output is untrusted input from a security standpoint (prompt injection can produce XSS payloads). `nh3` (Rust-backed `ammonia` port) is faster and safer than `bleach`. Sanitize after markdown-it-py renders. |
| python-multipart | — | Form parsing | FastAPI needs it for `Form(...)` parameters. `uv add fastapi[standard]` pulls it in; be explicit or the first form POST will 500. |

### Optional but worth considering

| Library | Purpose | When to add |
|---------|---------|-------------|
| orjson | Faster JSON | If the LLM response parsing or DB read bulk starts showing up in profiles. Not needed for MVP. |
| rich | Pretty CLI output | Only if you add any CLI commands. Skip for pure web. |
| httpx-retries | Retry middleware for httpx | Can replace per-call `tenacity` use for URL fetching. Tenacity is fine too. |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why not the alternative |
|----------|-------------|-------------|------------------------|
| Web framework | FastAPI | Starlette bare, Litestar, Quart | FastAPI already uses Starlette. Litestar has momentum but smaller ecosystem; FastAPI's Pydantic integration and `Depends()` DI are exactly what the spec needs. Quart is Flask-async, no DI. |
| Templating | Jinja2 | Chameleon, Mako | Jinja2 is the defacto FastAPI pairing. No reason to leave the path. |
| Client interactivity | HTMX | Alpine.js, Stimulus, Hotwire/Turbo | HTMX is the 2026 standard for "I don't want an SPA." Turbo requires Rails-ish conventions; Alpine is complementary not substitute. |
| CSS | Pico.css | Tailwind, Bulma, Beer CSS, Simple.css | Spec explicitly says "UI is not a focus." Pico v2 is classless + zero-build; Tailwind would require a build step (contradicts the zero-build goal). |
| DB | SQLite + async | Postgres + asyncpg, DuckDB | Single-user local app. Postgres is overkill; asyncpg's advantage (massive concurrency) doesn't apply. DuckDB is columnar — wrong shape for OLTP. |
| Async SQLite driver | aiosqlite | sqlite (sync), `sqlitecloud` | The spec's learning goal is async; sync sqlite violates it. `sqlitecloud` is a cloud service. |
| Migrations | Alembic | yoyo-migrations, dbmate | Alembic is the SQLAlchemy-native tool. One thing to learn, one source of truth for schema. |
| LLM SDK | `anthropic` | `litellm`, `instructor`, raw HTTP | Spec names Anthropic as the MVP provider; port abstraction handles the multi-provider future. `instructor` layers Pydantic-validated structured output over SDKs and is worth evaluating for DTO parsing — see "Known-issue flags" below. |
| HTML → markdown | Not in spec (yet) | N/A | Not needed — trafilatura emits plain text and the LLM rewrites it. |
| URL extraction | trafilatura | readability-lxml, goose3, newspaper4k | `trafilatura` consistently wins extraction benchmarks on 2024-2025 data. `newspaper3k` is abandoned; `newspaper4k` is a fork with uneven quality. |
| HTTP client | httpx | aiohttp, requests | `httpx` has the cleanest API and sync/async parity. `aiohttp`'s session model is clunky for one-off fetches. |
| Type checker | ty | mypy, pyright, pyre | See "Known-issue flags" — `ty` is still preview. |
| Test runner | pytest | unittest | Not a real contest in 2026. |
| Async test lib | pytest-asyncio | anyio's pytest plugin | `anyio` plugin is more general but pytest-asyncio is simpler and has larger ecosystem for this flavour of project. |
| HTTP test stub | respx | pytest-httpx, vcrpy | `respx` is the conventional `httpx` pairing. `pytest-httpx` works too and is sometimes better-maintained; see flag. |
| E2E | Playwright | Selenium, Cypress | Playwright is the 2026 default for Python-driven E2E. |

---

## Known-issue flags (per-library)

Ordered by "most important to double-check."

### FLAG 1 — `ty` is not 1.0 yet (Confidence: HIGH this is still preview)

`ty` (Astral's type checker) was unreleased / in active preview as of my
knowledge cutoff. Astral has explicitly said they will break APIs
pre-1.0 and that error output is not yet frozen.

**Risk:** project chose `ty` as a quality gate. A breaking release
(error format change, new strictness default) could fail CI without a
real bug in the code. `make check` is intended to be stable — a
type-checker that shifts under you violates that.

**Mitigations (pick one):**

- Pin `ty` to an exact patch version and upgrade deliberately, reviewing
  the diff of new errors each bump.
- Fall back to `mypy` for CI correctness gating and run `ty` as an
  advisory layer only (no `make check` failure).
- Use `pyright --strict` instead; it has the fastest feedback loop on a
  single-user local repo, is mature, and integrates with VS Code out of
  the box.

**Recommendation:** keep `ty` to honor the spec, **but pin it
aggressively** (`ty == 0.0.x`) and read the release notes before each
bump. If `ty` misses 1.0 by Phase 3, reassess.

### FLAG 2 — `respx` maintenance cadence (Confidence: MEDIUM)

`respx` is the conventional `httpx` stubbing library but has shipped
slowly relative to `httpx`. Confirm the version you pin declares
compatibility with the `httpx` version you pin (check the `respx`
`pyproject.toml` `httpx` pin).

**Alternative if `respx` lags:** `pytest-httpx` (different API, same
job). Slightly more fiddly for stream/retry scenarios, but more actively
maintained. Either works.

**Recommendation:** pick `respx` per spec. If `uv add respx` pulls in a
version that pins an older `httpx`, switch to `pytest-httpx`.

### FLAG 3 — Alembic + async env boilerplate (Confidence: HIGH)

The vanilla `alembic init` template is **sync**. Switching it to async
is a known gotcha — `env.py` needs `run_async_migrations()` that creates
an `AsyncEngine` and calls `connection.run_sync(context.run_migrations)`
inside it. The SQLAlchemy docs "Using Alembic with Async SQLAlchemy"
page has the exact snippet; follow it verbatim.

**What breaks:** if you use `alembic init` without modifying `env.py`,
autogenerate works but `upgrade`/`downgrade` will silently fail or
deadlock against aiosqlite.

**Recommendation:** bake the async `env.py` into the Phase-1 scaffold
task in the roadmap. Don't leave it as "follow the docs later."

### FLAG 4 — Pydantic v2 breaking changes still bite (Confidence: HIGH)

If any dependency lags on Pydantic v1 (rare in 2026 but it happens),
install will resolve an incompatible matrix. Also:

- `BaseSettings` moved to `pydantic-settings`.
- `@validator` → `@field_validator`, `@root_validator` → `@model_validator`.
- Config dicts changed (`model_config = ConfigDict(...)`).

**Recommendation:** when writing DTOs in `app/application/dtos.py`, use
v2 idioms only. Don't copy Pydantic v1 examples off blogs.

### FLAG 5 — Anthropic structured output: tool use vs response format (Confidence: MEDIUM)

Spec §4.2 says "Structured output via tool use." That's the original
pattern (2023-2024) — define a tool schema, parse the tool-use output
JSON. It works.

By late 2025, Anthropic's Messages API added a more direct JSON-mode /
response-format mechanism. Which one to use depends on the current SDK.

**Tradeoffs:**

- **Tool use as structured output:** works on every Claude version,
  slightly verbose, but you get the Pydantic schema directly from the
  tool definition.
- **JSON mode:** cleaner, but may not enforce schema as strictly.

**Recommendation:** start with tool use (it's safe and the spec calls
for it). Evaluate JSON mode / response format in Phase 2 when the
adapter surface is well-understood. **Consider the `instructor`
library** (<https://github.com/jxnl/instructor>) as a thin layer that
gives you "Pydantic model in, Pydantic model out" across providers
including Anthropic — it handles the tool-use-as-structured-output dance
cleanly. Worth 15 minutes of evaluation before hand-rolling.

### FLAG 6 — SQLite foreign keys are OFF by default (Confidence: HIGH)

SQLite does not enforce foreign keys unless you enable `PRAGMA
foreign_keys = ON` on **every connection**. aiosqlite + SQLAlchemy does
not do this automatically.

**Fix:** add a connection-event listener in `app/infrastructure/db/session.py`:

```python
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine

@event.listens_for(engine.sync_engine, "connect")
def _enable_sqlite_fks(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

This pairs with the `Source ||--o{ Card` cascade in the domain model
(§3). Without it, FK cascades are lies.

### FLAG 7 — HTMX 2.x attribute renames (Confidence: HIGH)

Moving from HTMX 1.x tutorials to HTMX 2.x, a handful of attributes
changed names (e.g. `hx-ws` → `hx-ext="ws"`, some event hooks). Follow
only 2.x docs; don't copy 1.x blog posts.

### FLAG 8 — Playwright requires an OS-level browser install (Confidence: HIGH)

`uv add playwright` does not install Chromium. You need a post-install
step (`playwright install chromium`) — bake it into `make install` or
the CI workflow, not a README bullet.

### FLAG 9 — trafilatura pulls lxml (Confidence: HIGH)

`trafilatura` depends on `lxml`, which has C extensions and occasional
wheel pain on niche platforms. On Mac/Linux x64 and Apple Silicon in
2026, wheels exist and it Just Works. Flag it as a dep-chain fact, not
as a problem to avoid.

### FLAG 10 — Jinja2 auto-escape and LLM content (Confidence: HIGH)

Jinja2 does **not** auto-escape by default when loaded with
`Jinja2Templates(...)` unless you pass `autoescape=True` (FastAPI's
default wrapper does enable it for `.html` files, but verify for your
version). Combined with LLM-generated content, disabling autoescape is
an XSS wildcard. Keep it on.

For rendered-markdown → HTML specifically, after `markdown-it-py`
produces HTML, pass it through `nh3.clean()` and emit it with
`{{ safe_html|safe }}`. Do not render LLM output with `|safe` raw.

---

## Installation

### `pyproject.toml` skeleton

```toml
[project]
name = "dojo"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
    # Web
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "jinja2>=3.1",
    "python-multipart>=0.0.9",
    # Config
    "pydantic>=2.8",
    "pydantic-settings>=2.4",
    # DB
    "sqlalchemy[asyncio]>=2.0.35",
    "aiosqlite>=0.20",
    "alembic>=1.13",
    # LLM + content
    "anthropic>=0.39",
    "markdown-it-py>=3.0",
    "mdit-py-plugins>=0.4",
    "trafilatura>=1.12",
    "httpx>=0.27",
    # Recommended additions
    "tenacity>=9.0",
    "structlog>=24.4",
    "nh3>=0.2",
]

[dependency-groups]
dev = [
    "ruff>=0.6",
    "ty",  # pin exactly once resolved; preview channel
    "interrogate>=1.7",
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "respx>=0.21",  # or pytest-httpx>=0.30
    "playwright>=1.47",
    "pre-commit>=3.7",
]

[tool.ruff]
line-length = 79
target-version = "py312"

[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "--strict-markers --cov=app --cov-report=term-missing"

[tool.interrogate]
fail-under = 100
```

### First-time setup

```bash
# Resolve current versions
uv sync

# Install Playwright browser
uv run playwright install chromium

# Set up pre-commit
uv run pre-commit install

# Initial DB
uv run alembic upgrade head
```

### Version-verification step (the thing this researcher couldn't do)

Before committing the skeleton above, run:

```bash
uv tree --depth 1
```

…and check each top-level dep's resolved version. If any resolved
version is materially newer than the floor listed here, update the
floor in `pyproject.toml` and skim that library's changelog between the
floor and the resolved version for anything breaking.

---

## Sources

- `/Users/pvardanis/Documents/projects/dojo/.planning/PROJECT.md`
- `/Users/pvardanis/Documents/projects/dojo/docs/superpowers/specs/2026-04-18-dojo-design.md`
- Training data (Claude Opus 4.7, knowledge cutoff January 2026) — used
  for library-ecosystem knowledge.
- **Not consulted (tools unavailable in this run):** Context7, PyPI
  live API, official GitHub release pages, WebSearch. See
  "Research-tool caveat" at the top of this file — every version is a
  floor, not a pin; live-verify before committing `pyproject.toml`.

## Confidence summary

| Area | Confidence | Reason |
|------|------------|--------|
| Stack *choices* (which lib for what role) | HIGH | Choices are standard 2026 patterns; I can defend each without needing live sources. |
| Exact version numbers | MEDIUM | Based on training data (Jan 2026 cutoff); project is being scaffolded April 2026. Most libs will have released patches or minor versions since. Floors should all be valid; pin what `uv` resolves. |
| Known-issue flags | MEDIUM-HIGH | The major flags (`ty` preview, Alembic async boilerplate, SQLite FKs off, Jinja autoescape, HTMX 2 rename, Playwright browser install) are well-documented ecosystem facts with HIGH confidence. The `respx` and `instructor` evaluations are judgment calls (MEDIUM). |
| Missing-library gaps | HIGH | `tenacity`, `structlog`, `nh3` are idiomatic picks any Python engineer would add; the rationale for each (retry backoff in §6.1, untrusted LLM HTML, structured logging for future observability) is concrete and project-specific. |
