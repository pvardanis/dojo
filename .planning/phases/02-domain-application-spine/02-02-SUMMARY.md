---
phase: 02-domain-application-spine
plan: 02
subsystem: application
tags:
  - application
  - ports
  - protocols
  - dtos
  - pydantic
  - dip-boundary
  - tdd

requires:
  - phase: 02-domain-application-spine
    plan: 01
    provides: "Domain entities (Source/Note/Card/CardReview with title+content_md fields), value objects (SourceKind/Rating StrEnums + 4 typed-ID NewTypes), DojoError root exception"
provides:
  - "app/application/__init__.py: layer package marker (no re-exports)"
  - "app/application/ports.py: 6 typing.Protocol ports (LLMProvider, SourceRepository, NoteRepository, CardRepository, CardReviewRepository, DraftStore) + 2 PEP 695 type aliases (UrlFetcher, SourceReader) + DraftToken NewType"
  - "app/application/dtos.py: Pydantic v2 LLM-boundary DTOs (NoteDTO, CardDTO, GeneratedContent) + stdlib frozen use-case dataclasses (GenerateRequest, GenerateResponse, DraftBundle)"
  - "app/application/exceptions.py: UnsupportedSourceKind, DraftExpired, LLMOutputMalformed (all inherit DojoError)"
  - "tests/unit/application/: 22 unit tests across 4 files (test_ports, test_dtos, test_use_case_dtos, test_exceptions)"
affects:
  - 02-03-hand-written-fakes
  - 02-04-generate-from-source-use-case
  - 02-05-contract-harness-import-linter
  - 03-infrastructure-adapters
  - 04-generate-review-save-flow

tech-stack:
  added: []
  patterns:
    - "typing.Protocol for multi-method / stateful ports (no @runtime_checkable)"
    - "PEP 695 `type X = Y` type aliases for stateless single-op Callable ports"
    - "Pydantic v2 at the untrusted-input boundary: ConfigDict(extra='ignore') + Field(min_length=1)"
    - "Stdlib @dataclass(frozen=True) for trusted internal use-case DTOs"
    - "NewType over uuid.UUID for typed identity tokens (DraftToken alongside SourceId/NoteId/CardId/ReviewId)"
    - "Circular-import avoidance via TYPE_CHECKING guard (ports ↔ dtos only reference each other in annotations)"
    - "Two-file DTO test split: Pydantic boundary tests vs. stdlib-dataclass use-case tests"

key-files:
  created:
    - app/application/__init__.py
    - app/application/ports.py
    - app/application/dtos.py
    - app/application/exceptions.py
    - tests/unit/application/__init__.py
    - tests/unit/application/test_ports.py
    - tests/unit/application/test_dtos.py
    - tests/unit/application/test_use_case_dtos.py
    - tests/unit/application/test_exceptions.py
  modified: []

key-decisions:
  - "Used PEP 695 `type X = Y` for UrlFetcher/SourceReader (ruff UP040 autofix requires it on Python 3.12+); the plan's `X: TypeAlias = Y` skeleton was pre-Python-3.12 syntax. Spirit preserved: still a Callable alias, not a Protocol."
  - "Broke the ports ↔ dtos circular dependency with `if TYPE_CHECKING:` guards on both sides: ports imports NoteDTO/CardDTO/DraftBundle only as annotations; dtos imports DraftToken only as annotation. `from __future__ import annotations` makes this safe at runtime."
  - "Aligned NoteDTO fields with Plan 01's Note entity: `title` + `content_md` (not the plan-skeleton's single `content` field). Plan 01's domain is the locked contract."
  - "Added GeneratedContent Pydantic envelope with `cards: list[CardDTO] = Field(min_length=1)` — the objective and success criteria required it even though the PLAN.md skeleton omitted it. Closes PITFALL M6 (empty-cards-list escape)."
  - "Kept RED+GREEN merged per unit of behavior, per Plan 02-01's committed convention override. The pre-commit pytest-unit hook independently verifies GREEN on every commit."
  - "Split test_dtos.py (122 lines) into test_dtos.py (70 lines, Pydantic DTOs) + test_use_case_dtos.py (60 lines, stdlib dataclasses) to honor the ≤100-line file ceiling."

patterns-established:
  - "Application-layer __init__.py: ABOUTME + module docstring, no re-exports (D-11 rule inherited from Phase 1)"
  - "Protocol method docstrings specify return/error semantics in one line (PITFALL M11 + CONTEXT Claude's discretion), not restatements of the method name"
  - "Pydantic validation lives in DTOs as the LLM trust boundary; stdlib dataclasses are internal and carry no validation"
  - "PEP 695 type-alias syntax for Callable ports (not the older `TypeAlias = ...` form)"

requirements-completed:
  - DRAFT-01
  - TEST-01

# Metrics
duration: ~5min
completed: 2026-04-22
---

# Phase 2 Plan 02: Application Ports & DTOs Summary

**Application-layer spine complete: six `typing.Protocol` ports + two PEP 695 `type` aliases + `DraftToken` NewType, Pydantic LLM-boundary DTOs with `extra="ignore"` + `min_length=1`, stdlib frozen use-case dataclasses, and a DojoError-derived exception hierarchy — all delivered TDD with 22 passing unit tests and zero `@runtime_checkable`.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-22T10:47:46Z
- **Completed:** 2026-04-22T10:52:53Z
- **Tasks:** 2 planned → delivered as 4 atomic commits per the commit-convention override
- **Files created:** 9 (4 source + 5 test)
- **Tests added:** 22 (4 exceptions + 9 Pydantic DTOs + 4 use-case DTOs + 5 ports)

## Accomplishments

- Six `typing.Protocol` ports declared with exactly the right surface: `LLMProvider.generate_note_and_cards(source_text, user_prompt)` per CONTEXT D-10, `DraftStore.put`+`pop` only per CONTEXT D-04 (no `get`, no TTL API), repos expose only the `save`/`get` pairs the use case needs.
- Two PEP 695 `type` aliases for stateless Callable ports (`UrlFetcher`, `SourceReader`) per CLAUDE.md Protocol-vs-function clarifier.
- `DraftToken` NewType over `uuid.UUID` declared in ports.py (CONTEXT D-03). Lives in the application layer because draft semantics are application-level.
- Pydantic `NoteDTO` + `CardDTO` + `GeneratedContent` with `ConfigDict(extra="ignore")` and `Field(min_length=1)` on all required strings; `GeneratedContent.cards` has `min_length=1` to close PITFALL M6's empty-cards-list escape.
- Stdlib `GenerateRequest`, `GenerateResponse`, `DraftBundle` as `@dataclass(frozen=True)` — the internal trust boundary, no validation overhead.
- `UnsupportedSourceKind`, `DraftExpired`, `LLMOutputMalformed` inherit from `DojoError`, human-readable messages round-trip via `str(exc)`.
- DIP boundary intact: `app/application/` imports only `__future__`, `uuid`, stdlib collections/dataclasses/pathlib/typing, `pydantic`, and `app.domain.*`. Zero `app.infrastructure` or `app.web` imports (Plan 05's import-linter will ratify at CI level).
- `make check` green end-to-end: 55 tests pass, ruff clean, ty clean, interrogate 100%.
- File sizes all under 100 lines; no `ports/` split required (ports.py lands at 98).

## Task Commits

Per the Plan 02-01 commit-convention override (RED+GREEN merged per unit of behavior because the pytest-unit pre-commit hook blocks RED-only commits that import unbuilt modules), commits are per unit rather than per TDD-phase:

1. **Application package scaffold + exceptions** — `9d451b0` (`feat(02-02): add application package scaffold and exception hierarchy`)
2. **DTOs + DraftToken** — `fed958a` (`feat(02-02): add application DTOs and DraftToken NewType`)
3. **Full ports surface** — `5da215c` (`feat(02-02): add full application ports surface (6 Protocols + 2 aliases)`)
4. **Test-file split for ≤100-line ceiling** — `afb657f` (`refactor(02-02): split test_dtos.py into Pydantic and use-case halves`)

**Plan metadata commit:** forthcoming (adds this SUMMARY + STATE.md + ROADMAP.md updates).

## TDD Log

Per the override, RED-commit proof is replaced with this in-commit proof-of-process. For every unit (exceptions, DTOs, ports), the tests were written and executed locally *before* the implementation file existed, then re-executed after the implementation landed.

| Unit | RED failure observed (pre-impl) | GREEN result |
|------|---------------------------------|--------------|
| `exceptions.py` | `ModuleNotFoundError: No module named 'app.application.exceptions'` on test collection | 4/4 tests passed |
| `dtos.py` (Pydantic + use-case) | `ModuleNotFoundError: No module named 'app.application.dtos'` on test collection | 13/13 tests passed |
| `ports.py` (full surface) | `AttributeError: module 'app.application.ports' has no attribute 'LLMProvider'` (etc.) — 4/5 ports smoke tests failed, DraftToken test already passed from Unit 2's stub | 5/5 tests passed post-expansion |

The `pytest-unit` pre-commit hook (which re-runs `pytest tests/unit/ -x --ff` on every commit that touches Python) independently re-verified the GREEN state at each commit.

## Files Created/Modified

| File | Lines | Purpose |
|------|-------|---------|
| `app/application/__init__.py` | 3 | Application package marker (ABOUTME + docstring; no re-exports) |
| `app/application/ports.py` | 98 | 6 Protocols + 2 PEP 695 Callable aliases + DraftToken NewType |
| `app/application/dtos.py` | 68 | NoteDTO + CardDTO + GeneratedContent (Pydantic) + 3 stdlib frozen DTOs |
| `app/application/exceptions.py` | 19 | UnsupportedSourceKind, DraftExpired, LLMOutputMalformed (DojoError-derived) |
| `tests/unit/application/__init__.py` | 3 | Test-package marker |
| `tests/unit/application/test_ports.py` | 49 | 5 smoke tests: surface shape, Callable aliases, DraftToken supertype, DraftStore {put, pop} only, no @runtime_checkable |
| `tests/unit/application/test_dtos.py` | 70 | 9 Pydantic DTO tests: empty-string rejection, `extra='ignore'`, `min_length=1`, default tags tuple |
| `tests/unit/application/test_use_case_dtos.py` | 60 | 4 stdlib dataclass tests: frozenness, None-input for TOPIC, token+bundle holding |
| `tests/unit/application/test_exceptions.py` | 36 | 4 exception tests: DojoError subclass + message round-trip |

All 9 new `.py` files start with two `# ABOUTME:` lines; every public symbol carries a one-line docstring (interrogate 100%).

## Port Surface Snapshot

```
# 6 Protocols (no @runtime_checkable)
LLMProvider               — generate_note_and_cards(source_text, user_prompt)
SourceRepository          — save / get
NoteRepository            — save / get (regenerate-overwrites at adapter)
CardRepository            — save / get (regenerate-appends at adapter)
CardReviewRepository      — save (append-only)
DraftStore                — put / pop  (atomic, no get — CONTEXT D-04)

# 2 PEP 695 Callable aliases (NOT Protocols)
type UrlFetcher    = Callable[[str], str]
type SourceReader  = Callable[[Path], str]

# 1 NewType
DraftToken = NewType("DraftToken", uuid.UUID)
```

## Decisions Made

1. **PEP 695 `type` keyword for Callable aliases** — ruff UP040 flags `TypeAlias = Callable[...]` on Python 3.12+; autofix points at `type X = Y`. Adopted the newer syntax; spirit of the plan's skeleton preserved (alias on Callable, not Protocol).
2. **Circular imports broken via TYPE_CHECKING guards** — ports.py needs `NoteDTO`/`CardDTO`/`DraftBundle` for Protocol signatures; dtos.py needs `DraftToken` for `GenerateResponse.token`. Both are annotation-only, so both live under `if TYPE_CHECKING:`. `from __future__ import annotations` keeps them as strings at runtime.
3. **NoteDTO field names align with Plan 01's Note entity** — Plan 01 shipped `Note.title` + `Note.content_md`, not the plan-skeleton's single `content` field. The domain is the locked contract; DTOs mirror it to avoid mapper complexity.
4. **Added `GeneratedContent` Pydantic envelope** — the objective and success criteria explicitly required it ("Pydantic DTOs for LLM I/O: NoteDTO, CardDTO, GeneratedContent"), even though the PLAN.md task skeleton omitted it. `cards: list[CardDTO] = Field(min_length=1)` closes PITFALL M6's empty-list escape. The LLM adapter in Phase 3 will deserialise Anthropic tool-use output into `GeneratedContent`, then unpack it into `(NoteDTO, list[CardDTO])` to match the `LLMProvider` Protocol return type.
5. **Shipped all three application exceptions up-front** — `DraftExpired` and `LLMOutputMalformed` will only be raised in Phase 3's adapters, but declaring them here keeps the app-layer exception hierarchy coherent in one commit.
6. **Merged RED+GREEN per unit of behavior** — carried forward from Plan 02-01's committed override. TDD discipline lives in the dev loop; commits are atomic units.

## Deviations from Plan

### Rule 1 — Tooling gate (ruff UP040)

**Found during:** Unit 3 (ports.py expansion)

**Issue:** Plan skeleton used `UrlFetcher: TypeAlias = Callable[[str], str]`. Ruff UP040 on Python 3.12+ requires the PEP 695 `type X = Y` keyword syntax and cannot auto-fix it under `--safe-fixes`.

**Fix:** Rewrote both aliases as `type UrlFetcher = Callable[[str], str]` / `type SourceReader = Callable[[Path], str]`; removed the `TypeAlias` import from `typing`. Smoke tests use `hasattr`, so they pass regardless of the alias form.

**Files modified:** `app/application/ports.py`
**Commit:** `5da215c`

### Rule 3 — File-size ceiling

**Found during:** post-GREEN verification pass after Unit 2

**Issue:** `tests/unit/application/test_dtos.py` reached 122 lines after adding GeneratedContent tests — over the ≤100-line ceiling per CLAUDE.md and the python-project-setup wiki.

**Fix:** Split along the natural Pydantic-vs-stdlib seam. Pydantic boundary tests (NoteDTO/CardDTO/GeneratedContent, 9 tests) stay in `test_dtos.py` (70 lines). Stdlib use-case DTO tests (GenerateRequest/GenerateResponse/DraftBundle, 4 tests) move to new `test_use_case_dtos.py` (60 lines).

**Files modified:** `tests/unit/application/test_dtos.py`, `tests/unit/application/test_use_case_dtos.py` (new)
**Commit:** `afb657f`

### Skipped plan instructions

- **None required skipping.** The `<critical_updated_convention>` warned about plan tasks that might re-add `__post_init__` validation to domain entities — none of Plan 02-02's actual tasks touched `app/domain/`, so no skip was needed.
- **`GeneratedContent` was added beyond the PLAN.md task skeleton** (but matched the plan frontmatter's objective + success criteria, which are authoritative).

## Issues Encountered

- **Ruff UP040** on the initial `TypeAlias` declarations — not auto-fixable without `--unsafe-fixes`, so hand-switched both aliases to PEP 695 `type` syntax. (Deviation Rule 1 above.)
- **test_dtos.py over the 100-line ceiling** after GeneratedContent tests were added. Split the file. (Deviation Rule 3 above.)

No authentication gates, no architectural decisions, no blockers carried forward.

## Self-Check

Files created (all present):
- app/application/__init__.py — FOUND
- app/application/ports.py — FOUND
- app/application/dtos.py — FOUND
- app/application/exceptions.py — FOUND
- tests/unit/application/__init__.py — FOUND
- tests/unit/application/test_ports.py — FOUND
- tests/unit/application/test_dtos.py — FOUND
- tests/unit/application/test_use_case_dtos.py — FOUND
- tests/unit/application/test_exceptions.py — FOUND

Commits (all present in `git log main..HEAD`):
- 9d451b0 — FOUND (feat: package scaffold + exceptions)
- fed958a — FOUND (feat: DTOs + DraftToken)
- 5da215c — FOUND (feat: full ports surface)
- afb657f — FOUND (refactor: test-file split)

Gate checks (final run, 2026-04-22):
- `make check` — PASSED (55 tests; ruff/ty/interrogate clean)
- `uv run pytest tests/unit/application/ -v` — 22/22 PASSED
- `grep -rE "@runtime_checkable" app/application/` — no decorator; only one comment mention (the negative-assertion ABOUTME) — PASSED
- Inward-only imports in `app/application/` — PASSED (stdlib + pydantic + app.domain only)
- `wc -l app/application/*.py tests/unit/application/*.py` — every file ≤100 lines — PASSED (max is ports.py at 98)
- Every new `.py` starts with two `# ABOUTME:` lines — PASSED
- Branch is `phase-02-plan-02-application-ports-dtos` — PASSED

## Self-Check: PASSED

## Next Phase Readiness

- **Plan 02-03 (hand-written fakes) unblocked.** Fakes can now structurally subtype the 6 Protocols via duck-typed method signatures. All 6 Protocols + 2 Callable aliases + DraftToken are importable via `from app.application.ports import ...`.
- **Plan 02-04 (GenerateFromSource use case) unblocked at the port level.** Needs Plan 02-03's fakes before it can be driven end-to-end.
- **Phase 2 Success Criterion #2 satisfied.** Ports declared as `typing.Protocol` with no `@runtime_checkable`; Callable aliases present. The import-linter structural proof of SC #6 ships in Plan 05.
- **DRAFT-01 port declaration discharged** (fake + concrete implementation in Plan 02-03 / Phase 3).
- **TEST-01 requirement completed** at the ports-frozen level.
- **No blockers** carried forward.

---
*Phase: 02-domain-application-spine*
*Completed: 2026-04-22*
