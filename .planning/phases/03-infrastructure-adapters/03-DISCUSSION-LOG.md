# Phase 3: Infrastructure Adapters - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or
> execution agents. Decisions are captured in `03-CONTEXT.md` — this
> log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 03-infrastructure-adapters
**Areas discussed:** Transaction boundary, ORM↔domain mapping,
Anthropic retry ownership, DraftStore concurrency

---

## Area Selection

**Question:** Which Phase 3 areas do you want to discuss? (Pick any —
others default to Claude's discretion in planning.)

| Option | Selected |
|---|---|
| Transaction boundary | ✓ |
| ORM↔domain mapping style | ✓ |
| Anthropic retry ownership | ✓ |
| DraftStore concurrency model | ✓ |

**User's choice:** All four.

---

## Transaction boundary

**Question:** Who owns the SQLAlchemy session + transaction boundary?

| Option | Description | Selected |
|---|---|---|
| Use case opens `session.begin()` | FastAPI dep yields per-request Session; use case constructs session-bound repos inside `with session.begin():`; no UnitOfWork port. | ✓ |
| Explicit UnitOfWork Protocol | New `UnitOfWork` Protocol exposing `uow.sources` etc. + `__enter__`/`__exit__`/`commit`; adds new port + `SqlUnitOfWork` adapter. | |
| Route opens the transaction | FastAPI dep opens both session and `session.begin()`; use case never touches lifecycle. | |

**User's choice:** Use case opens `session.begin()`.
**Notes:** Repos receive Session at construction (Phase 2 port
signatures already preclude per-method session args). No new
UnitOfWork Protocol — the Session already serves the role.

---

## ORM↔domain mapping style

**Question (initial):** How should domain entities map to SQLAlchemy
rows?

User requested clarification on option 1 before answering. Option 1
was re-explained with a concrete code sketch (separate `*Row(Base)`
classes + pure `to_row`/`from_row` mapper functions; repo calls
translate at the boundary), after which the user asked about the
full end-to-end flow (who sees domain vs ORM vs Session). Provided
a who-sees-what matrix and a concrete trace through
`use_case → repo.save → mapper → session.merge → SQL`. User then
asked specifically about how `GenerateFromSource` calls a repo;
clarified that it does not — generation is pre-persist, only
`DraftStore` is touched; repo calls land in a future Phase 4
`SaveDraft` use case. User also asked to elaborate on
"use case sees Session", which was expanded: the use case holds a
`Session` reference as a transaction-scoping handle and only calls
`.begin()` on it; all SQL-adjacent calls go through repos.

**Question (re-asked):** Given the concrete sketch above, how should
domain entities map to SQLAlchemy rows?

| Option | Description | Selected |
|---|---|---|
| Declarative ORM + mapper fns | Separate `*Row(Base)` classes + pure `to_row`/`from_row` functions; repos translate at boundary; domain stays stdlib-pure. | ✓ |
| Imperative mapping on dataclasses | `registry.map_imperatively` on domain dataclasses; fuses domain + ORM. | |
| Domain IS the ORM model | Collapse into one class inheriting from Base; breaks import-linter contract. | |

**User's choice:** Declarative ORM + mapper fns.
**Notes:** User followed up with three documentation asks that were
captured as Phase 3 deliverables in CONTEXT.md §D-09 and a
chore PR #11:
1. `GenerateFromSource` docstring clarification (pre-persist
   contract) → landed as PR #11 on `chore/generate-from-source-docstring`.
2. Arch doc extension (persistence data flow, save-side trace,
   Session semantics, mapper sketch, SaveDraft diagram) → Phase 3
   deliverable.
3. Fix stale `asyncio.Lock` line in arch doc §4 → Phase 3
   deliverable alongside Area 4 lock.

---

## Anthropic retry ownership

**Question (initial):** Which layer owns the Anthropic retry budget?

User requested elaboration before answering. Option 1 was expanded
with a concrete adapter sketch showing two distinct retry layers:
(1) tenacity-decorated transport retries on the SDK call, (2)
explicit `try/except ValidationError` semantic retry for malformed
JSON. Covered the exception whitelist (`RateLimitError`,
`APIStatusError`, `APIConnectionError` only; permanent failures like
401/400/404 propagate). Covered worst-case call count (6 HTTP calls
before giving up). Covered Phase 3 SC #4 test pattern via respx
stub.

**Question (re-asked):** Given that sketch, which layer owns the
Anthropic retry budget?

| Option | Description | Selected |
|---|---|---|
| Tenacity owns, SDK muzzled | `Anthropic(max_retries=0)` + `@retry` decorator; separate try/except for semantic retry. | ✓ |
| SDK owns retries | `Anthropic(max_retries=3)`, skip tenacity; contradicts prior tenacity decision. | |
| Both (C7 trap) | Stack them; name-and-reject. | |

**User's choice:** Tenacity owns, SDK muzzled.
**Notes:** Locked exception whitelist, locked separation of
transport retry (tenacity) vs semantic retry (try/except). SDK
exceptions wrap into domain types at the adapter's outer boundary.

---

## DraftStore concurrency model

**Question (initial):** What concurrency primitive should
InMemoryDraftStore use?

User requested elaboration on option 1 and the GIL atomicity
claim. Expanded: explained GIL as CPython implementation detail;
enumerated which dict operations are atomic (including
`dict.pop(k, default)`) vs which require a lock; explained asyncio
single-event-loop as a second safety net independent of GIL;
sketched the full `InMemoryDraftStore` class with injected clock
for TTL testing; sketched SC #5 test patterns; flagged
CPython-3.13-no-GIL as a future caveat worth a docstring comment.

**Question (re-asked):** Given the GIL atomicity explanation, what
concurrency primitive should InMemoryDraftStore use?

| Option | Description | Selected |
|---|---|---|
| Plain dict, no lock | `dict.pop(token, None)` is GIL-atomic; lazy TTL via injected clock; class docstring names the GIL assumption. | ✓ |
| `threading.Lock` around put/pop | Defense-in-depth for hypothetical future sync routes; trivial overhead but adds indirection. | |
| `asyncio.Lock` | Requires flipping Protocol to `async def`; contradicts Phase 2 D-04. | |

**User's choice:** Plain dict, no lock.
**Notes:** Supersedes Phase 2 CONTEXT.md §D-05's `asyncio.Lock`
note (which came from the pre-reversal async-throughout
assumption). Lazy TTL check on access; no background sweep.
Class docstring must name the CPython-GIL assumption so no-GIL
Python (PEP 703) isn't accidentally shipped.

---

## Claude's Discretion

Captured in `03-CONTEXT.md` §Decisions → Claude's Discretion:
- Per-request Session via FastAPI `Depends(get_session)`
- Repository file layout (one file per repo vs one combined file)
- Anthropic tool schema shape (one tool vs two)
- Exact tenacity decorator wiring (module vs instance)
- Fake clock fixture shape
- respx fixture organization
- `trafilatura` config options
- Exception class hierarchy additions

Plus sub-areas settled without explicit discussion:
- URL fetcher paywall heuristics (D-05)
- FILE reader encoding + path policy (D-06)
- Contract harness extension pattern (D-07)
- Migration authoring workflow (D-08)

---

## Deferred Ideas

Captured in `03-CONTEXT.md` §Deferred:
- `UnitOfWork` Protocol (revisit if second persistence backend)
- ORM relationships (revisit if aggregate-load dominates)
- Background TTL sweep (revisit if memory pressure)
- `threading.Lock` in DraftStore (revisit on no-GIL Python)
- Anthropic SDK built-in retry (revisit if tenacity is awkward)
- Async SQLAlchemy repositories (rejected project-wide)
- OpenAI / Ollama providers (v1 out-of-scope)
- FOLDER source kind + RAG (v2)
- SRS / streaks / FTS / Anki export (v2+)
