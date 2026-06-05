from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from trading_system_agents.config import AgentRunConfig
from trading_system_agents.llm_adapter import TradingAgentsLLMConfig
from trading_system_agents.snapshot import DataSnapshot
from trading_system_agents.tradingagents_e2e import run_tradingagents_e2e
from trading_system_agents.vendor_bridge import MissingSnapshotError, get_snapshot


def _snapshot(ticker: str = "AAPL") -> DataSnapshot:
    return DataSnapshot(
        ticker=ticker,
        exchange="NASDAQ",
        analysis_date="2026-06-05",
        display_name="Apple Inc.",
        current_price=190.0,
        indicators={"SMA_20": 188.0},
        fundamentals={"sector": "Technology"},
        news_items=[],
    )


def _llm() -> TradingAgentsLLMConfig:
    return TradingAgentsLLMConfig(
        provider="ollama",
        deep_model="qwen2.5:7b",
        quick_model="qwen2.5:7b",
        base_url="http://localhost:11434/v1",
    )


@pytest.mark.asyncio
async def test_e2e_runner_uses_persistent_checkpoint_cache_and_per_run_memory_log(
    tmp_path,
) -> None:
    checkpoint_root = tmp_path / "checkpoint-cache"
    run_root = tmp_path / "runs"

    def graph_step(config: dict[str, object]) -> dict[str, object]:
        assert config["data_cache_dir"] == str(checkpoint_root.resolve())
        assert str(config["memory_log_path"]).startswith(str((run_root / "run-1").resolve()))
        assert Path(str(config["memory_log_path"])).name == "trading_memory.md"
        assert config["data_cache_dir"] != str(Path(str(config["memory_log_path"])).parent)
        return {"final_trade_decision": "**Rating**: Buy\n\nMock PM decision."}

    result = await run_tradingagents_e2e(
        snapshot=_snapshot(),
        analysis_run_id="analysis-1",
        run_id="run-1",
        runtime_base_dir=run_root,
        checkpoint_data_dir=checkpoint_root,
        llm_config=_llm(),
        run_config=AgentRunConfig(llm_provider="ollama"),
        graph_step=graph_step,
        checkpoint_initialize=lambda _config, pointer: pointer.checkpoint_db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        ),
    )

    assert result.checkpoint_pointer is not None
    assert result.checkpoint_pointer.checkpoint_db_path.parent == (
        checkpoint_root / "checkpoints"
    ).resolve()
    assert result.runtime_dirs.run_dir == (run_root / "run-1").resolve()


@pytest.mark.asyncio
async def test_e2e_runner_sets_snapshot_inside_executor_thread(tmp_path) -> None:
    with pytest.raises(MissingSnapshotError):
        get_snapshot()

    def graph_step(_config: dict[str, object]) -> dict[str, object]:
        active_snapshot = get_snapshot()
        return {
            "market_report": f"Active ticker: {active_snapshot.ticker}",
            "final_trade_decision": "**Rating**: Hold\n\nSnapshot was available.",
        }

    with ThreadPoolExecutor(max_workers=1) as executor:
        result = await run_tradingagents_e2e(
            snapshot=_snapshot("SHOP"),
            analysis_run_id="analysis-1",
            run_id="run-1",
            runtime_base_dir=tmp_path / "runs",
            checkpoint_data_dir=tmp_path / "checkpoint-cache",
            llm_config=_llm(),
            run_config=AgentRunConfig(llm_provider="ollama"),
            graph_step=graph_step,
            executor=executor,
        )

    assert result.final_state["market_report"] == "Active ticker: SHOP"
    assert result.signal == "HOLD"
    with pytest.raises(MissingSnapshotError):
        get_snapshot()


@pytest.mark.asyncio
async def test_e2e_runner_extracts_signal_from_mock_final_decision(tmp_path) -> None:
    result = await run_tradingagents_e2e(
        snapshot=_snapshot(),
        analysis_run_id="analysis-1",
        run_id="run-1",
        runtime_base_dir=tmp_path / "runs",
        checkpoint_data_dir=tmp_path / "checkpoint-cache",
        llm_config=_llm(),
        run_config=AgentRunConfig(llm_provider="ollama"),
        graph_step=lambda _config: {
            "final_trade_decision": "**Rating**: Sell\n\nMock PM decision with a clear signal.",
        },
    )

    final_report = {report.stage: report for report in result.reports}["final"]
    assert result.signal == "SELL"
    assert final_report.structured_json["signal"] == "SELL"


@pytest.mark.asyncio
async def test_e2e_runner_degrades_when_checkpoint_initialization_fails(tmp_path) -> None:
    def fail_checkpoint(_config: dict[str, object], _pointer) -> None:
        raise PermissionError("readonly checkpoint cache")

    result = await run_tradingagents_e2e(
        snapshot=_snapshot(),
        analysis_run_id="analysis-1",
        run_id="run-1",
        runtime_base_dir=tmp_path / "runs",
        checkpoint_data_dir=tmp_path / "checkpoint-cache",
        llm_config=_llm(),
        run_config=AgentRunConfig(llm_provider="ollama"),
        graph_step=lambda _config: {"final_trade_decision": "**Rating**: Buy"},
        checkpoint_initialize=fail_checkpoint,
    )

    assert result.checkpoint_skipped is True
    assert result.checkpoint_pointer is None
    assert result.config["checkpoint_enabled"] is False
    assert "readonly checkpoint cache" in result.checkpoint_skip_reason
    assert result.signal == "BUY"
