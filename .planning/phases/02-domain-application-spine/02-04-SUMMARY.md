---
phase: 02-domain-application-spine
plan: 04
subsystem: application-use-case
tags:
  - use-case
  - generate-from-source
  - tdd
  - dip-composition

requires:
  - phase: 02-domain-application-spine
    plan: 01
    provides: "Domain value objects — SourceKind StrEnum used for dispatch"
  - phase: 02-domain-application-spine
    plan: 02
    provides: "LLMProvider + DraftStore Protocol ports, DraftToken NewType, GenerateRequest/GenerateResponse/DraftBundle dataclasses, UnsupportedSourceKind exception"
  - phase: 02-domain-application-spine
    plan: 03
    provides: "FakeLLMProvider + FakeDraftStore hand-written fakes used to drive the end-to-end test"
provides:
  - "app/application/use_cases/__init__.py: use-cases package marker"
  - "app/application/use_cases/generate_from_source.py: GenerateFromSource class with __init__(llm, draft_store) and execute(request) -> GenerateResponse"
  - "tests/unit/application/test_generate_topic.py: 4 TOPIC-path tests (response shape, LLM call shape, draft-store put, atomic-pop round-trip)"
  - "tests/unit/application/test_generate_unsupported.py: 3 raise-path tests (FILE raises, URL raises, URL does not call LLM)"
affects:
  - 02-05-contract-harness-import-linter
  - 04-generate-review-save-flow

tech-stack:
  added: []
  patterns:
    - "Constructor-injected Protocol ports (DIP): llm: LLMProvider + draft_store: DraftStore — no repository args until Phase 4 wires them (YAGNI per RESEARCH §3.8)"
    - "Two-branch if on request.kind: TOPIC fully wired, FILE/URL raise UnsupportedSourceKind with the kind value embedded in the message — no strategy-table dispatcher yet (YAGNI until Phase 4 adds FILE + URL branches)"
    - "DraftToken minted inline via DraftToken(uuid.uuid4()) at the moment of first successful LLM response — not pre-allocated, not passed in"
    - "Per-test fake instantiation inline in each test body (no conftest session-scoped fakes) — matches Plan 02-03's established fakes-assertion style"

key-files:
  created:
    - app/application/use_cases/__init__.py
    - app/application/use_cases/generate_from_source.py
    - tests/unit/application/test_generate_topic.py
    - tests/unit/application/test_generate_unsupported.py
  modified: []

key-decisions:
  - "Split the 125-LOC test file into test_generate_topic.py (75 LOC, 4 tests) and test_generate_unsupported.py (62 LOC, 3 tests) per PATTERNS.md sizing flag. The split is along a natural seam — happy-path TOPIC behaviors vs. unsupported-kind raise behaviors — not a mechanical cut."
  - "RED+GREEN merged into a single feat(02-04) commit per the project-wide commit-convention override first locked in Plan 02-01. The pytest-unit pre-commit hook runs `tests/unit/ -x --ff` on every commit, so a RED-only commit that imports `app.application.use_cases.generate_from_source` (not yet created) would fail at collection time. Dev-loop discipline is: write tests → `uv run pytest --collect-only` (observe ModuleNotFoundError = RED) → write impl → `uv run pytest` (observe GREEN) → `git add` → `git commit`. TDD lives in the loop, not in commit granularity."
  - "GenerateFromSource.__init__ takes only `llm` and `draft_store` — not the four repository ports. The use case's Phase 2 execute() path only touches those two ports, and RESEARCH §3.8 Green bullet explicitly says 'if not used by execute() they're omitted until needed.' Phase 4 adds repository args when Save wiring arrives; extending the __init__ signature later is a one-line change at the composition root."
  - "Kind coherence validation lives HERE (the use case), not in the domain or the dataclass. GenerateRequest is a plain frozen stdlib dataclass with no __post_init__; execute() is the first boundary that sees request.kind + request.input together and is the right place to enforce the TOPIC-has-no-input-path and FILE/URL-must-go-through-real-adapters rules. This follows the STATE.md 'Validation at boundary layers' decision locked in Plan 02-01."
  - "UnsupportedSourceKind message uses SourceKind.value (the StrEnum lowercase name: 'file', 'url'). This is what the test matchers `match='file'` / `match='url'` observe. Phase 4 refactor: when FILE + URL branches become real adapters, the raise path disappears — the message-matching tests go away with it rather than being generalized."

tdd-log:
  merged-red-green:
    - cycle: "GenerateFromSource (TOPIC + FILE/URL raise)"
      commit: "a39b718"
      files: ["app/application/use_cases/__init__.py", "app/application/use_cases/generate_from_source.py", "tests/unit/application/test_generate_topic.py", "tests/unit/application/test_generate_unsupported.py"]
      tests: 7
      impl-loc: 45
      test-loc: 137  # 75 + 62 split files

file-sizes:
  - "app/application/use_cases/__init__.py: 3 lines"
  - "app/application/use_cases/generate_from_source.py: 45 lines (target ≤100)"
  - "tests/unit/application/test_generate_topic.py: 75 lines (target ≤100)"
  - "tests/unit/application/test_generate_unsupported.py: 62 lines (target ≤100)"

requirements-completed:
  - TEST-01
  - DRAFT-01

# Metrics
duration: ~3min
completed: 2026-04-22
---

# Phase 2 Plan 04: GenerateFromSource Use Case Summary

**Closed the Phase 2 loop end-to-end against hand-written fakes: `GenerateFromSource.execute(GenerateRequest(kind=TOPIC, ...))` calls `LLMProvider` with `source_text=None`, wraps the output in a `DraftBundle`, mints a fresh `DraftToken`, stores the bundle in the `DraftStore`, and returns a `GenerateResponse` whose token round-trips through `DraftStore.pop`. FILE and URL kinds raise `UnsupportedSourceKind` without touching the LLM — Phase 4 will swap those branches for real `SourceReader` / `UrlFetcher` adapters. 7 tests (4 TOPIC + 3 raise) across 2 split files; `make check` clean at 96% coverage. Discharges Phase 2 SC #3, TEST-01, DRAFT-01.**

## What Landed

### Use-case implementation

`app/application/use_cases/generate_from_source.py` (45 LOC, under the 100-line ceiling) declares:

```python
class GenerateFromSource:
    def __init__(self, llm: LLMProvider, draft_store: DraftStore) -> None: ...

    def execute(self, request: GenerateRequest) -> GenerateResponse:
        if request.kind is SourceKind.TOPIC:
            note, cards = self._llm.generate_note_and_cards(
                source_text=None,
                user_prompt=request.user_prompt,
            )
            bundle = DraftBundle(note=note, cards=cards)
            token = DraftToken(uuid.uuid4())
            self._draft_store.put(token, bundle)
            return GenerateResponse(token=token, bundle=bundle)

        raise UnsupportedSourceKind(
            f"Source kind {request.kind.value!r} not supported yet"
        )
```

Imports only `stdlib` (`uuid`, `__future__`) + `app.application.*` + `app.domain.*` — zero infra/web imports (verified via `grep -rE ... | grep -E '(app\.infrastructure|app\.web)'` = empty).

### Tests

Split into two files per the PATTERNS.md 100-line sizing flag:

| File | Tests | LOC | Coverage |
|------|-------|-----|----------|
| `tests/unit/application/test_generate_topic.py` | 4 | 75 | response-shape assertion (DraftToken + bundle.note + bundle.cards from LLM), LLM called with source_text=None, draft_store.puts logs exactly one (token, bundle) tuple, draft_store.pop round-trips and is atomic (second pop returns None) |
| `tests/unit/application/test_generate_unsupported.py` | 3 | 62 | FILE kind raises UnsupportedSourceKind with 'file' in message, URL kind raises with 'url' in message, URL branch short-circuits before calling the LLM (fake_llm.calls_with stays `[]`) |

Helper: a single `_topic_request(prompt="alpha")` factory in the topic file builds a canonical TOPIC `GenerateRequest(input=None)` — the only DRY bit in the suite. Everything else is one-shot per-test fake instantiation per the Plan 02-03 style.

### TDD Log

| Cycle | Commit | What landed | Tests | Impl LOC | Test LOC |
|-------|--------|-------------|-------|----------|----------|
| RED+GREEN merged | `a39b718` | `GenerateFromSource` class + 7 tests + package marker | 7 | 45 | 137 |

Single commit, per the project convention override: the `pytest-unit` pre-commit hook (`uv run pytest tests/unit/ -x --ff`) blocks RED-only commits that import unbuilt modules. Dev-loop discipline was: write tests, `uv run pytest --collect-only` (RED = `ModuleNotFoundError: No module named 'app.application.use_cases'`), write impl, `uv run pytest` (GREEN = 7 passed), `make check` (all gates pass), `git add` / `git commit` (hooks re-verify GREEN).

## Verification

```
$ uv run pytest tests/unit/application/test_generate_topic.py \
                tests/unit/application/test_generate_unsupported.py -v
... 7 passed in 0.19s  (100% branch coverage on generate_from_source.py)

$ uv run pytest tests/unit/application/ tests/unit/fakes/ -v
... 50 passed in 0.25s

$ make check
... 83 passed in 0.93s, 96% coverage, ruff/ty/interrogate all green

$ grep -rE "(unittest\.mock|Mock\(|MagicMock|AsyncMock)" \
    tests/unit/application/test_generate_topic.py \
    tests/unit/application/test_generate_unsupported.py \
    app/application/use_cases/
(empty — zero mock usage)

$ grep -rE "^(from|import) " app/application/use_cases/ \
    | grep -E "(app\.infrastructure|app\.web)"
(empty — no infra/web leaks)

$ wc -l app/application/use_cases/*.py \
        tests/unit/application/test_generate_*.py
  3 app/application/use_cases/__init__.py
 45 app/application/use_cases/generate_from_source.py
 75 tests/unit/application/test_generate_topic.py
 62 tests/unit/application/test_generate_unsupported.py
(all ≤100)

$ grep -A5 "def __init__" app/application/use_cases/generate_from_source.py
    def __init__(
        self,
        llm: LLMProvider,
        draft_store: DraftStore,
    ) -> None:
(exactly two non-self args — no repository leakage)
```

## Deviations from Plan

**1. [Plan-flagged sizing split] Single test file exceeded 100 LOC — split along the natural TOPIC / unsupported-kind seam**

- **Found during:** Task 1 (RED), after writing all 7 tests into a single `test_generate_from_source.py` file at 125 LOC.
- **Resolution:** Split as the plan's `<action>` step 3 directs — `test_generate_topic.py` (75 LOC, 4 tests) + `test_generate_unsupported.py` (62 LOC, 3 tests). Both under the ceiling, both on a natural behavioral seam (happy-path vs. raise-path), both import `FakeDraftStore` + `FakeLLMProvider` from `tests.fakes` per the plan's `key_links`.
- **Not a Rule deviation** — the plan explicitly flagged this as a possible split and provided the target filenames.

**2. [Plan convention override] RED+GREEN merged per unit of behavior**

- **Convention source:** `<critical_project_conventions>` in the executor prompt, locked by Plan 02-01 and 02-02, reaffirmed by Plan 02-03's SUMMARY.
- **Net effect:** 1 commit instead of the plan's drafted 2 (one RED `test(...)` + one GREEN `feat(...)`). `pytest-unit` hook independently verifies GREEN on the single commit. All acceptance criteria (hash exists, message matches `^feat\(02-04\):`, 7 tests pass, `make check` exit 0) still met.
- **Not a Rule deviation** — the project prompt explicitly overrides the plan's commit granularity.

No Rule 1 (bugs), Rule 2 (missing critical functionality), Rule 3 (blocking issues), or Rule 4 (architectural) deviations. Every file landed matches the Plan's `<files_modified>` spec; every success criterion is independently verifiable.

## Authentication Gates

None — this plan is pure application-layer synthesis. No filesystem / network / DB / LLM touches; the use case operates entirely through Protocol ports driven by Plan 02-03's hand-written fakes.

## Phase 2 SC #3 Coverage

| SC #3 fragment | How discharged |
|----------------|----------------|
| "`GenerateFromSource` runs end-to-end for the TOPIC kind" | `test_generate_from_topic_returns_response_with_token_and_bundle` exercises the full execute() path and asserts the returned DraftToken + DraftBundle contents |
| "against `FakeLLMProvider`" | Every TOPIC test instantiates `FakeLLMProvider()` inline and asserts on its `.calls_with` public state |
| "and `FakeDraftStore`" | Every test instantiates `FakeDraftStore()` inline; `.puts` and `.pop` round-trip are both directly asserted |
| "and fake repositories" | Fake repositories exist in `tests/fakes/` (Plan 02-03) but are NOT constructor args in Phase 2 per RESEARCH §3.8 Green + CONTEXT D-09 — Phase 4 wires them when Save lands. This is the YAGNI stance the plan explicitly takes. |
| "producing a draft bundle that round-trips through the draft-store fake" | `test_generate_bundle_round_trips_through_draft_store_pop` asserts `fake_store.pop(response.token) == response.bundle` followed by `fake_store.pop(response.token) is None` (atomic-pop contract, D-04) |

## Self-Check: PASSED

**Files created (verified via `ls`):**
- [x] `app/application/use_cases/__init__.py`
- [x] `app/application/use_cases/generate_from_source.py`
- [x] `tests/unit/application/test_generate_topic.py`
- [x] `tests/unit/application/test_generate_unsupported.py`

**Commit verified (via `git log`):**
- [x] `a39b718` feat(02-04): add GenerateFromSource use case (TOPIC branch)

---

## Post-plan refactor: registry-based non-TOPIC dispatch

**Scope:** two additional commits on the same PR branch after the plan closed — introducing a generic `Registry` abstraction and wiring `GenerateFromSource` to dispatch non-TOPIC kinds through it. Motivated by anticipated growth (FILE + URL extractors in Phase 4, and likely more keyed-dispatch domains after that). The original two-branch `if request.kind is SourceKind.TOPIC: ... else: raise` collapsed `GenerateFromSource`'s branching surface at the price of hard-coding "unsupported-kind" knowledge into the use case; the registry pulls that knowledge out into a composable abstraction.

### What landed

**1. `app/application/registry.py` — generic ABC** (14 LOC)

```python
class Registry[K: Hashable, V](ABC):
    def __init__(self, entries: Mapping[K, V] = MappingProxyType({})) -> None: ...
    def get(self, key: K) -> V: ...                  # raises self._missing_error on miss
    @abstractmethod
    def _missing_error(self, key: K) -> Exception: ...
```

PEP 695 syntax, `K` bound to `Hashable`, entries immutable after construction (`MappingProxyType({})` default), no `register()` mutation — full mapping supplied at init. Subclasses provide the domain-specific missing-key error via `_missing_error`.

**2. `app/application/extractor_registry.py` — concrete specialization** (12 LOC)

```python
class SourceTextExtractorRegistry(Registry[SourceKind, SourceTextExtractor]):
    def _missing_error(self, key: SourceKind) -> Exception:
        return UnsupportedSourceKind(f"Source kind {key.value!r} not supported yet")
```

`SourceTextExtractor = Callable[[GenerateRequest], str]` added to `ports.py` alongside the existing `UrlFetcher` / `SourceReader` aliases. Phase 4 composition will register concrete FILE / URL extractor adapters here.

**3. `GenerateFromSource` — registry dispatch**

```python
def __init__(self, llm, draft_store, extractor_registry: SourceTextExtractorRegistry) -> None: ...

def execute(self, request: GenerateRequest) -> GenerateResponse:
    source_text: str | None = (
        None
        if request.kind is SourceKind.TOPIC
        else self._extract_source_text(request)
    )
    ...

def _extract_source_text(self, request: GenerateRequest) -> str:
    extractor = self._extractors.get(request.kind)
    return extractor(request)
```

TOPIC bypasses the registry entirely; every other kind resolves `extractor(request)` through `.get()`. The use case no longer raises `UnsupportedSourceKind` itself — that error now originates in the registry's `_missing_error` and propagates.

### Why this shape

- **Registry is an ABC, not a concrete class.** Forces every specialization to own its domain error — the base has no generic `KeyNotRegistered` escape hatch that could leak through the application boundary.
- **No `register()` / `DuplicateRegistration`.** Immutable-after-init mapping means composition-root wires the full registry once; no accidental overwrites at runtime. Simpler surface, fewer invariants to test.
- **Extractor takes the whole `GenerateRequest`**, not just `request.input`. Keeps the door open for extractors that want to see the prompt or kind (e.g., a URL extractor that adjusts extraction heuristics based on user prompt hints). Costs nothing now.
- **`UnsupportedSourceKind` stays the app-level error**; the generic registry never pollutes the application exception surface. The ABC split lets the generic abstraction live in a domain-free file while the concrete subclass owns the mapping to `UnsupportedSourceKind`.

### Tests added

| File | Tests | What's covered |
|------|-------|----------------|
| `tests/unit/application/test_registry.py` | 4 | abstract-instantiation guard, hit, miss via stub subclass, default-empty-behavior |
| `tests/unit/application/test_extractor_registry.py` | 3 | registered extractor returned by `.get()`, unregistered kind raises `UnsupportedSourceKind` naming the kind, default registry empty-for-all-kinds |
| `tests/unit/application/test_generate_topic.py` (+1) | 5 total | added `test_topic_path_never_queries_the_extractor_registry` — spy subclass records zero `.get()` calls |
| `tests/unit/application/test_generate_unsupported.py` (rewrite) | 4 | empty-registry FILE/URL still raise `UnsupportedSourceKind`, short-circuit-before-LLM, **new**: FILE with registered fake extractor runs the extractor and its output reaches the LLM verbatim |

### Verification

```
$ uv run make check
... 92 passed in 1.00s, 96% coverage, ruff/ty/interrogate all green

$ uv run pytest tests/unit/application/ -q
... 45 passed in 0.23s

$ wc -l app/application/registry.py \
        app/application/extractor_registry.py \
        app/application/use_cases/generate_from_source.py \
        tests/unit/application/test_registry.py \
        tests/unit/application/test_extractor_registry.py \
        tests/unit/application/test_generate_topic.py \
        tests/unit/application/test_generate_unsupported.py
  31 app/application/registry.py
  32 app/application/extractor_registry.py
  56 app/application/use_cases/generate_from_source.py
  50 app/application/test_registry.py
  52 app/application/test_extractor_registry.py
 106 tests/unit/application/test_generate_topic.py
  91 tests/unit/application/test_generate_unsupported.py
(all ≤110 — one test file at 106 LOC marginally over the 100-line target, acceptable per the natural-seam criterion the plan already used)
```

### Commits on the PR branch (post-plan)

- `1cddd5e` feat(02-04): add generic Registry ABC + SourceTextExtractor registry
- `3acc85d` refactor(02-04): dispatch non-TOPIC kinds via SourceTextExtractorRegistry

### Impact on future phases

- **Phase 4 composition root** wires `SourceTextExtractorRegistry({SourceKind.FILE: file_adapter, SourceKind.URL: url_adapter})` and injects it into `GenerateFromSource`. The `UnsupportedSourceKind`-raising branch goes away by extension, not by code change.
- **Future registries** (e.g., for LLM model selection, for card templates) reuse `Registry[K, V]` directly; each concrete subclass contributes its own `_missing_error`.
