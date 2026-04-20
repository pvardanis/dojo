---
phase: 01-project-scaffold-tooling
plan: 03
type: execute
wave: 3
depends_on:
  - "01-02"
files_modified:
  - app/infrastructure/__init__.py
  - app/infrastructure/db/__init__.py
  - app/infrastructure/db/session.py
  - alembic.ini
  - migrations/env.py
  - migrations/script.py.mako
  - migrations/versions/0001_initial.py
autonomous: true
requirements:
  - OPS-01
tags:
  - python
  - sqlalchemy
  - async
  - alembic
  - aiosqlite
  - migrations

must_haves:
  truths:
    - "`uv run alembic upgrade head` succeeds against a fresh aiosqlite
      tmp DB and creates the `alembic_version` tracking table (SC #3)"
    - "`app/infrastructure/db/session.py` exposes an async `engine`, an
      `AsyncSessionLocal` factory (with `expire_on_commit=False`), and
      an empty `Base` that Phase 3 will extend"
    - "SQLite PRAGMAs (`foreign_keys=ON`, `journal_mode=WAL`,
      `busy_timeout=5000`) are applied via a dialect-guarded connect
      listener — a future Postgres swap requires no code changes to
      session.py"
    - "`migrations/env.py` reads `DATABASE_URL` from
      `app.settings.get_settings()` — single source of truth (D-01)"
  artifacts:
    - path: "app/infrastructure/__init__.py"
      provides: "Infrastructure layer package marker"
      contains: "# ABOUTME:"
    - path: "app/infrastructure/db/__init__.py"
      provides: "DB subpackage marker"
      contains: "# ABOUTME:"
    - path: "app/infrastructure/db/session.py"
      provides: "Async engine + session factory + Base + dialect-guarded
        PRAGMA listener"
      exports: ["Base", "engine", "AsyncSessionLocal"]
      contains: "expire_on_commit=False"
    - path: "alembic.ini"
      provides: "Alembic CLI config (runtime URL overridden by env.py)"
      contains: "[alembic]"
    - path: "migrations/env.py"
      provides: "Async Alembic env with pydantic-settings wiring"
      contains: "async_engine_from_config"
    - path: "migrations/script.py.mako"
      provides: "Alembic revision template (stock async)"
      contains: "${upgrades"
    - path: "migrations/versions/0001_initial.py"
      provides: "Empty baseline revision"
      contains: "revision: str = \"0001\""
  key_links:
    - from: "app/infrastructure/db/session.py"
      to: "app.settings.get_settings"
      via: "create_async_engine(_settings.database_url, ...)"
      pattern: "get_settings\\(\\)"
    - from: "app/infrastructure/db/session.py"
      to: "SQLite PRAGMA listener"
      via: "@event.listens_for(engine.sync_engine, 'connect') +
        dialect guard"
      pattern: "PRAGMA foreign_keys=ON"
    - from: "migrations/env.py"
      to: "app.settings"
      via: "config.set_main_option('sqlalchemy.url',
        get_settings().database_url)"
      pattern: "set_main_option"
    - from: "migrations/env.py"
      to: "app.infrastructure.db.session.Base"
      via: "target_metadata = Base.metadata"
      pattern: "from app.infrastructure.db.session import Base"
---

<objective>
Build the full async-Alembic pipeline against a pydantic-settings
singleton: `app/infrastructure/db/session.py` (async engine + session
factory + dialect-guarded PRAGMA listener), `alembic.ini` (stock
template), `migrations/env.py` (async runner, settings-driven URL),
`migrations/script.py.mako` (stock async template), and
`migrations/versions/0001_initial.py` (empty baseline revision).

Purpose: closes phase-entry gate C4 (async Alembic actually runs
async), establishes the portability-by-construction database posture
(D-01 — no hardcoded SQLite URL outside defaults, dialect-guarded
PRAGMAs), and gives Phase 3 a migrated-once baseline to autogenerate on
top of.

Output: `make migrate` succeeds on a fresh working copy. `rm -f
/tmp/dojo.db && DATABASE_URL=sqlite+aiosqlite:////tmp/dojo.db uv run
alembic upgrade head && sqlite3 /tmp/dojo.db .schema` shows the
`alembic_version` table (SC #3 gate).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/01-project-scaffold-tooling/01-CONTEXT.md
@.planning/phases/01-project-scaffold-tooling/01-RESEARCH.md
@.planning/phases/01-project-scaffold-tooling/01-PATTERNS.md
@.planning/phases/01-project-scaffold-tooling/01-02-SUMMARY.md
@.planning/research/PITFALLS.md
@app/settings.py
@app/logging_config.py
@pyproject.toml

<interfaces>
<!-- Types and functions downstream plans will import from this plan's outputs. -->

From `app/infrastructure/db/session.py` (created in this plan):
```python
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

class Base(DeclarativeBase): ...      # empty in Phase 1; Phase 3 adds models
engine: AsyncEngine                    # module-level, bound to settings.database_url
AsyncSessionLocal: async_sessionmaker[AsyncSession]  # with expire_on_commit=False
```

From `app/settings.py` (imported by this plan):
```python
def get_settings() -> Settings: ...   # returns cached Settings singleton
# Settings.database_url: str (default "sqlite+aiosqlite:///dojo.db")
```

**Consumers** (downstream plans):
- `migrations/env.py` (this plan) imports `Base` and `get_settings`
- `tests/conftest.py` (Plan 05) uses `alembic.command.upgrade` against
  `alembic.ini` + tmp-DATABASE_URL
- Phase 3+ repositories import `Base`, `AsyncSessionLocal`, `engine`
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create app/infrastructure/ package shells + app/infrastructure/db/session.py</name>
  <files>app/infrastructure/__init__.py, app/infrastructure/db/__init__.py, app/infrastructure/db/session.py</files>
  <read_first>
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      348-398 (verbatim drop-in)
    - .planning/phases/01-project-scaffold-tooling/01-CONTEXT.md
      decisions D-01, D-02 (portability posture), D-03 (portability
      rationale — dialect guard is ~3-5 lines), D-06 (fixture
      architecture pairs with this file)
    - .planning/phases/01-project-scaffold-tooling/01-PATTERNS.md lines
      243-265 (key structural elements)
    - .planning/research/PITFALLS.md C3 (expire_on_commit=False), C9
      (dialect-guarded setup), M12 (WAL + busy_timeout)
    - app/settings.py (consumer of `get_settings()`)
  </read_first>
  <action>
    **D-03 rationale applies here:** the dialect guard is 3-5 lines of
    conditional code in session.py; no further portability infrastructure
    is built in Phase 1. The portability posture is "not slamming the
    door" (D-02), not plug-and-play swap.

    **Create subpackage markers unconditionally.** Both
    `app/infrastructure/__init__.py` and `app/infrastructure/db/__init__.py`
    must exist for Python to resolve `app.infrastructure.db.session` as
    an importable module. These are NOT D-11 "empty shells that serve no
    structural purpose" — they are structurally required by Python's
    package resolution rules and by hatchling's `packages = ["app"]`
    wheel-build config. Each contains the two-line ABOUTME header plus a
    one-line module docstring:

    `app/infrastructure/__init__.py`:
    ```python
    # ABOUTME: Infrastructure layer — adapters for DB, LLM, sources.
    # ABOUTME: Imports inward only (from app.application / app.domain).
    """Infrastructure layer package."""
    ```

    `app/infrastructure/db/__init__.py`:
    ```python
    # ABOUTME: DB-infrastructure subpackage (engine, session, repos).
    # ABOUTME: Phase 1 provides Base + session; Phase 3 adds repositories.
    """Database infrastructure subpackage."""
    ```

    Write `app/infrastructure/db/session.py` — paste the drop-in from
    01-RESEARCH.md lines 348-398 verbatim. Key structural preservations:

    1. Two-line `# ABOUTME:` header: "Async SQLAlchemy engine + session
       factory." / "Dialect-guarded connection listener sets SQLite
       pragmas."
    2. Module docstring (add if not present in drop-in): `"""Async
       SQLAlchemy engine + session factory for Dojo."""`.
    3. `from __future__ import annotations`.
    4. Imports: `sqlalchemy.event`, `sqlalchemy.ext.asyncio`
       (`AsyncSession`, `async_sessionmaker`, `create_async_engine`),
       `sqlalchemy.orm.DeclarativeBase`, `app.settings.get_settings`.
    5. `class Base(DeclarativeBase):` with docstring "Declarative base
       for all ORM models (populated in Phase 3)." — empty body.
    6. `_settings = get_settings()` at module level (leading underscore
       — private; downstream code imports `get_settings` directly).
    7. `engine = create_async_engine(_settings.database_url, echo=False,
       future=True)` — module-level singleton.
    8. `AsyncSessionLocal: async_sessionmaker[AsyncSession] =
       async_sessionmaker(engine, expire_on_commit=False,
       class_=AsyncSession)` — **`expire_on_commit=False` is
       non-negotiable** (PITFALL C3).
    9. `@event.listens_for(engine.sync_engine, "connect")` decorated
       function `_configure_sqlite(dbapi_conn, _)`:
       - One-line docstring "Apply SQLite-only pragmas; no-op on other
         dialects."
       - Dialect guard: `if engine.dialect.name != "sqlite": return`
         (D-01 — portability-by-construction; D-03 — this 3-line guard
         is the entirety of Phase 1's portability cost).
       - Execute PRAGMAs: `foreign_keys=ON`, `journal_mode=WAL`,
         `busy_timeout=5000`. Use `cursor = dbapi_conn.cursor()`,
         execute, `cursor.close()` (not `with` — dbapi cursors don't
         support the sync context-manager protocol here).

    **Anti-patterns to avoid (from RESEARCH.md §Anti-Patterns):**
    - Do NOT hardcode `"sqlite+aiosqlite:///dojo.db"` in session.py —
      must read from `get_settings().database_url`.
    - Do NOT set `expire_on_commit=True`.
    - Do NOT drop the dialect guard — that would try to execute SQLite
      PRAGMA statements against a Postgres connection in a future swap.

    Verify:
    - `wc -l app/infrastructure/db/session.py` ≤ 100.
    - 2 ABOUTME lines, ruff clean, ty clean, interrogate 100%.
    - Import smoke test:
      `uv run python -c "from app.infrastructure.db.session import
      Base, engine, AsyncSessionLocal; print('engine=', engine.url);
      print('Base.metadata.tables=', dict(Base.metadata.tables));
      assert Base.metadata.tables == {}; print('OK')"` — Base.metadata
      is empty in Phase 1 (Phase 3 adds models); expects OK.
  </action>
  <verify>
    <automated>test -f app/infrastructure/__init__.py &amp;&amp; grep -c '^# ABOUTME:' app/infrastructure/__init__.py | grep -q '^2$' &amp;&amp; test -f app/infrastructure/db/__init__.py &amp;&amp; grep -c '^# ABOUTME:' app/infrastructure/db/__init__.py | grep -q '^2$' &amp;&amp; test -f app/infrastructure/db/session.py &amp;&amp; test $(wc -l &lt; app/infrastructure/db/session.py) -le 100 &amp;&amp; grep -c '^# ABOUTME:' app/infrastructure/db/session.py | grep -q '^2$' &amp;&amp; grep -q 'expire_on_commit=False' app/infrastructure/db/session.py &amp;&amp; grep -q 'if engine.dialect.name != "sqlite"' app/infrastructure/db/session.py &amp;&amp; grep -q 'PRAGMA foreign_keys=ON' app/infrastructure/db/session.py &amp;&amp; grep -q 'PRAGMA journal_mode=WAL' app/infrastructure/db/session.py &amp;&amp; grep -q 'PRAGMA busy_timeout=5000' app/infrastructure/db/session.py &amp;&amp; grep -q 'class Base(DeclarativeBase)' app/infrastructure/db/session.py &amp;&amp; grep -q 'get_settings()' app/infrastructure/db/session.py &amp;&amp; uv run ruff format --check app/infrastructure/db/session.py &amp;&amp; uv run ruff check app/infrastructure/db/session.py &amp;&amp; uv run interrogate -c pyproject.toml app/infrastructure/db/session.py &amp;&amp; uv run python -c "from app.infrastructure.db.session import Base, engine, AsyncSessionLocal; assert Base.metadata.tables == {}; print('OK')" | grep -q '^OK$'</automated>
  </verify>
  <done>
    Both `__init__.py` shells exist with ABOUTME headers. `session.py`
    exists with ABOUTME header; all four structural elements present
    (Base, engine, AsyncSessionLocal, dialect-guarded listener); PRAGMAs
    correct; import smoke test green.
  </done>
</task>

<task type="auto">
  <name>Task 2: Generate Alembic scaffold and wire env.py to settings</name>
  <files>alembic.ini, migrations/env.py, migrations/script.py.mako, migrations/versions/0001_initial.py</files>
  <read_first>
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      536-564 (empty initial revision drop-in)
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      578-652 (async env.py drop-in)
    - .planning/phases/01-project-scaffold-tooling/01-CONTEXT.md
      decisions D-01 (settings-driven URL), D-08, D-09, D-10 (empty
      initial revision rationale)
    - .planning/phases/01-project-scaffold-tooling/01-PATTERNS.md lines
      271-336 (key structural elements + caveats)
    - .planning/research/PITFALLS.md C4 (async Alembic), M9 (Base eager
      import), New Pitfall 5 (asyncio.run + pytest loop)
  </read_first>
  <action>
    This task generates the Alembic scaffold using the CLI, then
    replaces `env.py` and writes the initial revision by hand. Follow
    these steps IN ORDER:

    **Step 1 — Generate scaffold via CLI:**
    ```
    uv run alembic init -t async migrations
    ```
    This creates:
    - `alembic.ini` (repo root) — keep as-is except for one cosmetic
      tweak below.
    - `migrations/env.py` — **discard** (we replace this).
    - `migrations/script.py.mako` — **keep as-is** (stock async
      template; Phase 3+ relies on it).
    - `migrations/README` — keep.
    - `migrations/versions/` (empty dir) — keep; will receive our
      hand-written 0001 revision.

    **Step 2 — Tidy alembic.ini:**
    Per PATTERNS.md §alembic.ini: the runtime `sqlalchemy.url` is
    overridden by env.py's `config.set_main_option()`, so the value in
    `alembic.ini` is effectively a placeholder. Leave it at whatever
    the generator produced (likely `driver://user:pass@localhost/dbname`)
    or cosmetically set it to `sqlite+aiosqlite:///dojo.db` for clarity.
    Do NOT depend on this value — env.py's override is the source of
    truth (D-01).

    Add two `# ABOUTME:` lines at the top of `alembic.ini` (INI uses
    `#` for comments). Example:
    ```
    # ABOUTME: Alembic CLI config.
    # ABOUTME: Runtime sqlalchemy.url is overridden by migrations/env.py (D-01).
    ```

    **Step 3 — Replace `migrations/env.py` with the drop-in:**
    Paste the drop-in from 01-RESEARCH.md lines 582-652 verbatim into
    `migrations/env.py`, overwriting the generator's output. Key
    structural preservations (per PATTERNS.md):

    1. Two-line `# ABOUTME:` header at top.
    2. Module docstring: `"""Async Alembic environment wired to the
       Dojo pydantic-settings singleton."""` (for interrogate).
    3. `config.set_main_option("sqlalchemy.url",
       get_settings().database_url)` — replaces ini value (D-01).
    4. `from app.infrastructure.db.session import Base  # noqa: F401`
       — the `noqa: F401` is INTENTIONAL (M9 defense: importing Base
       transitively imports model modules in Phase 3+; Phase 1 has no
       models but the structural import stays).
    5. `target_metadata = Base.metadata`.
    6. `run_migrations_offline()`, `do_run_migrations(connection)`,
       `run_async_migrations()` (async), `run_migrations_online()` —
       all four functions as in the drop-in, each with a sphinx-style
       docstring (interrogate 100%).
    7. Module-level conditional at end:
       ```python
       if context.is_offline_mode():
           run_migrations_offline()
       else:
           run_migrations_online()
       ```

    **Do NOT** import `migrations.env` from any test code — per New
    Pitfall 5, env.py's `asyncio.run(run_async_migrations())` clashes
    with pytest-asyncio's running loop. Tests (Plan 05) use
    `alembic.command.upgrade` wrapped in `asyncio.to_thread`.

    **Step 4 — Write migrations/versions/0001_initial.py:**
    Paste the drop-in from 01-RESEARCH.md lines 538-564 verbatim.
    Preserve:

    1. Two-line `# ABOUTME:` header: "Initial empty Alembic revision." /
       "Creates the alembic_version tracking table as a side effect."
    2. Docstring header (Alembic convention): `"""initial\n\nRevision
       ID: 0001\nRevises:\nCreate Date: 2026-04-20 00:00:00.000000\n\n"""`.
    3. `revision: str = "0001"`, `down_revision: str | None = None`,
       `branch_labels: str | Sequence[str] | None = None`,
       `depends_on: str | Sequence[str] | None = None`.
    4. `def upgrade() -> None:` body is docstring only: `"""No schema
       changes in Phase 1; Phase 3 adds real tables."""` (no `pass` —
       the docstring is the body; interrogate counts the docstring).
    5. `def downgrade() -> None:` body is docstring only: `"""No-op;
       initial revision has nothing to undo."""`.

    **Naming note (D-10):** the filename `0001_initial.py` is fine;
    alternatively a date-stamp format works. Use `0001_initial.py` per
    the drop-in unless `alembic init` already created a date-stamped
    placeholder that should be overwritten — in that case delete the
    placeholder first.

    **Step 5 — Smoke test the migration pipeline:**
    ```bash
    rm -f /tmp/dojo.smoke.db
    DATABASE_URL=sqlite+aiosqlite:////tmp/dojo.smoke.db \
        uv run alembic upgrade head
    # Confirm alembic_version table was created
    sqlite3 /tmp/dojo.smoke.db '.schema' | grep -q 'alembic_version'
    # Downgrade smoke
    DATABASE_URL=sqlite+aiosqlite:////tmp/dojo.smoke.db \
        uv run alembic downgrade base
    rm -f /tmp/dojo.smoke.db
    ```
    Both commands must exit zero. The `grep` for `alembic_version` MUST
    succeed — that is SC #3.

    **Anti-patterns to avoid:**
    - Do NOT manually edit the sync Alembic template into env.py
      (PITFALL C4). Always use the `-t async` scaffold.
    - Do NOT `import app.infrastructure.db.session` in any way other
      than `from app.infrastructure.db.session import Base  # noqa:
      F401` — M9 relies on this one-line import for future eager model
      loading.
    - Do NOT add `op.create_table` to `0001_initial.py` — D-08 mandates
      empty upgrade body. Phase 3 owns the first real-schema migration.
  </action>
  <verify>
    <automated>test -f alembic.ini &amp;&amp; test -f migrations/env.py &amp;&amp; test -f migrations/script.py.mako &amp;&amp; test -f migrations/versions/0001_initial.py &amp;&amp; grep -c '^# ABOUTME:' alembic.ini | grep -q '^2$' &amp;&amp; grep -c '^# ABOUTME:' migrations/env.py | grep -q '^2$' &amp;&amp; grep -c '^# ABOUTME:' migrations/versions/0001_initial.py | grep -q '^2$' &amp;&amp; grep -q 'from app.infrastructure.db.session import Base' migrations/env.py &amp;&amp; grep -q 'from app.settings import get_settings' migrations/env.py &amp;&amp; grep -q 'set_main_option' migrations/env.py &amp;&amp; grep -q 'async_engine_from_config' migrations/env.py &amp;&amp; grep -q 'revision: str = "0001"' migrations/versions/0001_initial.py &amp;&amp; rm -f /tmp/dojo.smoke.db &amp;&amp; DATABASE_URL=sqlite+aiosqlite:////tmp/dojo.smoke.db uv run alembic upgrade head &amp;&amp; sqlite3 /tmp/dojo.smoke.db '.schema' | grep -q 'alembic_version' &amp;&amp; rm -f /tmp/dojo.smoke.db</automated>
  </verify>
  <done>
    All four Alembic files exist; env.py wired to settings; empty
    initial revision written; `alembic upgrade head` against a fresh
    tmp DB creates the `alembic_version` table (SC #3 gate passes).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `DATABASE_URL` env var → `create_async_engine` | untrusted URL interpreted as a DB connection string |
| Alembic CLI → `env.py` imports | `env.py` pulls `app.settings.get_settings()`, which reads `.env` |
| DB connection → SQLite PRAGMA listener | `dbapi_conn` is trusted (owned by SQLAlchemy), but PRAGMA SQL is fixed strings |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1-PATH-02 | Tampering | `migrations/env.py` reading `DATABASE_URL` | mitigate | env.py reads from `get_settings().database_url` (pydantic-settings), not from externally-controlled paths. Settings fields are typed; pydantic rejects malformed URLs. Per planning guidance point 8: explicitly out-of-scope-this-plan in the broad sense but covered by the settings-driven design. |
| T-1-SQLi-02 | Tampering | PRAGMA SQL in `_configure_sqlite` | mitigate | The three PRAGMA statements are fixed string literals — no variable interpolation — so there is no SQL-injection surface. Dialect guard (`engine.dialect.name == "sqlite"`) prevents cross-dialect execution. |
| T-1-ELEVATION-01 | Elevation of Privilege | `PRAGMA foreign_keys=ON` | mitigate | Enabling foreign keys is a security positive (data-integrity). The WAL + busy_timeout PRAGMAs improve concurrent-write reliability without expanding trust. |
| T-1-DOS-01 | Denial of Service | Alembic `asyncio.run()` at module top | mitigate | env.py runs `asyncio.run()` only in standalone CLI mode (PITFALL New 5). Tests (Plan 05) use `alembic.command.upgrade` via `asyncio.to_thread` to avoid clashing with pytest-asyncio's loop. |
| T-1-CONFIG-02 | Information Disclosure | `alembic.ini` `sqlalchemy.url` placeholder | accept | env.py overrides at runtime; ini value is effectively cosmetic. No secret leakage risk because it is a local-SQLite URL, not a password-bearing string. |
| T-1-DB-LEAK-01 | Information Disclosure | `dojo.db`, `dojo.db-wal`, etc. on disk | mitigate | All DB artefacts are gitignored (Plan 01 Task 2). Phase 1 has no user data; empty `alembic_version` table only. |
</threat_model>

<verification>
Run after all tasks complete:

```bash
# All five artefacts exist
ls -l app/infrastructure/db/session.py alembic.ini migrations/env.py \
      migrations/script.py.mako migrations/versions/0001_initial.py

# Linters
uv run ruff format --check app/infrastructure/db/session.py migrations/env.py migrations/versions/0001_initial.py
uv run ruff check app/infrastructure/db/session.py migrations/env.py migrations/versions/0001_initial.py
uv run interrogate -c pyproject.toml app/infrastructure/db/session.py

# SC #3 gate: fresh DB upgrade + schema check
rm -f /tmp/dojo.verify.db
DATABASE_URL=sqlite+aiosqlite:////tmp/dojo.verify.db uv run alembic upgrade head
sqlite3 /tmp/dojo.verify.db '.schema' | grep -q 'alembic_version' && echo "SC#3 OK"
rm -f /tmp/dojo.verify.db
```
</verification>

<success_criteria>
- `app/infrastructure/__init__.py` and `app/infrastructure/db/__init__.py`
  exist with ABOUTME headers (subpackage markers required for
  `app.infrastructure.db.session` import resolution).
- `app/infrastructure/db/session.py` exposes `Base`, `engine`, and
  `AsyncSessionLocal`; dialect-guarded PRAGMA listener fires only on
  SQLite.
- `migrations/env.py` reads `DATABASE_URL` exclusively from
  `app.settings.get_settings()` — single source of truth (D-01).
- `alembic upgrade head` on a fresh aiosqlite DB creates the
  `alembic_version` table (SC #3 gate).
- `alembic downgrade base` runs without error (bidirectional contract
  honored).
- Plan 04 (web routes + main.py) can start in parallel with this plan
  (no file overlap).
- Plan 05 (tests) can start after this plan commits — conftest.py
  depends on `alembic.command.upgrade` + the env.py drop-in working.
</success_criteria>

<output>
After completion, create
`.planning/phases/01-project-scaffold-tooling/01-03-SUMMARY.md` per the
execute-plan template. Summary must note: (a) both
`app/infrastructure/__init__.py` and `app/infrastructure/db/__init__.py`
created unconditionally as subpackage markers, (b) the exact
revision-ID filename produced (e.g., `0001_initial.py` vs
`20260420_0000-initial.py`), (c) smoke test result on `/tmp/dojo.smoke.db`
showing `alembic_version` created.
</output>
</content>
</invoke>