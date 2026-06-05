from __future__ import annotations

import hashlib
from pathlib import Path

from trading_system_agents.checkpoint import (
    TradingAgentsCheckpointPointer,
    build_checkpoint_pointer,
    configure_checkpoint_or_degrade,
)
from trading_system_agents.tradingagents_runtime import prepare_isolated_runtime_dirs


def test_checkpoint_pointer_matches_tradingagents_path_and_thread_id(tmp_path) -> None:
    data_cache_dir = tmp_path / "persistent-cache"

    pointer = build_checkpoint_pointer(data_cache_dir, ticker="SHOP.TO", trade_date="2026-06-05")

    assert pointer.checkpoint_db_path == (data_cache_dir / "checkpoints" / "SHOP.TO.db").resolve()
    assert pointer.thread_id == hashlib.sha256("SHOP.TO:2026-06-05".encode()).hexdigest()[:16]
    assert pointer.checkpoint_ns == ""
    assert pointer.as_dict() == {
        "checkpoint_db_path": str((data_cache_dir / "checkpoints" / "SHOP.TO.db").resolve()),
        "thread_id": pointer.thread_id,
        "checkpoint_ns": "",
    }
    assert TradingAgentsCheckpointPointer.from_dict(pointer.as_dict()) == pointer


def test_checkpoint_runtime_config_uses_persistent_cache_and_per_run_memory_log(
    tmp_path,
) -> None:
    runtime_dirs = prepare_isolated_runtime_dirs(tmp_path / "runs", run_id="aapl-20260605")
    checkpoint_cache = tmp_path / "checkpoint-cache"

    result = configure_checkpoint_or_degrade(
        runtime_dirs,
        checkpoint_data_dir=checkpoint_cache,
        ticker="AAPL",
        trade_date="2026-06-05",
        initialize=lambda _config, pointer: pointer.checkpoint_db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        ),
    )

    assert result.checkpoint_skipped is False
    assert result.pointer is not None
    assert result.config["checkpoint_enabled"] is True
    assert result.config["data_cache_dir"] == str(checkpoint_cache.resolve())
    assert result.config["results_dir"] == str(runtime_dirs.results_dir)
    assert result.config["memory_log_path"] == str(runtime_dirs.memory_log_path)
    assert Path(result.config["memory_log_path"]).parent == runtime_dirs.memory_log_path.parent
    assert result.pointer.checkpoint_db_path.parent.is_dir()


def test_checkpoint_setup_degrades_when_initialization_fails(tmp_path) -> None:
    runtime_dirs = prepare_isolated_runtime_dirs(tmp_path / "runs", run_id="aapl-20260605")

    def fail_init(_config: dict[str, object], _pointer) -> None:
        raise PermissionError("readonly checkpoint dir")

    result = configure_checkpoint_or_degrade(
        runtime_dirs,
        checkpoint_data_dir=tmp_path / "checkpoint-cache",
        ticker="AAPL",
        trade_date="2026-06-05",
        initialize=fail_init,
    )

    assert result.checkpoint_skipped is True
    assert result.pointer is None
    assert result.config["checkpoint_enabled"] is False
    assert "readonly checkpoint dir" in result.checkpoint_skip_reason
