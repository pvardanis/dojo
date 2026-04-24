---
phase: 3
slug: infrastructure-adapters
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-24
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (+ pytest-asyncio, respx, pytest-repeat) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/unit tests/contract -x -q` |
| **Full suite command** | `make check` (format + lint + typecheck + docstrings + pytest) |
| **Estimated runtime** | ~30 seconds (unit + contract); ~60 seconds (`make check`) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/unit tests/contract -x -q`
- **After every plan wave:** Run `make check`
- **Before `/gsd-verify-work`:** `make check` must be green, including all Phase 3 integration tests
- **Max feedback latency:** 30 seconds (quick), 60 seconds (full)

---

## Per-Task Verification Map

> Filled in by the planner per plan. Each Phase 3 task produces at least one automated assertion. The harness below is seeded from RESEARCH.md's Validation Architecture dimensions; the planner MUST map each task to one of these rows or declare an additional row.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 3-01-XX | 01 | 1 | GEN-02, LLM-01, LLM-02, PERSIST-02 | — | Runtime deps installed (anthropic, tenacity, trafilatura, httpx promoted); exceptions module exists | unit | `uv run python -c "import anthropic, tenacity, trafilatura, httpx"` | ❌ W0 | ⬜ pending |
| 3-02-XX | 02 | 1 | PERSIST-02 | — | ORM row classes + mappers round-trip; Alembic migration creates 4 tables | integration | `uv run pytest tests/integration/test_migrations.py tests/unit/test_mappers.py -x` | ❌ W0 | ⬜ pending |
| 3-03-XX | 03 | 2 | PERSIST-02 | — | Each Sql*Repository passes Phase 2 contract harness (real leg) + atomic 3-insert rollback + regenerate overwrites Note, appends Cards | contract + integration | `uv run pytest tests/contract/test_*_repository_contract.py tests/integration/test_atomic_save.py tests/integration/test_regenerate.py -x` | ❌ W0 | ⬜ pending |
| 3-04-XX | 04 | 2 | LLM-01, LLM-02 | — | AnthropicLLMProvider: Pydantic DTO validation, 1 semantic retry, tenacity retry count == 1 on 429→200, SDK exceptions wrapped | contract + integration | `RUN_LLM_TESTS=0 uv run pytest tests/contract/test_llm_provider_contract.py tests/integration/test_anthropic_provider.py -x` | ❌ W0 | ⬜ pending |
| 3-05-XX | 05 | 3 | GEN-02 | — | InMemoryDraftStore TTL + concurrent-pop race; read_file UTF-8 strict + PermissionError wrap; fetch_url paywall + length + non-2xx heuristics | contract + integration | `uv run pytest tests/contract/test_draft_store_contract.py tests/contract/test_source_reader_contract.py tests/contract/test_url_fetcher_contract.py -x --count=10` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Validation Dimensions (from RESEARCH.md §Validation Architecture)

Each dimension below MUST have at least one automated assertion somewhere in the phase's plans.

| # | Dimension | Evidence Required | Test File (planner assigns) |
|---|-----------|-------------------|------------------------------|
| 1 | Port-contract conformance (7 ports × fake + real legs) | Each `tests/contract/test_{port}_contract.py` passes on both `fake` and `real` params; LLM real leg is env-gated via `RUN_LLM_TESTS=1` | `tests/contract/*.py` |
| 2 | Atomic-transaction rollback (SC #2) | Force 3rd insert to raise inside `with session.begin()`; assert 0 rows in `sources`, `notes`, `cards` tables | `tests/integration/test_sql_repositories_atomic.py` |
| 3 | Retry-count correctness (SC #4) | `respx` stub returns 429 then 200; assert exactly 2 HTTP calls; with 401, assert 1 HTTP call (whitelist check) | `tests/integration/test_anthropic_retry_count.py` |
| 4 | Tool-use DTO schema match (SC #3) | Valid tool-use response → returns `NoteDTO` + `list[CardDTO]`; malformed → `LLMOutputMalformed` raised after one semantic retry | `tests/integration/test_anthropic_provider.py` |
| 5 | TTL fake-clock coverage (SC #5) | Inject list-captured clock; TTL eviction triggers lazy on `pop`; assert entry is None post-expiry | `tests/integration/test_draft_store_concurrency.py` |
| 6 | Concurrent-pop race (SC #5) | Two asyncio coroutines race on same token; `asyncio.gather` confirms exactly one non-None return; `--count=10` reinforces (CPython 3.12 GIL observability) | `tests/integration/test_draft_store_concurrency.py` |
| 7 | URL-fetch paywall + length heuristics (SC #6) | `respx` stubs: <1000 char → `SourceNotArticle`; paywall markers → `SourceNotArticle`; 503 → `SourceFetchFailed`; timeout → `SourceFetchFailed` | `tests/integration/test_url_fetcher.py` |
| 8 | File-read UTF-8 strictness | tmp file with invalid UTF-8 bytes → `SourceUnreadable`; missing path → `SourceNotFound`; chmod-0 path → `SourceUnreadable` | `tests/integration/test_file_reader.py` |
| 9 | Alembic round-trip (M9 mitigation) | `alembic upgrade head` then `downgrade base` then `upgrade head` succeeds; `Base.metadata.tables` contains all 4 expected tables after import | `tests/integration/test_migrations.py` |
| 10 | Regenerate semantics (SC #7) | Existing Source with Note + 3 Cards → regenerate → Note row overwritten, 3 new Card rows appended (6 total), original 3 Cards untouched | `tests/integration/test_sql_repositories_regenerate.py` |
| 11 | Composition-root factory wiring | `app/main.py` exposes factory functions returning wired `GenerateFromSource` with real adapters (`AnthropicLLMProvider`, `Sql*Repository`, `InMemoryDraftStore`, real file/URL readers); unit-testable by inspecting returned type and attribute graph without running server. Env-switch for fake adapters deferred to Phase 7 (E2E). | `tests/unit/test_composition_root.py` |

---

## Wave 0 Requirements

- [ ] `tests/contract/test_source_repository_contract.py` — stubs for PERSIST-02 (Wave 0 scaffolds fail-import stubs)
- [ ] `tests/contract/test_note_repository_contract.py` — stubs for PERSIST-02
- [ ] `tests/contract/test_card_repository_contract.py` — stubs for PERSIST-02
- [ ] `tests/contract/test_card_review_repository_contract.py` — stubs for PERSIST-02
- [ ] `tests/contract/test_draft_store_contract.py` — stubs for GEN-02
- [ ] `tests/contract/test_source_reader_contract.py` — stubs for GEN-02
- [ ] `tests/contract/test_url_fetcher_contract.py` — stubs for GEN-02
- [ ] `tests/integration/test_atomic_save.py` — SC #2 stub
- [ ] `tests/integration/test_regenerate.py` — SC #7 stub
- [ ] `tests/integration/test_migrations.py` — SC alembic round-trip stub
- [ ] `tests/integration/test_anthropic_provider.py` — SC #3, #4 stubs (env-gated real leg)
- [ ] `tests/integration/test_url_fetcher.py` — SC #6 stubs
- [ ] `tests/integration/test_file_reader.py` — file-reader stubs
- [ ] `tests/unit/test_mappers.py` — pure-function mapper tests (PERSIST-02)
- [ ] `tests/unit/test_composition_root.py` — composition-root swap smoke test

*Framework already installed (pytest, pytest-asyncio, respx from Phase 1).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real Anthropic round-trip | LLM-01 | Costs money; opt-in via `RUN_LLM_TESTS=1`; not in CI gate | `RUN_LLM_TESTS=1 uv run pytest tests/contract/test_llm_provider_contract.py -k real -x` |
| Trafilatura extraction quality on real articles | GEN-02 | Heuristic thresholds (D-05) are directional; need human review on 3-5 real URLs (one paywalled, one SPA, one clean article) | Documented in plan SUMMARY as deferred follow-up; not blocking for phase close |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s (full `make check`)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
