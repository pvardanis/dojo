# Phase 1: Project Scaffold & Tooling - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 01-project-scaffold-tooling
**Areas discussed:** DB portability posture (interactive); pytest-asyncio + DB fixtures, Alembic baseline migration, Scaffold depth + landing page, Tooling micro-decisions (Claude's discretion)

---

## DB portability posture

| Option | Description | Selected |
|--------|-------------|----------|
| (a) SQLite-first | Hardcode `sqlite+aiosqlite://` URL, unconditional PRAGMA setup, accept a future refactor if a DB swap ever happens. Aligns with PROJECT.md "localhost forever" stance. Matches YAGNI strictly. | |
| (b) Portable-by-construction | `DATABASE_URL` pydantic-settings field with sqlite default, dialect-guarded PRAGMA event listener, Alembic `env.py` reads from settings. ~3-5 extra lines beyond the correctness-mandated work. | ✓ |
| (c) Portable + dialect-agnostic abstractions | Explicit DB adapter layer, dialect-agnostic migrations, etc. Overkill for this project. | |

**User's choice:** (b) portable-by-construction.
**Notes:** User raised the question explicitly ("does the system support DB change in case I decide to go with postgres for example in the future?"). Claude's honest read was that the marginal Phase 1 cost is trivial (~3-5 lines in `session.py` for the dialect guard) because most of the "portability work" — DATABASE_URL in settings, Alembic reading from pydantic-settings — is already mandated by correctness concerns (PITFALLS.md C4: no parallel config sources). The ceiling on a future swap is meaningfully lower with (b), even though (b) doesn't make a swap free: Phase 3 column-type decisions and future-migration DDL discipline carry additional portability cost that Phase 1 cannot pre-pay. User accepted the recommendation without further discussion.

---

## pytest-asyncio + DB fixtures (Claude's discretion)

No interactive question posed — user selected "None — your call on the rest" and delegated the remaining three gray areas.

**Claude's call:**
- `asyncio_mode = "auto"` in `pyproject.toml`
- Session-scoped `event_loop_policy` fixture (pytest-asyncio 0.24+ canonical, not the deprecated `event_loop` fixture)
- Session-scoped async engine bound to a tmp-file SQLite DB (not `:memory:` — cross-connection visibility issues in async SQLAlchemy)
- `alembic upgrade head` once per test session against the tmp DB (exercises the migration pipeline in tests)
- Function-scoped session with outer-transaction rollback for per-test isolation
- SC #4 ("10 times in a row") verified via a dedicated target using `pytest-repeat`

**Rationale summary:** PITFALLS.md M8 is explicit that the canonical pytest-asyncio pattern has moved between versions and older tutorials are wrong. The tmp-file choice over `:memory:` is load-bearing — async SQLAlchemy with `:memory:` fails silently as soon as a fixture opens more than one connection.

---

## Alembic baseline migration (Claude's discretion)

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Empty initial revision | No DDL in the first revision. `alembic upgrade head` creates `alembic_version` table as a side effect; that satisfies SC #3's "expected tables" language. Canonical Alembic pattern. | ✓ |
| (b) Placeholder `_schema_version` table | Add a trivial throwaway table to prove end-to-end async migration. Phase 3 has to drop it. | |
| (c) Defer migration creation to Phase 3 | Phase 1 only wires `env.py`; re-interprets SC #3 to "wiring proven." Conflicts with the explicit SC #3 wording ("applies an async migration"). | |

**Claude's call:** (a). This is the canonical Alembic pattern — every project's first `upgrade head` creates `alembic_version` before any real DDL. It proves the full async-migration pipeline (C4 is gated) without introducing throwaway tables. Phase 3 runs `alembic revision --autogenerate` on top of this baseline to add the real entity tables.

---

## Scaffold depth + landing page (Claude's discretion)

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Absolute minimum | Only create files needed to boot. Phase 2+ creates `app/{domain,application,infrastructure,web}/` subdirs as each phase touches them. `/` renders a Jinja home page + separate `/health` JSON endpoint. | ✓ |
| (b) Full `app/` tree with empty `__init__.py` + ABOUTME shells | Pre-create every subdirectory Phase 2+ will eventually need. Phase 2 walks into an existing skeleton. | |

**Claude's call:** (a) + both `/` (Jinja home) and `/health` (JSON). Rationale: YAGNI — no benefit to pre-creating empty `__init__.py`s when Phase 2 will touch them anyway. SC #2 wording ("minimal health/home route") explicitly uses both words, so two separate routes is the honest read.

---

## Tooling micro-decisions (Claude's discretion)

No interactive questions — folded into CONTEXT.md decisions D-14 through D-20:

- **Pre-commit hook scope:** ruff format → ruff check --fix → ty → interrogate → `pytest tests/unit/ -x --ff` (unit only; full suite in CI). Spec §8.2 says "pre-commit runs... pytest" — Claude's call narrows this to unit tests to avoid PITFALL M10 (pre-commit pytest degrades dev loop past ~10s and people stop committing).
- **interrogate + Protocol methods:** accept one-line docstrings, do not add `ports.py` to the ignore list. PITFALL M11 mitigated by policy, not by exception.
- **`ty` version:** pin to an exact patch version (not a floor). Document `mypy` as a drop-in fallback in CLAUDE.md but don't pre-install.
- **Structlog:** `ConsoleRenderer` in dev/test, `JSONRenderer` in prod. Tests set log level to `WARNING` via conftest to honour pristine-output rule.
- **Settings surface (day one):** `ANTHROPIC_API_KEY`, `DATABASE_URL`, `LOG_LEVEL`, `RUN_LLM_TESTS`.
- **CI:** single job, Python 3.12, cache `uv` deps keyed on `uv.lock` hash, cancel in-progress PR runs. No Playwright install in Phase 1.
- **Package mode:** `pyproject.toml` declares Dojo as an installable package so Alembic can `import app.infrastructure.db.Base` without PYTHONPATH hacks.

## Deferred Ideas

- Full plug-and-play Postgres swap (Phase 3+ concern: column types, migration DDL discipline, connection pool)
- Playwright in CI (Phase 7)
- `mypy` as `ty` fallback (re-open if `ty` blocks Phase 2/3)
- Import-linter for domain/application layer boundaries (Phase 2, where those layers first exist)
- Playwright + HTMX flake mitigations (Phase 5/7)
