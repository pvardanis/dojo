---
phase: 02-domain-application-spine
plan: 04
type: tdd
wave: 4
depends_on:
  - "02-01"
  - "02-02"
  - "02-03"
files_modified:
  - app/application/use_cases/__init__.py
  - app/application/use_cases/generate_from_source.py
  - tests/unit/application/test_generate_from_source.py
autonomous: true
requirements:
  - TEST-01
  - DRAFT-01
tags:
  - use-case
  - generate-from-source
  - tdd
must_haves:
  truths:
    - "`GenerateFromSource.execute(GenerateRequest(kind=TOPIC, input=None, user_prompt=...))` returns a `GenerateResponse(token, bundle)` where `bundle` contains the LLM's note + cards."
    - "The use case calls `LLMProvider.generate_note_and_cards(source_text=None, user_prompt=...)` for TOPIC kind (source_text is `None` per CONTEXT D-10)."
    - "After successful TOPIC generation, the use case stores the bundle in `DraftStore.put(token, bundle)` and returns the same `(token, bundle)` in the response."
    - "`DraftStore.pop(response.token)` returns the bundle exactly once (round-trip semantic per CONTEXT D-04 atomic pop)."
    - "FILE and URL kinds raise `UnsupportedSourceKind` (app-layer exception) — Phase 4 replaces these branches with real adapters (CONTEXT D-09)."
    - "Use case's `__init__` takes `llm: LLMProvider` and `draft_store: DraftStore` only — the four repository ports are NOT constructor args in Phase 2 (YAGNI per RESEARCH §3.8; Phase 4 adds them)."
  artifacts:
    - path: "app/application/use_cases/__init__.py"
      provides: "Use-cases package marker (ABOUTME + module docstring)."
    - path: "app/application/use_cases/generate_from_source.py"
      provides: "`GenerateFromSource` class with `__init__(llm, draft_store)` and `execute(request) -> GenerateResponse`."
    - path: "tests/unit/application/test_generate_from_source.py"
      provides: "End-to-end unit test against `FakeLLMProvider` + `FakeDraftStore`."
  key_links:
    - from: "app/application/use_cases/generate_from_source.py"
      to: "app/application/ports.py + app/application/dtos.py + app/application/exceptions.py"
      via: "imports LLMProvider, DraftStore, DraftToken, DraftBundle, GenerateRequest, GenerateResponse, UnsupportedSourceKind, SourceKind"
      pattern: "from app\\.application\\."
    - from: "tests/unit/application/test_generate_from_source.py"
      to: "tests/fakes/__init__.py"
      via: "imports `FakeLLMProvider, FakeDraftStore`"
      pattern: "from tests\\.fakes import"
---

<objective>
Deliver the `GenerateFromSource` use case — the TOPIC branch wired
end-to-end against Plan 03's fakes. This is the "close the loop" plan
for Phase 2: after this plan lands, Dojo has a pure-logic generation
flow that produces a draft bundle from a `GenerateRequest`, stores it
under a `DraftToken`, and the bundle round-trips through `DraftStore.pop`.

FILE and URL kinds raise `UnsupportedSourceKind` per CONTEXT D-09 — Phase
4 will replace those branches with real `SourceReader` and `UrlFetcher`
calls. The per-kind dispatch is a two-branch `if` (YAGNI; pre-designing a
strategy table is forbidden per RESEARCH §3.8 refactor note).

Discharges ROADMAP Phase 2 SC #3 (`GenerateFromSource` runs end-to-end
for TOPIC against `FakeLLMProvider` + `FakeDraftStore` + fake repos,
producing a draft bundle that round-trips through the draft-store fake)
and the use-case end of TEST-01 (hand-written fakes drive the use-case
unit test — no `Mock()` in sight).

This plan is small (1 use-case file + 1 test file + 1 package marker;
RESEARCH estimates 150-250 LOC). TDD cycle is tight: one RED covering
three behaviors, one GREEN that implements them.
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
@.planning/phases/02-domain-application-spine/02-CONTEXT.md
@.planning/phases/02-domain-application-spine/02-RESEARCH.md
@.planning/phases/02-domain-application-spine/02-PATTERNS.md
@CLAUDE.md

# Plan 01-03 outputs (required)
@.planning/phases/02-domain-application-spine/02-01-SUMMARY.md
@.planning/phases/02-domain-application-spine/02-02-SUMMARY.md
@.planning/phases/02-domain-application-spine/02-03-SUMMARY.md
@app/application/ports.py
@app/application/dtos.py
@app/application/exceptions.py
@app/domain/value_objects.py
@tests/fakes/__init__.py
@tests/fakes/fake_llm_provider.py
@tests/fakes/fake_draft_store.py

# Phase 1 analog (orchestrator shape)
@app/web/routes/home.py

<interfaces>
<!-- Contracts the use case is built against — all from Plans 02 + 03. -->

From `app/application/ports.py`:
```python
class LLMProvider(Protocol):
    def generate_note_and_cards(
        self,
        source_text: str | None,
        user_prompt: str,
    ) -> tuple[NoteDTO, list[CardDTO]]: ...

class DraftStore(Protocol):
    def put(self, token: DraftToken, bundle: DraftBundle) -> None: ...
    def pop(self, token: DraftToken) -> DraftBundle | None: ...

DraftToken = NewType("DraftToken", uuid.UUID)
```

From `app/application/dtos.py`:
```python
@dataclass(frozen=True)
class DraftBundle:
    note: NoteDTO
    cards: list[CardDTO]

@dataclass(frozen=True)
class GenerateRequest:
    kind: SourceKind
    input: str | None
    user_prompt: str

@dataclass(frozen=True)
class GenerateResponse:
    token: DraftToken
    bundle: DraftBundle
```

From `app/application/exceptions.py`:
```python
class UnsupportedSourceKind(DojoError):
    """Raised when a source kind is not yet supported by the use case."""
```

From `tests/fakes/__init__.py`:
```python
# Ready to import:
from tests.fakes import FakeLLMProvider, FakeDraftStore
```

From `app/web/routes/home.py` (Phase 1 orchestrator analog — shape only):
```python
# ABOUTME: Home + health routes — the Phase 1 minimum endpoints.
"""Home and health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
# ... thin handler body, typed signature, one-line docstring.
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Red — end-to-end failing tests for `GenerateFromSource`</name>
  <read_first>
    - .planning/phases/02-domain-application-spine/02-CONTEXT.md D-07 (GenerateRequest shape), D-08 (GenerateResponse + DraftBundle), D-09 (TOPIC only in Phase 2; FILE/URL raise), D-10 (LLMProvider signature `source_text: str | None`).
    - .planning/phases/02-domain-application-spine/02-RESEARCH.md §3.8 (full RED/GREEN/REFACTOR bullets including test names and skeleton code).
    - .planning/phases/02-domain-application-spine/02-PATTERNS.md "tests/unit/application/test_generate_from_source.py" (full test-file skeleton with imports + three representative tests).
    - app/application/ports.py and app/application/dtos.py and app/application/exceptions.py (Plan 02 output — contract surface).
    - tests/fakes/fake_llm_provider.py and tests/fakes/fake_draft_store.py (Plan 03 output — drivers for the use-case test).
    - app/web/routes/home.py (orchestrator-shape analog for the impl task).
  </read_first>
  <behavior>
    One RED commit covering all observable behaviors. Tests in
    `tests/unit/application/test_generate_from_source.py`:

    - `test_generate_from_topic_returns_response_with_token_and_bundle`:
      execute with TOPIC request → `response.token` is a UUID wrapped
      in `DraftToken`; `response.bundle.note == fake_llm.next_response[0]`
      and `response.bundle.cards == fake_llm.next_response[1]`.
    - `test_generate_from_topic_calls_llm_with_none_source_text`: after
      execute, `fake_llm.calls_with == [(None, "alpha")]` (source_text
      is `None` for TOPIC per CONTEXT D-10).
    - `test_generate_from_topic_stores_bundle_in_draft_store`:
      `fake_store.puts == [(response.token, response.bundle)]`.
    - `test_generate_bundle_round_trips_through_draft_store_pop`: after
      execute, `fake_store.pop(response.token) == response.bundle` AND
      a second `pop` returns `None` (atomic-pop contract).
    - `test_generate_file_kind_raises_unsupported_source_kind`:
      `execute(GenerateRequest(kind=SourceKind.FILE, input="/tmp/x.md",
      user_prompt="p"))` raises `UnsupportedSourceKind` and the message
      mentions the kind (e.g., `"file"`).
    - `test_generate_url_kind_raises_unsupported_source_kind`: same for
      `SourceKind.URL`.
    - `test_generate_url_kind_does_not_call_llm`: after the raise,
      `fake_llm.calls_with == []` (the unsupported branch must not
      touch the LLM).

    That's 7 tests. Keep the file ≤100 lines — split into
    `test_generate_topic.py` + `test_generate_unsupported.py` only if
    the file exceeds the ceiling (per PATTERNS.md sizing flag).
  </behavior>
  <action>
**RED: write the failing tests first.**

1. Create `tests/unit/application/test_generate_from_source.py`. Copy
   the PATTERNS.md "tests/unit/application/test_generate_from_source.py"
   header verbatim and extend to the full 7-test set:

   ```python
   # ABOUTME: GenerateFromSource end-to-end test against hand-written fakes.
   # ABOUTME: Covers TOPIC success, draft-store round-trip, FILE/URL raise.
   """GenerateFromSource use-case tests."""

   from __future__ import annotations

   import pytest

   from app.application.dtos import GenerateRequest
   from app.application.exceptions import UnsupportedSourceKind
   from app.application.use_cases.generate_from_source import (
       GenerateFromSource,
   )
   from app.domain.value_objects import SourceKind
   from tests.fakes import FakeDraftStore, FakeLLMProvider
   ```

   Representative test bodies (write all 7, following these patterns):
   ```python
   def test_generate_from_topic_calls_llm_with_none_source_text() -> None:
       """TOPIC path passes source_text=None to the LLM port."""
       fake_llm = FakeLLMProvider()
       fake_store = FakeDraftStore()
       use_case = GenerateFromSource(
           llm=fake_llm, draft_store=fake_store
       )
       use_case.execute(
           GenerateRequest(
               kind=SourceKind.TOPIC, input=None, user_prompt="alpha"
           )
       )
       assert fake_llm.calls_with == [(None, "alpha")]


   def test_generate_bundle_round_trips_through_draft_store_pop() -> None:
       """Bundle put into store is returned by the subsequent pop."""
       fake_llm = FakeLLMProvider()
       fake_store = FakeDraftStore()
       use_case = GenerateFromSource(
           llm=fake_llm, draft_store=fake_store
       )
       response = use_case.execute(
           GenerateRequest(
               kind=SourceKind.TOPIC, input=None, user_prompt="alpha"
           )
       )
       assert fake_store.pop(response.token) == response.bundle
       assert fake_store.pop(response.token) is None


   def test_generate_file_kind_raises_unsupported_source_kind() -> None:
       """FILE kind raises in Phase 2; Phase 4 adds SourceReader wiring."""
       use_case = GenerateFromSource(
           llm=FakeLLMProvider(), draft_store=FakeDraftStore()
       )
       with pytest.raises(UnsupportedSourceKind, match="file"):
           use_case.execute(
               GenerateRequest(
                   kind=SourceKind.FILE,
                   input="/tmp/x.md",
                   user_prompt="p",
               )
           )


   def test_generate_url_kind_does_not_call_llm() -> None:
       """Unsupported-kind branch must short-circuit before hitting LLM."""
       fake_llm = FakeLLMProvider()
       use_case = GenerateFromSource(
           llm=fake_llm, draft_store=FakeDraftStore()
       )
       with pytest.raises(UnsupportedSourceKind):
           use_case.execute(
               GenerateRequest(
                   kind=SourceKind.URL,
                   input="https://example.com",
                   user_prompt="p",
               )
           )
       assert fake_llm.calls_with == []
   ```

2. Run `uv run pytest tests/unit/application/test_generate_from_source.py
   --collect-only` → expect `ModuleNotFoundError` on
   `app.application.use_cases.generate_from_source`.

3. **Sizing check:** `wc -l tests/unit/application/test_generate_from_source.py`
   — if >100, split per PATTERNS.md sizing flag into
   `test_generate_topic.py` (4 TOPIC-path tests) and
   `test_generate_unsupported.py` (3 raise-path tests), both under
   `tests/unit/application/`. Adjust imports accordingly.

4. Commit. Message:
   `test(02-04): add failing end-to-end tests for GenerateFromSource`
  </action>
  <verify>
    <automated>uv run pytest tests/unit/application/test_generate_from_source.py --collect-only 2>&1 | grep -E "ModuleNotFoundError|collected 0" | head -5</automated>
  </verify>
  <acceptance_criteria>
    - `tests/unit/application/test_generate_from_source.py` exists (or the split-pair `test_generate_topic.py` + `test_generate_unsupported.py`). Each file ≤100 lines.
    - The test file(s) collectively contain ≥7 `def test_` functions.
    - Imports include: `GenerateRequest`, `UnsupportedSourceKind`, `GenerateFromSource`, `SourceKind`, `FakeDraftStore`, `FakeLLMProvider`.
    - `uv run pytest tests/unit/application/test_generate_from_source.py --collect-only 2>&1` exits non-zero AND output contains `ModuleNotFoundError: No module named 'app.application.use_cases.generate_from_source'`.
    - No file exists yet at `app/application/use_cases/` (RED-only task). Verify: `ls app/application/use_cases/ 2>&1` shows "No such file or directory".
    - No use of `Mock`/`MagicMock`/`AsyncMock` in the test file(s). Verify: `grep -rE "(unittest\.mock|Mock\(|MagicMock|AsyncMock)" tests/unit/application/test_generate_from_source*.py tests/unit/application/test_generate_topic.py tests/unit/application/test_generate_unsupported.py 2>/dev/null` returns zero matches.
    - Commit exists with message matching `^test\(02-04\): add failing end-to-end tests for GenerateFromSource`.
  </acceptance_criteria>
  <done>Failing tests committed. No use-case implementation exists. `pytest --collect-only` fails with `ModuleNotFoundError` on the use case.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Green — implement `GenerateFromSource` + `make check`</name>
  <read_first>
    - Task 1's committed test file(s) (the tests this task must pass).
    - .planning/phases/02-domain-application-spine/02-CONTEXT.md D-09 (Phase 2 wires TOPIC only), D-10 (`generate_note_and_cards(source_text, user_prompt)` signature).
    - .planning/phases/02-domain-application-spine/02-RESEARCH.md §3.8 GREEN section (full impl bullets).
    - .planning/phases/02-domain-application-spine/02-PATTERNS.md "app/application/use_cases/generate_from_source.py" (full class skeleton) + "app/application/use_cases/__init__.py" (package marker).
    - app/application/ports.py + dtos.py + exceptions.py (contracts this use case consumes).
    - app/web/routes/home.py (orchestrator-shape reference).
    - Makefile (target `check:` must exit 0 at end of task).
  </read_first>
  <action>
**GREEN: implement the minimum that makes Task 1's tests pass.**

1. Create `app/application/use_cases/__init__.py` (per PATTERNS.md):
   ```python
   # ABOUTME: Application use cases — one class per file.
   # ABOUTME: Each use case takes ports via __init__ and exposes execute().
   """Application use-case modules."""
   ```

2. Create `app/application/use_cases/generate_from_source.py` verbatim
   from PATTERNS.md "app/application/use_cases/generate_from_source.py":
   ```python
   # ABOUTME: GenerateFromSource use case — TOPIC branch wired in Phase 2.
   # ABOUTME: FILE + URL branches raise UnsupportedSourceKind until Phase 4.
   """GenerateFromSource use case."""

   from __future__ import annotations

   import uuid

   from app.application.dtos import (
       DraftBundle,
       GenerateRequest,
       GenerateResponse,
   )
   from app.application.exceptions import UnsupportedSourceKind
   from app.application.ports import DraftStore, DraftToken, LLMProvider
   from app.domain.value_objects import SourceKind


   class GenerateFromSource:
       """Generate a draft note + cards from a source, store under token."""

       def __init__(
           self,
           llm: LLMProvider,
           draft_store: DraftStore,
       ) -> None:
           """Wire the use case against its ports."""
           self._llm = llm
           self._draft_store = draft_store

       def execute(self, request: GenerateRequest) -> GenerateResponse:
           """Dispatch on kind; TOPIC fully wired, FILE/URL raise."""
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

   **Do NOT add:** repository constructor args (YAGNI per RESEARCH §3.8);
   strategy-table dispatcher (YAGNI); prompt-shaping logic (Phase 3).
   Keep `execute()` to the two-branch `if`.

3. Run `uv run pytest tests/unit/application/test_generate_from_source.py
   -v` (or both split test files). All 7 tests must pass.

4. Run full application-layer unit tests to confirm no regression:
   `uv run pytest tests/unit/application/ -v` — all tests from Plans 02
   + 04 pass (≥19 + 7 = ≥26 tests).

5. Run the full fake suite to confirm no regression from Plan 03:
   `uv run pytest tests/unit/fakes/ -v` — ≥23 tests pass.

6. Run `make check` end-to-end. Must exit 0.

7. **Sizing check:** `wc -l app/application/use_cases/generate_from_source.py`
   — must be ≤100 (estimated 45-75; well under the ceiling).

8. Commit. Message:
   `feat(02-04): add GenerateFromSource use case (TOPIC branch)`

9. If any formatter tweak is applied by `make check`, commit:
   `chore(02-04): apply make check fixes`
   (skip if clean).
  </action>
  <verify>
    <automated>uv run pytest tests/unit/application/test_generate_from_source.py tests/unit/application/test_generate_topic.py tests/unit/application/test_generate_unsupported.py -v 2>/dev/null; make check</automated>
  </verify>
  <acceptance_criteria>
    - `app/application/use_cases/__init__.py` exists with two `# ABOUTME:` lines + module docstring.
    - `app/application/use_cases/generate_from_source.py` contains the literal strings: `class GenerateFromSource:`, `def __init__(`, `def execute(`, `llm: LLMProvider`, `draft_store: DraftStore`, `source_text=None`, `SourceKind.TOPIC`, `DraftToken(uuid.uuid4())`, `self._draft_store.put(token, bundle)`, `raise UnsupportedSourceKind(`. File is ≤100 lines.
    - `__init__` signature has exactly two non-self args (`llm`, `draft_store`). No repository args. Verify: `grep -A5 "def __init__" app/application/use_cases/generate_from_source.py` shows only `self`, `llm`, `draft_store`.
    - `grep -E "^(from|import) " app/application/use_cases/generate_from_source.py` shows only stdlib (`uuid`, `__future__`) and `app.application.*` / `app.domain.*` — no infrastructure, no web.
    - `uv run pytest tests/unit/application/test_generate_from_source.py -v` (and split-pair if applicable) exits 0 with ≥7 tests passed.
    - `uv run pytest tests/unit/application/ -v` exits 0 with ≥26 tests passed (19 from Plan 02 + 7 from Plan 04, minimum).
    - `uv run pytest tests/unit/fakes/ -v` exits 0 (no regression from Plan 03).
    - `make check` exits 0.
    - Commit exists with message matching `^feat\(02-04\): add GenerateFromSource use case`.
  </acceptance_criteria>
  <done>GenerateFromSource implemented for TOPIC. All 7 use-case tests pass. FILE and URL raise `UnsupportedSourceKind`. `make check` clean. ROADMAP Phase 2 SC #3 satisfied end-to-end against fakes.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

The use case runs entirely in-process and receives its dependencies via
constructor injection. It does not open files, network sockets, or DB
connections in Phase 2 (all those calls are abstracted behind ports,
and the Phase 2 implementations are fakes). The only untrusted input
is the `user_prompt` string in `GenerateRequest` — in Phase 2 it is
passed opaquely to the fake LLM, and in Phase 4 FastAPI will validate it
as form data before the request ever reaches `execute()`.

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-04-01 | Tampering | `execute()` accepts a FILE/URL kind silently (no raise) and later phases think the feature is wired, leading to silent data loss or partial persistence | mitigate | `UnsupportedSourceKind` is raised with a kind-specific message. Tests `test_generate_{file,url}_kind_raises_unsupported_source_kind` and `test_generate_url_kind_does_not_call_llm` are the backstop — a silent pass here would fail both. |
| T-02-04-02 | Elevation of Privilege | A future refactor adds a default value to `GenerateRequest.kind` that accidentally flows through to a non-TOPIC branch without raising | accept | `@dataclass(frozen=True)` with no defaults on `kind` (per CONTEXT D-07) means `GenerateRequest()` without kind is a TypeError. Frozen instance + explicit kind requirement is structural mitigation. |
| T-02-04-03 | Information Disclosure | Use case logs the user prompt or the draft bundle (which could later contain PII in Phase 4) | accept | No logging in Phase 2's use case. Phase 4 will add logging at the FastAPI route layer; at that point structured-log redaction rules apply (see CLAUDE.md + Phase 1 `app/logging_config.py`). |
| T-02-04-04 | Tampering | `DraftToken` collision — two concurrent `execute()` calls mint the same UUID | accept | `uuid.uuid4()` has negligible collision probability. Phase 3's real `InMemoryDraftStore` adds `asyncio.Lock` around writes (C10 mitigation) which defends against the put-phase race even on a collision. No additional Phase 2 mitigation. |

No high-severity threats.
</threat_model>

<verification>
Phase-level verification (run after both tasks complete):

```bash
# 1. Use-case end-to-end tests green
uv run pytest tests/unit/application/test_generate_from_source.py -v
# (or the split-pair test_generate_topic.py + test_generate_unsupported.py)

# 2. Full application + fakes regression
uv run pytest tests/unit/application/ tests/unit/fakes/ -v

# 3. Full gate
make check

# 4. File sizes
wc -l app/application/use_cases/generate_from_source.py \
      app/application/use_cases/__init__.py \
      tests/unit/application/test_generate_from_source.py
# All ≤100.

# 5. No infrastructure/web leaks
grep -rE "^(from|import) " app/application/use_cases/ | grep -E "(app\.infrastructure|app\.web)"
# Expected: no output.
```
</verification>

<success_criteria>
Plan 04 is complete when:

1. `app/application/use_cases/` contains `__init__.py` (marker) and
   `generate_from_source.py` (≤100 lines).
2. `tests/unit/application/test_generate_from_source.py` (or the split
   pair) exists with ≥7 tests covering TOPIC success, draft-store
   round-trip, and FILE/URL raise paths.
3. `uv run pytest tests/unit/application/test_generate_from_source.py -v`
   exits 0 with ≥7 tests passed.
4. `uv run pytest tests/unit/application/ tests/unit/fakes/ -v` exits 0
   with ≥49 tests passed total (19 app-layer + 23 fakes + 7 use-case).
5. `make check` exits 0.
6. `GenerateFromSource.__init__` takes only `llm` and `draft_store`
   (no repository args; Phase 4 adds them).
7. `execute()` dispatch is a two-branch `if` on `request.kind`:
   TOPIC wires end-to-end, FILE and URL raise `UnsupportedSourceKind`.
8. ROADMAP Phase 2 SC #3 satisfied: "The `GenerateFromSource` use case
   runs end-to-end for the TOPIC kind against `FakeLLMProvider`,
   `FakeDraftStore`, and fake repositories, producing a draft bundle
   that round-trips through the draft-store fake." (Fake repositories
   exist in Plan 03 but are not constructor args of this use case in
   Phase 2 — fully-wired phrasing is Phase 4's concern per CONTEXT D-09
   and RESEARCH §3.8.)
</success_criteria>

<output>
After completion, create `.planning/phases/02-domain-application-spine/02-04-SUMMARY.md`
documenting:
- Files created (with line counts).
- Whether the test file was split at the 100-line ceiling.
- Test list (TOPIC tests + raise tests).
- Commit hashes (RED + GREEN).
- Confirmation: `GenerateFromSource.__init__` takes only `llm` + `draft_store`.
- Confirmation: FILE and URL branches both raise `UnsupportedSourceKind`
  without touching the LLM port.
</output>
