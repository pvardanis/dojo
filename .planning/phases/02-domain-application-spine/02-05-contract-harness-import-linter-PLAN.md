---
phase: 02-domain-application-spine
plan: 05
type: tdd
wave: 5
depends_on:
  - "02-01"
  - "02-02"
  - "02-03"
  - "02-04"
files_modified:
  - pyproject.toml
  - Makefile
  - tests/contract/__init__.py
  - tests/contract/test_llm_provider_contract.py
autonomous: true
requirements:
  - TEST-03
tags:
  - test-03
  - contract-test
  - import-linter
  - boundary
  - ci
must_haves:
  truths:
    - "`tests/contract/test_llm_provider_contract.py` runs on every `make check` for the `\"fake\"` parameter leg and auto-skips on the `\"anthropic\"` leg when `RUN_LLM_TESTS=1` is unset OR when `app.infrastructure.llm.anthropic_provider` does not import."
    - "With `RUN_LLM_TESTS=1` set but the adapter module still absent (current Phase-2 state), the anthropic leg skips via `pytest.importorskip` — it does not error and it does not flake."
    - "`pyproject.toml` contains a `[tool.importlinter]` section with `root_package = \"app\"` and two forbidden contracts: `app.domain` and `app.application` must not import from `app.infrastructure` or `app.web`."
    - "`uv run lint-imports` exits 0 against the current tree (post Plans 01-04). A deliberate violation (e.g., `from app.infrastructure.db.session import engine` injected into `app/domain/entities.py` in a throwaway branch) makes `lint-imports` exit non-zero."
    - "`make lint` runs `uv run ruff check --fix .` followed by `uv run lint-imports`; `make check` picks up the new step automatically (no `check:` edit needed — it already calls `lint`)."
  artifacts:
    - path: "tests/contract/__init__.py"
      provides: "Contract-test package marker (ABOUTME + module docstring)."
    - path: "tests/contract/test_llm_provider_contract.py"
      provides: "TEST-03 harness — parametrised fixture over `[fake, anthropic]` with double-gate auto-skip on the real leg."
    - path: "pyproject.toml (modified)"
      provides: "`import-linter>=2.0` in dev deps; `[tool.importlinter]` section with two forbidden contracts enforcing the DIP boundary."
    - path: "Makefile (modified)"
      provides: "`lint:` target extended with `uv run lint-imports` as the second step."
  key_links:
    - from: "tests/contract/test_llm_provider_contract.py"
      to: "tests/fakes/fake_llm_provider.py"
      via: "fake leg constructs `FakeLLMProvider` as the parametrised fixture value"
      pattern: "from tests\\.fakes import FakeLLMProvider"
    - from: "tests/contract/test_llm_provider_contract.py"
      to: "app/application/dtos.py"
      via: "contract assertions check the LLM return-type shape via `isinstance(note, NoteDTO)` etc."
      pattern: "from app\\.application\\.dtos import"
    - from: "Makefile `lint:` target"
      to: "pyproject.toml `[tool.importlinter]`"
      via: "`lint-imports` auto-discovers the `[tool.importlinter]` block from pyproject.toml"
      pattern: "uv run lint-imports"
---

<objective>
Close Phase 2 by wiring the TEST-03 contract harness and the
import-linter boundary enforcement. These are the two load-bearing
gates that keep Phase 2's port shapes honest once real adapters arrive
in Phase 3:

1. **TEST-03 contract harness** (`tests/contract/test_llm_provider_contract.py`)
   is a pytest fixture parameterised over `["fake", "anthropic"]`. The
   fake leg always runs — the Phase 2 `FakeLLMProvider` is exercised
   against the same assertions the real `AnthropicLLMProvider` will
   face in Phase 3. The anthropic leg auto-skips in Phase 2 because
   `app.infrastructure.llm.anthropic_provider` does not exist; Phase 3
   creates the module and the param activates without any Phase 2
   revision needed.

2. **import-linter boundary enforcement** closes the
   Phase-1-LEARNINGS open item "Phase-2 boundary lint". Two forbidden
   contracts ensure `app.domain` and `app.application` never import
   from `app.infrastructure` or `app.web`. Enforcement lives in
   `pyproject.toml` + a new `uv run lint-imports` step in `make lint`.

Discharges TEST-03 in full and ROADMAP Phase 2 SC #5 + SC #6:
- SC #5: contract-test harness parameterised over
  `[FakeLLMProvider, AnthropicLLMProvider]` exists and is gated on
  `RUN_LLM_TESTS=1`.
- SC #6: `import-linter` is configured so a test asserts that
  `app/domain/` and `app/application/` never import from
  `app/infrastructure/` or `app/web/`.

Together with Plans 01-04, this plan closes Phase 2 in its entirety.
After merge, `make check` is the single CI contract that covers every
Phase 2 success criterion and every requirement (DRAFT-01, TEST-01,
TEST-03).

Scope: 2 new test files + 2 existing config files modified. RESEARCH
estimates 150-250 LOC. This plan contains one unusual element — a
deliberate negative-verification step in Task 2 where the executor
commits a deliberately-invalid import, runs `lint-imports` to confirm it
fails, then reverts the deliberate violation. This proves the gate is
actually enforcing the contract rather than trivially passing.
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

# Plans 01-04 outputs (all required for contract test + linter sanity)
@.planning/phases/02-domain-application-spine/02-01-SUMMARY.md
@.planning/phases/02-domain-application-spine/02-02-SUMMARY.md
@.planning/phases/02-domain-application-spine/02-03-SUMMARY.md
@.planning/phases/02-domain-application-spine/02-04-SUMMARY.md
@app/application/ports.py
@app/application/dtos.py
@tests/fakes/__init__.py
@tests/fakes/fake_llm_provider.py

# Config files to modify
@pyproject.toml
@Makefile

# Phase 1 analogs
@tests/integration/__init__.py

# Phase 1 LEARNINGS open item this plan closes
@.planning/phases/01-project-scaffold-tooling/LEARNINGS.md

<interfaces>
<!-- Existing pyproject.toml sections the executor must extend, not replace. -->

From `pyproject.toml` `[dependency-groups] dev`:
```toml
[dependency-groups]
dev = [
    "ruff>=0.8",
    "ty==0.0.31",              # D-16: exact pin, still beta
    "interrogate>=1.7",
    "pytest>=8.3",
    "pytest-asyncio>=1.0",
    "pytest-cov>=5.0",
    "pytest-repeat>=0.9.4",
    "httpx>=0.28",
    "pre-commit>=3.7",
]
```

From `Makefile` (lines 14-15):
```makefile
lint:
	uv run ruff check --fix .
```

`[tool.importlinter]` section to APPEND (not replace) — verified against
current import-linter stable docs per RESEARCH §1.1e:
```toml
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

From `tests/fakes/__init__.py` (Plan 03 output):
```python
from tests.fakes import FakeLLMProvider  # ready to import
```

From `app/application/dtos.py` (Plan 02 output):
```python
class NoteDTO(BaseModel): ...
class CardDTO(BaseModel): ...
```

From `app/application/ports.py` (Plan 02 output):
```python
class LLMProvider(Protocol):
    def generate_note_and_cards(
        self,
        source_text: str | None,
        user_prompt: str,
    ) -> tuple[NoteDTO, list[CardDTO]]: ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Red→Green for the TEST-03 contract harness</name>
  <read_first>
    - .planning/phases/02-domain-application-spine/02-CONTEXT.md D-11 (parametrised fixture pattern + double-gate: `RUN_LLM_TESTS=1` AND importable adapter module).
    - .planning/phases/02-domain-application-spine/02-RESEARCH.md §2.6 (full harness shape), §3.9 (cross-cutting TDD notes — anthropic leg auto-skips because the module does not exist yet; pytest.importorskip handles this without a stub).
    - .planning/phases/02-domain-application-spine/02-PATTERNS.md "tests/contract/test_llm_provider_contract.py" (full skeleton with fixture + contract test).
    - tests/integration/__init__.py (Phase 1 package-marker analog).
    - tests/fakes/fake_llm_provider.py (Plan 03 output — the fake leg driver).
    - app/application/ports.py and app/application/dtos.py (Plan 02 — contract signatures).
  </read_first>
  <behavior>
    One RED commit (failing tests before the harness exists); one GREEN
    commit (harness implemented; fake leg passes, anthropic leg skips
    cleanly).

    `tests/contract/test_llm_provider_contract.py` must include:

    - `@pytest.fixture(params=["fake", "anthropic"]) def llm_provider(request): ...`
      with the double-gate behavior:
        - `"fake"` always yields `FakeLLMProvider()`.
        - `"anthropic"` checks `os.getenv("RUN_LLM_TESTS")` → if falsy,
          `pytest.skip("RUN_LLM_TESTS not set")`. Then
          `adapter_module = pytest.importorskip("app.infrastructure.llm.anthropic_provider")`
          → module absent in Phase 2, harness skips silently without
          needing a stub.
    - `test_generate_returns_note_and_card_list(llm_provider)`:
        - `note, cards = llm_provider.generate_note_and_cards(source_text=None, user_prompt="alpha")`.
        - `isinstance(note, NoteDTO)`, `isinstance(cards, list)`,
          `len(cards) >= 1`, every card `isinstance(c, CardDTO)`.

    Expected behavior:
    - `uv run pytest tests/contract/test_llm_provider_contract.py -v` on
      an unset `RUN_LLM_TESTS` → 1 passed, 1 skipped.
    - Same command with `RUN_LLM_TESTS=1 uv run pytest tests/contract/...` →
      still 1 passed, 1 skipped (the adapter module is absent in Phase
      2; `pytest.importorskip` handles the skip).
  </behavior>
  <action>
**Part A — RED: failing harness.**

1. Create `tests/contract/__init__.py` (per PATTERNS.md):
   ```python
   # ABOUTME: Contract tests — shared-fixture harness across fake + real impls.
   # ABOUTME: Real-leg skips unless RUN_LLM_TESTS=1 + adapter module imports.
   """Contract tests."""
   ```

2. Create `tests/contract/test_llm_provider_contract.py` verbatim from
   PATTERNS.md "tests/contract/test_llm_provider_contract.py":
   ```python
   # ABOUTME: TEST-03 contract harness — asserts Protocol shape for LLM port.
   # ABOUTME: Fake leg always runs; anthropic leg auto-skips (import + env).
   """LLMProvider contract tests — shared across fake and real impls."""

   from __future__ import annotations

   import os

   import pytest

   from app.application.dtos import CardDTO, NoteDTO
   from tests.fakes import FakeLLMProvider


   @pytest.fixture(params=["fake", "anthropic"])
   def llm_provider(request: pytest.FixtureRequest):
       """Yield a fake or real LLMProvider; real skips without opt-in."""
       if request.param == "fake":
           yield FakeLLMProvider()
           return

       if not os.getenv("RUN_LLM_TESTS"):
           pytest.skip("RUN_LLM_TESTS not set")
       adapter_module = pytest.importorskip(
           "app.infrastructure.llm.anthropic_provider"
       )
       yield adapter_module.AnthropicLLMProvider()


   def test_generate_returns_note_and_card_list(llm_provider) -> None:
       """Return type is (NoteDTO, list[CardDTO]) with non-empty cards."""
       note, cards = llm_provider.generate_note_and_cards(
           source_text=None, user_prompt="alpha"
       )
       assert isinstance(note, NoteDTO)
       assert isinstance(cards, list)
       assert len(cards) >= 1
       assert all(isinstance(c, CardDTO) for c in cards)
   ```

   Note: this task ships both the RED and GREEN in quick succession
   because the harness's "failing state" is essentially nonexistent —
   creating the file either passes immediately (fake leg green) or
   fails with an import error on fakes if something is genuinely
   broken. The "RED" step here is a sanity check that the test **would
   fail** if we removed the fake.

3. Run `uv run pytest tests/contract/test_llm_provider_contract.py -v` —
   expect: `1 passed, 1 skipped` (fake leg passes; anthropic skipped
   on `RUN_LLM_TESTS not set`).

4. Commit. Message:
   `test(02-05): add TEST-03 contract harness for LLMProvider`

**Part B — Negative verification (belt-and-braces RED).**

5. Temporarily break `FakeLLMProvider.generate_note_and_cards` in a
   throwaway local change so it returns `(note, "not a list")` instead
   of `(note, [card])`. Do NOT commit. Run the contract test — it must
   fail on `isinstance(cards, list)`. This proves the harness catches
   real drift.

6. Revert the local change (`git checkout tests/fakes/fake_llm_provider.py`).
   Re-run the test — back to `1 passed, 1 skipped`.

**Part C — Verify anthropic leg with `RUN_LLM_TESTS=1`.**

7. `RUN_LLM_TESTS=1 uv run pytest tests/contract/test_llm_provider_contract.py -v`
   — still `1 passed, 1 skipped` (the anthropic-leg skip now fires via
   `pytest.importorskip` because the adapter module does not exist yet).
   Confirms Phase 3 gets a clean auto-activation when the adapter lands.

8. `uv run ruff check tests/contract/` exits 0.
   `uv run ty check app` exits 0 (contract tests live under `tests/`,
   excluded from ty scope by pyproject.toml interrogate exclude — but
   they should still be ruff-clean).

9. Commit any additional polish if ruff auto-fixed formatting:
   `chore(02-05): ruff auto-fix contract harness`
   (skip if clean).
  </action>
  <verify>
    <automated>uv run pytest tests/contract/test_llm_provider_contract.py -v && RUN_LLM_TESTS=1 uv run pytest tests/contract/test_llm_provider_contract.py -v</automated>
  </verify>
  <acceptance_criteria>
    - `tests/contract/__init__.py` exists with two `# ABOUTME:` lines + module docstring.
    - `tests/contract/test_llm_provider_contract.py` exists and contains the literal strings: `@pytest.fixture(params=["fake", "anthropic"])`, `def llm_provider(request`, `yield FakeLLMProvider()`, `pytest.skip("RUN_LLM_TESTS not set")`, `pytest.importorskip("app.infrastructure.llm.anthropic_provider")`, `def test_generate_returns_note_and_card_list(llm_provider)`, `isinstance(note, NoteDTO)`, `isinstance(cards, list)`, `len(cards) >= 1`.
    - `uv run pytest tests/contract/test_llm_provider_contract.py -v` exits 0 with output containing `1 passed` and `1 skipped`.
    - `RUN_LLM_TESTS=1 uv run pytest tests/contract/test_llm_provider_contract.py -v` exits 0 with output containing `1 passed` and `1 skipped` (adapter module absent → importorskip handles it).
    - Contract harness file is ≤100 lines (`wc -l tests/contract/test_llm_provider_contract.py`).
    - `uv run ruff check tests/contract/` exits 0.
    - No use of `Mock`/`MagicMock`/`AsyncMock` in the harness (`grep -rE "(unittest\.mock|Mock\(|MagicMock|AsyncMock)" tests/contract/` returns zero).
    - Commit exists with message matching `^test\(02-05\): add TEST-03 contract harness for LLMProvider`.
  </acceptance_criteria>
  <done>TEST-03 harness exists. Fake leg passes; anthropic leg auto-skips whether or not `RUN_LLM_TESTS` is set (because the adapter module does not exist yet). Phase 3 will activate the real leg automatically.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Import-linter wiring — deps, config, Makefile, negative-path proof</name>
  <read_first>
    - .planning/phases/02-domain-application-spine/02-CONTEXT.md D-12 (import-linter choice + two forbidden contracts + `make lint` wiring).
    - .planning/phases/02-domain-application-spine/02-RESEARCH.md §1.1 (verified against current import-linter docs — copy-pastable config block §1.1e).
    - .planning/phases/02-domain-application-spine/02-PATTERNS.md "pyproject.toml (modified)" + "Makefile (modified)" (exact placement guidance).
    - pyproject.toml (current state — existing `[dependency-groups]`, `[tool.*]` sections; import-linter block is appended, nothing replaced).
    - Makefile (current `lint:` target — one line `uv run ruff check --fix .`).
    - .planning/phases/01-project-scaffold-tooling/LEARNINGS.md "Open items → Phase-2 boundary lint" (this task closes it).
  </read_first>
  <action>
**Part A — Add import-linter dep + config.**

1. Edit `pyproject.toml` `[dependency-groups] dev` list: append the line
   ```toml
       "import-linter>=2.0",      # Plan 02-05: domain/app boundary enforcement
   ```
   Position: alphabetically appropriate or at the end — import-linter
   alphabetically falls between `interrogate` and `pre-commit`, so
   insert after `interrogate>=1.7,` for stylistic consistency with the
   existing alphabetical-ish order in dev deps.

2. Append the `[tool.importlinter]` section to `pyproject.toml`. Location:
   at the end of the file, after the existing `[tool.ty]` block. Copy
   verbatim from RESEARCH §1.1e / PATTERNS.md:
   ```toml
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

3. Run `uv sync` to install import-linter into the venv. `uv.lock`
   regenerates automatically.

4. Run `uv run lint-imports` — must exit 0 (Plans 01-04 already obey
   the contract because their acceptance criteria required stdlib-only
   imports in `app/domain/` and only domain-or-stdlib imports in
   `app/application/`).

**Part B — Wire into Makefile `lint:` target.**

5. Edit `Makefile`. Replace the current single-line `lint:` target
   (line 14-15) with the two-line version from PATTERNS.md:
   ```makefile
   lint:
   	uv run ruff check --fix .
   	uv run lint-imports
   ```
   Leave every other target untouched. `check:` (line 26) already calls
   `lint`, so the new step flows into `make check` automatically — no
   edit to `check:` needed.

6. Run `make lint` — must exit 0. If it exits non-zero, there's a real
   boundary leak in Plans 01-04 that slipped through the per-plan
   greps; fix by removing the offending import from `app/domain/` or
   `app/application/`. (This is a HARD gate — do not workaround with
   `allow_indirect_imports = true` or by adding to an `ignore` list.)

7. Run `make check` end-to-end. Must exit 0.

8. Commit. Message:
   `feat(02-05): wire import-linter boundary enforcement into make lint`

**Part C — Negative-path proof (the gate must actually enforce).**

9. **Create a throwaway local violation** to prove `lint-imports`
   catches it. In a separate git worktree OR using a stash-based
   throwaway:

   ```bash
   # Inject a deliberate violation
   echo "from app.infrastructure.db.session import engine  # intentional violation" >> app/domain/entities.py

   # Confirm the gate fires
   uv run lint-imports 2>&1 | tee /tmp/lint-imports-violation.log
   # Expected: non-zero exit; output mentions
   # "Domain must not depend on infrastructure or web" BROKEN
   # and names app.domain.entities -> app.infrastructure.db.session.

   # Revert IMMEDIATELY — do NOT commit
   git checkout app/domain/entities.py

   # Confirm lint-imports is green again
   uv run lint-imports
   # Expected: exit 0.
   ```

10. **Do not commit the violation.** The negative-path proof is a
    local verification only. The evidence is the captured log output
    at `/tmp/lint-imports-violation.log` (or recorded in the SUMMARY).

**Part D — Final sanity gate.**

11. Run `make check` one more time from a clean tree. Must exit 0.
    Captures format + lint (ruff + lint-imports) + typecheck +
    docstrings + pytest (unit + integration + contract).

12. Run the Phase 2-specific test regression:
    ```bash
    uv run pytest tests/unit/domain/ tests/unit/application/ \
                  tests/unit/fakes/ tests/contract/ -v
    ```
    All tests pass (≥49 unit + 1 contract fake-leg + 1 contract
    skipped = ≥51 tests exercised; ≥50 pass + 1 skip).

13. Commit any final formatter polish if needed:
    `chore(02-05): apply make check fixes`
    (skip if clean).
  </action>
  <verify>
    <automated>make check && uv run lint-imports && uv run pytest tests/unit/domain/ tests/unit/application/ tests/unit/fakes/ tests/contract/ -v</automated>
  </verify>
  <acceptance_criteria>
    - `pyproject.toml` `[dependency-groups] dev` list contains the literal string `"import-linter>=2.0"` (verified by `grep "import-linter" pyproject.toml`).
    - `pyproject.toml` contains a `[tool.importlinter]` section with `root_package = "app"` and two `[[tool.importlinter.contracts]]` blocks with names `Domain must not depend on infrastructure or web` and `Application must not depend on infrastructure or web`. Verify: `grep -c "\[\[tool\.importlinter\.contracts\]\]" pyproject.toml` returns `2`.
    - `Makefile` `lint:` target contains two lines: `uv run ruff check --fix .` AND `uv run lint-imports`. Verify: `grep -A2 "^lint:" Makefile | grep -E "(ruff check|lint-imports)"` returns 2 lines.
    - `uv run lint-imports` exits 0 against the current tree.
    - `make lint` exits 0.
    - `make check` exits 0 — covers format + lint (ruff + lint-imports) + typecheck + docstrings + pytest.
    - Negative-path evidence exists (captured log of a deliberate violation making `lint-imports` exit non-zero, recorded in the SUMMARY file). Verify via SUMMARY audit at phase close.
    - Final regression `uv run pytest tests/unit/domain/ tests/unit/application/ tests/unit/fakes/ tests/contract/ -v` exits 0 with the expected counts (≥50 pass, 1 skip — the anthropic contract leg).
    - Commit exists with message matching `^feat\(02-05\): wire import-linter boundary enforcement into make lint`.
  </acceptance_criteria>
  <done>import-linter installed and wired into `make lint`. Two forbidden contracts enforce the DIP boundary. `make check` green. Phase 1 LEARNINGS open item "Phase-2 boundary lint" closed. Phase 2 SC #6 satisfied.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

The contract harness and boundary-lint gate both run inside the CI
sandbox. The `RUN_LLM_TESTS=1` path (when activated in Phase 3+)
crosses a real trust boundary — it will make a network call to
api.anthropic.com — but in Phase 2 that path is gated off by both the
env var check and the `importorskip`, so no network I/O happens in
Phase 2.

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-05-01 | Tampering | A future `AnthropicLLMProvider` ships with a malformed `generate_note_and_cards` signature that silently returns a different type (e.g., `list[dict]`) | mitigate | TEST-03 contract harness `test_generate_returns_note_and_card_list` asserts `isinstance(note, NoteDTO)` + `isinstance(cards, list)` + per-card `isinstance(c, CardDTO)`. Any shape drift breaks CI the moment Phase 3 sets `RUN_LLM_TESTS=1` in its own CI pipeline. |
| T-02-05-02 | Tampering | A future refactor adds `from app.infrastructure.*` to `app/domain/` or `app/application/` — breaks the DIP contract and leaks infrastructure types across layers | mitigate | `[tool.importlinter]` forbidden contracts fail `make lint` on any such import. The contracts check *indirect* imports too (per RESEARCH §1.1b), so a chain like `app.domain.entities → some_neutral_module → app.infrastructure.db.session` is caught. Gated in pre-commit + CI via `make check`. |
| T-02-05-03 | Spoofing | `RUN_LLM_TESTS=1` is set in CI but the test silently no-ops because `AnthropicLLMProvider` is absent — Phase 3's real-leg coverage looks green but isn't | mitigate | `pytest.importorskip` emits a clear "skipped" message naming the missing module in verbose output. Phase 3's CI can assert `1 passed` (not `1 passed, 1 skipped`) as a stronger signal that the real leg ran. This plan documents the expectation; Phase 3 inherits the harness. |
| T-02-05-04 | Denial of Service | `lint-imports` is slow and becomes a bottleneck on `make check` | accept | import-linter builds the full import graph; on Dojo's Phase 2 tree (roughly 20 Python files) this is sub-second. RESEARCH §1.1c noted `--show-timings` flag availability if perf later matters. No action needed now. |
| T-02-05-05 | Information Disclosure | `RUN_LLM_TESTS=1` + real `ANTHROPIC_API_KEY` leak into CI logs via a test failure's traceback | accept | No Phase 2 action: the env var and key are not exercised in Phase 2 (anthropic leg skipped). Phase 3's real adapter will be responsible for wrapping SDK exceptions so traceback content is sanitised — logged as a Phase 3 concern in CONTEXT and PITFALL C6. |

No high-severity threats.
</threat_model>

<verification>
Phase-level verification (run after both tasks complete):

```bash
# 1. Contract harness
uv run pytest tests/contract/test_llm_provider_contract.py -v
# Expected: "1 passed, 1 skipped".

RUN_LLM_TESTS=1 uv run pytest tests/contract/test_llm_provider_contract.py -v
# Expected: still "1 passed, 1 skipped" (adapter absent in Phase 2).

# 2. import-linter configuration visible
grep -A1 "^\[tool\.importlinter\]" pyproject.toml
grep "import-linter" pyproject.toml

# 3. Boundary enforcement
uv run lint-imports
# Expected: exit 0. "Contracts: 2. Broken: 0."

# 4. Makefile wiring
grep -A2 "^lint:" Makefile
# Expected: two lines under lint: target.

# 5. Full gate including lint-imports
make check
# Expected: exit 0, all gates green.

# 6. Phase-close regression
uv run pytest tests/unit/domain/ tests/unit/application/ \
              tests/unit/fakes/ tests/contract/ -v
# Expected: ≥50 passed, 1 skipped.

# 7. Negative-path proof (documented in SUMMARY)
# Deliberate injection + revert — evidence of a working gate.
```
</verification>

<success_criteria>
Plan 05 is complete — and therefore Phase 2 is complete — when:

1. `tests/contract/` contains `__init__.py` and
   `test_llm_provider_contract.py` (≤100 lines each).
2. `uv run pytest tests/contract/test_llm_provider_contract.py -v` exits
   0 with `1 passed, 1 skipped` regardless of whether `RUN_LLM_TESTS=1`
   is set (Phase-2 behavior — adapter module absent).
3. `pyproject.toml` dev deps includes `"import-linter>=2.0"`.
4. `pyproject.toml` contains a `[tool.importlinter]` section with
   `root_package = "app"` and two `[[tool.importlinter.contracts]]`
   blocks per CONTEXT D-12.
5. `Makefile` `lint:` target is the two-line form (ruff then
   lint-imports). `check:` target is unchanged (already calls `lint`).
6. `uv run lint-imports` exits 0 against the current tree.
7. A deliberate negative-path injection proves `lint-imports` catches
   boundary violations (logged in SUMMARY; not committed).
8. `make check` exits 0 end-to-end.
9. ROADMAP Phase 2 SC #5 satisfied (contract-test harness parameterised
   over `[FakeLLMProvider, AnthropicLLMProvider]`, gated on
   `RUN_LLM_TESTS=1`, Fake variant runs on every `make check`, Anthropic
   variant skips cleanly when env var unset or adapter absent).
10. ROADMAP Phase 2 SC #6 satisfied (`import-linter` configured; a
    violation of the DIP boundary fails `make check`).
11. Phase 1 LEARNINGS open item "Phase-2 boundary lint" is closed in
    the Phase 2 LEARNINGS.md at phase close.
12. TEST-03 requirement discharged.
</success_criteria>

<output>
After completion, create `.planning/phases/02-domain-application-spine/02-05-SUMMARY.md`
documenting:
- Files created + modified (with line counts).
- Contract-harness behavior snapshot (1 passed, 1 skipped — with env + without).
- pyproject.toml diff (dep addition + `[tool.importlinter]` append).
- Makefile diff (lint: target expansion).
- **Negative-path evidence**: the captured output of the deliberate
  violation, showing `lint-imports` exits non-zero and names the
  broken contract. Include a snippet (≤10 lines) of the log.
- `make check` end-to-end timing (informational — RESEARCH noted
  lint-imports is sub-second; actual runtime captured here).
- Confirmation that TEST-03 is discharged and the Phase-1 LEARNINGS
  open item is closed.
- Phase-2 close confirmation: DRAFT-01 + TEST-01 + TEST-03 all
  discharged; SC #1-#6 all satisfied.
</output>
