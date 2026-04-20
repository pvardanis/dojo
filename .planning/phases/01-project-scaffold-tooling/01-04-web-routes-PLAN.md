---
phase: 01-project-scaffold-tooling
plan: 04
type: execute
wave: 3
depends_on:
  - "01-02"
files_modified:
  - app/main.py
  - app/web/__init__.py
  - app/web/routes/__init__.py
  - app/web/routes/home.py
  - app/web/templates/base.html
  - app/web/templates/home.html
  - app/web/static/.gitkeep
autonomous: true
requirements:
  - OPS-04
tags:
  - python
  - fastapi
  - jinja2
  - uvicorn
  - asgi
  - routes

must_haves:
  truths:
    - "`make run` (via `uv run uvicorn app.main:app`) starts uvicorn on
      localhost:8000 without raising, and serves `/` (HTML, rendered
      through Jinja) and `/health` (JSON `{\"status\": \"ok\"}`) — SC #2
      gate"
    - "The FastAPI app's lifespan startup calls
      `configure_logging(settings.log_level)` exactly once — OPS-04
      gate"
    - "Jinja autoescape is on for the home template (Starlette's
      `Jinja2Templates(directory=...)` default per FLAG 10)"
    - "`app/main.py` is the only module in the repo that imports across
      layers (settings + logging_config + web routes) — composition
      root"
  artifacts:
    - path: "app/main.py"
      provides: "FastAPI composition root + lifespan + app factory"
      exports: ["app", "create_app"]
      contains: "Jinja2Templates"
    - path: "app/web/__init__.py"
      provides: "Web (presentation) layer package marker"
      contains: "# ABOUTME:"
    - path: "app/web/routes/__init__.py"
      provides: "Routes subpackage marker"
      contains: "# ABOUTME:"
    - path: "app/web/routes/home.py"
      provides: "GET / (home) and GET /health (JSON) route handlers"
      exports: ["router"]
      contains: "APIRouter"
    - path: "app/web/templates/base.html"
      provides: "Jinja base template with title + content blocks"
      contains: "{% block content %}"
    - path: "app/web/templates/home.html"
      provides: "Jinja home template extending base.html"
      contains: "{% extends \"base.html\" %}"
    - path: "app/web/static/.gitkeep"
      provides: "Empty dir marker for future static assets (Phase 4+)"
  key_links:
    - from: "app/main.py"
      to: "app.logging_config.configure_logging"
      via: "lifespan startup calls configure_logging(settings.log_level)"
      pattern: "configure_logging\\("
    - from: "app/main.py"
      to: "app.web.routes.home.router"
      via: "app.include_router(home.router)"
      pattern: "include_router"
    - from: "app/web/routes/home.py"
      to: "request.app.state.templates"
      via: "HTMLResponse via TemplateResponse"
      pattern: "app.state.templates"
---

<objective>
Build the minimal FastAPI web tier: `app/main.py` (composition root
with lifespan-driven logging config + Jinja template mount), the two
routes (`/` renders `home.html`, `/health` returns JSON), the two
Jinja templates (base + home), and the empty static directory marker.

Purpose: satisfies SC #2 (`make run` serves `/` + `/health`) and OPS-04
(structlog configured at app startup via lifespan). Establishes the
composition-root pattern (`app/main.py` is the only module that wires
layers — every future route module and repository plugs in here).

Output: `uv run uvicorn app.main:app --port 8765` starts cleanly;
`curl http://localhost:8765/` returns 200 HTML containing the home
heading; `curl http://localhost:8765/health` returns `{"status":"ok"}`.
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
@app/settings.py
@app/logging_config.py
@pyproject.toml

<interfaces>
<!-- Types and entry points downstream plans will import. -->

From `app/main.py` (created in this plan):
```python
from fastapi import FastAPI

def create_app() -> FastAPI: ...   # factory
app: FastAPI                        # module-level binding for uvicorn
```

From `app/web/routes/home.py` (created in this plan):
```python
from fastapi import APIRouter
router: APIRouter   # two routes: GET / (HTML), GET /health (JSON)
```

**Consumers** (downstream plans):
- `tests/integration/test_home.py` (Plan 05) imports `app.main.app`
  and uses `httpx.AsyncClient(transport=ASGITransport(app=app))` to
  exercise both routes.
- `Makefile` `run` target (Plan 06) invokes
  `uv run uvicorn app.main:app --reload --port 8000`.
- Phase 4+ adds more routers via the same
  `app.include_router(...)` pattern in `create_app()`.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create Jinja templates + static dir marker + web package shells</name>
  <files>app/web/__init__.py, app/web/routes/__init__.py, app/web/templates/base.html, app/web/templates/home.html, app/web/static/.gitkeep</files>
  <read_first>
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      895-920 (verbatim drop-in for base.html + home.html)
    - .planning/phases/01-project-scaffold-tooling/01-CONTEXT.md
      decisions D-11 (static populated in later phases), D-12 (home
      template shape)
    - .planning/phases/01-project-scaffold-tooling/01-PATTERNS.md lines
      226-237 (template structural elements)
  </read_first>
  <action>
    Create directory tree: `app/web/templates/` and `app/web/static/`
    and `app/web/routes/`.

    **Create `__init__.py` files unconditionally** in `app/web/` and
    `app/web/routes/`. These are required for Python package resolution
    when `home.py` is imported as `app.web.routes.home` in Task 3 and
    when `home` module is imported in Task 3's main.py. Each
    `__init__.py` contains only a two-line ABOUTME header plus a
    one-line module docstring.

    `app/web/__init__.py`:
    ```python
    # ABOUTME: Presentation layer (FastAPI routes + Jinja templates).
    # ABOUTME: Imports from app.settings / app.logging_config only.
    """Dojo presentation-layer package."""
    ```

    `app/web/routes/__init__.py`:
    ```python
    # ABOUTME: FastAPI route modules — one APIRouter per file.
    # ABOUTME: Home + health in Phase 1; generate/drill/read in later phases.
    """FastAPI route modules."""
    ```

    Template and static dirs are NOT Python packages and do NOT get
    `__init__.py`.

    Write `app/web/templates/base.html` — paste drop-in from
    01-RESEARCH.md lines 895-909 verbatim (the minimal HTML5 shell
    with title and content blocks).

    Write `app/web/templates/home.html` — paste drop-in from
    01-RESEARCH.md lines 911-920 verbatim (extends base.html, overrides
    title to "Dojo", content contains an h1 heading "Dojo" and a short
    placeholder paragraph).

    Create `app/web/static/.gitkeep` as an empty file — pure directory
    marker per D-11. Phase 4+ populates this with Pico.css + HTMX
    assets. Phase 1 leaves it intentionally empty so
    `StaticFiles(directory=...)` mount in `app/main.py` does not fail
    (StaticFiles is fine with an empty dir; missing dir would crash at
    mount).

    Per PATTERNS.md line 54, `.gitkeep` is a convention-only file with
    no ABOUTME header requirement. Leave it zero bytes.

    **Note on Jinja autoescape (FLAG 10):** do NOT add
    `{% autoescape true %}` blocks. Starlette's `Jinja2Templates(
    directory=...)` enables `select_autoescape()` by default for
    `.html/.htm/.xml` (verified in 01-RESEARCH.md §"Note on Jinja2
    autoescape", PR Kludex/starlette#3148); the templates themselves
    do not need to re-declare autoescape.

    Per T-1-XSS-01 in the threat model: Phase 1 home.html renders only
    static strings (no LLM content), but the autoescape-on default is
    still the Phase 4+ safety net — verify it is not explicitly
    disabled anywhere.
  </action>
  <verify>
    <automated>test -f app/web/templates/base.html &amp;&amp; test -f app/web/templates/home.html &amp;&amp; test -f app/web/static/.gitkeep &amp;&amp; ! test -s app/web/static/.gitkeep &amp;&amp; test -f app/web/__init__.py &amp;&amp; test -f app/web/routes/__init__.py &amp;&amp; grep -q 'block title' app/web/templates/base.html &amp;&amp; grep -q 'block content' app/web/templates/base.html &amp;&amp; grep -q 'extends "base.html"' app/web/templates/home.html &amp;&amp; grep -qi 'Dojo' app/web/templates/home.html &amp;&amp; grep -c '^# ABOUTME:' app/web/__init__.py | grep -q '^2$' &amp;&amp; grep -c '^# ABOUTME:' app/web/routes/__init__.py | grep -q '^2$'</automated>
  </verify>
  <done>
    All five files exist; templates contain the expected Jinja block
    markers; .gitkeep is empty; `__init__.py` shells have ABOUTME
    headers. No `{% autoescape %}` override in either template.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create app/web/routes/home.py (GET / + GET /health)</name>
  <files>app/web/routes/home.py</files>
  <read_first>
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      864-891 (verbatim drop-in for home.py)
    - .planning/phases/01-project-scaffold-tooling/01-CONTEXT.md decisions
      D-12 (home route), D-13 (health route JSON shape)
    - .planning/phases/01-project-scaffold-tooling/01-PATTERNS.md lines
      202-223 (key structural elements + autoescape clarification)
    - app/web/templates/home.html (created in Task 1 — home route
      references this filename)
  </read_first>
  <action>
    Write `app/web/routes/home.py` — paste drop-in from 01-RESEARCH.md
    lines 864-891 verbatim. Key structural preservations:

    1. Two-line `# ABOUTME:` header: "Home + health routes — the Phase
       1 minimum endpoints." / "Proves FastAPI + Jinja + autoescape
       wiring end-to-end."
    2. Module docstring: `"""Home and health endpoints."""` (for
       interrogate).
    3. `from __future__ import annotations`.
    4. Imports: `from fastapi import APIRouter, Request`; `from
       fastapi.responses import HTMLResponse, JSONResponse`.
    5. `router = APIRouter()` at module level — ONE router per module.
    6. `@router.get("/", response_class=HTMLResponse)` decorator on
       `async def home(request: Request) -> HTMLResponse:` — docstring
       "Render the minimal Dojo home page." Body uses `templates =
       request.app.state.templates` then `return
       templates.TemplateResponse(request=request, name="home.html",
       context={})`. Note: `request.app.state.templates` avoids
       importing `Jinja2Templates` in the route module (keeps Jinja
       instance a composition-root concern per PATTERNS.md).
    7. `@router.get("/health", response_class=JSONResponse)` on
       `async def health() -> dict[str, str]:` — docstring "Return a
       lightweight health probe JSON payload." Body: `return
       {"status": "ok"}`. Per D-13, FastAPI auto-serializes the dict
       to JSON; no manual `json.dumps` needed.

    **Anti-patterns to avoid:**
    - Do NOT import `Jinja2Templates` in this module — `app.state`
      mounting in `app/main.py` is the composition-root pattern.
    - Do NOT hardcode absolute template paths — use the `name=...`
      string so Starlette's loader resolves against the mounted
      directory.
    - Do NOT add a `/healthz` or `/status` alias. D-13 specifies one
      health route at `/health`.

    Verify:
    - `wc -l app/web/routes/home.py` ≤ 100 (drop-in is ~30 lines).
    - 2 ABOUTME lines.
    - 79-char compliant.
    - `uv run ruff format --check app/web/routes/home.py` passes.
    - `uv run ruff check app/web/routes/home.py` passes.
    - `uv run interrogate -c pyproject.toml app/web/routes/home.py`
      reports 100% (module + 2 functions need docstrings).
    - Import smoke: `uv run python -c "from app.web.routes.home import
      router; assert len(router.routes) == 2; paths = sorted(r.path for
      r in router.routes); assert paths == ['/', '/health']; print('OK')"`
  </action>
  <verify>
    <automated>test -f app/web/routes/home.py &amp;&amp; test $(wc -l &lt; app/web/routes/home.py) -le 100 &amp;&amp; grep -c '^# ABOUTME:' app/web/routes/home.py | grep -q '^2$' &amp;&amp; grep -q 'router = APIRouter()' app/web/routes/home.py &amp;&amp; grep -q '@router.get("/", response_class=HTMLResponse)' app/web/routes/home.py &amp;&amp; grep -q '@router.get("/health"' app/web/routes/home.py &amp;&amp; grep -q 'request.app.state.templates' app/web/routes/home.py &amp;&amp; grep -q '"status": "ok"' app/web/routes/home.py &amp;&amp; uv run ruff format --check app/web/routes/home.py &amp;&amp; uv run ruff check app/web/routes/home.py &amp;&amp; uv run interrogate -c pyproject.toml app/web/routes/home.py &amp;&amp; uv run python -c "from app.web.routes.home import router; paths = sorted(r.path for r in router.routes); assert paths == ['/', '/health'], paths; print('OK')" | grep -q '^OK$'</automated>
  </verify>
  <done>
    `home.py` exists with ABOUTME header, both routes defined, no
    direct Jinja2Templates import, templates accessed via
    `request.app.state.templates`, all linters pass, import smoke green.
  </done>
</task>

<task type="auto">
  <name>Task 3: Create app/main.py (composition root + lifespan + uvicorn smoke)</name>
  <files>app/main.py</files>
  <read_first>
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      807-856 (verbatim drop-in for main.py)
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      858-862 (autoescape note — Starlette default)
    - .planning/phases/01-project-scaffold-tooling/01-CONTEXT.md decisions
      D-11 (absolute-minimum scaffold), D-12/D-13 (two routes)
    - .planning/phases/01-project-scaffold-tooling/01-PATTERNS.md lines
      121-150 (key structural elements + what NOT to add)
    - app/settings.py, app/logging_config.py, app/web/routes/home.py
      (modules this imports)
  </read_first>
  <action>
    Write `app/main.py` — paste drop-in from 01-RESEARCH.md lines
    807-856 verbatim. Key structural preservations (per PATTERNS.md):

    1. Two-line `# ABOUTME:` header: "FastAPI composition root — wires
       settings, templates, routes." / "The only module allowed to
       import across layers."
    2. Module docstring: `"""FastAPI composition root for Dojo."""`.
    3. `from __future__ import annotations`.
    4. Imports: `asynccontextmanager` from `contextlib`; `Path`;
       `FastAPI` from `fastapi`; `StaticFiles` from
       `fastapi.staticfiles`; `Jinja2Templates` from
       `fastapi.templating`; `configure_logging` and `get_logger`
       from `app.logging_config`; `get_settings` from `app.settings`;
       `home` from `app.web.routes`.
    5. `log = get_logger(__name__)` at module level — establishes the
       project-wide convention (OPS-04).
    6. `_HERE = Path(__file__).resolve().parent` — module-local dir.
    7. `_TEMPLATES = Jinja2Templates(directory=_HERE / "web" /
       "templates")` — **Starlette's default is autoescape ON for
       .html/.htm/.xml** (FLAG 10 resolved; do NOT add
       `autoescape=True` kwarg — it is not needed and would be
       redundant).
    8. `_STATIC = _HERE / "web" / "static"`.
    9. `@asynccontextmanager async def lifespan(app: FastAPI):` with
       docstring "Startup: configure logging. Shutdown: nothing in
       Phase 1."
       - Body: `settings = get_settings()`;
         `configure_logging(settings.log_level)`;
         `log.info("dojo.startup", database_url=settings.database_url)`;
         `yield`.
       - DO NOT log the API key (settings.anthropic_api_key is a
         SecretStr — logging it is safe as it renders as `'**********'`,
         but there is no reason to log it at all at startup).
    10. `def create_app() -> FastAPI:` with docstring "Build the
        FastAPI app. Called by uvicorn via `app.main:app`."
        - Body: `app = FastAPI(title="Dojo", lifespan=lifespan)`;
          `app.state.templates = _TEMPLATES`; `app.mount("/static",
          StaticFiles(directory=_STATIC), name="static")`;
          `app.include_router(home.router)`; `return app`.
    11. `app = create_app()` at module level — uvicorn targets this
        name via `app.main:app`.

    **Anti-patterns (per PATTERNS.md):**
    - Do NOT configure logging at import time — only from the lifespan
      startup hook (test isolation + fixture control).
    - Do NOT create a DB session dependency here — Phase 3+ wires
      `get_session`.
    - Do NOT include use-case wiring — Phase 4+ adds that.
    - Do NOT add lifespan DB engine disposal — Phase 3+ owns that.
    - Do NOT add route-level state or globals beyond `app.state.templates`.

    **Uvicorn smoke test (critical):** after writing the file, start
    uvicorn in the background on a non-default port (e.g., 8765 to
    avoid conflicts with any running dev server), curl both routes,
    then kill uvicorn. This is the SC #2 canary ahead of Plan 05's
    integration test:

    ```bash
    uv run uvicorn app.main:app --port 8765 &amp; UVICORN_PID=$!
    sleep 2
    curl -sS http://localhost:8765/ | grep -qi 'dojo' &amp;&amp; echo "/ OK"
    curl -sS http://localhost:8765/health | grep -q '"status":"ok"' &amp;&amp; echo "/health OK"
    kill $UVICORN_PID 2>/dev/null || true
    wait $UVICORN_PID 2>/dev/null || true
    ```

    If either curl fails, fix the wiring before committing. Do NOT use
    `--reload` in this smoke test (it spawns a child process, making
    `kill $UVICORN_PID` unreliable).

    Verify:
    - `wc -l app/main.py` ≤ 100 (drop-in is ~45 lines).
    - 2 ABOUTME lines; ruff + ty + interrogate clean.
    - ASGI smoke test (faster than uvicorn subprocess, and what Plan
      05's test_home.py will do):
      ```
      uv run python -c "
      import httpx, asyncio
      from httpx import ASGITransport
      from app.main import app
      async def main():
          async with httpx.AsyncClient(
              transport=ASGITransport(app=app),
              base_url='http://test',
          ) as c:
              r1 = await c.get('/')
              r2 = await c.get('/health')
              assert r1.status_code == 200, r1.status_code
              assert 'Dojo' in r1.text
              assert r2.status_code == 200, r2.status_code
              assert r2.json() == {'status': 'ok'}
          print('ASGI smoke OK')
      asyncio.run(main())
      "
      ```
      This is sufficient for Phase 1 verify; the `uvicorn --port 8765`
      subprocess smoke is an extra guardrail, skip if the ASGI smoke
      is green.
  </action>
  <verify>
    <automated>test -f app/main.py &amp;&amp; test $(wc -l &lt; app/main.py) -le 100 &amp;&amp; grep -c '^# ABOUTME:' app/main.py | grep -q '^2$' &amp;&amp; grep -q '@asynccontextmanager' app/main.py &amp;&amp; grep -q 'async def lifespan' app/main.py &amp;&amp; grep -q 'configure_logging(settings.log_level)' app/main.py &amp;&amp; grep -q 'def create_app() -&gt; FastAPI' app/main.py &amp;&amp; grep -q 'app = create_app()' app/main.py &amp;&amp; grep -q 'app.include_router(home.router)' app/main.py &amp;&amp; grep -q 'app.state.templates' app/main.py &amp;&amp; ! grep -q 'autoescape=True' app/main.py &amp;&amp; uv run ruff format --check app/main.py &amp;&amp; uv run ruff check app/main.py &amp;&amp; uv run interrogate -c pyproject.toml app/main.py &amp;&amp; uv run python -c "import httpx, asyncio; from httpx import ASGITransport; from app.main import app;
async def main():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as c:
        r1 = await c.get('/'); r2 = await c.get('/health')
        assert r1.status_code == 200; assert 'Dojo' in r1.text
        assert r2.status_code == 200; assert r2.json() == {'status': 'ok'}
    print('ASGI_SMOKE_OK')
asyncio.run(main())" | grep -q 'ASGI_SMOKE_OK'</automated>
  </verify>
  <done>
    `app/main.py` exists with ABOUTME header, lifespan-driven logging,
    composition-root imports, `app = create_app()` module binding; all
    linters pass; ASGI smoke test confirms GET / returns 200 HTML
    containing "Dojo" and GET /health returns `{"status": "ok"}`.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| HTTP client → ASGI app | untrusted request bodies / headers / query strings |
| Jinja template context → HTML output | any string value could contain HTML/JS if autoescape off |
| Static directory → HTTP response | files served as-is; Phase 1 dir is empty |
| App lifespan → process state | logging + settings loaded once on startup |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1-XSS-01 | Tampering / Info Disclosure | Jinja template rendering in `home.py` | mitigate | Starlette's `Jinja2Templates(directory=...)` enables `select_autoescape()` for `.html/.htm/.xml` by default (FLAG 10, verified via Kludex/starlette#3148). Templates do NOT disable autoescape. Phase 1 templates render only static strings — no LLM content yet — but the safety net is verified live via Plan 05's `test_home.py`. |
| T-1-SSRF-01 | Information Disclosure | FastAPI `/` + `/health` routes | mitigate | Phase 1 routes make no outbound requests. No SSRF surface. |
| T-1-OPEN-REDIRECT-01 | Tampering | `/` + `/health` | accept | Neither route performs redirects; no open-redirect surface in Phase 1. |
| T-1-HEALTH-LEAK-01 | Information Disclosure | `/health` JSON body | mitigate | Body is a literal `{"status": "ok"}` dict — no version, build ID, env fingerprint, or other system info leaked. Phase 1 design choice per D-13. |
| T-1-LOG-LEAK-01 | Information Disclosure | `log.info("dojo.startup", database_url=...)` | mitigate | `database_url` is a pydantic-settings field with a local SQLite default; it does not contain credentials. If/when a Phase 3 DB is hosted with a password, the URL itself becomes sensitive and this log line must be revisited. Phase 1 disposition: accept; Phase 3 must audit the startup log. |
| T-1-STATIC-DIR-TRAVERSAL-01 | Information Disclosure | `StaticFiles(directory=_STATIC)` | mitigate | Starlette's `StaticFiles` guards against path traversal (`../` requests). Phase 1 static dir is empty — no files to leak anyway. |
| T-1-LLM03-05 | Information Disclosure | API key appearing in lifespan log | mitigate | Lifespan log DOES NOT log `anthropic_api_key`. If a future change tried to log it, SecretStr's `__repr__` renders `'**********'` — defense in depth. |
</threat_model>

<verification>
Run after all three tasks complete:

```bash
# All five files exist
ls -l app/main.py app/web/routes/home.py app/web/templates/base.html \
      app/web/templates/home.html app/web/static/.gitkeep

# Linters
uv run ruff format --check app/
uv run ruff check app/
uv run interrogate -c pyproject.toml app/

# SC #2 gate — ASGI smoke (home + health)
uv run python -c "
import httpx, asyncio
from httpx import ASGITransport
from app.main import app
async def main():
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as c:
        r1 = await c.get('/')
        r2 = await c.get('/health')
        assert r1.status_code == 200 and 'Dojo' in r1.text, r1.text[:200]
        assert r2.status_code == 200 and r2.json() == {'status': 'ok'}
    print('SC#2 OK')
asyncio.run(main())
"
```
</verification>

<success_criteria>
- `app/web/__init__.py` and `app/web/routes/__init__.py` exist with
  ABOUTME headers (required subpackage markers for route import).
- `app/main.py` exposes `create_app()` and module-level `app = create_app()`.
- `app/web/routes/home.py` exposes `router` with exactly two routes:
  `/` (HTML) and `/health` (JSON).
- Base + home templates present; home extends base; autoescape is
  Starlette default (no explicit override).
- ASGI smoke test passes — GET / returns 200 HTML containing "Dojo";
  GET /health returns `{"status": "ok"}`.
- Plan 05 (tests) can now wire `tests/integration/test_home.py`
  against `app.main.app`.
- Plan 06 (Makefile) can now wire `run: uv run uvicorn app.main:app`.
</success_criteria>

<output>
After completion, create
`.planning/phases/01-project-scaffold-tooling/01-04-SUMMARY.md` per the
execute-plan template. Summary must note: (a) both `__init__.py`
shells created unconditionally in `app/web/` and `app/web/routes/` as
required subpackage markers, (b) lifespan confirmed wired to
`configure_logging` + `log.info("dojo.startup", ...)`, (c) autoescape
confirmed via Starlette default (no explicit kwarg; Plan 05's
test_home.py will regression-test this).
</output>
</content>
</invoke>