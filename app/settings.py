# ABOUTME: App settings loaded from .env via pydantic-settings.
# ABOUTME: Single source of truth for config, including DB + API key.
"""Application settings loaded from .env via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
_SUPPORTED_DB_SCHEMES = (
    "sqlite://",
    "postgresql://",
    "postgresql+psycopg2://",
    "postgresql+psycopg://",
)


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
    database_url: str = "sqlite:///dojo.db"
    log_level: LogLevel = "INFO"
    run_llm_tests: bool = False

    @field_validator("database_url")
    @classmethod
    def _require_supported_scheme(cls, v: str) -> str:
        """Reject DB URLs for drivers we don't ship support for."""
        if not v.startswith(_SUPPORTED_DB_SCHEMES):
            raise ValueError(
                f"database_url must use a supported scheme "
                f"{_SUPPORTED_DB_SCHEMES}; got {v!r}"
            )
        return v


@lru_cache
def get_settings() -> Settings:
    """Return the app's singleton settings (cached).

    :returns: The process-wide `Settings` instance loaded from
        environment variables + `.env` on first call; subsequent
        calls return the cached instance.
    """
    # pydantic-settings loads fields from env/.env at call time; the
    # type checker can't see those sources, hence the ignore.
    return Settings()  # type: ignore[call-arg]  # pydantic-settings stubs gap
