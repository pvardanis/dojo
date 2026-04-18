# Domain Pitfalls

**Domain:** Local LLM-powered study app (Python async FastAPI + async SQLAlchemy 2.0 + Anthropic SDK + HTMX + Pico.css + TDD-with-fakes)
**Researched:** 2026-04-18
**Confidence note:** External web/documentation lookup tools (Context7, WebSearch, WebFetch) and Bash were unavailable in this session. Findings are drawn from Claude's training knowledge of these specific stacks. Items marked **[VERIFY]** should be double-checked against current docs before committing to them in the roadmap. Nothing here contradicts the spec; it's the "fresh eyes" implementation-layer caution list the milestone requested.

---

## Critical Pitfalls

Mistakes that cause rewrites, data loss, corrupted DB state, or multi-phase refactors. If you hit one of these mid-Phase 1, you re-plan.

### C1. `MissingGreenlet` from touching an unloaded relationship after the session closes

**What goes wrong:** A use case returns a domain entity (or worse, leaks an ORM model) and the template/route accesses `card.reviews` or `source.note`. SQLAlchemy 2.0 async raises `MissingGreenlet` because it tried to emit lazy SQL from a non-greenlet-enabled call site. Sometimes it surfaces as `sqlalchemy.exc.InvalidRequestError: This session is in 'closed' state` instead. Both mean the same thing: you touched a relationship outside the session scope.

**Why it happens:**
- Async SQLAlchemy forbids implicit lazy loading in async contexts — `greenlet_spawn` wraps sync ORM code; bare attribute access outside that wrapping blows up.
- The 4-layer mapper pattern (ORM → domain) mitigates this if the mapper fully materialises every relationship it needs. It re-breaks the moment a mapper forgets one.
- aiosqlite's in-memory-like speed hides the bug in dev; it only fires on the path where a relationship wasn't eager-loaded.

**Consequences:** Random 500s in production paths, inconsistent between dev and E2E. Worse: the `CardReview` log is a one-to-many from `Card`; if a view layer ever iterates `card.reviews`, you're one route away from a blow-up.

**Prevention:**
- **Rule:** domain entities returned from repositories MUST be fully materialised — no live ORM references reach the application layer. The mapper does the `selectinload` / explicit `await session.execute(...)` and builds the dataclass.
- In `infrastructure/db/mappers.py`, every relationship referenced by the domain dataclass must have a corresponding eager load in the repo query. Make this a code-review checklist item.
- Configure models with `lazy="raise"` on all relationships. This converts accidental lazy access into a loud `InvalidRequestError` at development time instead of a silent-then-greenlet-later failure. **[VERIFY]** for SQLAlchemy 2.0 async behaviour.
- Write one integration test per repository that fetches an entity, closes the session, and then serialises the domain object end-to-end. If anything lazy-loads, the test dies.

**Warning signs:**
- Tests pass, the happy path in dev works, but a new view hits a relationship and explodes.
- Error traces mention `greenlet_spawn has not been called` or `IO was attempted in unexpected place`.
- You start sprinkling `await session.refresh(obj)` to make errors go away. Stop — refactor the mapper.

**Phase:** Phase 1, structural — addressed in the repository + mapper component.
**Severity:** Critical. Easy to hit; annoying to fix late because it's spread across every repo.

---

### C2. `selectinload` vs `joinedload` — and why `joinedload` on a collection almost always corrupts pagination

**What goes wrong:** A developer defaults to `joinedload` because "it's one query." On a `Source → Cards` relationship with 20 cards, the outer join returns 20 rows per source. Add pagination (`.limit(10)`) and you get 10 *rows*, not 10 sources — i.e. roughly one source with 10 of its cards. List pages silently truncate.

**Why it happens:**
- `joinedload` uses a LEFT OUTER JOIN, which multiplies parent rows by child-count before LIMIT is applied.
- `selectinload` issues an IN-clause second query and doesn't multiply rows; it's the correct default for collections.
- Beginner SQLAlchemy tutorials often showcase `joinedload`, which works fine for scalar/many-to-one but quietly breaks for one-to-many.

**Consequences:** "Missing sources" bug in the list view. Worst case: you notice after users report it.

**Prevention:**
- **Rule:** `selectinload` for collections (one-to-many, many-to-many). `joinedload` only for one-to-one or many-to-one (`Note → Source`, `CardReview → Card`).
- Document this in `docs/architecture/` — one sentence under the repositories section.
- Write a repository test that inserts >1 card per source and asserts `list_sources(limit=1)` returns exactly 1 source (with all its cards).

**Warning signs:** Repos using `joinedload(Source.cards)` or `joinedload(Card.reviews)`. These should be `selectinload`.

**Phase:** Phase 1 — data access layer.
**Severity:** High. Silent data bug.

---

### C3. `expire_on_commit=True` makes returned domain objects re-trigger SQL

**What goes wrong:** After `await session.commit()`, SQLAlchemy expires all attributes on attached instances. The next attribute access triggers a refetch — which, in async, re-triggers `MissingGreenlet` if the session is closed, or a surprise SQL call if it isn't.

**Why it happens:** `expire_on_commit` is `True` by default on `sessionmaker`. It's fine in sync code; it's a trap in async where reloads cross the async boundary invisibly.

**Consequences:** Same class of failures as C1, but specifically clustered around the `save_draft` use case which commits Source + Note + Cards atomically. Any "return what we just saved" pattern breaks.

**Prevention:**
- Configure `async_sessionmaker(..., expire_on_commit=False)`.
- The mapper pattern (entity → ORM → commit → map back from already-captured values) already prevents most of this. Make sure the mapping back to the domain entity doesn't pass through the ORM instance after commit.
- Prefer returning IDs from the save use case, then re-fetching via the `by_id` repo method for the "post-save" view. Two small queries beat one subtle bug.

**Warning signs:** `DetachedInstanceError` or the same `MissingGreenlet` trace right after a commit; tests pass for "save-and-throw-away" but fail for "save-and-return."

**Phase:** Phase 1 — session factory config.
**Severity:** High.

---

### C4. Alembic async env.py not actually running async

**What goes wrong:** The default `alembic init` scaffold is synchronous. Applying it to an async engine either (a) explodes with "cannot run async engine in sync context" or (b) worse, silently runs migrations against a fresh sync engine that doesn't see the same connection string / pragmas — the classic "migration ran, but my test DB still has the old schema" confusion.

**Why it happens:** The async Alembic template is a separate scaffold (`alembic init -t async`). It's one flag; people forget it and then patch env.py by hand and get it subtly wrong.

**Consequences:** Migrations that appear to work but don't apply to the real async database; schema drift between `make migrate` and runtime; hours of "but I migrated, why is the table missing" in integration tests.

**Prevention:**
- Use `alembic init -t async migrations` — the async template. **[VERIFY]** flag name against current Alembic docs.
- First migration: create all tables. Commit it, then **actually run it against a fresh DB and inspect with `sqlite3 dojo.db .schema`** before writing any app code that depends on the schema.
- Configure Alembic to read the DB URL from the same `pydantic-settings` singleton the app uses — no parallel config source.

**Warning signs:** `alembic upgrade head` completes instantly without printing "running migration...", or the target DB is untouched.

**Phase:** Phase 1 — earliest step after repo scaffolding. Addressed in infrastructure/db setup.
**Severity:** Critical if missed; it blocks integration tests entirely.

---

### C5. Atomic save is not atomic if the session is managed wrong

**What goes wrong:** The spec §5.1 says "Source + Note + Cards in one async transaction." Standard mistakes:
- Three separate repo methods, each opening their own session → three transactions, partial writes on failure.
- One session but three `await session.commit()` calls — same thing, just more elaborate.
- Dependency-injected `AsyncSession` with session-per-request, but the "save" use case spawns a background task and commits off the original session.

**Why it happens:** Repositories that manage their own sessions feel clean but break the unit-of-work invariant. FastAPI's session-per-request `Depends` is correct but easy to undermine with `async with session.begin()` nested blocks that commit prematurely.

**Consequences:** Orphan `Source` rows with no `Note`, or `Source + Note` but 0 cards because the card insert hit a constraint. The draft store is in-memory so you can't recover the cards.

**Prevention:**
- **Rule:** repositories receive an `AsyncSession` (or an injected `session factory`); they do NOT commit. Only the use case commits.
- Use `async with session.begin():` at the use case layer, wrapping all three repo calls. On exception, rollback is automatic.
- Write an integration test that forces the third insert to fail (e.g. a too-long string, a unique constraint) and asserts the first two did NOT persist.
- Verify the draft still exists in memory after a failed save, so the user can retry without regenerating.

**Warning signs:** Repositories importing `async_sessionmaker` directly. Repositories calling `.commit()` or `.rollback()`. Use-case code lacking an explicit transaction boundary.

**Phase:** Phase 1 — Save use case.
**Severity:** Critical. First time a save fails halfway, you have corrupt data.

---

### C6. Anthropic tool-use for structured output: the response is *still* JSON-ish, not guaranteed JSON

**What goes wrong:** The "use Anthropic tool use to get structured output" recipe is the correct approach, but the returned `tool_use` block's `input` field is a dict the SDK has already parsed from the model's JSON. Assumption: "if the SDK parsed it, the schema is validated." Not true — the SDK gives you the parsed dict; schema validation is still on you. The model can and does:
- Omit optional fields you require.
- Return a list for a field declared as a string when the prompt implied pluralness.
- Return an empty list for `cards` if it thinks the prompt didn't warrant any.
- Return `"question": null` for a required field under safety pressure.

**Why it happens:** Tool use constrains shape far better than raw JSON prompting, but it's not JSON Schema enforcement in the strict sense — especially across long prompts and multi-turn contexts. **[VERIFY]** against current Anthropic docs for the exact guarantees; recent versions may have tightened this.

**Consequences:** App crashes at the DTO boundary, or worse, silently produces empty card lists that users then "approve" (approving nothing, saving a `Source + Note` with 0 cards).

**Prevention:**
- Validate the tool-use `input` against a Pydantic DTO *inside* the infrastructure adapter. On validation fail, raise `LLMOutputMalformed` per spec §6.1 — and do the spec's one-retry with stricter prompt. Don't swallow.
- Assert `len(cards) > 0` explicitly in the use case and treat zero-cards as an error worth surfacing ("the LLM generated no cards — try a more specific prompt").
- Log the raw tool-use input on every validation failure at WARN level with the request ID. Reviewing these logs teaches you what the model actually returns.

**Warning signs:** Pydantic `ValidationError` buried inside adapter code; tests passing because `FakeLLMProvider` returns a perfect DTO but real Anthropic returns something slightly different; users reporting "I hit generate and got to review with no cards."

**Phase:** Phase 1 — Anthropic adapter.
**Severity:** Critical. First-week issue; every user hits it before prompts are tuned.

---

### C7. Anthropic rate limits vs the spec's 3-retry backoff: the default retry can *cause* rate limits

**What goes wrong:** The spec says "exponential backoff, 3 retries max" for 429s. The Anthropic SDK itself has default retry behaviour (it retries 429 and 5xx automatically, with backoff). Stacking your own retry over the SDK's retry multiplies the attempt count (3 × 2 default SDK retries = 9 real calls for one logical request) and burns more of the rate-limit budget on the same operation.

**Why it happens:** The SDK's retry is silent and documented but easily missed. Developers write their own `tenacity.retry` layer, then wonder why the "3 retries" takes 45 seconds and why they hit the RPM limit.

**Consequences:**
- Unexpectedly slow failure paths (users wait 30+ seconds on a hard error).
- Genuine rate-limit exhaustion on the Anthropic side during development (Anthropic's tier-1 RPM is low).
- Retry storms that hide the root cause (e.g. an auth error getting retried 9 times before surfacing).

**Prevention:**
- Pick one retry layer. Either (a) configure the Anthropic SDK's built-in retry (pass `max_retries=N` to the client) and skip your own, OR (b) set `max_retries=0` on the SDK and own the retry loop explicitly. **Do not stack them.**
- Don't retry 401, 403, 400 (validation), or 404 — retries on non-transient errors waste time. The SDK skips these by default; your own retry code should too.
- Write a test with `respx`-like stubbing that returns 429 once, then 200 — assert exactly one retry happened. If the count is wrong, you have doubled-up retries.
- **[VERIFY]** Check current `anthropic` Python SDK docs for the retry parameter name and default count at time of implementation.

**Warning signs:** A single failing generation takes 30+ seconds of user wait. Logs show "retrying (attempt 7/9)" when spec says 3.

**Phase:** Phase 1 — Anthropic adapter.
**Severity:** Critical. Masks real bugs and wastes quota.

---

### C8. Context-window truncation on long Black Lodge wiki docs

**What goes wrong:** The content spine is existing wiki docs in `~/Documents/Black Lodge/knowledge-base/`. Some are long (`kubernetes-patterns.md`, `ml-systems-architecture.md` tend to be dense). Combined with a verbose system prompt + the tool-use schema + the user's prompt + room for a reply, you can approach or exceed the model's effective useful context — well before the hard limit. The symptom is not an error; it's the model losing track of instructions midway and producing low-quality cards or ignoring the "skip RBAC" style of directive.

**Why it happens:** Claude's context window is large, but "fits in the window" ≠ "model uses it well." Quality degrades well before the hard limit. Meanwhile the adapter doesn't know the input is degrading quality.

**Consequences:** Cards that aren't grounded in the source, user complaints "I said skip RBAC and it's all RBAC," silent quality degradation that's hard to attribute.

**Prevention:**
- Measure `len(source_text)` in characters/tokens in the adapter; warn/log if it exceeds a threshold (e.g. 30k tokens as a soft limit — **[VERIFY]** current Claude context recommendations).
- For the Phase 1 single-file path: if the source is long, surface a UI hint: "source is large; consider a more focused prompt or splitting the doc." Do not silently truncate without telling the user.
- Consider trimming boilerplate (navigation YAML frontmatter, wiki link sections) before sending — a one-line `strip_frontmatter` helper in the FILE reader.
- Phase 2's RAG addresses this properly; Phase 1 can ship with the warning + trim.

**Warning signs:** "Quality is bad when I generate from the long doc, fine from the short one." Users resorting to pasting excerpts.

**Phase:** Phase 1 — FILE reader + Anthropic adapter.
**Severity:** High. Affects perceived product quality.

---

### C9. Trafilatura + httpx: extraction quality silently varies; "worked on my site" is not a shipping criterion

**What goes wrong:** Trafilatura is the best general-purpose article extractor available, but:
- Paywall sites return a preview + upsell; trafilatura returns the preview as "the article." User is confused why their cards reference "sign up for full access."
- JS-rendered SPA sites (many modern blogs, Medium derivatives, Substack paywalls) return a skeletal HTML that trafilatura extracts to 40 words of nothing. No error, just empty-ish content.
- Character encoding detection can mis-detect on edge cases (Windows-1252 labelled as UTF-8); symptoms are � or mangled quotes. LLM then studies those.
- Some sites reject default `httpx` User-Agent (Cloudflare challenges, anti-bot); you get a 403 HTML page, trafilatura parses it, you generate cards about Cloudflare's challenge page.

**Why it happens:** Article extraction is fundamentally a best-effort heuristic job. Sites are varied, and failures are usually not HTTP errors — they're *successful HTTP responses with wrong content*.

**Consequences:** LLM generates confident, nicely-formatted cards based on garbage or the empty string or a paywall upsell. Worse than an error, because users won't realise the input was bad.

**Prevention:**
- After extraction, validate: `len(extracted_text) > MIN_CHARS` (e.g. 500), else raise `SourceNotArticle`. Short extractions are almost always wrong.
- Detect paywall markers in the extracted text (case-insensitive check for "subscribe", "sign up", "paywall", "continue reading", "free article") — if extraction is < 2000 chars AND contains two or more of these, flag as suspected paywall. This is heuristic but catches the common case.
- Set an explicit User-Agent (`Dojo/0.1 (+localhost)`), set `follow_redirects=True`, set a strict timeout (10s connect, 20s read). Catch `httpx.TimeoutException` explicitly and re-raise as `SourceFetchFailed` per spec §6.2.
- Respect the spec's `SourceNotArticle` exception — add a test for each of: (a) server returns 200 with 50 chars, (b) server returns a known paywall HTML snippet, (c) server returns binary. Each case must raise the correct exception.
- Log the first 200 chars of `source_text` on successful extraction at DEBUG — invaluable when debugging "why are my cards weird."

**Warning signs:** Users say "I gave it a URL and the cards are about things not in the article." "The URL fetched fine but the notes say 'see the full article' a lot."

**Phase:** Phase 1 — URL fetcher.
**Severity:** High. Affects URL source path quality.

---

### C10. In-memory draft store: two tabs, one token, mystery wrong-tab approvals

**What goes wrong:** The spec's in-memory draft store is keyed by a per-generation UUID session token. That's correct — one token per generation, not per user. But three subtle failure modes:

1. **Two tabs, same user, one generation each.** Fine in principle (two tokens). But if the tabs share a sticky "last draft" cookie/session, one tab overwrites the other's reference. User approves in the wrong tab, saves, sees unexpected content.
2. **User clicks "Generate" twice before the first completes.** Two LLM calls in flight; whichever returns last wins the token slot if the store key is anything other than strictly the server-generated UUID (e.g. if it's keyed on some form-derived value).
3. **TTL eviction during review.** User generates, walks away for 31 minutes, comes back, clicks approve. Draft is evicted. The save handler returns a confusing 404-ish error.
4. **Concurrent save + TTL eviction.** The save handler reads the draft, a reaper thread evicts it mid-save, write succeeds but then a retry sees nothing. Race window is small but real.

**Why it happens:** In-memory stores are easy to get wrong when multiple coroutines touch them. Python's dicts are thread-safe for single ops but not for read-modify-write sequences.

**Consequences:**
- Silent approval of wrong draft (bad).
- Confusing "your draft expired" error with no path to recover (bad UX).
- Lost work after LLM cost.

**Prevention:**
- **Store key:** server-generated UUID, returned to the template as a hidden form field. Never derive the key from user input.
- **Concurrency:** wrap the draft dict in an `asyncio.Lock` for write/delete operations. Reads can be lock-free if you `pop(key, default=None)` on save (atomic) rather than read-then-delete.
- **TTL:** 30 minutes per spec is fine; extend to 60 for the "walked away" case. Run the reaper as a lazy cleanup on access rather than a background task — simpler and no race with save handler. On every `get`/`pop`, check `now - created_at > ttl`, treat as missing if so.
- **UX on eviction:** if the save handler finds no draft, render a page explaining "your draft expired — the source_text and prompt are still in the URL, click here to regenerate." Store the regeneration inputs in the form, not only in the draft.
- **"Two tabs" mitigation:** Show the generation prompt prominently on the review page, so users see which draft they're looking at. Cheap and it works.
- Write a test that: generates, waits past TTL (use a fake clock, not `asyncio.sleep`), then saves — assert the "expired" error path.
- Write a test for concurrent save on the same token (two coroutines both call `save_draft`) — assert exactly one succeeds.

**Warning signs:** Any code path that does `draft = store[token]; ...; del store[token]` — non-atomic.

**Phase:** Phase 1 — Draft store + Save use case.
**Severity:** High. Will happen in normal single-user workflow.

---

## Moderate Pitfalls

Will cost hours, not days. Fixable at the phase they surface.

### M1. HTMX + FastAPI: forgetting to detect HX-Request for partial vs full renders

**What goes wrong:** A route returns a partial fragment (e.g. the updated card-review sidebar). User bookmarks or reloads the URL. They get a naked fragment with no `<html>`, no CSS, no nav — a broken page.

**Why it happens:** HTMX adds `HX-Request: true` on its requests. Routes need to branch on that header to return a full page for normal GETs and a fragment for HTMX GETs. It's a pattern people learn after the first bug report.

**Prevention:**
- A FastAPI dependency: `is_htmx_request: bool = Depends(lambda request: request.headers.get("HX-Request") == "true")`. Every route that returns partials uses it.
- Template convention: `partials/foo.html` for fragments, `pages/foo.html` for full pages, and a `pages/foo.html` that `include`s the partial. One source of truth per fragment.
- E2E test: for every URL used as an HTMX target, also verify a direct GET returns a full page.

**Phase:** Phase 1 — web routes.
**Severity:** Moderate. Easy fix; easy to ship the bug.

---

### M2. HTMX out-of-band (OOB) swaps: swap order matters; first-match wins for the main target

**What goes wrong:** You return a response with `<div id="result">...</div>` (main swap target) and `<div id="flash" hx-swap-oob="true">...</div>` (OOB). If the OOB element comes *before* the main target element in the response, you sometimes see the OOB swap happen and the main swap not happen, or vice versa, depending on HTMX version.

**Why it happens:** HTMX's parsing assumes the main target is the top-level direct child of the response. OOB elements are extracted; the rest is the "main" response. If your Jinja template is indented or wrapped in whitespace, parsing can be fussy.

**Prevention:**
- Put the main target as the first top-level element.
- Prefer `hx-swap-oob="outerHTML:#flash"` form (explicit selector) over inline `id`-matching.
- For the drill "card slides off + next card loads + progress bar updates" pattern, this is three swap targets. Consider: is it simpler to return one large fragment that contains all three regions? Usually yes.
- Add a simple E2E test that verifies all three regions updated after a drill rating POST.

**Phase:** Phase 1 — drill endpoint.
**Severity:** Moderate. Hard to debug without a browser.

---

### M3. HTMX + card slide-off animation: swap-before-animation kills the slide

**What goes wrong:** The Bumble/Tinder feel requires the card to animate off, *then* be replaced. HTMX's default swap is immediate — the card pops out, no slide. Add a CSS transition and it doesn't fire because the element is already gone before the browser can animate.

**Why it happens:** HTMX's `hx-swap-oob` and `hx-swap` don't wait for CSS transitions by default. You need `hx-swap="outerHTML swap:500ms"` (swap-delay) or an equivalent. **[VERIFY]** exact syntax against HTMX docs; this area has had refinements.

**Prevention:**
- Use `hx-swap` with `swap:Nms` timing to match the CSS transition duration.
- Add the CSS class (`.swiping-right` or `.swiping-left`) via `hx-on::before-request` (HTMX event hook). The sequence: user presses arrow → JS applies class → CSS transition runs → HTMX swap happens after `swap:Nms` → new card rendered.
- Prototype this early in Phase 1 — the drill UX is the defining UX of the app; getting it wrong ruins the "feel" that justifies the design.
- Tune `swap` delay to match CSS duration exactly; mismatches show as flashes/jitter.

**Warning signs:** "The card pops instead of sliding." "There's a flicker between cards."

**Phase:** Phase 1 — drill template + CSS.
**Severity:** Moderate on paper; high on perceived-polish since it's the flagship interaction.

---

### M4. HTMX inside partials: keyboard handlers stop working after first swap

**What goes wrong:** Put a JS keyboard listener in the drill template's partial. First card works. After HTMX swaps in the next card, the listener is still attached to the *old* element (which is detached) or to `document`. Multiple swaps → multiple listeners piling up → every key press triggers two actions (the "double-fire" bug).

**Why it happens:**
- Listeners attached to elements swapped out are garbage. Listeners attached to `document` accumulate on each swap.
- HTMX fires `htmx:afterSwap`; you can re-wire in that hook, but it's easy to forget.

**Prevention:**
- Attach keyboard listeners to `document` ONCE, at page load. Handle the key by looking up the currently-active card via its DOM id or a known class. One listener, routes by target.
- Alternatively use `hx-trigger="keyup[key=='ArrowRight'] from:body"` to bind via HTMX — no JS — and let HTMX re-bind on each swap. **[VERIFY]** current HTMX `from:` modifier behaviour.
- Write an E2E test that drills 3 cards and asserts each keyboard press produced exactly one rating (not two).

**Warning signs:** "Space skips two cards." "Arrow rates the card twice."

**Phase:** Phase 1 — drill template.
**Severity:** Moderate. Easy to spot; easy to fix once you know the pattern.

---

### M5. CSRF on HTMX POST: local app, but still a footgun

**What goes wrong:** Local-only app, so "no CSRF" feels fine. Until a user runs a malicious local page that POSTs to `http://localhost:8000/cards/123/rate`. Browser sends the request. Dojo cheerfully records a rating. Low-stakes, but the bad pattern can propagate to Phase 2/3 where real data is at risk.

**Why it happens:** Localhost is not a security boundary. Same-origin policy helps against cross-site POSTs from the browser's cross-origin protections, but lax CORS / no checks at all is still a lazy habit.

**Prevention:**
- **Don't enable CORS** beyond same-origin. FastAPI defaults are fine; don't install `CORSMiddleware` with `allow_origins=["*"]`.
- Add a `SameSite=Strict` cookie for any session/CSRF token.
- Skip a full CSRF middleware for MVP, but document the decision in `docs/architecture/` so Phase 2 knows it needs one if anything becomes remote.
- FastAPI `fastapi-csrf-protect` or similar is a one-hour add if we later decide we want it.

**Phase:** Phase 1 — web routes / document in architecture.
**Severity:** Low-moderate (local only), but don't let the pattern bleed into deployed code.

---

### M6. Pydantic DTO for LLM I/O: over-constraining the schema makes retries succeed slower

**What goes wrong:** The Pydantic DTO for `GeneratedContent` is strict: `title: str`, `content_md: str`, `cards: list[CardDraft]` with at least one. Spec §6.1 says "one retry with stricter prompt" on malformed output. If the DTO forbids optional fields that the model sometimes includes (e.g. a `notes_on_generation` field the prompt optionally asks for), every response with the extra field fails validation and consumes a retry.

**Why it happens:** Pydantic defaults to `extra="ignore"` since v2 — **[VERIFY]** for the version you pin. If someone sets `extra="forbid"` aspirationally ("strictness is good"), unexpected-but-harmless fields become validation failures.

**Prevention:**
- `model_config = ConfigDict(extra="ignore")` on DTOs. Let the model include extra stuff; ignore it.
- Strict-typed required fields, optional fields default-None.
- `min_length=1` on `cards` list — a real constraint — is worth enforcing and retrying for.
- Separate "schema conformance" from "quality." The DTO ensures shape; the use case ensures `len(cards) > 0`; the user ensures the content is good via the review UI.

**Phase:** Phase 1 — Anthropic adapter + DTOs.
**Severity:** Moderate. Wastes LLM calls.

---

### M7. TDD-with-fakes drift: the "testing your fake" anti-pattern

**What goes wrong:** Tests pass against `FakeLLMProvider`, real adapter is broken. The fake's behaviour encodes assumptions that the real adapter doesn't satisfy (or vice versa). Test suite is green; production is broken. The fake silently *became* the spec.

**Why it happens:**
- Fakes are written alongside the use case and drift toward "whatever makes the test pass" rather than "whatever the real adapter does."
- No contract test exists to pin both implementations to the same behaviour.
- The real adapter gets exercised only in manual testing or E2E, which is rare.

**Prevention:**
- **Contract tests:** one test suite, parameterised over `[FakeLLMProvider, AnthropicLLMProvider]`, that asserts Protocol-level behaviour. The Anthropic version is gated behind `RUN_LLM_TESTS=1` (per spec §7.2). This is the single most effective defense; without it, fakes drift within a sprint.
- **Fake design rules:**
  - Fakes should implement the Protocol method signatures, nothing more.
  - Fakes should NOT silently succeed on inputs the real adapter would fail on — if the real adapter raises `LLMContextTooLarge` at N tokens, the fake should too (configurable).
  - Fake state (`fake.calls`, `fake.saved_cards`) should be assertable via dataclass equality, not call-pattern matching.
- **"Integration over fake" rule:** if a use case's behaviour depends on subtle real-adapter semantics (e.g. the exact shape of tool-use responses), the test for it should be an integration test with a stubbed HTTP layer (`respx` against real Anthropic SDK), not a unit test against the fake.
- Document in `docs/architecture/`: "fakes are for orchestration tests; adapter semantics are tested in integration."
- Review checklist: every time the real adapter's behaviour changes, the fake is updated OR the fake's behaviour is explicitly flagged as "intentionally simpler than real."

**Warning signs:** A commit modifies `AnthropicLLMProvider` but not the `FakeLLMProvider`. A fake has conditional logic that mirrors production ("if source_text is None…") — now the fake has bugs too.

**Phase:** Phase 1, and it compounds every phase after. Address at the boundary definition step.
**Severity:** High long-term. Subtle and self-reinforcing; easy to ignore until production bites.

---

### M8. pytest-asyncio `event_loop` / `asyncio_mode` footguns

**What goes wrong:** Async SQLAlchemy sessions are bound to an event loop. If `pytest-asyncio` creates a new loop per test and your session fixture persists across tests, the session silently refers to a dead loop on the second test → cryptic `RuntimeError: Event loop is closed` or `this Session's transaction has been rolled back due to a previous exception during flush` mid-suite.

**Why it happens:**
- `pytest-asyncio` has two modes (`auto`, `strict`). Pick one.
- Default fixture scopes (function-level) create a new loop per test. Session-scoped DB engines cross that boundary.
- The "correct" pattern has moved between versions; older tutorials are wrong.

**Prevention:**
- Set `asyncio_mode = "auto"` in `pyproject.toml` under `[tool.pytest.ini_options]` — less per-test boilerplate.
- Use a session-scoped event loop fixture if you use session-scoped DB fixtures:
  ```python
  @pytest.fixture(scope="session")
  def event_loop_policy():
      return asyncio.DefaultEventLoopPolicy()
  ```
  **[VERIFY]** against current `pytest-asyncio` docs — the canonical fixture has changed.
- Alternatively: function-scoped engine per test, tmp-file SQLite, apply migrations once (session) but fresh session per test. Slower but robust.
- First integration test written: run it 10 times in a row; if it flakes, you have an event-loop bug, not a test bug.

**Phase:** Phase 1 — test infrastructure. Address before writing more than 3 integration tests.
**Severity:** Moderate. Won't corrupt data, but can sink a day.

---

### M9. `uv` + editable install + Alembic: migrations import the app, app needs migrations

**What goes wrong:** `migrations/env.py` imports `app.infrastructure.db.models` so autogenerate works. Under `uv` with an editable install (`uv pip install -e .`), this works — *until* you add a new module `app/infrastructure/db/foo.py` and forget to re-sync the env. Specifically: sometimes people run `alembic revision --autogenerate` in a stale venv and it doesn't see the new model → empty migration.

**Why it happens:** Editable installs link the source tree, but Python's import caching, plus environment-directory confusion across `uv run` vs an already-activated shell, can cause stale discovery. Plus: new files need the package's `__init__.py` export to be discovered by `Base.metadata` if you're relying on side-effect imports.

**Prevention:**
- `env.py` imports a single `Base` (from `app.infrastructure.db.models`) and that module eagerly imports every model file (one `from . import foo, bar, baz` line that's updated as models are added).
- Add a test or make target that asserts `Base.metadata.tables` includes every expected table — a 5-line smoke test catches the "forgot to import" case.
- Document the "add-a-model" procedure in `docs/architecture/` so it's rote.
- Use `uv run alembic revision ...` rather than activating the venv manually — uv guarantees the environment matches the lockfile.

**Phase:** Phase 1 — as models are added.
**Severity:** Moderate. Silent empty migrations are a footgun, but smoke tests catch it.

---

### M10. Ruff + ty + interrogate: ordering in pre-commit determines signal quality

**What goes wrong:** Pre-commit runs all three checks. If `ruff format` is first and changes a file, the subsequent `ty` and `interrogate` runs on the already-staged content or on the unchanged file, depending on hook config. The failure is cryptic: "format fixed things, but the commit fails because interrogate saw old docstrings."

**Why it happens:**
- Pre-commit hook ordering matters.
- Some hooks auto-fix (ruff format, ruff check `--fix`). Others don't (ty, interrogate, pytest).
- If an auto-fixer runs and makes changes, the *whole commit* is aborted by default and the developer must re-stage — but people then re-run hooks without understanding the flow.

**Prevention:**
- Pre-commit order: (1) `ruff format`, (2) `ruff check --fix`, (3) `ty`, (4) `interrogate`, (5) `pytest`. Auto-fixers first; checks that report-only after. Format before lint prevents format churn from causing lint failures.
- Tell developers: if pre-commit says "files modified, re-stage and re-commit," that's expected — it's the auto-fixer doing its job.
- Don't run `pytest` in pre-commit if the suite takes >10 seconds. Put it in a push-hook or CI only.
- Document the rationale in `.pre-commit-config.yaml` comments.

**Phase:** Phase 1 — tooling setup.
**Severity:** Moderate — will confuse the first person who commits, not damaging.

---

### M11. `interrogate` 100% + Protocol methods: docstring compliance fights "self-documenting protocol" idiom

**What goes wrong:** 100% docstring coverage means every Protocol method needs a docstring. Protocols by nature are interface definitions where method signatures often speak for themselves. Forcing a docstring produces noise: `"""Save a source."""` above `def save(self, source: Source) -> None: ...`.

**Why it happens:** `interrogate` counts docstrings at the method level. It doesn't have a "Protocol methods are interface declarations" exception.

**Prevention:**
- Option A (preferred): accept the mild noise, write one-line docstrings that at least specify the return/error semantics rather than restate the name. Example: `"""Save source; raises DuplicateSource if identifier exists."""` — adds info.
- Option B: configure `interrogate` to ignore a specific path (`app/application/ports.py`). Documented in `pyproject.toml`. Keeps the 100% target honest elsewhere.
- Pick one in Phase 1; don't let it simmer.

**Phase:** Phase 1 — first ports.pyrum through interrogate.
**Severity:** Low; but worth deciding early to avoid churn.

---

### M12. aiosqlite single-writer: concurrent writes block, not error

**What goes wrong:** SQLite has one writer. Under aiosqlite, a second concurrent write waits. With two coroutines both saving drafts (unlikely in single-user, but possible if the user clicks Save + navigates + triggers another action), one coroutine blocks. At Phase 1 scale it's invisible. At E2E test scale where tests run in parallel on the same DB file, you get timeouts.

**Why it happens:** SQLite `busy_timeout` is finite; concurrent writers past that error out with "database is locked." aiosqlite respects this.

**Prevention:**
- Set `PRAGMA journal_mode=WAL` on connection. WAL mode allows concurrent read + one writer without blocking readers. Set this once in connection init.
- Set `PRAGMA busy_timeout = 5000` (5s) to retry contended writes.
- E2E tests use per-test DB files, not a shared file.
- Document that MVP is single-user; concurrency is not a perf goal.

**Phase:** Phase 1 — DB session setup.
**Severity:** Low for production usage; moderate for parallel test runs.

---

## Minor Pitfalls

Annoyances. Won't derail but worth naming.

### m1. `.env` precedence vs real env vars

`pydantic-settings` loads `.env` but real env vars win. If a developer has `ANTHROPIC_API_KEY` in their shell from another project, they can't override it by changing `.env`. Confusing first time. Prevention: document the precedence in `.env.example` header comments. One sentence.

### m2. `markdown-it-py` default doesn't sanitize

Notes come from the LLM. LLMs rarely produce XSS; they occasionally produce `<script>` blocks in code samples. The default renderer leaves HTML untouched by spec. Prevention: enable HTML escaping in renderer config OR run output through `bleach`/equivalent. For a local-single-user app the risk is tiny, but treating it as "rendered markdown input" is a bad habit to form. **[VERIFY]** markdown-it-py default safe-mode behaviour.

### m3. Mermaid rendering in Obsidian vs GitHub

The four architecture diagrams must render in both. Obsidian and GitHub have diverged in Mermaid features slightly (GitHub uses a specific pinned version). Diagrams with newer Mermaid syntax render in Obsidian, silently fail on GitHub. Prevention: stick to basic `flowchart TB`, `erDiagram`, `sequenceDiagram` — no `classDiagram` or `timeline` unless manually verified. Test by pushing and viewing on GitHub, not just locally.

### m4. Pico.css theme override in partial templates

Pico.css applies styles based on `<main>`, `<article>`, `<section>` containers. HTMX partials returning bare fragments outside these containers get un-styled. First fix is usually "wrap every partial in `<article>`," which sometimes duplicates `<article>` tags if the swap target is already an article. Prevention: decide at template-design time which partial goes into which container type, document on the partial.

### m5. Playwright + HTMX timing

Playwright's `page.click` returns when the click is dispatched, not when the HTMX swap completes. Assertions immediately after clicks flake. Prevention: after any HTMX-triggering click, use `await page.wait_for_selector(...)` on a post-swap DOM marker, or `await page.wait_for_load_state("networkidle")`. Never `await asyncio.sleep(0.5)` — flake factory.

### m6. `ruff` 79-char line limit forces odd function signatures

79 chars is tight for type-annotated async FastAPI signatures with `Depends`. Developers break signatures across many lines in ugly ways. Ruff's formatter does it well; manual formatting fights ruff. Prevention: let ruff format. Don't manually format signatures.

### m7. `ty` (Astral) — early-stage type checker

`ty` is Astral's new type checker (aka `red-knot`). At time of writing **[VERIFY — check release status in 2026]**, it's young compared to mypy/pyright. It may not support every construct; expect occasional false positives or unsupported features (complex generics, some Protocols with overloads). Prevention: have a `pyproject.toml` fallback plan to add `mypy` if `ty` blocks progress on a specific pattern. Don't fight the tool; swap tools.

### m8. "Pristine test output" rule + noisy third-party libs

`trafilatura`, `httpx`, and occasionally `anthropic` log warnings at WARN or INFO level that appear in pytest output. "Pristine" means zero noise. Prevention: configure `pytest` logging to only show messages from our own logger namespace, or set third-party loggers to ERROR in a conftest fixture. Decide early so tests don't accrete skipped-warning technical debt.

---

## Phase-Specific Warnings

| Phase / Topic | Likely Pitfall | Mitigation |
| --- | --- | --- |
| Phase 1 — DB setup (earliest) | C4 (async Alembic), M8 (pytest-asyncio loop) | Do these first, verify with a full `make migrate && make test` loop before writing business code |
| Phase 1 — Repositories | C1 (MissingGreenlet), C2 (selectinload vs joinedload), C3 (expire_on_commit), C5 (atomic save) | Integration tests with real aiosqlite from day 1; use `lazy="raise"`; mapper pattern enforced |
| Phase 1 — Anthropic adapter | C6 (schema reliability), C7 (double-retry), C8 (context size), M6 (DTO strictness) | One-retry pattern in spec; pin SDK retry config; token-size warning |
| Phase 1 — URL fetcher | C9 (extraction quality) | Min-length + paywall-heuristic + explicit User-Agent |
| Phase 1 — Draft store | C10 (TTL, concurrency, two-tab) | `asyncio.Lock`, lazy TTL, UUID server-generated key, regen-from-URL fallback |
| Phase 1 — Drill UX | M3 (swap timing), M4 (keyboard listeners), m5 (Playwright flake) | Prototype early; swap-delay + CSS transition matched; document-level listeners; explicit waits in E2E |
| Phase 1 — HTMX routes | M1 (HX-Request detection), M2 (OOB swap order), M5 (CSRF local) | `is_htmx_request` dep; main target first; no `CORS *` |
| Phase 1 — Tests | M7 (fake drift), M8 (event loop), m8 (test noise) | Contract tests gated on env; session-scoped loop if session-scoped DB; logger fixtures |
| Phase 1 — Tooling | M9 (uv+alembic), M10 (pre-commit order), M11 (interrogate+Protocol) | Eager imports in Base module + smoke test; documented hook order; decide interrogate exception policy |
| Phase 2 — RAG | (carry-forward) C1/C2 (new repo + relationships), C6 (embedding-provider port quality checks) | Same mapper discipline; contract tests for the retriever port |
| Phase 2 — Mock interview | C6 (more complex structured output: grading dict) | Stricter DTO; more retry-on-malformed budget |
| Phase 3 — SRS | Migration from `CardReview` log to scheduling columns — Alembic async migration involving data backfill | Practice a data-migration Alembic revision first; off-peak run; backup `.db` before migrate |

---

## The 8 Focus Areas — Coverage Map

| Focus area (from milestone context) | Covered by |
| --- | --- |
| 1. Async SQLAlchemy 2.0 + FastAPI + aiosqlite | C1, C2, C3, C4, C5, M8, M9, M12 |
| 2. Anthropic SDK + structured output | C6, C7, C8, M6 |
| 3. HTMX + FastAPI + Jinja | M1, M2, M3, M4, M5 |
| 4. Trafilatura + httpx | C9, m2 |
| 5. TDD with hand-written fakes | M7 (primary), plus M8 for the infra side |
| 6. Pico.css + HTMX drill animation | M3, M4, m4 |
| 7. In-memory draft store | C10 |
| 8. Dev tooling (ruff/ty/interrogate/uv/alembic/pre-commit) | C4, M9, M10, M11, m1, m6, m7, m8 |

All 8 focus areas covered. None skipped.

---

## Sources

External verification was not available in this session (WebSearch, Context7, and WebFetch were denied at the tool layer). Everything here is drawn from Claude's training-era knowledge of these stacks. Items marked **[VERIFY]** inline are the highest-priority targets for a second-pass docs check before roadmap commitment; the rest are well-established enough to trust but would benefit from confirmation against current library versions.

Recommended verification sources when docs access is available:

- **SQLAlchemy 2.0 async docs** — specifically `lazy="raise"`, `expire_on_commit`, and greenlet-compatibility sections.
- **Alembic async migrations** — `alembic init -t async` scaffold and env.py patterns.
- **Anthropic Python SDK README + API docs** — retry config, tool-use input parsing, context-window sizes current as of 2026-04.
- **trafilatura documentation** — extraction-quality guarantees, known-broken-site lists in their test suite.
- **HTMX docs** — `hx-swap` timing modifiers, `from:` trigger modifier, OOB swap ordering rules.
- **pytest-asyncio release notes** — current fixture pattern; the canonical has changed a few times.
- **ty (Astral) release notes / issue tracker** — check what's supported as of 2026-04 before committing.

Confidence on the pitfalls themselves: **HIGH** for items 1–7 that are fundamental to the libraries (greenlet, selectinload, expire_on_commit, Alembic async, atomic transactions, schema reliability, rate-limiting). **MEDIUM** for items depending on library-version specifics (HTMX swap-delay syntax, pytest-asyncio fixture shape, ty capabilities). **LOW** for items where the recommendation is a heuristic (paywall detection in C9, context-size threshold in C8) — these are directionally correct but the exact numbers need tuning from real usage.
