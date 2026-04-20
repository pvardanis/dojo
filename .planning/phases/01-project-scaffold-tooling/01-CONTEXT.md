# Phase 1: Project Scaffold & Tooling - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

A freshly-cloned Dojo repo boots end-to-end through `make install &&
make check && make run` with every quality gate configured, CI green on
the empty skeleton, and the async-infrastructure footguns (async
Alembic template, pytest-asyncio event-loop config, structlog,
pydantic-settings) verified green **before any business code exists**.

Phase 1 delivers the *foundation*, not the application. Domain
entities (Phase 2), ORM models and real adapters (Phase 3), and the
Generate/Drill/Read flows (Phases 4-6) are explicitly out of scope
here — but the scaffold must make them startable.

</domain>

<decisions>
## Implementation Decisions

### Database portability posture

- **D-01:** Portable-by-construction. The scaffold does **not** hardcode
  SQLite as the only supported database. Concretely:
  - `DATABASE_URL` is a pydantic-settings field (default:
    `sqlite+aiosqlite:///dojo.db`) — not hardcoded in `session.py`.
  - The SQLite PRAGMA setup (`foreign_keys=ON`, `journal_mode=WAL`,
    `busy_timeout=5000`) lives in a connection-event listener that is
    **dialect-guarded** — only fires when
    `engine.dialect.name == "sqlite"`. Postgres/other dialects receive
    no SQLite PRAGMAs.
  - Alembic `env.py` reads the DB URL from the same
    `pydantic-settings` singleton the app uses (no parallel config
    source). This is also mandated for correctness by PITFALLS.md C4
    — it's not purely a portability concern.
  - Tests parameterise their DB fixture off `DATABASE_URL` too, so
    test DBs don't require editing `session.py`.
- **D-02:** Portability in Phase 1 is about **not slamming the door**,
  not about making a swap plug-and-play. Column-type portability (JSON
  arrays vs comma-joined strings for tags, UUID vs str for IDs,
  TIMESTAMPTZ vs ISO-text for timestamps) is a Phase 3 concern and is
  *not* pre-decided here. Migrations must be written to avoid
  SQLite-only DDL quirks from Phase 3 onward; this CONTEXT.md notes
  the expectation but doesn't encode it as a Phase 1 task.
- **D-03:** Rationale for going portable despite "SQLite forever" in
  PROJECT.md: the marginal cost in Phase 1 is ~3-5 lines (the dialect
  guard around PRAGMAs) because the rest of the work — env var for DB
  URL, Alembic reading from settings — is correctness-mandated
  regardless of DB choice. Not adding an abstraction, just not writing
  anti-portability.

### Test infrastructure (pytest-asyncio + DB fixtures)

- **D-04:** `asyncio_mode = "auto"` in `pyproject.toml` under
  `[tool.pytest.ini_options]`. No per-test `@pytest.mark.asyncio`
  decorators.
- **D-05:** Use the pytest-asyncio 0.24+ canonical pattern: a
  session-scoped `event_loop_policy` fixture (not the deprecated
  `event_loop` fixture). Cross-reference pytest-asyncio release notes
  at implementation time — PITFALLS.md M8 flags that the canonical has
  moved between versions and older tutorials are wrong.
- **D-06:** DB fixture architecture:
  - **Session-scoped async engine** bound to a **tmp-file SQLite DB**
    (not `:memory:`). Rationale: `:memory:` SQLite DBs are per-connection
    in async SQLAlchemy — multiple connections don't see each other,
    which breaks any fixture that opens more than one session. Tmp-file
    is bulletproof and negligibly slower.
  - **Session-scoped migration run:** `alembic upgrade head` is executed
    once per test session against the tmp DB — this exercises the async
    Alembic pipeline in tests (defense against C4 drift) rather than
    bypassing migrations via `Base.metadata.create_all`.
  - **Function-scoped session** with outer-transaction rollback: each
    test opens a session, runs inside `async with session.begin():`,
    and rolls back at teardown. Isolation is per-test without
    re-migrating.
- **D-07:** SC #4 ("first integration test runs 10 times in a row
  without event-loop flakes") is verified by a dedicated target (e.g.
  `make test-flakes` or `pytest --count 10`, using `pytest-repeat` as
  a dev-group dep). The first integration test opens a real async
  session against the tmp DB, executes a trivial query, and closes
  cleanly; this is the canary for the whole fixture architecture.

### Alembic baseline migration

- **D-08:** Create an **empty initial revision** in Phase 1 (no DDL,
  no `op.create_table`). `alembic upgrade head` runs this revision and,
  as a side effect, creates Alembic's own tracking table
  (`alembic_version`) in the fresh DB. That `alembic_version` table
  is the "expected table" that satisfies SC #3 when
  `sqlite3 dojo.db .schema` is run.
- **D-09:** Rationale: this is the canonical Alembic pattern — every
  project's first `upgrade head` creates `alembic_version` before any
  real DDL. It proves the full async-migration pipeline (C4 is gated)
  without introducing throwaway tables that Phase 3 would have to drop.
- **D-10:** Phase 3 owns the first real-schema migration (creating
  `sources`, `notes`, `cards`, `card_reviews` tables). Phase 1's
  handoff to Phase 3 is: working async Alembic env.py, empty initial
  revision applied, verified against a fresh aiosqlite DB. Phase 3
  runs `alembic revision --autogenerate` on top of this baseline.

### Scaffold depth + landing page

- **D-11:** **Absolute-minimum scaffold.** Phase 1 creates only what's
  needed to boot:
  - `app/main.py` (composition root — minimal: app factory, settings
    dependency, one route include)
  - `app/settings.py` (pydantic-settings — `ANTHROPIC_API_KEY`,
    `DATABASE_URL`, `LOG_LEVEL`, `RUN_LLM_TESTS` fields)
  - `app/logging_config.py` (structlog configuration; one
    `get_logger(__name__)` helper)
  - `app/web/routes/home.py` (the `/` and `/health` routes)
  - `app/web/templates/base.html` + `app/web/templates/home.html`
  - `app/web/static/` (empty; populated in later phases when HTMX and
    Pico land)
  - `app/infrastructure/db/session.py` (async engine, session factory,
    SQLite PRAGMA listener — dialect-guarded)
  - `migrations/env.py` + `migrations/versions/<stamp>_initial.py`
    (empty revision)
  - `tests/conftest.py` + `tests/integration/test_db_smoke.py` (the
    first integration test)

  Phase 2+ creates `app/domain/`, `app/application/`,
  `app/infrastructure/repositories/`, `app/infrastructure/llm/`,
  `app/infrastructure/sources/` as each phase needs them. No empty
  `__init__.py` shells.
- **D-12:** `/` renders a minimal Jinja home page (title "Dojo" +
  placeholder text — no real links yet, the flows don't exist). This
  proves the Jinja wiring end-to-end (autoescape on, template loader
  configured, `HTMLResponse` returned). Template extends `base.html`
  so Phase 4+ has the base template ready.
- **D-13:** `/health` returns JSON `{"status": "ok"}` — cheap, standard,
  lets CI and later Playwright smoke-test the app boot without parsing
  HTML. SC #2 wording ("health/home route") is read as two routes, not
  one.

### Tooling decisions (Claude's discretion, recorded for transparency)

- **D-14:** **Pre-commit hook scope:** matches spec §8.2 — ruff format,
  ruff check, ty, interrogate, **and** pytest. But pytest in the hook
  runs only unit tests (`pytest tests/unit/`) with `-x --ff` for fast
  feedback, not the full integration suite. Rationale: SC #5 requires
  ruff/ty/interrogate to block; PITFALL M10 warns full-suite pytest in
  pre-commit degrades the dev loop past ~10s. Unit-only in pre-commit
  + full `make check` in CI strikes the balance. Hook ordering: (1)
  ruff format, (2) ruff check --fix, (3) ty, (4) interrogate,
  (5) pytest tests/unit/ -x --ff.
- **D-15:** **interrogate + Protocol methods** (PITFALL M11): accept
  one-line docstrings on Protocol methods. Do **not** add
  `app/application/ports.py` to interrogate's ignore list — 100% means
  100%. Docstrings on Protocol methods should specify return/error
  semantics, not restate the method name.
- **D-16:** **`ty` version pinning** (FLAG 1): pin `ty` to an exact
  patch version in `pyproject.toml` (not a floor). Upgrade deliberately,
  reviewing the diff of new errors each bump. If `ty` blocks progress
  in Phase 2/3 with unsupported constructs, `mypy` is the drop-in
  fallback — document this in CLAUDE.md but don't pre-install `mypy`.
- **D-17:** **Structlog rendering:** dev uses
  `structlog.dev.ConsoleRenderer` (human-readable, colored); tests use
  the same renderer but with log level set to `WARNING` via a conftest
  fixture so pristine-output rule (PITFALL m8) is respected; prod mode
  (`LOG_LEVEL=INFO` + `DOJO_ENV=prod` or similar) uses
  `structlog.processors.JSONRenderer`. One `get_logger(__name__)`
  helper; every module obtains its logger through it (OPS-04).
- **D-18:** **Settings surface** on day one: `ANTHROPIC_API_KEY`,
  `DATABASE_URL` (default `sqlite+aiosqlite:///dojo.db`), `LOG_LEVEL`
  (default `INFO`), `RUN_LLM_TESTS` (default `False`). All loaded from
  `.env` via pydantic-settings. `.env.example` ships every field with
  safe placeholder values.
- **D-19:** **CI workflow** (`.github/workflows/ci.yml`): single job,
  Python 3.12, steps are checkout → setup uv → `make install` → `make
  check`. Cache `uv` dependencies keyed on `uv.lock` hash. Concurrency
  group cancels in-progress runs for the same PR. Playwright browser
  install is **not** in Phase 1 CI (no E2E tests until Phase 7) — add
  when needed.
- **D-20:** **Package mode for uv:** `pyproject.toml` declares the
  project as an installable package (`[project]` + implicit `[tool.uv]`
  `package = true`) so Alembic's `env.py` can `from app.infrastructure.db
  import Base` without PYTHONPATH hacks. This also gives us `uv run
  alembic ...` and `uv run pytest` that always see the current source
  tree.

### Claude's Discretion

The following micro-decisions are left to the planner/executor unless
they surface as conflicts:

- Exact `tmp_path_factory` fixture shape for the session DB tmp file
- Whether to use `pytest-repeat` (dev dep) or a shell loop for SC #4's
  "10 times in a row" check
- Concrete `ty` patch version (resolve via `uv sync` then pin)
- Whether `pre-commit` config uses `local` hooks calling `uv run` vs
  language-native hook repositories (planner picks based on pre-commit
  ergonomics)
- `.env.example` exact field wording

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level (authoritative)

- `.planning/PROJECT.md` — vision, principles, key decisions, out-of-scope
- `.planning/REQUIREMENTS.md` — owns the OPS-01/02/03/04, TEST-02, LLM-03
  requirements Phase 1 must satisfy (see §v1 Requirements → Operations
  and dev tooling, Tests, LLM provider)
- `.planning/ROADMAP.md` §"Phase 1: Project Scaffold & Tooling" — Phase
  1 Goal, Dependencies, Requirements, 8 Success Criteria
- `CLAUDE.md` (project root) — distilled conventions and Protocol-vs-
  function clarifier (project-local)

### Design spec (authoritative on implementation detail)

- `docs/superpowers/specs/2026-04-18-dojo-design.md` — single source
  of truth for architecture and implementation detail
  - §4.1 Package layout — directory tree Phase 1 must scaffold minimally
  - §4.2 Library picks — locked library choices
  - §8.1 Makefile targets — the 9 required targets (`install`, `format`,
    `lint`, `typecheck`, `docstrings`, `test`, `check`, `run`, `migrate`)
  - §8.2 Pre-commit — "pre-commit runs ruff format, ruff check, ty,
    interrogate, and pytest"
  - §8.3 CI (GitHub Actions) — single job, Python 3.12, steps
  - §8.4 Project `CLAUDE.md` — what the repo-root CLAUDE.md must cover
    (under 150 lines)
  - §9 Decisions log — non-obvious decisions already resolved

### Research (Phase 1 entry gates)

- `.planning/research/STACK.md` — version floors, known-issue flags
  - §"Core framework" / "Database" / "Dev tooling" tables — exact
    version floors to seed `pyproject.toml`
  - FLAG 1 (`ty` preview) — pin aggressively
  - FLAG 3 (Alembic async env.py) — use `alembic init -t async`, do not
    hand-patch the sync template
  - FLAG 6 (SQLite FKs off by default) — PRAGMA listener
  - FLAG 8 (Playwright OS-level install) — not in Phase 1 CI
  - FLAG 10 (Jinja2 autoescape + LLM content) — verify autoescape on
- `.planning/research/PITFALLS.md` — every Phase 1 entry gate
  - C4 (Alembic async env.py not actually running async) — use async
    template, verify with fresh DB + `sqlite3 .schema`
  - C9 (must verify) — referenced via STACK.md FLAG 6 for PRAGMA
  - M8 (pytest-asyncio `event_loop` / `asyncio_mode` footguns) —
    informs D-04 through D-07
  - M9 (uv + editable install + Alembic) — Base imports every model
    file; smoke test `Base.metadata.tables`
  - M10 (Ruff + ty + interrogate hook ordering) — informs D-14
  - M11 (interrogate 100% + Protocol methods) — informs D-15
  - M12 (aiosqlite single-writer + WAL) — part of D-01's PRAGMA set

### External conventions

- `~/Documents/Black Lodge/knowledge-base/wiki/python-project-setup.md`
  — authoritative on file size limits, ABOUTME convention, Protocol vs
  ABC preference, dataclass-for-containers, Pydantic at validation
  boundaries, `logging` with `get_logger(__name__)` (structlog wraps
  it)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

None — the repo currently contains only `.planning/`, `docs/`,
`CLAUDE.md`, and `.git/`. Phase 1 builds the initial `app/`,
`migrations/`, `tests/` trees, plus the tooling config files
(`pyproject.toml`, `Makefile`, `alembic.ini`, `.env.example`,
`.pre-commit-config.yaml`, `.github/workflows/ci.yml`,
`.gitignore`).

### Established Patterns

None yet — this phase establishes them:

- The **`# ABOUTME:` two-line header** on every Python file is
  established here (CLAUDE.md project-local + python-project-setup
  wiki).
- The **composition-root pattern** (`app/main.py` is the only module
  that wires layers) is established here but exercised in later phases.
- The **`pydantic-settings` singleton** pattern (both app and
  Alembic read from the same `Settings` instance) is established here.
- The **dialect-guarded connection-event listener** pattern for
  per-dialect connection setup is established in `session.py`.

### Integration Points

- **Alembic `env.py` ↔ `app.settings.Settings`** — env.py imports
  `Settings()` to read `DATABASE_URL`. No parallel config source.
- **Alembic `env.py` ↔ future `Base.metadata`** — Phase 1 leaves
  `env.py` pointing at `app.infrastructure.db.models:Base`, which does
  not exist yet. The first migration (empty revision) does not
  reference `Base`. Phase 3 creates `Base` + model files; M9 mitigation
  (eager imports of every model file from a single `Base` module) is
  set up structurally in Phase 1 even though it imports nothing yet.
- **`make check` ↔ pre-commit ↔ CI** — all three invoke the same
  command set (§8.2 of spec). Pre-commit's pytest step is narrower
  (unit only; see D-14), but formatter/linter/typechecker/docstrings
  are identical.
- **structlog ↔ stdlib logging** — structlog wraps stdlib `logging`
  per python-project-setup wiki. Every module uses
  `get_logger(__name__)`; the helper lives in `app/logging_config.py`
  and is imported (not redefined) everywhere.

</code_context>

<specifics>
## Specific Ideas

- **The "boring correct" principle:** Phase 1 must feel like a
  Python-project-setup reference implementation — no clever shortcuts,
  every pitfall in PITFALLS.md covered by config or by an explicit
  note in this CONTEXT.md. If a decision is between "elegant" and
  "boring with a pitfall gated," prefer boring.
- **The first integration test is the canary.** It's not a throwaway
  — it's the thing that proves pytest-asyncio, async Alembic, tmp-file
  SQLite, session rollback, and structlog pristine-output all work
  together. Plan it deliberately; it becomes the template every future
  integration test follows.
- **Repo-root `CLAUDE.md` already exists** (committed) and is close to
  the target state. Phase 1's CLAUDE.md task is to reconcile it
  against the spec §8.4 requirements (under 150 lines, covers the six
  specified sections) rather than write from scratch.

</specifics>

<deferred>
## Deferred Ideas

- **Full DB portability (plug-and-play Postgres swap)** — Phase 1
  keeps the door open but doesn't make a swap free. Phase 3 column
  types and future-migration DDL discipline carry additional
  portability cost. If/when a Postgres swap is actually on the table,
  revisit: (a) column types, (b) connection-pool config, (c)
  migration DDL patterns, (d) test parameterisation across dialects.
- **Playwright in CI** — Phase 7 adds E2E tests; Playwright browser
  install and CI step belong there, not in Phase 1.
- **`mypy` as ty fallback** — document the fallback in CLAUDE.md but
  don't preemptively install. Re-open if `ty` blocks Phase 2/3.
- **Import-linter** — Phase 2 owns the layer-boundary test since that's
  when domain/application layers first exist. Phase 1 has no `app/`
  business code to lint, so deferring is correct.
- **Playwright + HTMX flake mitigations (PITFALL m5)** — Phase 5/7,
  not Phase 1.

</deferred>

---

*Phase: 01-project-scaffold-tooling*
*Context gathered: 2026-04-20*
