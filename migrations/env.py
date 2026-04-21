# ABOUTME: Sync Alembic env.py.
# ABOUTME: Reads DB URL from app.settings; imports Base for autogen.
"""Sync Alembic environment wired to the Dojo pydantic-settings singleton."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.infrastructure.db.session import Base  # noqa: F401 (M9)
from app.settings import get_settings

config = context.config

# Fill the static URL in alembic.ini from pydantic-settings only when the
# caller hasn't provided one. Programmatic callers (e.g. pytest fixtures)
# that `cfg.set_main_option("sqlalchemy.url", ...)` before command.upgrade
# want their URL to win; CLI callers see the ini placeholder and fall
# through to the settings singleton (D-01 — settings is source of truth).
_ALEMBIC_INI_PLACEHOLDER = "driver://user:pass@localhost/dbname"
_current_url = config.get_main_option("sqlalchemy.url")
if not _current_url or _current_url == _ALEMBIC_INI_PLACEHOLDER:
    config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode (for --sql output)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode (the usual path)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
