# Phase 1 Study Notes — Scaffolding Python for Production

Cheat-sheet drawn from building Dojo's scaffold. Focused on interview-relevant patterns; gotchas marked **⚠**.

---

## 1. SQLAlchemy 2.0 + Alembic

### Engine / Session / sessionmaker — three separate things

```python
engine = create_engine("sqlite:///dojo.db")  # connection pool
SessionLocal = sessionmaker(                 # factory config
    engine, expire_on_commit=False, class_=Session,
)
with SessionLocal() as sess:                 # unit of work
    ...
```

**Why three layers:** engine owns the pool, sessionmaker is config, Session is the transactional scope. Swap any one without rebuilding the others.

**`expire_on_commit=False`** — default is `True`, which expires every loaded attribute after `commit()`. Next attribute access re-queries. In short web requests that's fine; in anything longer-lived (background workers, tests, async contexts) it means surprise N+1 queries and (in async) `MissingGreenlet` errors. Set False unless you specifically need the refresh.

### Transactions — begin / commit / rollback + SAVEPOINT

```python
# normal use
with SessionLocal() as sess:
    with sess.begin():        # opens tx, commits on exit, rollbacks on exception
        sess.add(obj)

# nested / SAVEPOINT
with sess.begin_nested():     # inner savepoint
    sess.add(risky_obj)       # can rollback independently of outer tx
```

**Test isolation recipe (SAVEPOINT):**
```python
with engine.connect() as conn:
    outer = conn.begin()
    factory = sessionmaker(
        bind=conn,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",  # key flag
    )
    with factory() as sess:
        yield sess             # test can call sess.commit() freely
    outer.rollback()           # undoes everything — even committed writes
```
`join_transaction_mode="create_savepoint"` makes every `sess.commit()` a savepoint closure, not a real commit. Outer rollback nukes the whole thing at teardown. Cleanest cross-test DB isolation without the "drop and recreate schema" cost.

### DeclarativeBase + typed columns (SA 2.0 style)

```python
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
```
`Mapped[T]` + `mapped_column()` = the 2.0 idiom. Types live in annotations, not in a separate `Column(...)` call.

### SQLite PRAGMAs via event listener

```python
@event.listens_for(engine, "connect")
def _configure_sqlite(dbapi_conn, _):
    if engine.dialect.name != "sqlite":
        return                                   # ← dialect guard
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")        # FKs off by default (!!)
    cur.execute("PRAGMA journal_mode=WAL")       # concurrent reads during writes
    cur.execute("PRAGMA busy_timeout=5000")      # 5s retry vs SQLITE_BUSY
    cur.close()
```
**⚠ Gotcha**: the listener fires ONLY for the engine you registered it on. If tests `create_engine()` a fresh engine, they bypass the listener entirely. Either re-register, or write a dedicated test against the production module engine.

### Alembic env.py — sync stock shape

```python
config.set_main_option("sqlalchemy.url", settings.database_url)
connectable = engine_from_config(config.get_section(...), prefix="sqlalchemy.")
with connectable.connect() as conn:
    context.configure(connection=conn, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
```

**⚠ Gotcha — caller-URL-wins**: if env.py unconditionally sets the URL, programmatic callers (tests, internal migration runners) get their URL silently overwritten. Only fallback to settings when the Config URL is unset or the ini placeholder:
```python
placeholder = "driver://user:pass@localhost/dbname"
if not config.get_main_option("sqlalchemy.url") \
    or config.get_main_option("sqlalchemy.url") == placeholder:
    config.set_main_option("sqlalchemy.url", settings.database_url)
```

**War story**: Dojo's first env.py unconditionally overrode the URL. `test_alembic_smoke` failed because it migrated `dojo.db` (project root) instead of the tmp DB. `test_db_smoke` (SELECT 1) false-passed because SELECT 1 doesn't need tables — only `test_alembic_smoke` (asserts on `sqlite_master`) caught it. Lesson: smoke tests must assert on something that would fail if the underlying wiring is wrong.

### alembic_version table

First `alembic upgrade head` run creates this table regardless of your migration body. Stores the current revision (e.g. `"0001"`). Assert on it to verify "the migration pipeline actually ran," not just that the table exists.

---

## 2. FastAPI + ASGI lifecycle

### Composition root pattern

`app/main.py` is the ONLY module that imports across layers.

```python
def create_app() -> FastAPI:
    app = FastAPI(title="Dojo", lifespan=lifespan)
    app.state.templates = Jinja2Templates(directory=...)
    app.mount("/static", StaticFiles(directory=...))
    app.include_router(home.router)
    return app

app = create_app()  # uvicorn's "app.main:app" points here
```
Factory lets tests build an app with different wiring; module-level `app` is what uvicorn imports.

### Lifespan — startup/shutdown hook

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    log.info("dojo.startup", database_url=settings.database_url)
    yield
    # shutdown: engine.dispose(), cache flush, etc.
```
Replaces the old `@app.on_event("startup")` decorator. Everything before `yield` runs once at boot; after `yield` runs once at shutdown.

**⚠ Gotcha**: `httpx.AsyncClient(transport=ASGITransport(app))` does **NOT** invoke lifespan. To drive it in tests:
```python
async with app.router.lifespan_context(app):
    pass  # startup just ran; shutdown on exit
```

### Router per module

```python
# app/web/routes/home.py
router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    templates = request.app.state.templates   # ← app-scoped DI
    return templates.TemplateResponse(request=request, name="home.html", ...)
```
Access app state via `request.app.state.*` — keeps route modules from importing Jinja2Templates directly, so Jinja stays a composition-root concern.

### `response_class` and return types

- Return a `dict` + declare `response_class=JSONResponse` → FastAPI auto-serializes
- Return `JSONResponse({...})` directly → you control status + headers
- Return `templates.TemplateResponse(...)` + `response_class=HTMLResponse` → Jinja rendered
- Signatures don't have to match runtime returns; FastAPI serializes loosely

### Jinja2 autoescape

`Jinja2Templates(directory=...)` enables `select_autoescape(["html", "htm", "xml"])` by **default** in modern Starlette. Don't pass `autoescape=True` — redundant. XSS protection is on unless a template explicitly disables it.

### In-memory testing via ASGITransport

```python
async with httpx.AsyncClient(
    transport=ASGITransport(app=app),
    base_url="http://test",
) as c:
    r = await c.get("/health")
```
Drives FastAPI without a socket — faster than uvicorn subprocess. Just remember: **no lifespan** (see gotcha above).

---

## 3. pytest + async testing + isolation

### pytest-asyncio 1.x config

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"                            # every async def test_* is async
asyncio_default_fixture_loop_scope = "session"   # one event loop for all async fixtures
filterwarnings = ["error"]                       # any unhandled warning = test failure
```
**⚠ 1.x migration**: the `event_loop` fixture was removed. Override via the `event_loop_policy` fixture instead if you need a custom loop.

### Session-scoped async fixtures

```python
@pytest_asyncio.fixture(scope="session")
async def _migrated_engine(test_db_url):
    command.upgrade(cfg, "head")
    engine = create_engine(test_db_url)
    try: yield engine
    finally: engine.dispose()
```
Use `@pytest_asyncio.fixture` (not `@pytest.fixture`) when the fixture body is async. `scope="session"` → one engine per pytest process, not per test.

### asyncio.to_thread for sync CLIs

```python
await asyncio.to_thread(command.upgrade, cfg, "head")
```
Alembic's CLI is sync and spawns its own asyncio loop internally. Calling it from an async test deadlocks: two loops can't nest. `asyncio.to_thread` pushes it to a worker thread where its loop is fine.

### caplog after stdlib wrapping

When structlog is configured to route through stdlib (see §4), pytest's built-in `caplog` fixture captures events:
```python
def test_startup(caplog):
    caplog.set_level(logging.INFO, logger="app.main")
    async with app.router.lifespan_context(app):
        pass
    assert any("dojo.startup" in r.getMessage() for r in caplog.records)
```

**⚠ War story**: `structlog.testing.capture_logs()` works fine on pure-structlog configs, but when structlog wraps stdlib and `filterwarnings = ["error"]` is set, a `configure_once` call during `capture_logs` emits a RuntimeWarning that escalates to failure. Switch to `caplog`, or replace `configure_once` with `is_configured() + configure()`.

### `_env_file=None` for deterministic settings tests

```python
settings = Settings(_env_file=None)  # bypass repo's .env
```
pydantic-settings reads `.env` silently. Without this, your "defaults" test fails on a developer with a local `.env`. `_env_file=None` forces library defaults. Pair with `monkeypatch.delenv(...)` to also clear process env.

---

## 4. structlog + stdlib + Python type patterns

### structlog wrapping stdlib (not parallel to it)

```python
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,             # early exit based on stdlib level
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.dev.ConsoleRenderer(),              # or JSONRenderer in prod
    ],
    wrapper_class=structlog.stdlib.BoundLogger,       # <<< key
    logger_factory=structlog.stdlib.LoggerFactory(),  # <<< key
    cache_logger_on_first_use=True,
)
```
**Why**: with `stdlib.LoggerFactory`, events go through `logging.getLogger(name)`. That means `logging.getLogger("app").setLevel(WARNING)` actually gates structlog output — and pytest `caplog` sees events.

**⚠ War story**: the naive default (`PrintLoggerFactory` + `make_filtering_bound_logger`) runs structlog parallel to stdlib, not wrapping it. `logging.getLogger(...).setLevel(...)` does nothing; `caplog` sees nothing. Caught in review. The test-side "clamp trafilatura/httpx/anthropic to WARNING" fixture was a silent no-op for weeks.

### configure_once vs is_configured() + configure()

- `structlog.configure_once(...)` — idempotent, emits `RuntimeWarning` on repeat
- Under `filterwarnings = ["error"]`, that warning becomes a test failure
- Fix: `if not structlog.is_configured(): structlog.configure(...)` — same idempotency, silent

### Env-switched renderer

```python
if os.getenv("DOJO_ENV") == "prod":
    processors.append(structlog.processors.JSONRenderer())   # machine-readable
else:
    processors.append(structlog.dev.ConsoleRenderer())       # human-readable (colors)
```

### Protocol vs Callable — when each

```python
# Stateless, one operation → Callable alias
UrlFetcher = Callable[[str], str]

# State / multiple methods / growth pressure → Protocol
class Repository(Protocol):
    def save(self, entity: Entity) -> None: ...
    def get(self, id: EntityId) -> Entity | None: ...
```
Don't Protocol-wrap a single stateless function. Flat `Callable[...]` aliases keep the type surface honest.

### pydantic-settings + SecretStr + Literal + field_validator

```python
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

class Settings(BaseSettings):
    anthropic_api_key: SecretStr = SecretStr("dev-placeholder")
    database_url: str = "sqlite:///dojo.db"
    log_level: LogLevel = "INFO"

    @field_validator("database_url")
    @classmethod
    def _require_supported_scheme(cls, v: str) -> str:
        if not v.startswith(("sqlite://", "postgresql://")):
            raise ValueError(f"unsupported scheme: {v!r}")
        return v
```
- `SecretStr` masks its `repr()` as `'**********'` — never leaks via logs or tracebacks
- `.get_secret_value()` is the only way out — makes every leak site explicit (and greppable)
- `Literal` is a closed enum at the type level; invalid values fail at Settings load, not at first use
- `field_validator` catches config typos before any dependent code runs

### @lru_cache singleton + cache_clear

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()

# in tests:
monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp.db")
get_settings.cache_clear()
assert get_settings().database_url == "sqlite:///tmp.db"
```
Cheapest singleton pattern in Python. `cache_clear()` is the escape hatch; call in test setup if you're monkeypatching env vars.

---

## Coming later (not in this doc)

- Domain modeling + DDD layering (Phase 2)
- DIP with Protocols in action + hand-written fakes (Phase 2)
- Anthropic SDK + tenacity retries + structured tool use (Phase 3)
- HTMX partials + progressive enhancement (Phase 4+)

---

*Phase 1 study notes · 2026-04-21*
