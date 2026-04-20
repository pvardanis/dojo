---
phase: 01-project-scaffold-tooling
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - .gitignore
  - .env.example
  - CLAUDE.md
autonomous: true
requirements:
  - OPS-01
  - TEST-02
  - LLM-03
tags:
  - python
  - tooling
  - pyproject
  - uv
  - pydantic-settings
user_setup: []

must_haves:
  truths:
    - "A fresh clone can run `uv sync` and get a reproducible dev
      environment with every Phase 1 tool pinned"
    - "`.env` is git-ignored; `.env.example` documents every Settings
      field with a safe placeholder"
    - "`pyproject.toml` configures ruff (79-char), pytest (asyncio auto,
      session fixture loop, filterwarnings=error), interrogate (100%),
      ty (pinned exact) in a single file"
    - "`CLAUDE.md` is under 150 lines and covers the six spec §8.4
      sections (project purpose, layout pointer, run instructions, DIP
      boundary location, Protocol-vs-function clarifier, test strategy)"
  artifacts:
    - path: "pyproject.toml"
      provides: "Project + tool config (deps, ruff, pytest, interrogate,
        ty, uv package mode)"
      contains: "fastapi>=0.118"
    - path: ".gitignore"
      provides: "Ignore rules for venv, cache, secrets, local DB"
      contains: ".env"
    - path: ".env.example"
      provides: "Committed template for .env with all Settings fields"
      contains: "ANTHROPIC_API_KEY"
    - path: "CLAUDE.md"
      provides: "Distilled project instructions for future Claude
        sessions, ≤150 lines, six required sections"
      contains: "## Project"
  key_links:
    - from: "pyproject.toml"
      to: "uv resolution"
      via: "uv sync reads [project].dependencies + [dependency-groups]"
      pattern: "\\[dependency-groups\\]"
    - from: ".gitignore"
      to: ".env protection"
      via: "grep -qE '^\\.env$' .gitignore"
      pattern: "^\\.env$"
    - from: "pyproject.toml"
      to: "pytest config"
      via: "[tool.pytest.ini_options] sets asyncio_mode + filterwarnings"
      pattern: "asyncio_mode = \"auto\""
---

<objective>
Establish the project's root configuration: `pyproject.toml` with the
full dependency and tool configuration, `.gitignore` with .env/DB
protection, `.env.example` documenting every Settings field, and a
reconciled `CLAUDE.md` that hits all six spec §8.4 sections under 150
lines.

Purpose: these four files are the foundation every other Phase 1 plan
builds on. `pyproject.toml` gates `uv sync`; `.gitignore` protects the
API key; `.env.example` documents the Settings surface; `CLAUDE.md` is
the agent-facing convention document that future sessions read first.

Output: four repo-root files committed. `uv sync` resolves without
errors. `grep -qE '^\.env$' .gitignore` succeeds. `wc -l CLAUDE.md`
≤150.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/01-project-scaffold-tooling/01-CONTEXT.md
@.planning/phases/01-project-scaffold-tooling/01-RESEARCH.md
@.planning/phases/01-project-scaffold-tooling/01-PATTERNS.md
@docs/superpowers/specs/2026-04-18-dojo-design.md
@CLAUDE.md

<interfaces>
This plan creates foundational config. No Python interfaces yet.

**Settings field contract** (established here via `.env.example`, full
pydantic class lands in Plan 02):

```
ANTHROPIC_API_KEY  : SecretStr, required (with dev-placeholder default per D-18 + A7)
DATABASE_URL       : str, default "sqlite+aiosqlite:///dojo.db"
LOG_LEVEL          : str, default "INFO"
RUN_LLM_TESTS      : bool, default False
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create pyproject.toml with pinned deps + tool config</name>
  <files>pyproject.toml</files>
  <read_first>
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      925-1012 (verbatim drop-in)
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      201-231 (verified version table — confirm floors match drop-in)
    - .planning/phases/01-project-scaffold-tooling/01-CONTEXT.md
      decisions D-04, D-15, D-16, D-18, D-20
    - .planning/phases/01-project-scaffold-tooling/01-PATTERNS.md lines
      437-464 (key structural elements commentary)
  </read_first>
  <action>
    Paste the `pyproject.toml` drop-in from 01-RESEARCH.md lines
    925-1012 into the repo-root `pyproject.toml`. Verify these locked
    structural elements are present verbatim (per D-04, D-15, D-16,
    D-18, D-20):

    1. `[build-system]` block with `requires = ["hatchling"]` and
       `build-backend = "hatchling.build"` (per New Pitfall 6 — required
       pair for `[tool.uv] package = true`).
    2. `[project]` with `name = "dojo"`, `version = "0.1.0"`,
       `requires-python = ">=3.12,<3.13"` (tight upper bound per spec).
    3. `[project].dependencies` — exact floors from the drop-in:
       fastapi>=0.118, uvicorn[standard]>=0.30, jinja2>=3.1,
       python-multipart>=0.0.9, pydantic>=2.9, pydantic-settings>=2.8,
       sqlalchemy[asyncio]>=2.0.38, aiosqlite>=0.22.1, alembic>=1.13,
       structlog>=24.4.
    4. `[dependency-groups].dev` — ruff>=0.8, **ty==0.0.31** (exact pin
       per D-16 — NOT a floor), interrogate>=1.7, pytest>=8.3,
       pytest-asyncio>=1.0, pytest-cov>=5.0, pytest-repeat>=0.9.4,
       pre-commit>=3.7. `pytest-repeat` resolves Open Question #2 per
       planning guidance point 5.
    5. `[tool.uv] package = true` (D-20 — enables editable install for
       Alembic's `from app.infrastructure.db import Base`).
    6. `[tool.hatch.build.targets.wheel] packages = ["app"]`.
    7. `[tool.ruff] line-length = 79`, `target-version = "py312"`;
       `[tool.ruff.lint] select = ["E", "F", "W", "I", "B", "UP",
       "SIM"]`; `[tool.ruff.format] quote-style = "double"`.
    8. `[tool.pytest.ini_options]` — `asyncio_mode = "auto"` (D-04),
       `asyncio_default_fixture_loop_scope = "session"` (New Pitfall 1),
       `addopts = ["--strict-markers", "--strict-config", "-ra",
       "--cov=app", "--cov-report=term-missing"]`,
       `filterwarnings = ["error"]` (per planning guidance point 4 —
       start ON; resolve Assumption A5 by keeping targeted ignores
       as a follow-up if needed), `testpaths = ["tests"]`.
    9. `[tool.coverage.run] branch = true`, `source = ["app"]`.
    10. `[tool.interrogate] fail-under = 100` (D-15), `verbose = 2`,
        `exclude = ["migrations", "tests", "docs"]`,
        `ignore-init-method = true`, `ignore-init-module = true`,
        `ignore-magic = true`. DO NOT add `app/application/ports.py` to
        `exclude` (D-15 is strict on this).
    11. `[tool.ty]` block present but empty (D-16 — tighten in Phase 2).

    Do NOT add a top `# ABOUTME:` comment to pyproject.toml (TOML does
    not follow the Python ABOUTME convention; the file is config, not
    code). Verify ruff format leaves the file alone — run `uv run ruff
    format --check pyproject.toml` after creation (it should skip TOML
    quietly).

    After writing the file, run `uv sync` and confirm it resolves
    without errors. `uv sync` WILL create a `uv.lock` — commit it with
    this task (lock file is part of reproducible install).
  </action>
  <verify>
    <automated>uv sync &amp;&amp; uv tree --depth 1 | grep -q 'fastapi' &amp;&amp; uv tree --depth 1 | grep -q 'pytest-asyncio' &amp;&amp; test -f uv.lock &amp;&amp; grep -q 'asyncio_mode = "auto"' pyproject.toml &amp;&amp; grep -q 'fail-under = 100' pyproject.toml &amp;&amp; grep -q 'ty==0.0.31' pyproject.toml &amp;&amp; grep -q 'package = true' pyproject.toml &amp;&amp; grep -q 'filterwarnings = \["error"\]' pyproject.toml</automated>
  </verify>
  <done>
    `pyproject.toml` exists, `uv sync` succeeds, `uv.lock` is written,
    and every grep above matches. `uv tree --depth 1` shows fastapi,
    pytest-asyncio, ty, pydantic-settings, sqlalchemy at the expected
    floors.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create .gitignore and .env.example</name>
  <files>.gitignore, .env.example</files>
  <read_first>
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      717-736 (`.env.example` drop-in)
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      1256-1286 (`.gitignore` drop-in)
    - .planning/phases/01-project-scaffold-tooling/01-CONTEXT.md decision
      D-18 (Settings surface); LLM-03 requirement wording
  </read_first>
  <action>
    Create `.gitignore` at repo root — paste the drop-in from
    01-RESEARCH.md lines 1256-1286 verbatim. Verify it contains at
    minimum: `__pycache__/`, `*.py[cod]`, `*.egg-info/`, `.venv/`,
    `.uv/`, `uv-cache/`, `.pytest_cache/`, `.coverage`, `htmlcov/`,
    `dist/`, `build/`, `.env` (on its own line — LLM-03 requires
    `grep -qE '^\.env$' .gitignore` to succeed), `dojo.db`,
    `dojo.db-journal`, `dojo.db-wal`, `dojo.db-shm`, `.idea/`,
    `.vscode/`.

    Create `.env.example` at repo root — paste the drop-in from
    01-RESEARCH.md lines 717-736 verbatim. Verify it:
    - Has two `# ABOUTME:` header lines (dotenv uses `#` for comments,
      convention applies).
    - Documents every field in the locked Settings surface (D-18):
      `ANTHROPIC_API_KEY=sk-ant-your-key-here` (with the
      "replace-this-for-Phase-3" comment per Open Question #1
      resolution in planning guidance),
      `DATABASE_URL=sqlite+aiosqlite:///dojo.db`, `LOG_LEVEL=INFO`,
      `RUN_LLM_TESTS=0`.
    - Includes the "Real env vars win over .env values" note so
      developers know the precedence.

    Do NOT create the real `.env` file — that is user-authored and
    gitignored. Do NOT add an ABOUTME header to `.gitignore` (it is
    conventionally a bare ignore file; RESEARCH.md drop-in does not
    include one).
  </action>
  <verify>
    <automated>test -f .gitignore &amp;&amp; test -f .env.example &amp;&amp; grep -qE '^\.env$' .gitignore &amp;&amp; grep -qE '^dojo\.db$' .gitignore &amp;&amp; grep -q '__pycache__/' .gitignore &amp;&amp; grep -q 'ANTHROPIC_API_KEY=' .env.example &amp;&amp; grep -q 'DATABASE_URL=sqlite+aiosqlite' .env.example &amp;&amp; grep -q 'LOG_LEVEL=' .env.example &amp;&amp; grep -q 'RUN_LLM_TESTS=' .env.example &amp;&amp; grep -c '^# ABOUTME:' .env.example | grep -q '^2$' &amp;&amp; test ! -f .env</automated>
  </verify>
  <done>
    `.gitignore` and `.env.example` exist, `.env` is NOT present, and
    every grep above matches. `.env.example` has exactly two ABOUTME
    comment lines and all four Settings fields documented.
  </done>
</task>

<task type="auto">
  <name>Task 3: Reconcile repo-root CLAUDE.md against spec §8.4</name>
  <files>CLAUDE.md</files>
  <read_first>
    - CLAUDE.md (the existing repo-root file — 123 lines, already
      committed)
    - docs/superpowers/specs/2026-04-18-dojo-design.md §8.4 (lines
      535-547 per PATTERNS.md — "six required sections, under 150 lines")
    - .planning/phases/01-project-scaffold-tooling/01-CONTEXT.md
      "Specific Ideas" — "Repo-root CLAUDE.md already exists and is
      close to the target state; task is to reconcile, not rewrite"
    - .planning/phases/01-project-scaffold-tooling/01-PATTERNS.md lines
      569-588 (CLAUDE.md reconcile guidance)
  </read_first>
  <action>
    Read `CLAUDE.md` (repo root) in full. It currently has these
    headings per `grep '^##' CLAUDE.md`:
    - ## Project (line 4) — project purpose
    - ## Technology Stack (line 20) — library picks
    - ## Conventions (line 37) — file/style conventions + Protocol vs
      function clarifier
    - ## Architecture (line 65) — DIP boundary pointer
    - ## Project Skills (line 95) — skills discovery
    - ## GSD Workflow Enforcement (line 102) — entry points
    - ## Developer Profile (line 118) — profile placeholder

    Reconcile against spec §8.4's six required sections:
    1. Project purpose in one paragraph → covered by `## Project` (line
       4) ✓
    2. Package layout pointer (point at `docs/architecture/` and `app/`)
       → covered by `## Architecture` (line 65) ✓ if it references
       `docs/architecture/`; verify the link is present, add a one-line
       pointer if missing.
    3. How to run (`make install && make run`) → **verify** — the
       existing file references `make install && make run` in `##
       Project` but should also be mentioned in an explicit "How to
       run" bullet or under `## Technology Stack`. Add a one-line run
       pointer under `## Project` if not explicit.
    4. Where the DIP boundaries are (point at `app/application/ports.py`)
       → covered by `## Architecture` — confirm the file path
       `app/application/ports.py` appears literally.
    5. Protocol-vs-function clarifier (project-local copy) → covered by
       `## Conventions` "On Protocol vs function (project-local
       clarifier)" block ✓
    6. Test strategy summary → covered by `## Conventions` "TDD is
       mandatory" paragraph — verify it mentions "hand-written fakes at
       every DIP boundary" and "no `Mock()` for behavior testing"; if
       not, add a one-line summary.

    After reconciliation:
    - Line count MUST stay ≤150. Current is 123, giving ~25 lines of
      headroom. If the reconcile push would exceed 150, trim by
      removing the `## Developer Profile` placeholder block (lines
      118-123) — it can be regenerated via `/gsd-profile-user` later
      and is explicitly marked as "managed by generate-claude-profile,
      do not edit manually."
    - Do NOT rewrite sections already correct. The existing file is
      close to target; minimal deltas only.
    - Keep the two `# ABOUTME:` header convention out of CLAUDE.md —
      this is an .md instruction file, not Python source.

    If reconciliation produces zero deltas (the existing file already
    hits all six sections), the task is still considered done — record
    "no changes required" in the commit message and move on.
  </action>
  <verify>
    <automated>test $(wc -l &lt; CLAUDE.md) -le 150 &amp;&amp; grep -q 'app/application/ports.py' CLAUDE.md &amp;&amp; grep -q 'make install' CLAUDE.md &amp;&amp; grep -q 'Protocol vs function' CLAUDE.md &amp;&amp; grep -q 'docs/architecture' CLAUDE.md &amp;&amp; grep -q -i 'fake' CLAUDE.md</automated>
  </verify>
  <done>
    `CLAUDE.md` is ≤150 lines and every grep above matches. Existing
    content preserved; only deltas needed for §8.4 compliance were
    written.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Local shell → git repo | Developer could accidentally `git add .env` |
| `.env` file → process env | pydantic-settings reads on boot (Plan 02) |
| Log sink → stdout/files | Any logged value could leak if SecretStr is unwrapped |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1-SECRETS-01 | Information Disclosure | `.env` | mitigate | `.gitignore` contains `.env` on its own line; verified by `grep -qE '^\.env$' .gitignore`. `.env.example` ships as the committed template — real `.env` never committed. |
| T-1-LLM03-01 | Information Disclosure | `.env.example` contents | mitigate | `.env.example` uses literal placeholder `sk-ant-your-key-here` — never a real key. Explicit comment in file says "replace this for Phase 3 onward." |
| T-1-DEPS-01 | Tampering | `pyproject.toml` + `uv.lock` | mitigate | Version floors pinned; `ty==0.0.31` exact-pinned (D-16) to avoid beta churn silently breaking CI. `uv.lock` committed in this task for reproducible installs. |
| T-1-XSS-01 | Information Disclosure | Jinja templates | out-of-scope-this-plan | Templates land in Plan 04; autoescape verified there (Starlette default per FLAG 10). |
| T-1-SQLi-01 | Tampering | DB inputs | out-of-scope-this-phase | Phase 1 has no user-input paths reaching the DB; explicitly noted in planning guidance point 8. Phase 2+ domain code owns input validation. |
| T-1-PATH-01 | Tampering | migrations/env.py paths | out-of-scope-this-plan | env.py lands in Plan 03; reads only from settings (not externally-controlled paths). |
</threat_model>

<verification>
Run after all 3 tasks complete:

```bash
# Config is valid and installable
uv sync

# Python version pin honored
uv run python -c "import sys; assert sys.version_info[:2] == (3, 12)"

# Dep floors present (sampling)
uv tree --depth 1 | grep -E 'fastapi|pytest-asyncio|ty|pydantic-settings|sqlalchemy'

# Secrets protection
grep -qE '^\.env$' .gitignore && ! test -f .env
grep -c '^# ABOUTME:' .env.example  # → 2

# CLAUDE.md shape
wc -l CLAUDE.md  # ≤ 150
grep -c '^## ' CLAUDE.md  # sanity — expect 6-7 top-level sections
```
</verification>

<success_criteria>
- `uv sync` exits zero and writes `uv.lock`.
- `uv.lock` is committed.
- `.env` does not exist in the working tree; `.env.example` does.
- `grep -qE '^\.env$' .gitignore` succeeds (LLM-03 gate).
- `pyproject.toml` has all 11 locked structural elements from Task 1.
- `CLAUDE.md` is ≤150 lines and hits the six spec §8.4 sections.
- Plan 02 (settings/logging) can start immediately after this plan
  commits, because `pyproject.toml` is now in place.
</success_criteria>

<output>
After completion, create
`.planning/phases/01-project-scaffold-tooling/01-01-SUMMARY.md` per the
execute-plan template. Summary must note: (a) `uv.lock` created and
committed, (b) whether CLAUDE.md required deltas or was already
compliant, (c) resolved Open Question #1 (SecretStr default — deferred
to Plan 02 settings task), #2 (`pytest-repeat` chosen — added to dev
deps), #3 (`ty check app migrations` — Makefile scope deferred to Plan
06 per planning guidance 4).
</output>
</content>
</invoke>