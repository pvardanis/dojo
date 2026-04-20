# ABOUTME: App settings loaded from .env via pydantic-settings.
# ABOUTME: Single source of truth for config, including DB + API key.
"""Application settings loaded from .env via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Real environment variables take precedence over .env values
    (pydantic-settings default). Keep the surface minimal; add
    fields only when a phase needs them.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    anthropic_api_key: SecretStr = SecretStr("dev-placeholder")
    database_url: str = "sqlite+aiosqlite:///dojo.db"
    log_level: str = "INFO"
    run_llm_tests: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return the app's singleton settings (cached)."""
    return Settings()  # type: ignore[call-arg]
