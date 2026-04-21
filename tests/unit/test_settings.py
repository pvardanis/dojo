# ABOUTME: LLM-03 gate — ANTHROPIC_API_KEY loads via pydantic-settings.
# ABOUTME: Exercises lru_cache clear + env override semantics.
"""Settings unit tests."""

from __future__ import annotations

import pytest

from app.settings import Settings, get_settings


def test_anthropic_key_loaded_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`ANTHROPIC_API_KEY` env var takes precedence over default.

    MUST call `get_settings.cache_clear()` before `get_settings()` —
    `lru_cache` otherwise returns a previously-cached Settings and
    the monkeypatch has no effect.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.anthropic_api_key.get_secret_value() == "sk-ant-test"
    get_settings.cache_clear()


def test_defaults_are_present_when_env_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Settings instantiate with defaults when env is empty.

    `Settings(_env_file=None)` bypasses the repo's real `.env` so
    the test is deterministic across local and CI environments.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("RUN_LLM_TESTS", raising=False)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.database_url == "sqlite+aiosqlite:///dojo.db"
    assert settings.log_level == "INFO"
    assert settings.run_llm_tests is False
