from __future__ import annotations

from pathlib import Path

import pytest

from infra.scripts.init_db import InitDbConfig, run_initialization


@pytest.mark.asyncio
async def test_init_db_runs_alembic_without_checkpoint_setup(tmp_path: Path) -> None:
    calls: list[tuple[str, str | None]] = []

    def fake_upgrade(alembic_config_path: str, database_url: str | None) -> None:
        calls.append((alembic_config_path, database_url))

    result = await run_initialization(
        InitDbConfig(
            alembic_config_path="apps/api/alembic.ini",
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'app.db'}",
            checkpoint_setup_enabled=False,
            checkpoint_data_dir=tmp_path / "checkpoints",
            checkpoint_ticker="INIT",
        ),
        alembic_upgrade=fake_upgrade,
    )

    assert calls == [("apps/api/alembic.ini", f"sqlite+aiosqlite:///{tmp_path / 'app.db'}")]
    assert result["alembic_upgraded"] is True
    assert result["checkpoint_setup"] == "skipped"


@pytest.mark.asyncio
async def test_init_db_awaits_checkpoint_setup_when_enabled(tmp_path: Path) -> None:
    checkpoint_calls: list[tuple[Path, str]] = []

    async def fake_checkpoint_initializer(data_dir: Path, ticker: str) -> None:
        checkpoint_calls.append((data_dir, ticker))

    result = await run_initialization(
        InitDbConfig(
            alembic_config_path="apps/api/alembic.ini",
            database_url=None,
            checkpoint_setup_enabled=True,
            checkpoint_data_dir=tmp_path / "tradingagents",
            checkpoint_ticker="AAPL",
        ),
        alembic_upgrade=lambda *_args: None,
        checkpoint_initializer=fake_checkpoint_initializer,
    )

    assert checkpoint_calls == [(tmp_path / "tradingagents", "AAPL")]
    assert result["checkpoint_setup"] == "completed"
