# Phase 2: Domain & Application Spine - Research

**Date:** 2026-04-22
**Scope:** Narrow — covers import-linter config, package layout, TDD
shape, plan decomposition hint.
**Skipped intentionally:** NewType-UUID idiom, Pydantic v2 DTO posture,
pytest fixture canonical (`params=`), Protocol without
`@runtime_checkable`, frozen dataclasses, DraftStore port surface,
GenerateFromSource request/response shape, TEST-03 harness pattern,
boundary-enforcement choice — all locked in `02-CONTEXT.md`.

**Confidence:**
- Section 1 (import-linter): HIGH — verified against current official
  docs (Context7, `/websites/import-linter_readthedocs_io_en_stable`,
  2026 stable).
- Sections 2–4 (derived): HIGH for structure, MEDIUM for exact LOC
  estimates (rule-of-thumb).

---

## 1. import-linter Configuration

### 1.1 Facts verified against current docs

All claims in this subsection are `[CITED: import-linter.readthedocs.io/en/stable]`
unless explicitly marked otherwise.

**a. TOML syntax for forbidden contracts inside `pyproject.toml`** —
The current docs show two supported syntaxes. The one that belongs
inside `pyproject.toml` uses the nested-table form under
`[tool.importlinter]` and `[[tool.importlinter.contracts]]`:

```toml
[tool.importlinter]
root_package = "app"

[[tool.importlinter.contracts]]
name = "Human-readable contract name"
type = "forbidden"
source_modules = ["app.domain"]
forbidden_modules = ["app.infrastructure", "app.web"]
```

(The flat `[importlinter]` / `[importlinter:contract:name]` form shown
in some examples is the INI-file syntax used when config lives in a
separate `.importlinter`/`setup.cfg`, not inside `pyproject.toml`.)

**b. Sub-package coverage (the decision-critical fact):** Forbidden
contracts treat `source_modules` and `forbidden_modules` as **packages
by default**. The docs say verbatim:

> "By default, descendants of each module will be checked — so if
> `mypackage.one` is forbidden from importing `mypackage.two`, then
> `mypackage.one.blue` will be forbidden from importing
> `mypackage.two.green`. Indirect imports will also be checked."

This means one entry `app.domain` covers `app.domain.entities`,
`app.domain.value_objects`, `app.domain.exceptions`, etc. **No
wildcards or explicit sub-package listing required.** The knob that
turns this off is `as_packages = false` — we leave it at its default
(`true`).

Indirect imports are also caught by default: if `app.domain.entities`
imports `something_neutral` that in turn imports
`app.infrastructure.db.session`, the contract is still broken. (There
is an `allow_indirect_imports` option but Dojo leaves it off —
indirect leaks are exactly the bug we want to catch.)

**c. CLI invocation:**
- Command: `lint-imports` (single command, installed on PATH when the
  package is installed into the venv).
- Default discovery: looks for `pyproject.toml` (TOML parsed),
  `.importlinter` (INI), then `setup.cfg` (INI). Since Dojo already
  has `pyproject.toml` and we're adding `[tool.importlinter]` there,
  discovery is automatic — no `--config` flag needed.
- Exit codes: zero on pass, non-zero on any broken contract. This is
  what makes `make lint` fail the CI gate when a forbidden import
  sneaks in. [CITED: standard Unix exit semantics; import-linter
  follows them as per docs' "Run the linter" section.]
- Useful optional flags (not needed for Dojo's Phase 2 baseline, but
  worth knowing): `--contract <id>` to check just one, `--no-cache` to
  bypass the `.import_linter_cache/` dir it creates,
  `--show-timings` for perf debugging.

**d. `uv`-managed projects in package mode (Phase 1 D-20):** No known
pitfalls. `import-linter` imports the target package to build its
import graph, so the target package must be installable and importable
from the venv. Dojo's Phase 1 D-20 already declared `package = true`
under `[tool.uv]` and `packages = ["app"]` under
`[tool.hatch.build.targets.wheel]` — `uv sync` installs `app` as an
editable package, so `uv run lint-imports` resolves `import app` via
the venv exactly the same way `uv run pytest` resolves test imports.
No PYTHONPATH wrangling, no sys.path hacks. [CITED: D-20 in
`01-CONTEXT.md`; confirmed compatible with import-linter's "target
package must be importable" requirement from the getting-started
docs.]

Note for the planner: run `lint-imports` via `uv run lint-imports`
inside `make lint`, consistent with every other tool in the Makefile.

**e. Copy-pastable Dojo configuration.** Add to `pyproject.toml`:

```toml
# ABOUTME note: append this block to pyproject.toml; do not replace
# existing [tool.*] sections. Order within pyproject.toml is free.

[tool.importlinter]
root_package = "app"

[[tool.importlinter.contracts]]
name = "Domain must not depend on infrastructure or web"
type = "forbidden"
source_modules = ["app.domain"]
forbidden_modules = ["app.infrastructure", "app.web"]

[[tool.importlinter.contracts]]
name = "Application must not depend on infrastructure or web"
type = "forbidden"
source_modules = ["app.application"]
forbidden_modules = ["app.infrastructure", "app.web"]
```

Add to dev dependencies (`[dependency-groups] dev = [...]`):

```toml
"import-linter>=2.0",
```

Wire into `Makefile` — replace the current single-line `lint` target:

```makefile
lint:
	uv run ruff check --fix .
	uv run lint-imports
```

Rationale for ordering: ruff first (fast, fixes autofixable style);
lint-imports second (slower, builds the full import graph). If ruff
reordered/removed imports under autofix, lint-imports sees the post-fix
state. Exit-code short-circuit is the standard `make` behavior — if
ruff fails, `lint-imports` never runs, and the overall target fails.

One subtlety: `make lint` is invoked by `make check` (per Phase 1
Makefile), which runs `format → lint → typecheck → docstrings → test`.
That chain is the CI gate and the pre-commit hook backbone. Adding
`lint-imports` to `lint` means it now runs on every pre-commit, CI,
and local `make check` — exactly the enforcement scope SC #6
requires.

### 1.2 Section 1 checklist

- [x] Forbidden TOML syntax verified (Context7 snippet matched exactly
      against official docs URL).
- [x] Sub-package default behavior verified (`as_packages=true` means
      descendants included; explicit docs quote above).
- [x] CLI discovery behavior verified (looks for `pyproject.toml`
      automatically; no `--config` flag needed).
- [x] uv package-mode compat verified (Phase 1 D-20 already meets the
      "target must be importable" precondition).
- [x] Exit-code semantics verified (non-zero on broken contract ⇒
      `make check` fails ⇒ CI fails ⇒ pre-commit fails).
- [x] Copy-pastable `pyproject.toml` block + Makefile diff provided.

No `[ASSUMED]` items in Section 1 — every claim is sourced.

---

## 2. Package Layout — Files Created / Modified

Grouped by directory. LOC estimates assume the Phase 1 conventions
(≤100 lines per file, two-line ABOUTME header, one module docstring,
one-line docstrings on public symbols). "Analogous to" maps each new
file to the closest Phase 1 file, so the planner can point implementers
at a proven pattern without re-reading the CONTEXT.md each time.

### 2.1 `app/domain/` — pure stdlib, no I/O

| File | Job (one line) | Analogous to | Est. LOC |
|------|----------------|--------------|----------|
| `__init__.py` | Package marker (ABOUTME + one-line docstring, no re-exports — D-11 rule). | `app/infrastructure/db/__init__.py` | 5 |
| `value_objects.py` | `SourceKind` enum, `Rating` enum, `SourceId`/`NoteId`/`CardId`/`ReviewId` `NewType` aliases over `uuid.UUID`. | `app/settings.py` (structure) | 40–55 |
| `entities.py` | `Source`, `Note`, `Card`, `CardReview` frozen dataclasses with `default_factory=uuid.uuid4` IDs and `__post_init__` invariants. | no Phase 1 analog; follows dataclass-for-containers wiki rule | 70–95 |
| `exceptions.py` | `DojoError` base class; `InvalidEntity` if a real case surfaces, otherwise just the base + module docstring. | no Phase 1 analog (first layer exceptions file) | 15–25 |

Total: **4 files created.** Domain layer imports only `dataclasses`,
`enum`, `typing`, `uuid` — zero third-party imports. This is exactly
what SC #1 wants and what the import-linter contract will prove.

### 2.2 `app/application/` — ports + DTOs + use case

| File | Job (one line) | Analogous to | Est. LOC |
|------|----------------|--------------|----------|
| `__init__.py` | Package marker. | `app/infrastructure/__init__.py` | 5 |
| `ports.py` | `LLMProvider`, `SourceRepository`, `NoteRepository`, `CardRepository`, `CardReviewRepository`, `DraftStore` as `typing.Protocol`s (no `@runtime_checkable`); `UrlFetcher`, `SourceReader` as `Callable` aliases; `DraftToken` `NewType`. | `app/logging_config.py` (single-file central spine) | 80–100 (may split) |
| `dtos.py` | Pydantic `NoteDTO`, `CardDTO` (LLM I/O boundary per spec §3); stdlib dataclasses `GenerateRequest`, `GenerateResponse`, `DraftBundle` (per D-07/D-08). | `app/settings.py` (Pydantic usage pattern) | 60–80 |
| `exceptions.py` | `UnsupportedSourceKind`, `DraftExpired`, `LLMOutputMalformed` — all inherit from `DojoError`. | no Phase 1 analog | 20–30 |
| `use_cases/__init__.py` | Package marker. | `app/web/routes/__init__.py` | 5 |
| `use_cases/generate_from_source.py` | `GenerateFromSource` class with `execute(request) -> GenerateResponse`; TOPIC branch calls `LLMProvider.generate_note_and_cards(source_text=None, user_prompt=...)`, stores bundle via `DraftStore.put`, returns `(token, bundle)`. FILE/URL raise `UnsupportedSourceKind`. | `app/web/routes/home.py` (small orchestrator shape) | 45–75 |

**Note on `ports.py` sizing:** six Protocols × ~6–8 lines each + two
Callable aliases + `DraftToken` NewType + ABOUTME + module docstring ≈
80–100 lines. If interrogate-compliant one-line method docstrings push
it past 100, the planner should split into
`ports/repositories.py` + `ports/llm.py` + `ports/draft_store.py` +
`ports/aliases.py` at plan time. Flagged for the planner — not
pre-decided here.

Total: **6 files created** (7 if `ports.py` splits).

### 2.3 `tests/fakes/` — hand-written, no `Mock()`

Per CONTEXT.md discretion item "Fakes file layout": one fake per port,
re-exported from `__init__.py`.

| File | Job (one line) | Analogous to | Est. LOC |
|------|----------------|--------------|----------|
| `__init__.py` | Re-exports: `FakeLLMProvider`, `FakeSourceRepository`, `FakeNoteRepository`, `FakeCardRepository`, `FakeCardReviewRepository`, `FakeDraftStore`. | `tests/` root `__init__.py` (if any) | 10–15 |
| `fake_llm_provider.py` | Structural subtype of `LLMProvider`; returns a canned `(NoteDTO, list[CardDTO])` deterministically; exposes `fake.calls_with: list[tuple[str | None, str]]` + `fake.next_response` override hook. | no Phase 1 analog | 40–55 |
| `fake_source_repository.py` | Dict-backed in-memory impl of `SourceRepository`; exposes `fake.saved: dict[SourceId, Source]`. | no Phase 1 analog | 35–50 |
| `fake_note_repository.py` | Dict-backed `NoteRepository`; `fake.saved: dict[NoteId, Note]`; supports the regenerate-overwrite semantic (spec §3). | no Phase 1 analog | 35–50 |
| `fake_card_repository.py` | Dict-backed `CardRepository`; `fake.saved: dict[CardId, Card]`; supports append-only regeneration. | no Phase 1 analog | 35–50 |
| `fake_card_review_repository.py` | Dict-backed `CardReviewRepository`; `fake.saved: list[CardReview]`. | no Phase 1 analog | 30–45 |
| `fake_draft_store.py` | Dict-backed impl of `DraftStore.put` + atomic `pop`; exposes `fake.puts: list[tuple[DraftToken, DraftBundle]]` + `force_expire(token)` test hook (per D-06). | no Phase 1 analog | 35–55 |

Total: **7 files created.**

**One design rule the planner should carry into every fake:** expose
assertable state as public collections (per CONTEXT.md Claude's
discretion bullet "Fake assertion style"). No `.calls` or
`assert_called_with` — tests assert against `.puts`, `.saved`, etc.
This is the PITFALL M7 firewall: fakes are cheap, so tests assert on
the fake's post-state the same way they would assert on a real
repository's rows.

### 2.4 `tests/unit/domain/` — TDD entity tests

| File | Job (one line) | Analogous to | Est. LOC |
|------|----------------|--------------|----------|
| `__init__.py` | Package marker. | `tests/` init | 5 |
| `test_source.py` | `Source` construction + invariants (`user_prompt` non-empty `ValueError`); ID is a `SourceId` and unique across instances. | `tests/integration/test_db_smoke.py` (Phase 1 template) | 35–55 |
| `test_note.py` | `Note` construction + content non-empty invariant; association with `SourceId`. | same | 30–45 |
| `test_card.py` | `Card` construction + question/answer non-empty invariants; tags default; association with `SourceId`. | same | 35–55 |
| `test_card_review.py` | `CardReview` construction; `Rating` enum accepted; `is_correct` derived or stored (per spec §3). | same | 25–40 |
| `test_value_objects.py` | `SourceKind` enum has {FILE, URL, TOPIC}; `Rating` enum has {CORRECT, INCORRECT}; NewType IDs distinguishable at type-check time (smoke assert — ty handles the hard case). | same | 25–35 |
| `test_exceptions.py` | `DojoError` hierarchy smoke test; `InvalidEntity` (if declared) carries a message. | same | 15–25 |

Total: **7 files created.**

### 2.5 `tests/unit/application/` — TDD use case + DTO tests

| File | Job (one line) | Analogous to | Est. LOC |
|------|----------------|--------------|----------|
| `__init__.py` | Package marker. | Phase 1 test init | 5 |
| `test_dtos.py` | `NoteDTO`/`CardDTO` Pydantic validation (extra=ignore, required fields, `min_length=1` on cards list); `GenerateRequest`/`GenerateResponse` dataclass construction + frozenness. | no direct Phase 1 analog | 45–70 |
| `test_exceptions.py` | Application exceptions inherit `DojoError`; human-readable messages. | `tests/unit/domain/test_exceptions.py` | 15–25 |
| `test_generate_from_source.py` | `GenerateFromSource.execute(topic_request)` returns `(token, bundle)`; bundle round-trips through `FakeDraftStore.pop(token)`; `FakeLLMProvider.calls_with` shows `source_text=None`; FILE/URL requests raise `UnsupportedSourceKind`. | `tests/integration/test_db_smoke.py` (fixture-driven pattern) | 70–100 (may split) |

**Note on `test_generate_from_source.py` sizing:** this is the
end-to-end use-case test and covers the TOPIC success path +
unsupported-kind paths + draft-token round-trip. If it exceeds 100
lines, split into `test_generate_topic.py` + `test_generate_unsupported.py`.
Flagged for the planner.

Total: **4 files created.**

### 2.6 `tests/contract/` — TEST-03 harness per D-11

| File | Job (one line) | Analogous to | Est. LOC |
|------|----------------|--------------|----------|
| `__init__.py` | Package marker. | Phase 1 test init | 5 |
| `test_llm_provider_contract.py` | `pytest.fixture(params=["fake", "anthropic"])` pattern per D-11; "fake" branch yields `FakeLLMProvider`; "anthropic" branch skips via `pytest.importorskip` + `RUN_LLM_TESTS=1` double-gate; contract: `generate_note_and_cards` returns a tuple shaped `(NoteDTO, list[CardDTO])` with `len(cards) >= 1` and non-empty fields. | no Phase 1 analog | 55–85 |

Total: **2 files created.**

### 2.7 Files modified (not created)

| File | What changes |
|------|--------------|
| `pyproject.toml` | Add `"import-linter>=2.0"` to `[dependency-groups] dev`; append the full `[tool.importlinter]` + two `[[tool.importlinter.contracts]]` blocks from §1.1e. |
| `Makefile` | Replace the single-line `lint` target with the two-line version in §1.1e (ruff then lint-imports). |
| `uv.lock` | Regenerated automatically by `uv sync` after the dep addition. |

No edits to `app/main.py` this phase — Phase 2 adds no adapters to the
composition root. Phase 4 is where `deps.py` + real wiring land.

### 2.8 Summary

- Files created: **4 + 7 + 7 + 7 + 4 + 2 = 31 files** (or 32 if
  `ports.py` or `test_generate_from_source.py` splits).
- Files modified: **2** (`pyproject.toml`, `Makefile`).
- Total estimated LOC: roughly 1,000–1,400, spread across 31–33 files
  — well inside the ≤100/file rule with room to absorb the two
  flagged potential splits.

---

## 3. TDD Shape per Entity / Port / Use Case

Eight items total — 4 entities + DraftStore + 2 representative
repositories + GenerateFromSource use case. Each gets three bullets
(red → green → refactor), matching the planner's consumption format.
These are **shape hints**, not the plan: the planner chooses which
items go together in which plan and what the actual test names are.

### 3.1 `Source` entity

- **Red:** `test_source_construction_rejects_empty_user_prompt` —
  `Source(kind=SourceKind.TOPIC, user_prompt="")` raises `ValueError`.
  `test_source_id_is_unique_per_instance` — two `Source()` calls have
  distinct `SourceId`s.
- **Green:** Add frozen dataclass with `id: SourceId =
  field(default_factory=lambda: SourceId(uuid.uuid4()))`, `kind:
  SourceKind`, `user_prompt: str`, `input: str | None = None`,
  `created_at: datetime = field(default_factory=datetime.now)`;
  `__post_init__` checks `user_prompt.strip()`.
- **Refactor:** Extract `_require_nonempty(value, field_name)` helper
  in `entities.py` (shared with `Note`/`Card`) if duplication shows up
  in round 2.

### 3.2 `Note` entity

- **Red:** `test_note_construction_rejects_empty_content`;
  `test_note_carries_source_id_association`.
- **Green:** Frozen dataclass: `id: NoteId`, `source_id: SourceId`,
  `content: str`, timestamps; `__post_init__` checks
  `content.strip()`.
- **Refactor:** Use `_require_nonempty` helper from 3.1 once it
  exists.

### 3.3 `Card` entity

- **Red:** `test_card_construction_rejects_empty_question`;
  `test_card_construction_rejects_empty_answer`;
  `test_card_default_tags_is_empty_tuple` (not `[]` — tuples are
  hashable and frozen-dataclass-safe).
- **Green:** Frozen dataclass: `id: CardId`, `source_id: SourceId`,
  `question: str`, `answer: str`, `tags: tuple[str, ...] = ()`,
  timestamps.
- **Refactor:** Share the `_require_nonempty` helper; keep `tags`
  normalisation (strip whitespace, dedupe) in `__post_init__` if
  Phase 4 needs it (YAGNI otherwise — don't pre-build).

### 3.4 `CardReview` entity

- **Red:** `test_card_review_records_rating_and_time`;
  `test_card_review_is_correct_matches_rating` (if the field is
  derived from `Rating`).
- **Green:** Frozen dataclass: `id: ReviewId`, `card_id: CardId`,
  `rating: Rating`, `reviewed_at: datetime = field(default_factory=...)`,
  plus `is_correct: bool` as a `@property` returning
  `self.rating == Rating.CORRECT` (keeps the derivation pure — no
  stored-vs-computed drift risk).
- **Refactor:** If the spec later distinguishes correct/incorrect/skip,
  `is_correct` becomes less useful — revisit.

### 3.5 `DraftStore` port (representative Protocol)

- **Red:** `test_draft_store_put_then_pop_returns_bundle`;
  `test_draft_store_pop_is_atomic_read_and_delete` (second `pop`
  returns `None`); `test_draft_store_pop_missing_returns_none`. All
  driven through `FakeDraftStore`.
- **Green:** `FakeDraftStore` is a dict wrapper; `put` writes, `pop`
  calls `dict.pop(token, None)`. `DraftStore` Protocol has exactly
  the two methods per D-04, plus a docstring-level note on TTL /
  concurrency semantics per D-05.
- **Refactor:** Move the `force_expire(token)` test hook onto the
  fake (not the Protocol — per D-05 the port exposes no TTL API).
  Real `InMemoryDraftStore` implementation is Phase 3.

### 3.6 `SourceRepository` port (representative repository)

- **Red:** `test_source_repository_save_then_get_by_id_round_trips`;
  `test_source_repository_get_missing_returns_none`. Both driven
  through `FakeSourceRepository`.
- **Green:** `FakeSourceRepository` is a dict wrapper on `SourceId`;
  `SourceRepository` Protocol declares `save(source) -> None` and
  `get(source_id) -> Source | None` (and whatever the use case
  needs — nothing speculative).
- **Refactor:** Resist the urge to pre-declare `list()`, `delete()`,
  `filter_by_tag()` until Phases 5/6 need them. YAGNI — the port is
  the Phase 2 contract, and hardening later is cheap only if we
  didn't over-promise.

### 3.7 `LLMProvider` port (representative I/O boundary)

- **Red:** `test_llm_provider_generate_returns_note_and_cards` (via
  `FakeLLMProvider`, asserting the return type is
  `tuple[NoteDTO, list[CardDTO]]`);
  `test_llm_provider_called_with_none_source_text_for_topic` (asserts
  `fake.calls_with[-1] == (None, "prompt text")`).
- **Green:** Protocol declares
  `generate_note_and_cards(source_text: str | None, user_prompt: str)
  -> tuple[NoteDTO, list[CardDTO]]`. `FakeLLMProvider` records calls
  on `self.calls_with` and returns a deterministic canned DTO pair.
- **Refactor:** If multiple tests need distinct canned responses,
  upgrade `FakeLLMProvider` to accept a `responses: Iterator[...]`
  constructor arg rather than per-test monkey-patching.

### 3.8 `GenerateFromSource` use case

- **Red:** `test_generate_from_topic_puts_bundle_in_draft_store` —
  wires `FakeLLMProvider` + `FakeDraftStore` + fake repos, calls
  `execute(GenerateRequest(kind=TOPIC, input=None, user_prompt=...))`,
  asserts response has a `DraftToken` and a `DraftBundle` whose
  `note` + `cards` match the fake's canned response.
  `test_generate_bundle_round_trips_through_draft_store_pop` —
  `FakeDraftStore.pop(response.token) == response.bundle`.
  `test_generate_file_kind_raises_unsupported_source_kind`;
  `test_generate_url_kind_raises_unsupported_source_kind`.
- **Green:** `GenerateFromSource.__init__` takes the five
  dependencies (provider, draft store, three repos — though in Phase
  2 the repos may only be held for parity with Phase 4's constructor
  shape; if not used by `execute()` they're omitted until needed).
  `execute()` dispatches on `request.kind`: TOPIC calls the provider
  with `source_text=None`, wraps into `DraftBundle`, mints a fresh
  `DraftToken`, calls `draft_store.put(token, bundle)`, returns
  `GenerateResponse(token, bundle)`. FILE/URL raise
  `UnsupportedSourceKind`.
- **Refactor:** The per-kind dispatch is a two-branch `match` for now;
  Phase 4 adds the FILE branch (calls `SourceReader`) and the URL
  branch (calls `UrlFetcher`). Pre-designing the dispatch as a
  strategy table is YAGNI — the current shape extends cleanly.

### 3.9 Cross-cutting TDD notes for the planner

- Every fake in §2.3 lands **with** its consumer test in §2.4 / §2.5
  / §2.6. No "orphan fake" commits — if a fake doesn't have a test
  asserting on its state, the contract is not yet exercised.
- The TEST-03 contract harness (§2.6) is the backstop that catches
  fake-drift once Phase 3 adds `AnthropicLLMProvider`. In Phase 2 it
  exercises only the "fake" leg; the "anthropic" leg skips cleanly via
  the double-gate (`importorskip` + `RUN_LLM_TESTS=1`).
- Interrogate 100% is preserved by one-line docstrings on every
  Protocol method, per PITFALL M11 / CONTEXT.md discretion. Don't add
  ports.py to the interrogate exclude list.
- Domain tests never touch I/O. If a test needs a clock or a filesystem
  read, it belongs in application or infrastructure, not domain.

---

## 4. Plan Decomposition Hint

Phase 2 naturally breaks into five plans along responsibility lines
that minimise cross-plan fixture reuse and keep each PR under the
200–400-LOC review sweet spot from CLAUDE.md's PR Shape section.
Plan 01 (domain) is pure stdlib and has no application-layer
dependencies, so it ships first. Plans 02 and 03 (application ports +
DTOs, and fakes) depend on Plan 01 but are independent of each
other — they can ship in parallel in Wave 2 if capacity allows, since
ports.py is definitions-only and fakes can reference the Protocols by
structural subtyping without forcing a sequencing coupling. Plan 04
(GenerateFromSource use case + its unit tests) needs Plans 01–03 and
is the "close the loop" plan. Plan 05 (TEST-03 contract harness +
import-linter wiring + Makefile + `pyproject.toml` edits) is
infrastructure-for-tests and ships last so it can reference the real
port signatures without churn.

- **Plan 01 — Domain entities & value objects**
  - Scope: `app/domain/value_objects.py`, `entities.py`,
    `exceptions.py`, `__init__.py`; `tests/unit/domain/*` (all
    seven test files).
  - Deps: none (builds on Phase 1 scaffold only).
  - Size: ~200–350 LOC (7 test files + 4 source files, each small).
  - Landmark commit: SC #1 is satisfied and testable in isolation.

- **Plan 02 — Application ports & DTOs**
  - Scope: `app/application/__init__.py`, `ports.py`, `dtos.py`,
    `exceptions.py`; `tests/unit/application/test_dtos.py`,
    `test_exceptions.py`.
  - Deps: Plan 01 (ports reference `SourceId`, `Note`, etc.).
  - Size: ~150–250 LOC.
  - Landmark commit: SC #2 is satisfied; the Protocol shapes are
    frozen.

- **Plan 03 — Hand-written fakes + their unit tests**
  - Scope: `tests/fakes/*` (all seven files).
  - Deps: Plan 02 (fakes implement the Protocols). Independent of
    Plan 04 — the fakes don't know about the use case.
  - Size: ~300–400 LOC (heavier because it's seven files).
  - Landmark commit: SC #4 is satisfied; every port has a fake that
    exposes assertable state.

- **Plan 04 — GenerateFromSource use case + end-to-end unit test**
  - Scope: `app/application/use_cases/__init__.py`,
    `generate_from_source.py`;
    `tests/unit/application/test_generate_from_source.py`.
  - Deps: Plans 01, 02, 03.
  - Size: ~150–250 LOC.
  - Landmark commit: SC #3 is satisfied — the use case runs
    end-to-end against fakes with a draft-store round-trip.

- **Plan 05 — TEST-03 contract harness + import-linter boundary
  enforcement**
  - Scope: `tests/contract/__init__.py`,
    `test_llm_provider_contract.py`; `pyproject.toml`
    (`import-linter` dep + `[tool.importlinter]` block); `Makefile`
    (`lint` target split into `ruff + lint-imports`);
    `tests/unit/domain/test_layering.py` — optional Pythonic belt-and-
    braces that asserts `lint-imports` is runnable in-process (may be
    dropped if the Makefile gate is enough).
  - Deps: Plans 01–04 (contract test references real DTOs and
    Protocol shapes; boundary test runs against the real `app/`
    tree).
  - Size: ~150–250 LOC.
  - Landmark commit: SC #5 and SC #6 are satisfied; Phase 2 closes.

**Wave structure (for the executor):**

- **Wave 1:** Plan 01 (domain) — solo. Everything downstream waits
  on these types existing.
- **Wave 2:** Plan 02 (ports+DTOs) and Plan 03 (fakes) — optional
  parallel. If a single agent is running it, sequential 02 → 03 is
  fine; the coupling is one-directional. If two agents are running,
  02 must land slightly ahead to give 03 a Protocol to subtype
  against — treat 03 as "starts when 02's ports.py lands" not "starts
  when 02's PR merges."
- **Wave 3:** Plan 04 (use case) — solo, ties ports + fakes together.
- **Wave 4:** Plan 05 (contract harness + import-linter) — solo,
  closes the phase.

That's five plans, four waves, and every plan maps cleanly to one
user-memory PR per CLAUDE.md PR Shape. Total phase LOC lands around
1,000–1,500, consistent with the §2 estimate.

---

## Validation Architecture

Skipped. Phase 2 is a port-declaration + pure-logic phase; every
success criterion (SC #1–#6) is validated by existing `pytest`
infrastructure from Phase 1 (`make test`, `make check`) plus the new
`lint-imports` step added in Plan 05. No Nyquist-style sampling
analysis adds signal here — the framework is already configured, the
commands (`make check`, `uv run pytest tests/unit/...`,
`RUN_LLM_TESTS=1 uv run pytest tests/contract/...`) are
unambiguous, and SC → test mapping is already implicit in §2's file
list (each SC is satisfied by the corresponding test file landing
green).

If the planner wants explicit SC-to-test mapping in PLAN documents,
here's the cheat sheet:

| SC | Validated by |
|----|--------------|
| #1 | `tests/unit/domain/test_*.py` green + stdlib-only imports asserted by import-linter (Plan 05) |
| #2 | `tests/unit/application/test_*.py` green + `lint-imports` green |
| #3 | `tests/unit/application/test_generate_from_source.py` green |
| #4 | `tests/unit/**` green with zero `Mock()` usage (grepped in CI or reviewer-enforced) |
| #5 | `tests/contract/test_llm_provider_contract.py` — fake leg runs in `make check`, anthropic leg skips cleanly when `RUN_LLM_TESTS` is unset |
| #6 | `uv run lint-imports` exits zero against the current tree; a deliberate bad import (in a throwaway branch) exits non-zero |

---

## Sources

### Primary (HIGH confidence)

- **Context7 `/websites/import-linter_readthedocs_io_en_stable`** —
  fetched 2026-04-22. Sections consulted: "Configure Forbidden
  Contracts (TOML)", "Configure Forbidden Contracts (Python)",
  "Forbidden" (definition + `as_packages` default),
  "Import Linter TOML Configuration" (top-level shape,
  `root_package`/`root_packages`), "Run the linter" (CLI flags and
  discovery).
- **`.planning/phases/02-domain-application-spine/02-CONTEXT.md`** —
  locked decisions D-01 through D-12 and Claude's discretion
  clarifications.
- **`.planning/ROADMAP.md` §"Phase 2"** — the six success criteria
  referenced throughout.
- **`.planning/phases/01-project-scaffold-tooling/01-CONTEXT.md`
  §D-11, §D-20** — Phase 1 scaffold file list and package-mode uv
  declaration.
- **`/Users/pvardanis/Documents/projects/dojo/pyproject.toml`** —
  current dev deps and tool sections (verified no `import-linter`
  yet, verified `[tool.uv] package = true`).
- **`/Users/pvardanis/Documents/projects/dojo/Makefile`** — current
  `lint` target shape (single-line ruff invocation).
- **`ls -R app/`** — verified Phase 1 tree: `app/__init__.py`,
  `app/settings.py`, `app/logging_config.py`, `app/main.py`,
  `app/infrastructure/__init__.py`, `app/infrastructure/db/__init__.py`,
  `app/infrastructure/db/session.py`, `app/web/__init__.py`,
  `app/web/routes/__init__.py`, `app/web/routes/home.py`,
  `app/web/templates/{base,home}.html`, `app/web/static/` (empty).

### Secondary (none needed)

Budget preserved. No WebSearch or WebFetch invoked.

### Tertiary (none)

---

## Assumptions Log

Intentionally empty. Every factual claim in Section 1 is `[CITED]`
against the current import-linter stable docs. Sections 2–4 are
derived entirely from CONTEXT.md + the verified Phase 1 tree — no
assumptions about the code or tooling were introduced.

---

## RESEARCH COMPLETE
