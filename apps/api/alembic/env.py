from logging.config import fileConfig
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

REPO_ROOT = Path(__file__).resolve().parents[3]
for relative_path in [
    "apps/api",
    "packages/data",
    "packages/quant",
    "packages/agents",
    "packages/email",
    "workers/daily",
]:
    sys.path.insert(0, str(REPO_ROOT / relative_path))

from trading_system_api import models  # noqa: E402,F401
from trading_system_api.config import get_settings  # noqa: E402
from trading_system_api.database import Base  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _sync_database_url(database_url: str) -> str:
    return database_url.replace("+asyncpg", "").replace("+aiosqlite", "")


config.set_main_option("sqlalchemy.url", _sync_database_url(get_settings().database_url))


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
