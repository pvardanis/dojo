---
phase: 01-project-scaffold-tooling
plan: 06
type: execute
wave: 5
depends_on:
  - "01-01"
  - "01-02"
  - "01-03"
  - "01-04"
  - "01-05"
files_modified:
  - Makefile
  - .pre-commit-config.yaml
  - .github/workflows/ci.yml
autonomous: false
requirements:
  - OPS-01
  - OPS-02
  - OPS-03
  - TEST-02
tags:
  - tooling
  - make
  - pre-commit
  - github-actions
  - ci

must_haves:
  truths:
    - "`make install && make check` exits zero on a clean clone (SC #1)"
    - "`make run` starts uvicorn on localhost:8000 serving /+/health
      (SC #2)"
    - "`make migrate` applies the async Alembic migration and creates
      the `alembic_version` table (SC #3)"
    - "`make test-flakes` (new target in Phase 1) runs the 10x repeat
      of the DB smoke test and exits zero (SC #4)"
    - "`pre-commit install` is wired into `make install`; a violating
      commit is blocked by the hook chain (SC #5)"
    - "GitHub Actions CI runs `make install + make check` on push/PR
      against Python 3.12 and goes green (SC #6)"
  artifacts:
    - path: "Makefile"
      provides: "9 spec-§8.1 targets + `test-flakes` SC-#4 gate target"
      contains: "check: format lint typecheck docstrings test"
    - path: ".pre-commit-config.yaml"
      provides: "5 local hooks in D-14 order"
      contains: "repo: local"
    - path: ".github/workflows/ci.yml"
      provides: "Single-job CI, Python 3.12, uv-cached"
      contains: "astral-sh/setup-uv@v8"
  key_links:
    - from: "Makefile `install` target"
      to: "pre-commit install"
      via: "uv run pre-commit install"
      pattern: "pre-commit install"
    - from: "Makefile `check` target"
      to: "format + lint + typecheck + docstrings + test"
      via: "sequential phony deps"
      pattern: "check: format lint typecheck docstrings test"
    - from: ".github/workflows/ci.yml"
      to: "Makefile targets"
      via: "`make install` then `make check`"
      pattern: "make check"
    - from: ".pre-commit-config.yaml"
      to: "uv-run toolchain"
      via: "`uv run` in each hook entry"
      pattern: "entry: uv run"
---

<objective>
Ship the three final tooling files that glue the phase together:
`Makefile` (the 9 spec-mandated targets + a `test-flakes` gate target),
`.pre-commit-config.yaml` (5 local hooks in D-14 order), and
`.github/workflows/ci.yml` (single-job CI on Python 3.12 with uv cache).

Purpose: closes the remaining Phase 1 success criteria (SC #1, #5, #6)
and wires the entire scaffold into a reproducible developer workflow.
After this plan, a freshly-cloned Dojo repo can `make install && make
check` and be green.

Output: Running `make install` on a clean clone installs deps and
pre-commit hooks; `make check` runs the full quality gate chain;
`make run` serves the app; `make migrate` applies the async migration;
`make test-flakes` satisfies SC #4; pushing to GitHub triggers CI that
runs the same `make check` and goes green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/01-project-scaffold-tooling/01-CONTEXT.md
@.planning/phases/01-project-scaffold-tooling/01-RESEARCH.md
@.planning/phases/01-project-scaffold-tooling/01-PATTERNS.md
@.planning/phases/01-project-scaffold-tooling/01-VALIDATION.md
@.planning/phases/01-project-scaffold-tooling/01-01-SUMMARY.md
@.planning/phases/01-project-scaffold-tooling/01-02-SUMMARY.md
@.planning/phases/01-project-scaffold-tooling/01-03-SUMMARY.md
@.planning/phases/01-project-scaffold-tooling/01-04-SUMMARY.md
@.planning/phases/01-project-scaffold-tooling/01-05-SUMMARY.md
@.planning/research/PITFALLS.md
@docs/superpowers/specs/2026-04-18-dojo-design.md
@pyproject.toml
@Makefile
@.pre-commit-config.yaml

<interfaces>
<!-- External-contract endpoints established by this plan. -->

Makefile targets (spec §8.1):
```
make install      → uv sync + uv run pre-commit install
make format       → uv run ruff format .
make lint         → uv run ruff check --fix .
make typecheck    → uv run ty check app     (planning guidance 4: scope = app/ only — not migrations/)
make docstrings   → uv run interrogate -c pyproject.toml app
make test         → uv run pytest
make check        → format + lint + typecheck + docstrings + test
make run          → uv run uvicorn app.main:app --reload --port 8000
make migrate      → uv run alembic upgrade head
make test-flakes  → uv run pytest tests/integration/test_db_smoke.py --count=10  (SC #4 gate; Phase 1 addition)
```

Pre-commit hook order (D-14 / M10):
1. ruff-format
2. ruff-check --fix
3. ty (project-wide scan, `pass_filenames: false`)
4. interrogate (project-wide scan, `pass_filenames: false`)
5. pytest tests/unit/ -x --ff (unit only; Phase 1 is no-op)

CI workflow:
- `on: push: {branches: [main]}` + `on: pull_request`
- `concurrency.group + cancel-in-progress: true`
- Single job `check` on `ubuntu-latest`, Python 3.12 via setup-uv@v8
- `env: ANTHROPIC_API_KEY: ci-placeholder` (per RESEARCH.md A7)
- Steps: checkout → setup-uv → `make install` → `make check`
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write Makefile (9 spec targets + test-flakes)</name>
  <files>Makefile</files>
  <read_first>
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      1038-1072 (Makefile drop-in)
    - docs/superpowers/specs/2026-04-18-dojo-design.md §8.1 (9 required
      targets, NO db-reset)
    - .planning/phases/01-project-scaffold-tooling/01-CONTEXT.md
      (planning guidance 4: `ty check app` only, NOT `app migrations`;
      planning guidance 5: add `test-flakes` target for SC #4)
    - .planning/phases/01-project-scaffold-tooling/01-PATTERNS.md lines
      465-490 (key structural elements + anti-patterns)
    - OPS-01 requirement wording in .planning/REQUIREMENTS.md
  </read_first>
  <action>
    Write `Makefile` at repo root. Start from the drop-in at
    01-RESEARCH.md lines 1038-1072 but apply TWO planner-guidance
    adjustments:

    **Adjustment 1 (planning guidance point 4):** scope `typecheck` to
    `app/` only. The drop-in has `typecheck: uv run ty check app
    migrations` — replace with `typecheck: uv run ty check app`. Per
    RESEARCH.md Open Question #3 (A6), `ty` 0.0.31 may not handle
    Alembic's dynamic `context.configure(...)` in `migrations/env.py`;
    scoping to `app/` only avoids a known breakage path. Phase 2 can
    revisit if `ty` matures.

    **Adjustment 2 (planning guidance point 5):** add a `test-flakes`
    target as the SC #4 gate. This is a Phase 1 addition to the
    spec-§8.1 list (9 spec targets + this one = 10 total).

    Full expected Makefile content:
    ```makefile
    # ABOUTME: Dojo dev workflow. `make check` is the CI contract.
    # ABOUTME: Spec §8.1 9 targets + test-flakes (SC #4 gate).

    .PHONY: install format lint typecheck docstrings test check run \
            migrate test-flakes

    install:
    	uv sync
    	uv run pre-commit install

    format:
    	uv run ruff format .

    lint:
    	uv run ruff check --fix .

    typecheck:
    	uv run ty check app

    docstrings:
    	uv run interrogate -c pyproject.toml app

    test:
    	uv run pytest

    check: format lint typecheck docstrings test

    run:
    	uv run uvicorn app.main:app --reload --port 8000

    migrate:
    	uv run alembic upgrade head

    test-flakes:
    	uv run pytest tests/integration/test_db_smoke.py --count=10
    ```

    **Critical formatting notes:**
    - Makefiles REQUIRE literal tab characters for rule indentation
      (not spaces). Use actual tabs. If your editor inserts spaces,
      `make` will produce `*** missing separator. Stop.` errors.
    - Two `# ABOUTME:` header comment lines at the top (Makefile uses
      `#` for comments).
    - `.PHONY` declares all 10 targets — one line is fine if it fits
      79 chars (with `\` continuation as shown).
    - Each target body is ONE command. The drop-in uses `uv run ...`
      consistently (no bare `python`, `pytest`, etc.) — this
      guarantees the hook/CI/local toolchain versions match.

    **Anti-patterns (per PATTERNS.md + spec §8.1):**
    - Do NOT add a `db-reset` target. Spec §8.1 explicitly excludes
      it; `rm dojo.db && make migrate` is the manual reset path.
    - Do NOT add `venv` or `pyenv` targets — `uv sync` handles env
      creation.
    - Do NOT add shell-expansion variables for paths (`$(APP_DIR)`
      etc.). Hard-code `app`, `migrations`, etc. — Phase 1 has no
      variance to parameterize.

    **Gate-test each target (run them sequentially to catch issues):**
    ```bash
    # Dry-run parse check (all targets declared correctly)
    make -n install
    make -n format lint typecheck docstrings test check run migrate \
         test-flakes

    # Actual run — full suite
    make install
    make check
    make migrate   # creates ./dojo.db
    rm -f dojo.db  # clean up Phase 1 canary DB
    ```
    All four must exit 0. If `make check` fails because
    `tests/integration/test_home.py` needs the Plan 04 work (which
    lands before this plan), re-verify the dependency chain.
  </action>
  <verify>
    <automated>test -f Makefile &amp;&amp; grep -c '^# ABOUTME:' Makefile | grep -q '^2$' &amp;&amp; grep -qP '^\tuv sync' Makefile &amp;&amp; grep -q '^install:' Makefile &amp;&amp; grep -q '^format:' Makefile &amp;&amp; grep -q '^lint:' Makefile &amp;&amp; grep -q '^typecheck:' Makefile &amp;&amp; grep -q '^docstrings:' Makefile &amp;&amp; grep -q '^test:' Makefile &amp;&amp; grep -q '^check:' Makefile &amp;&amp; grep -q '^run:' Makefile &amp;&amp; grep -q '^migrate:' Makefile &amp;&amp; grep -q '^test-flakes:' Makefile &amp;&amp; grep -q 'check: format lint typecheck docstrings test' Makefile &amp;&amp; grep -q 'ty check app$' Makefile &amp;&amp; ! grep -q 'db-reset' Makefile &amp;&amp; make -n install &amp;&amp; make -n check &amp;&amp; make -n migrate &amp;&amp; make -n test-flakes &amp;&amp; make check &amp;&amp; make migrate &amp;&amp; rm -f dojo.db</automated>
  </verify>
  <done>
    `Makefile` exists with all 10 targets, `ty check app` (not
    `app migrations`), no `db-reset`, tab-indented rules. `make -n` on
    every target parses; `make check` and `make migrate` actually run
    successfully. Local `dojo.db` cleaned up.
  </done>
</task>

<task type="auto">
  <name>Task 2: Write .pre-commit-config.yaml (5 local hooks, D-14 order)</name>
  <files>.pre-commit-config.yaml</files>
  <read_first>
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      1087-1129 (pre-commit drop-in)
    - .planning/phases/01-project-scaffold-tooling/01-CONTEXT.md
      decision D-14 (hook order + unit-only pytest scope)
    - .planning/phases/01-project-scaffold-tooling/01-PATTERNS.md lines
      492-510 (key structural elements)
    - .planning/research/PITFALLS.md M10 (ruff/ty/interrogate hook
      ordering), New Pitfall 3 (ty beta, pin exact)
    - OPS-02 requirement wording in .planning/REQUIREMENTS.md
  </read_first>
  <action>
    Write `.pre-commit-config.yaml` at repo root. Paste drop-in from
    01-RESEARCH.md lines 1087-1129 verbatim. Key structural
    preservations (PATTERNS.md):

    1. Two-line `# ABOUTME:` header (YAML uses `#`).
    2. Single `repos:` list with ONE entry: `repo: local`. All hooks
       run via `uv run` to guarantee toolchain version alignment with
       `make check` (no version drift footgun).
    3. Five hooks in THIS EXACT order (D-14 + M10 — re-ordering
       changes the semantics):
       - **ruff-format** (`entry: uv run ruff format`, `types:
         [python]`, `pass_filenames: true`) — format must run FIRST so
         lint doesn't see unformatted code.
       - **ruff-check** (`entry: uv run ruff check --fix`, `types:
         [python]`, `pass_filenames: true`) — `--fix` autocorrects.
       - **ty** (`entry: uv run ty check`, `types: [python]`,
         `pass_filenames: false`) — `ty` scans the project itself; do
         NOT pass staged files (would override ty's own scanning per
         PATTERNS.md).
       - **interrogate** (`entry: uv run interrogate -c
         pyproject.toml`, `types: [python]`, `pass_filenames: false`)
         — same reason as ty.
       - **pytest-unit** (`entry: uv run pytest tests/unit/ -x --ff`,
         `types: [python]`, `pass_filenames: false`, `stages:
         [pre-commit]`). Per D-14, pytest in the hook runs UNIT ONLY
         — full suite is for CI. Rationale: PITFALL M10 warns full
         pytest in pre-commit degrades dev loop past ~10s.

    **Anti-patterns:**
    - Do NOT use `repo: https://github.com/astral-sh/ruff-pre-commit`
      or similar third-party hook repos — per PATTERNS.md line 501,
      `repo: local` guarantees the hook toolchain matches `uv run`
      (which matches `make check`). Any version drift between
      pre-commit's own ruff and uv's ruff becomes a debugging
      nightmare.
    - Do NOT make pre-commit run the FULL test suite (D-14: unit only
      in the hook; integration in CI).
    - Do NOT add `stages: [pre-push]` to keep pre-commit checks
      pre-commit-only (pre-push hooks slow down `git push`).

    **Installation smoke:**
    ```bash
    uv run pre-commit install
    # Creates .git/hooks/pre-commit — inspect it
    cat .git/hooks/pre-commit | head -5
    ```

    **Hook-fires-smoke (SC #5 gate — manual because it requires
    creating and reverting a broken commit):** see the manual-only
    verification in VALIDATION.md. This task does NOT automate the
    hook-fires check; Plan 06's task 4 (final CI commit) or a
    dedicated test-branch push handles it.

    **Idempotency smoke (automatic):**
    ```bash
    uv run pre-commit run --all-files
    ```
    Must exit 0 on the clean tree. Per RESEARCH.md verifier note 7,
    `--all-files` (not `pre-commit run` alone) exercises hooks against
    every file in the repo, not just staged ones.
  </action>
  <verify>
    <automated>test -f .pre-commit-config.yaml &amp;&amp; grep -c '^# ABOUTME:' .pre-commit-config.yaml | grep -q '^2$' &amp;&amp; grep -q 'repo: local' .pre-commit-config.yaml &amp;&amp; grep -q 'id: ruff-format' .pre-commit-config.yaml &amp;&amp; grep -q 'id: ruff-check' .pre-commit-config.yaml &amp;&amp; grep -q 'id: ty$' .pre-commit-config.yaml &amp;&amp; grep -q 'id: interrogate' .pre-commit-config.yaml &amp;&amp; grep -q 'id: pytest-unit' .pre-commit-config.yaml &amp;&amp; grep -q 'entry: uv run' .pre-commit-config.yaml &amp;&amp; grep -q 'pass_filenames: false' .pre-commit-config.yaml &amp;&amp; grep -q 'tests/unit/ -x --ff' .pre-commit-config.yaml &amp;&amp; uv run pre-commit install &amp;&amp; test -x .git/hooks/pre-commit &amp;&amp; uv run pre-commit run --all-files</automated>
  </verify>
  <done>
    `.pre-commit-config.yaml` exists with all five hooks in D-14 order;
    `repo: local` throughout; all `uv run`-based entries; pytest hook
    is unit-only. `pre-commit install` wires the git hook;
    `pre-commit run --all-files` exits 0 on the clean tree.
  </done>
</task>

<task type="auto">
  <name>Task 3: Write .github/workflows/ci.yml (single job, Python 3.12, uv-cached)</name>
  <files>.github/workflows/ci.yml</files>
  <read_first>
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      1154-1188 (CI drop-in)
    - .planning/phases/01-project-scaffold-tooling/01-RESEARCH.md lines
      1523 (A7 — `ANTHROPIC_API_KEY=ci-placeholder` env block)
    - .planning/phases/01-project-scaffold-tooling/01-CONTEXT.md
      decision D-19 (CI shape)
    - .planning/phases/01-project-scaffold-tooling/01-PATTERNS.md lines
      514-533 (key structural elements)
    - OPS-03 requirement wording in .planning/REQUIREMENTS.md
  </read_first>
  <action>
    Create the directory `.github/workflows/` if it does not already
    exist. Write `.github/workflows/ci.yml` by pasting the drop-in
    from 01-RESEARCH.md lines 1154-1188 verbatim, with ONE addition
    (A7 resolution):

    **Addition (A7):** add a top-level `env:` block inside the `check`
    job so `Settings()` instantiation does not fail when CI has no
    `.env` file.

    Full expected content:
    ```yaml
    # ABOUTME: CI — runs make check on push and PR against Python 3.12.
    # ABOUTME: Single job, uv-cached, cancels stale PR runs.

    name: ci

    on:
      push:
        branches: [main]
      pull_request:

    concurrency:
      group: ci-${{ github.workflow }}-${{ github.head_ref || github.run_id }}
      cancel-in-progress: true

    jobs:
      check:
        runs-on: ubuntu-latest
        timeout-minutes: 10
        env:
          # A7: Settings instantiation needs a value (pydantic-settings
          # has a dev-placeholder default, so this override is belt +
          # braces to ensure `make run`-equivalent code in tests works).
          ANTHROPIC_API_KEY: ci-placeholder
        steps:
          - uses: actions/checkout@v5

          - name: Set up uv
            uses: astral-sh/setup-uv@v8
            with:
              enable-cache: true
              python-version: "3.12"
              # setup-uv@v8 caches on **/uv.lock by default.

          - name: make install
            run: make install

          - name: make check
            run: make check
    ```

    **Structural preservations (per PATTERNS.md + D-19):**
    - Two-line `# ABOUTME:` header at top (YAML comments).
    - Triggers: `push` on `main` AND `pull_request` (D-19).
    - `concurrency.group: ci-${{ github.workflow }}-${{
      github.head_ref || github.run_id }}` + `cancel-in-progress:
      true`. On PRs, the head ref is stable across pushes so new
      commits cancel stale runs; on pushes to main the run_id fallback
      prevents unrelated main pushes from cancelling each other.
    - Single job `check` on `ubuntu-latest` with `timeout-minutes: 10`
      (prevents runaway runs).
    - `astral-sh/setup-uv@v8` with `enable-cache: true` +
      `python-version: "3.12"` — v8 auto-caches on `uv.lock`; no
      manual `actions/cache` step needed (Don't-Hand-Roll table).
    - Steps: `checkout@v5` → `setup-uv@v8` → `make install` → `make
      check`.
    - NO Playwright step (D-19 — Phase 7 adds that).

    **Anti-patterns (planner-guidance):**
    - Do NOT add `matrix.python-version: ["3.11", "3.12", "3.13"]` —
      spec pins to 3.12 only (D-19).
    - Do NOT add `actions/setup-python` — setup-uv@v8 handles Python
      installation (planning guidance + Don't-Hand-Roll).
    - Do NOT add `uses: actions/cache@v4` for uv — setup-uv@v8 caches
      automatically on `uv.lock`.
    - Do NOT add a separate `make test` step after `make check` —
      `make check` already includes `test` (OPS-01).

    **Validation on the committed file (local, not push):**
    ```bash
    # YAML well-formed
    uv run python -c "
    import yaml, sys
    with open('.github/workflows/ci.yml') as f:
        cfg = yaml.safe_load(f)
    assert 'on' in cfg or True in cfg  # PyYAML parses 'on:' key oddly
    assert 'jobs' in cfg
    assert 'check' in cfg['jobs']
    assert cfg['jobs']['check']['runs-on'] == 'ubuntu-latest'
    steps = [s.get('name') or s.get('uses') for s in cfg['jobs']['check']['steps']]
    assert any('make check' in (s or '') for s in steps)
    print('CI YAML OK:', steps)
    "
    ```
    If PyYAML is not in deps, install it in the dev group
    temporarily OR substitute a `grep`-based structure check:
    `grep -c 'make check' .github/workflows/ci.yml` ≥ 1.
  </action>
  <verify>
    <automated>test -d .github/workflows &amp;&amp; test -f .github/workflows/ci.yml &amp;&amp; grep -c '^# ABOUTME:' .github/workflows/ci.yml | grep -q '^2$' &amp;&amp; grep -q 'name: ci' .github/workflows/ci.yml &amp;&amp; grep -q 'on:' .github/workflows/ci.yml &amp;&amp; grep -q 'pull_request' .github/workflows/ci.yml &amp;&amp; grep -q 'concurrency:' .github/workflows/ci.yml &amp;&amp; grep -q 'cancel-in-progress: true' .github/workflows/ci.yml &amp;&amp; grep -q 'runs-on: ubuntu-latest' .github/workflows/ci.yml &amp;&amp; grep -q 'actions/checkout@v5' .github/workflows/ci.yml &amp;&amp; grep -q 'astral-sh/setup-uv@v8' .github/workflows/ci.yml &amp;&amp; grep -q 'python-version: "3.12"' .github/workflows/ci.yml &amp;&amp; grep -q 'ANTHROPIC_API_KEY: ci-placeholder' .github/workflows/ci.yml &amp;&amp; grep -q 'make install' .github/workflows/ci.yml &amp;&amp; grep -q 'make check' .github/workflows/ci.yml &amp;&amp; ! grep -q 'playwright' .github/workflows/ci.yml &amp;&amp; ! grep -q 'actions/setup-python' .github/workflows/ci.yml</automated>
  </verify>
  <done>
    `.github/workflows/ci.yml` exists with ABOUTME header; single
    `check` job; uses `setup-uv@v8` (not setup-python); ANTHROPIC_API_KEY
    env placeholder present; no Playwright; `make install` + `make
    check` as the two run steps. YAML grep structure passes.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 4: Human verification — CI green + pre-commit blocks violation</name>
  <what-built>
    Plans 01–05 built the scaffold + source + tests. Plan 06 tasks 1–3
    wrote the final three tooling files: `Makefile`, `.pre-commit-config.yaml`,
    `.github/workflows/ci.yml`. All automation has run and passed
    locally (including `make check`, `pre-commit run --all-files`, and
    `make test-flakes`).

    Two success criteria REQUIRE human verification per
    VALIDATION.md's manual-only table — neither can be automated
    without pushing to GitHub or making a deliberately-broken commit:

    - **SC #5:** pre-commit hook blocks a commit that violates
      ruff/ty/interrogate.
    - **SC #6:** GitHub Actions CI runs `make check` on push and goes
      green on the scaffold.
  </what-built>
  <how-to-verify>
    **Verification 1 — SC #5 (pre-commit blocks violation):**
    1. In a scratch branch (do not commit to main), create a
       deliberately-broken Python file:
       ```bash
       git checkout -b phase1/verify-precommit
       cat > /tmp/bad.py &lt;&lt; 'EOF'
       # ABOUTME: Deliberately broken for pre-commit verification.
       # ABOUTME: Delete before merge.
       import os;import sys
       x=1
       EOF
       cp /tmp/bad.py app/bad.py
       git add app/bad.py
       ```
    2. Attempt a commit: `git commit -m 'verify precommit blocks this'`.
       Expected: the commit is BLOCKED. The hook chain should fail at
       ruff-check (import-on-same-line is an F401/E401-ish violation
       when ruff has the `I` isort rule enabled) or at interrogate
       (missing docstrings on module/var). Either is a valid block.
    3. Clean up: `git restore --staged app/bad.py && rm app/bad.py &&
       git checkout main && git branch -D phase1/verify-precommit`.
    4. **Report:** paste the terminal output showing the hook failure
       and which hook(s) fired. Expected: at least one hook name
       appears in the failure output (ruff-format, ruff-check, ty,
       interrogate, or pytest-unit).

    **Verification 2 — SC #6 (CI goes green on push):**
    1. Push the Phase 1 branch to GitHub (the orchestrator will have
       committed all Phase 1 plans + files in a single commit before
       this checkpoint fires).
    2. Open the repo's GitHub Actions tab (https://github.com/&lt;you&gt;/&lt;dojo-repo&gt;/actions)
       and watch the `ci` workflow run.
    3. Expected: the single `check` job turns green within ~3-5
       minutes. First run may be slower due to cold uv cache;
       subsequent runs should cache-hit.
    4. If the job is RED, paste the failing step's log output back
       here. Common likely failures:
       - `make check` fails because `filterwarnings = ["error"]`
         tripped on a CI-only deprecation (resolution: add a targeted
         `ignore::DeprecationWarning:&lt;module&gt;` per Planning Guidance
         4).
       - Python version mismatch (setup-uv should resolve 3.12; if
         not, check `requires-python` in pyproject).
       - A test that uses `.env` fallback (CI has none; the
         `ANTHROPIC_API_KEY: ci-placeholder` env block should prevent
         this).
    5. **Report:** paste the link to the green CI run, OR the failing
       step name + last 40 lines of output.
  </how-to-verify>
  <resume-signal>
    Type "approved: SC5 &lt;hook name&gt; + SC6 &lt;CI run URL&gt;" once both
    verifications are green, OR describe the specific failure so the
    planner can revise (e.g., "SC6 failed: filterwarnings trip on
    pytest-asyncio 1.3.0 deprecation").
  </resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| developer shell → Makefile targets | user-invoked, trusted by definition |
| pre-commit hook → staged file content | hook reads staged bytes; hooks are trusted code |
| GitHub Actions runner → repo secrets | runner accesses `secrets.*` and env vars |
| CI `ANTHROPIC_API_KEY` env var | a placeholder string in clear text; no real key in CI yet |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1-CI-SECRET-01 | Information Disclosure | `ANTHROPIC_API_KEY: ci-placeholder` in `ci.yml` | accept | Phase 1 CI does NOT need a real Anthropic key (Phase 3+ adapter is not yet present; no Anthropic calls in Phase 1 tests). The `ci-placeholder` literal is not a real key and is committed to the public workflow file — explicitly safe. Phase 3+ must move to `${{ secrets.ANTHROPIC_API_KEY }}` if real calls are added to CI. |
| T-1-CI-CACHE-POISON-01 | Tampering | `setup-uv@v8` cache | mitigate | uv lock file (`uv.lock`) is committed; cache key is `uv.lock` hash. A tampered cache entry would produce different resolved bytes than `uv.lock` demands, causing `uv sync` to refetch. |
| T-1-PRECOMMIT-BYPASS-01 | Elevation of Privilege | `git commit --no-verify` | accept | Developers CAN bypass the pre-commit hook locally. Per the project CLAUDE.md, "NEVER SKIP, EVADE OR DISABLE A PRE-COMMIT HOOK" — the convention is enforced by discipline, not tooling. CI's `make check` is the eventual consistency check. |
| T-1-MAKE-SHELL-INJECTION-01 | Tampering | `Makefile` shell invocations | mitigate | All Makefile target bodies are static `uv run ...` invocations; no target consumes `$(VAR)` from env at runtime. There is no user-controlled input flowing into a Makefile shell command. |
| T-1-CI-WORKFLOW-INJECTION-01 | Elevation of Privilege | `${{ github.head_ref }}` in concurrency key | mitigate | `github.head_ref` is fixed by GitHub Actions (branch name; not user-crafted); using it in the concurrency group is a documented-safe pattern. No `${{ }}` expansion appears in `run:` bodies (which would be the real workflow-injection risk per GitHub's advisories). |
| T-1-CI-TIMEOUT-01 | Denial of Service | Runaway CI run (network hang, infinite loop) | mitigate | `timeout-minutes: 10` caps the `check` job; `concurrency.cancel-in-progress: true` cancels stale PR runs. |
| T-1-HOOK-TOOLCHAIN-DRIFT-01 | Tampering | pre-commit using a different ruff version than make check | mitigate | Per D-14 + PATTERNS.md, all hooks use `repo: local` with `uv run` — identical toolchain for hook/make/CI. `ty==0.0.31` pinned in pyproject; all three paths see the same version. |
</threat_model>

<verification>
Run after tasks 1-3 complete (task 4 is human):

```bash
# All three files present
ls -l Makefile .pre-commit-config.yaml .github/workflows/ci.yml

# SC #1 — full quality gate chain
make install &amp;&amp; make check

# SC #2 — uvicorn starts (quick subprocess smoke)
uv run uvicorn app.main:app --port 8765 &amp; PID=$!
sleep 2
curl -sS http://localhost:8765/health | grep -q '"status":"ok"'
kill $PID; wait $PID 2>/dev/null || true

# SC #3 — migration applies cleanly
rm -f dojo.db
make migrate
sqlite3 dojo.db '.schema' | grep -q 'alembic_version'
rm -f dojo.db dojo.db-journal dojo.db-wal dojo.db-shm 2>/dev/null || true

# SC #4 — flake check
make test-flakes

# SC #5 automatic portion — pre-commit idempotent on clean tree
uv run pre-commit run --all-files

# SC #6 — can only verify post-push (Task 4 checkpoint)
```
</verification>

<success_criteria>
- `Makefile` exists with 10 targets (9 spec + `test-flakes`); `ty
  check app` (planner-adjusted scope); no `db-reset`.
- `.pre-commit-config.yaml` exists with 5 hooks in D-14 order,
  `repo: local`, `uv run` throughout.
- `.github/workflows/ci.yml` exists with single job, `setup-uv@v8`,
  Python 3.12, concurrency cancel-in-progress, `ANTHROPIC_API_KEY:
  ci-placeholder` env block.
- `make install && make check` exits 0 on a clean clone (SC #1).
- `make run` (tested via uvicorn subprocess smoke) serves `/` + `/health`
  (SC #2).
- `make migrate` applies the empty initial revision and creates
  `alembic_version` (SC #3).
- `make test-flakes` passes 10/10 (SC #4).
- `pre-commit install` is wired into `make install`; `pre-commit run
  --all-files` exits 0 (SC #5 automatic portion).
- Human checkpoint confirms SC #5 block-violation and SC #6 CI green.
- **Phase 1 complete** after the checkpoint resumes approved.
</success_criteria>

<output>
After Task 4 resumes approved, create
`.planning/phases/01-project-scaffold-tooling/01-06-SUMMARY.md` per the
execute-plan template. Summary must note:
- (a) the exact `ty check app` vs `ty check app migrations` decision
  that was locked (planning guidance 4 — scope = `app/` only);
- (b) any `filterwarnings` targeted-ignore additions that surfaced in
  CI (should be zero; document if any);
- (c) the GitHub Actions run URL where CI went green (SC #6 evidence);
- (d) the pre-commit hook that blocked the deliberately-broken commit
  in Task 4's verification 1 (SC #5 evidence);
- (e) overall Phase 1 sign-off: all 8 success criteria addressable +
  green + committed.

Then create the phase-level retrospective summary
`.planning/phases/01-project-scaffold-tooling/SUMMARY.md` that stitches
together the six plan-level SUMMARYs into a Phase 1 exit artefact per
the execute-phase template.
</output>
