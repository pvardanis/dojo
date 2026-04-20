---
phase: 01-project-scaffold-tooling
plan: 02
type: execute
wave: 2
depends_on:
  - "01-01"
files_modified:
  - app/__init__.py
  - app/settings.py
  - app/logging_config.py
autonomous: true
requirements:
  - OPS-04
  - LLM-03
tags:
  - python
  - pydantic-settings
  - structlog
  - secrets
  - logging

must_haves:
  truths:
    - "`get_settings()` returns a cached Settings singleton with
      `anthropic_api_key` typed as `SecretStr` — repr renders as
      `'**********'` and the key never leaves settings except via
      explicit `.get_secret_value()` at the SDK boundary"
    - "`configure_logging(log_level)` can be called once at process
      startup and is idempotent (structlog's `configure_once`)"
    - "Every module can `from app.logging_config import get_logger; log
      = get_logger(__name__)` and write structured log events without
      raising"
    - "Dev mode renders to `ConsoleRenderer`; `DOJO_ENV=prod` switches
      to `JSONRenderer`"
  artifacts:
    - path: "app/__init__.py"
      provides: "Top-level app package marker (D-20 installable package)"
      contains: "# ABOUTME:"
    - path: "app/settings.py"
      provides: "Settings class (pydantic-settings) + @lru_cache
        get_settings() singleton"
      exports: ["Settings", "get_settings"]
      contains: "anthropic_api_key"
    - path: "app/logging_config.py"
      provides: "configure_logging + get_logger helpers"
      exports: ["configure_logging", "get_logger"]
      contains: "configure_once"
  key_links:
    - from: "app/settings.py"
      to: "pydantic-settings BaseSettings"
      via: "SettingsConfigDict(env_file='.env', extra='ignore')"
      pattern: "SettingsConfigDict"
    - from: "app/settings.py"
      to: "SecretStr protection"
      via: "anthropic_api_key: SecretStr"
      pattern: "SecretStr"
    - from: "app/logging_config.py"
      to: "structlog.configure_once"
      via: "env-switched processors list"
      pattern: "configure_once"
    - from: "app/logging_config.py"
      to: "stdlib logging.basicConfig"
      via: "sets level, stream=sys.stdout, format='%(message)s'"
      pattern: "logging\\.basicConfig"
---

<objective>
Create the two cross-cutting Python modules every future Phase 1+ file
depends on: `app/settings.py` (pydantic-settings singleton with
`SecretStr` for the API key) and `app/logging_config.py` (structlog
configuration + `get_logger(__name__)` helper).

Purpose: these two files resolve LLM-03 (API-key loading + non-leakage)
and OPS-04 (structlog at app startup + shared `get_logger` helper). Plan
03 (DB) and Plan 04 (web) both depend on `app.settings.get_settings`;
`app.main` depends on both `configure_logging` and `get_logger`.

Output: two Python files in `app/` — both with `# ABOUTME:` headers,
≤100 lines, 79-char-clean, 100% docstring coverage.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/01-project-scaffold-tooling/01-CONTEXT.md
@.planning/phases/01-project-scaffold-tooling/01-RESEARCH.md
@.planning/phases/01-project-scaffold-tooling/01-PATTERNS.md
@.planning/phases/01-project-scaffold-tooling/01-01-SUMMARY.md
@pyproject.toml
@CLAUDE.md

<interfaces>
<!-- Types and contracts downstream plans will import. Established by this plan. -->

From `app/settings.py` (created in this plan):
```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    anthropic_api_key: SecretStr  # default per D-18 + Open Q1 (see action below)
    database_url: str = "sqlite+aiosqlite:///dojo.db"
    log_level: str = "INFO"
    run_llm_tests: bool = False

def get_settings() -> Settings: ...  # @lru_cache'd singleton
```

From `app/logging_config.py` (created in this plan):
```python
def configure_logging(log_level: str = "INFO") -> None: ...
def get_logger(name: str) -> Any: ...  # structlog.get_logger(name)
```

**Consumers** (downstream plans):
- `app/infrastructure/db/session.py` (Plan 03) imports `get_settings`
- `migrations/env.py` (Plan 03) imports `get_settings`
- `app/main.py` (Plan 04) imports `configure_logging`, `get_logger`, `get_settings`
- `tests/unit/test_settings.py` (Plan 05) imports `Settings`, `get_settings`
- `tests/integration/test_logging_smoke.py` (Plan 05) imports
  `configure_logging`, `get_logger`
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create app/ package + app/__init__.py + app/settings.py</name>
  <files>app/__init__.py, app/settings.py</files>
  <read_first>
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      668-740 (verbatim drop-in for settings.py + .env.example note)
    - .planning/phases/01-project-scaffold-tooling/01-CONTEXT.md
      decisions D-11 (scaffold depth), D-18 (Settings surface), D-20
      (installable package)
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      1531-1546 (Open Question #1 — SecretStr default resolution)
    - .planning/phases/01-project-scaffold-tooling/01-PATTERNS.md lines
      153-177 (key structural elements + Open Question flag)
  </read_first>
  <action>
    Create directory `app/` (if it does not already exist).

    **Create `app/__init__.py` unconditionally** — D-20 declares Dojo an
    installable package (`[tool.uv] package = true` +
    `[tool.hatch.build.targets.wheel] packages = ["app"]`), so the
    top-level package marker MUST exist for Python and hatchling to
    resolve `app` as a package. This is NOT a D-11 "empty shell"
    prohibition — D-11 prohibits empty sub-package shells that serve no
    structural purpose; the top-level `app/__init__.py` is structurally
    required by D-20.

    Content of `app/__init__.py` (minimal — two-line ABOUTME + module
    docstring only; no re-exports, no `__all__`):

    ```python
    # ABOUTME: Top-level package marker for the Dojo application.
    # ABOUTME: Required by D-20 (installable via uv + hatchling).
    """Dojo application package."""
    ```

    Do NOT add downstream imports or `__version__` here. Composition
    lives in `app/main.py` (Plan 04); the package marker is purely
    structural.

    Create `app/settings.py`. Paste the drop-in from 01-RESEARCH.md
    lines 668-710 (the Python block, not the `.env.example` block which
    was already created in Plan 01 Task 2). Key structural preservations:

    1. Two-line `# ABOUTME:` header at the very top (lines 1-2 of file).
    2. `from __future__ import annotations` — PEP 563 postponed
       evaluation, consistent with project convention.
    3. `from functools import lru_cache`.
    4. `from pydantic import SecretStr`.
    5. `from pydantic_settings import BaseSettings, SettingsConfigDict`.
    6. `class Settings(BaseSettings):` with sphinx-style class
       docstring.
    7. `model_config = SettingsConfigDict(env_file=".env",
       env_file_encoding="utf-8", extra="ignore", case_sensitive=False)`.
    8. Four fields in this exact order (D-18):
       - `anthropic_api_key: SecretStr` — **CRITICAL:** per planning
         guidance point 4 (Open Question #1 resolution), give this a
         default: `anthropic_api_key: SecretStr = SecretStr("dev-placeholder")`.
         This makes `make run` work on a fresh clone without `.env`.
         Phase 3 (Anthropic adapter) raises on first use if the
         placeholder is still present. DO NOT make this field required
         (no default) — that violates planning guidance and SC #2.
       - `database_url: str = "sqlite+aiosqlite:///dojo.db"`
       - `log_level: str = "INFO"`
       - `run_llm_tests: bool = False`
    9. `@lru_cache`'d `get_settings() -> Settings:` with one-line
       docstring "Return the app's singleton settings (cached)." and
       body `return Settings()  # type: ignore[call-arg]`.

    Every public object (`Settings` class, `anthropic_api_key` field is
    not a "public method" so interrogate doesn't demand a docstring for
    it, but `Settings` and `get_settings` need docstrings — interrogate
    at 100% enforces this).

    Add a module-level docstring between the ABOUTME lines and the
    `from __future__` import: `"""Application settings loaded from .env
    via pydantic-settings."""` — interrogate counts the module itself.

    Verify file:
    - `wc -l app/settings.py` ≤ 100 (drop-in is ~45 lines with added
      module docstring).
    - `awk 'length > 79' app/settings.py` returns nothing.
    - `uv run ruff format --check app/settings.py` exits 0.
    - `uv run interrogate -c pyproject.toml app/settings.py` reports
      100%.
    - `uv run python -c "from app.settings import Settings,
      get_settings; s = get_settings(); assert
      s.anthropic_api_key.get_secret_value() == 'dev-placeholder' or
      s.anthropic_api_key.get_secret_value().startswith('sk-');
      assert s.database_url == 'sqlite+aiosqlite:///dojo.db';
      print('OK')"`
  </action>
  <verify>
    <automated>test -f app/__init__.py &amp;&amp; grep -c '^# ABOUTME:' app/__init__.py | grep -q '^2$' &amp;&amp; test -f app/settings.py &amp;&amp; test $(wc -l &lt; app/settings.py) -le 100 &amp;&amp; grep -c '^# ABOUTME:' app/settings.py | grep -q '^2$' &amp;&amp; grep -q 'SecretStr("dev-placeholder")' app/settings.py &amp;&amp; grep -q 'class Settings(BaseSettings)' app/settings.py &amp;&amp; grep -q '@lru_cache' app/settings.py &amp;&amp; grep -q 'def get_settings' app/settings.py &amp;&amp; uv run ruff format --check app/settings.py &amp;&amp; uv run ruff check app/settings.py &amp;&amp; uv run interrogate -c pyproject.toml app/settings.py &amp;&amp; uv run python -c "from app.settings import get_settings; s = get_settings(); assert s.database_url == 'sqlite+aiosqlite:///dojo.db'; assert s.log_level == 'INFO'; assert s.run_llm_tests is False; print('OK')"</automated>
  </verify>
  <done>
    `app/__init__.py` exists with ABOUTME header + docstring only.
    `app/settings.py` exists with ABOUTME header, class + `get_settings`
    defined, `SecretStr("dev-placeholder")` default present, ruff/ty/
    interrogate all pass, Python import smoke test succeeds.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create app/logging_config.py (structlog + get_logger)</name>
  <files>app/logging_config.py</files>
  <read_first>
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      742-805 (verbatim drop-in for logging_config.py)
    - .planning/phases/01-project-scaffold-tooling/01-CONTEXT.md decision
      D-17 (Structlog rendering: dev ConsoleRenderer, tests WARNING,
      prod JSONRenderer); OPS-04 requirement wording
    - .planning/phases/01-project-scaffold-tooling/01-PATTERNS.md lines
      180-199 (key structural elements)
  </read_first>
  <action>
    Create `app/logging_config.py`. Paste the drop-in from
    01-RESEARCH.md lines 742-797 verbatim. Key structural preservations:

    1. Two-line `# ABOUTME:` header at top.
    2. Module docstring: `"""Structlog + stdlib logging configuration
       for Dojo."""` (for interrogate).
    3. `from __future__ import annotations`.
    4. Imports: `logging`, `os`, `sys`, `typing.Any`, `structlog`.
    5. `configure_logging(log_level: str = "INFO") -> None:` with
       sphinx-style docstring "Configure structlog + stdlib logging
       once at app startup."
       - Computes `level = getattr(logging, log_level.upper(),
         logging.INFO)`.
       - Calls `logging.basicConfig(format="%(message)s",
         stream=sys.stdout, level=level)`.
       - Builds `processors: list[structlog.typing.Processor] = [...]`
         with: `merge_contextvars`, `add_log_level`, `TimeStamper(fmt=
         "iso", utc=True)`, `StackInfoRenderer()`, `format_exc_info`.
       - Env-switched final processor (D-17): `if os.getenv("DOJO_ENV",
         "dev") == "prod": processors.append(JSONRenderer())` else
         `processors.append(ConsoleRenderer())`.
       - Calls `structlog.configure_once(processors=processors,
         wrapper_class=structlog.make_filtering_bound_logger(level),
         context_class=dict, logger_factory=structlog.PrintLoggerFactory(),
         cache_logger_on_first_use=True)`. `configure_once` is
         idempotent — safe to call from both lifespan and test fixtures.
    6. `get_logger(name: str) -> Any:` with docstring "Return a
       module-bound structlog logger." Body:
       `return structlog.get_logger(name)`.

    **Anti-pattern — do NOT use:** `import logging; log =
    logging.getLogger(__name__)`. The project convention (CLAUDE.md +
    wiki) is to wrap stdlib via structlog's `get_logger`; the helper
    gives us structured context vars while preserving stdlib ergonomics.

    Verify file:
    - `wc -l app/logging_config.py` ≤ 100.
    - `awk 'length > 79' app/logging_config.py` returns nothing.
    - `uv run ruff format --check app/logging_config.py` passes.
    - `uv run ruff check app/logging_config.py` passes.
    - `uv run interrogate -c pyproject.toml app/logging_config.py` 100%.
    - Import smoke test:
      `uv run python -c "from app.logging_config import
      configure_logging, get_logger; configure_logging('INFO');
      log = get_logger('dojo.smoke'); log.info('hello',
      key='value'); print('OK')"` — must print `OK` and must NOT
      raise; the `hello` log line is allowed in stdout (it is the
      test's artifact).
  </action>
  <verify>
    <automated>test -f app/logging_config.py &amp;&amp; test $(wc -l &lt; app/logging_config.py) -le 100 &amp;&amp; grep -c '^# ABOUTME:' app/logging_config.py | grep -q '^2$' &amp;&amp; grep -q 'def configure_logging' app/logging_config.py &amp;&amp; grep -q 'def get_logger' app/logging_config.py &amp;&amp; grep -q 'configure_once' app/logging_config.py &amp;&amp; grep -q 'ConsoleRenderer' app/logging_config.py &amp;&amp; grep -q 'JSONRenderer' app/logging_config.py &amp;&amp; uv run ruff format --check app/logging_config.py &amp;&amp; uv run ruff check app/logging_config.py &amp;&amp; uv run interrogate -c pyproject.toml app/logging_config.py &amp;&amp; uv run python -c "from app.logging_config import configure_logging, get_logger; configure_logging('INFO'); log = get_logger('dojo.smoke'); log.info('hello', key='value'); print('OK')" | grep -q '^OK$'</automated>
  </verify>
  <done>
    `app/logging_config.py` exists with ABOUTME header, both functions
    defined, `configure_once` used, env-switched renderer present; all
    linters pass; smoke import + log call succeeds.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `.env` → pydantic-settings | untrusted file content parsed into typed fields |
| Settings instance → application code | SecretStr wraps API key; `.get_secret_value()` breaches the wrap |
| Application code → log sink | logs may flow to stdout, files, log aggregators |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1-LLM03-02 | Information Disclosure | `Settings.anthropic_api_key` | mitigate | Typed as `SecretStr`; `repr()` renders `'**********'`. Dev-placeholder default (`SecretStr("dev-placeholder")`) means no real key is needed for `make run` — Phase 3 validates on first use. Logging `settings.anthropic_api_key` directly (without `.get_secret_value()`) is safe: SecretStr formats as `****`. |
| T-1-LLM03-03 | Information Disclosure | Log records in `configure_logging` output | mitigate | structlog processors chain does NOT include any SecretStr-unwrapping processor. `get_logger()` returns a plain structlog logger; no API-key-aware processing needed at this layer. Project convention in CLAUDE.md forbids `.get_secret_value()` outside the Anthropic SDK boundary (Phase 3). |
| T-1-LLM03-04 | Information Disclosure | `os.getenv("DOJO_ENV")` branching | accept | `DOJO_ENV` is a non-secret runtime flag; selecting JSONRenderer vs ConsoleRenderer has no secrets impact. |
| T-1-CONFIG-01 | Tampering | pydantic-settings `extra="ignore"` | accept | Unknown env vars are silently ignored rather than crashing instantiation. Trade-off: slightly less strict, but avoids brittle CI when a future env var is added (standard pydantic-settings convention). |
| T-1-LOG-DOS-01 | Denial of Service | Log volume | accept | Phase 1 has no log-rate-limit logic; the single `dojo.startup` log message from `app/main.py` lifespan is low-volume. Phase 3+ request-handling paths are out-of-scope for this plan. |
</threat_model>

<verification>
Run after both tasks complete:

```bash
# Files exist and conform
wc -l app/settings.py app/logging_config.py  # each ≤ 100
grep -c '^# ABOUTME:' app/settings.py app/logging_config.py  # each = 2

# Linters clean
uv run ruff format --check app/
uv run ruff check app/
uv run interrogate -c pyproject.toml app/

# Behaviour smoke tests
uv run python -c "
from app.settings import get_settings
from app.logging_config import configure_logging, get_logger
s = get_settings()
configure_logging(s.log_level)
log = get_logger('dojo.verify')
log.info('phase1.plan02.green', db_url=s.database_url)
print('smoke OK')
"
```
</verification>

<success_criteria>
- `app/__init__.py` exists with ABOUTME header + module docstring
  (D-20 structural marker).
- `app/settings.py` and `app/logging_config.py` exist with ABOUTME
  headers and ≤100 lines each.
- `get_settings()` returns a Settings instance with all four D-18
  fields and the SecretStr dev-placeholder default for
  `anthropic_api_key`.
- `configure_logging("INFO")` can be called repeatedly (idempotent via
  `configure_once`) without raising.
- `get_logger(__name__)` returns a structlog logger that handles
  keyword-argument logging without raising.
- Plan 03 (DB) and Plan 04 (web) can start in parallel immediately
  after this plan commits — both `get_settings` and
  `configure_logging`/`get_logger` are ready to import.
</success_criteria>

<output>
After completion, create
`.planning/phases/01-project-scaffold-tooling/01-02-SUMMARY.md` per the
execute-plan template. Summary must note: (a) `app/__init__.py` created
unconditionally per D-20 (installable package) — content is the minimal
ABOUTME + docstring marker, (b) the resolved default for
`anthropic_api_key` (`SecretStr("dev-placeholder")` — implements Open
Question #1 per planning guidance), (c) confirmation that
`configure_once` idempotency lets tests call `configure_logging()`
repeatedly without warnings.
</output>
</content>
</invoke>