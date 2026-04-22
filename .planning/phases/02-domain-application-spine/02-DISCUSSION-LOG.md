# Phase 2: Domain & Application Spine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or
> execution agents. Decisions are captured in `02-CONTEXT.md` — this
> log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 02-domain-application-spine
**Areas discussed:** Typed IDs & identity, DraftStore port contract,
GenerateFromSource shape, TEST-03 + boundary enforcement

---

## Gray-Area Selection

**Question:** Which of these gray areas do you want to discuss before
Phase 2 planning?

| Option | Description | Selected |
|--------|-------------|----------|
| Typed IDs & identity | NewType vs dataclass wrapper vs bare UUID; mint site | ✓ |
| DraftStore port contract | Atomic pop vs get+delete; TTL scope | ✓ |
| GenerateFromSource shape | Request/response DTO shape; TOPIC-only scope | ✓ |
| TEST-03 + boundary enforcement | Contract harness pattern + layer lint choice | ✓ |

**User's choice:** All four.

---

## Typed IDs & Identity

### Q1 — ID representation

| Option | Description | Selected |
|--------|-------------|----------|
| NewType over UUID | Type-safe, zero runtime cost, stdlib-only | ✓ |
| Frozen dataclass wrapper | Room to grow (methods, validation); ceremony-heavy | |
| Bare UUID type alias | Simplest; loses type-level distinction | |
| int primary keys | Forces Optional[Id] / "unsaved" state in domain | |

**User's choice:** NewType over UUID (recommended).
**Notes:** Locked `SourceId = NewType("SourceId", uuid.UUID)` etc.
in `app/domain/value_objects.py`.

### Q2 — ID mint site

| Option | Description | Selected |
|--------|-------------|----------|
| Domain constructor via default_factory | Every entity fully identified at construction | ✓ |
| Application layer (use case mints) | No hidden defaults; every caller wires uuid | |
| IdGenerator Protocol port | Deterministic fake; overkill for UUID4 | |
| DB mints via server default | Requires Optional[Id]; violates "fully populated at construction" | |

**User's choice:** Domain constructor via default_factory (recommended).
**Notes:** Mapper in Phase 3 passes stored UUID explicitly when loading.
Tests override `id=` for determinism.

---

## DraftStore Port Contract

### Q1 — Port operations

| Option | Description | Selected |
|--------|-------------|----------|
| put + pop (atomic), nothing else | Two methods; pop is atomic read-and-delete (PITFALL C10) | ✓ |
| put + get + delete (explicit) | Three methods; every caller must remember to be atomic | |
| put + get + pop + delete | Full CRUD; larger surface = more fake-drift risk | |

**User's choice:** put + pop, nothing else (recommended).
**Notes:** No `get` on the port — forces callers to commit-or-discard.

### Q2 — TTL / concurrency semantics scope

| Option | Description | Selected |
|--------|-------------|----------|
| Port docstring only; Phase 3 adapter owns enforcement | Clean Protocol; matches C10 remedies as adapter-local | ✓ |
| Port exposes TTL / Clock explicitly | Drives tests at port level; bleeds adapter concerns | |
| Port exposes an `evict_expired()` method | Contradicts "lazy TTL on access"; no current caller | |

**User's choice:** Port docstring only (recommended).
**Notes:** FakeDraftStore has a `force_expire(token)` test hook.

---

## GenerateFromSource Shape

### Q1 — Request signature

| Option | Description | Selected |
|--------|-------------|----------|
| Typed GenerateRequest DTO | Single request dataclass; easy to extend; web layer stays thin | ✓ |
| Positional args (kind, input, user_prompt) | Less ceremony; every caller changes as signature grows | |
| Kind-specific execute methods | No nullable input; doubles surface; duplicates orchestration | |

**User's choice:** Typed GenerateRequest DTO (recommended).
**Notes:** Plain dataclass (not Pydantic — Pydantic reserved for LLM
I/O boundary).

### Q2 — Response shape

| Option | Description | Selected |
|--------|-------------|----------|
| Full DraftBundle + token | Review screen renders directly; keeps pop atomic | ✓ |
| Token only | Forces `get` on the port, reopens C10 hole | |
| Save-and-return-ids | Contradicts DRAFT-01 + PROJECT.md Key Decision | |

**User's choice:** Full DraftBundle + token (recommended).
**Notes:** `DraftBundle` is an app-layer dataclass, not a domain
entity. Draft store still holds a copy for reload.

### Q3 — FILE / URL behavior in Phase 2

| Option | Description | Selected |
|--------|-------------|----------|
| Raise UnsupportedSourceKind; scaffold error path | Explicit; Phase 4 flips the raise to a real call | ✓ |
| Scaffold all three branches calling fakes | All three kinds work end-to-end now; more Phase 2 churn | |
| Guard with assert / narrowed input type | Clean per-kind typing; duplicates orchestration | |

**User's choice:** Raise UnsupportedSourceKind (recommended).
**Notes:** Unit test covers the raise path.

---

## TEST-03 + Boundary Enforcement

### Q1 — Contract harness pattern

| Option | Description | Selected |
|--------|-------------|----------|
| pytest fixture param ids + skip-unless-env | Standard idiom; auto-skip on ImportError in Phase 2 | ✓ |
| Marker-gated separate classes | Two class bodies; risk of drift | |
| Deferred-import stub module in Phase 2 | Dead code committed for show; violates Phase-1 D-11 spirit | |

**User's choice:** pytest fixture params + skip-unless-env (recommended).
**Notes:** Anthropic branch skips unless `RUN_LLM_TESTS=1` AND
AnthropicLLMProvider import succeeds. Phase 2 import fails → auto-skip.

### Q2 — Boundary enforcement mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| import-linter with contracts file | Proper tool; declarative; clear failure messages | ✓ |
| grep-in-CI one-liner | Zero new deps; brittle under refactors | |
| Custom pytest AST walker | Reinvents a subset of import-linter | |

**User's choice:** import-linter (recommended).
**Notes:** Two forbidden contracts (domain → {infra, web}; app → {infra,
web}). Wired into `make lint`.

---

## Wrap-up

**Question:** Dig into remaining smaller gray areas or write CONTEXT.md now?

| Option | Description | Selected |
|--------|-------------|----------|
| Write CONTEXT.md now | Fold entity mutability, DTO posture, fakes layout, exception split into Claude's Discretion | ✓ |
| Discuss entity mutability | Frozen vs mutable dataclasses | |
| Discuss exception hierarchy | Common DojoError base vs stand-alone | |
| Discuss fake design conventions | .calls lists vs .saved_entities dicts | |

**User's choice:** Write CONTEXT.md now (recommended).
**Notes:** Claude's Discretion items locked with defaults; surface
only if planning/execution reveals a conflict.

---

## Claude's Discretion

Folded into `02-CONTEXT.md` `<decisions>` → Claude's Discretion:

- Entity mutability — frozen dataclasses, edits via `dataclasses.replace()`
- Pydantic DTO posture — `extra="ignore"` + `min_length=1` on cards
- Fakes file layout — one file per fake under `tests/fakes/`
- Fake assertion style — public attrs, not `.calls` lists
- Domain vs application exception split (`DojoError` base in domain,
  use-case failures in application)
- Entity construction invariants — `__post_init__` + `ValueError` for
  non-empty string checks

## Deferred Ideas

Folded into `02-CONTEXT.md` `<deferred>`:

- `FOLDER` source kind + Retriever/EmbeddingProvider ports (v2)
- Mock interview mode (v2)
- SRS scheduling (v2 Phase 3)
- `IdGenerator` Protocol port (rejected in favor of default_factory)
- DB-mint-at-insert for IDs (rejected)
- Port-level TTL / Clock injection on DraftStore (rejected)
- Deferred-import stub for AnthropicLLMProvider (rejected)
- Custom AST-walking pytest test for boundary (rejected)
