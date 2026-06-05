from __future__ import annotations

import argparse
import asyncio
import inspect
import os
from collections.abc import Awaitable, Callable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from alembic import command
from alembic.config import Config


@dataclass(frozen=True)
class InitDbConfig:
    alembic_config_path: str
    database_url: str | None
    checkpoint_setup_enabled: bool
    checkpoint_data_dir: Path
    checkpoint_ticker: str


AlembicUpgrade = Callable[[str, str | None], None]
CheckpointInitializer = Callable[[Path, str], None | Awaitable[None]]


async def run_initialization(
    config: InitDbConfig,
    *,
    alembic_upgrade: AlembicUpgrade = None,
    checkpoint_initializer: CheckpointInitializer = None,
) -> dict[str, object]:
    upgrade = alembic_upgrade or upgrade_database
    await asyncio.to_thread(upgrade, config.alembic_config_path, config.database_url)

    checkpoint_status = "skipped"
    if config.checkpoint_setup_enabled:
        initializer = checkpoint_initializer or setup_langgraph_checkpointer
        result = initializer(config.checkpoint_data_dir, config.checkpoint_ticker)
        if inspect.isawaitable(result):
            await result
        checkpoint_status = "completed"

    return {
        "alembic_upgraded": True,
        "checkpoint_setup": checkpoint_status,
        "checkpoint_data_dir": str(config.checkpoint_data_dir),
    }


def upgrade_database(alembic_config_path: str, database_url: str | None) -> None:
    with _temporary_database_url(database_url):
        command.upgrade(Config(alembic_config_path), "head")


def setup_langgraph_checkpointer(data_dir: Path, ticker: str) -> None:
    from tradingagents.graph.checkpointer import get_checkpointer

    data_dir.mkdir(parents=True, exist_ok=True)
    with get_checkpointer(data_dir, ticker):
        return None


def config_from_env() -> InitDbConfig:
    return InitDbConfig(
        alembic_config_path=os.getenv("ALEMBIC_CONFIG", "apps/api/alembic.ini"),
        database_url=os.getenv("DATABASE_URL"),
        checkpoint_setup_enabled=_env_bool("TRADINGAGENTS_CHECKPOINT_SETUP_ENABLED", False),
        checkpoint_data_dir=Path(
            os.getenv("TRADINGAGENTS_CHECKPOINT_DATA_DIR", ".runtime/tradingagents")
        ),
        checkpoint_ticker=os.getenv("TRADINGAGENTS_CHECKPOINT_SETUP_TICKER", "__INIT__"),
    )


async def async_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Initialize the trading-system database.")
    parser.add_argument("--skip-checkpoint-setup", action="store_true")
    args = parser.parse_args(argv)

    config = config_from_env()
    if args.skip_checkpoint_setup:
        config = InitDbConfig(
            alembic_config_path=config.alembic_config_path,
            database_url=config.database_url,
            checkpoint_setup_enabled=False,
            checkpoint_data_dir=config.checkpoint_data_dir,
            checkpoint_ticker=config.checkpoint_ticker,
        )
    result = await run_initialization(config)
    print(result)
    return 0


def main() -> int:
    return asyncio.run(async_main())


@contextmanager
def _temporary_database_url(database_url: str | None):
    if database_url is None:
        yield
        return

    original = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
