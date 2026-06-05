from __future__ import annotations

from types import SimpleNamespace

import pytest

from trading_system_agents.config import AgentRunConfig
from trading_system_agents.llm_adapter import TradingAgentsLLMConfig
from trading_system_agents.network_guard import MarketDataNetworkBlocked
from trading_system_agents.snapshot import DataSnapshot
from trading_system_agents.tradingagents_live import (
    TradingAgentsModules,
    build_agent_input,
    run_live_tradingagents_e2e,
    run_live_tradingagents_graph,
)
from trading_system_agents.vendor_bridge import get_snapshot, run_with_snapshot


def _snapshot(ticker: str = "AAPL") -> DataSnapshot:
    return DataSnapshot(
        ticker=ticker,
        exchange="NASDAQ",
        analysis_date="2026-06-05",
        display_name="Apple Inc.",
        current_price=190.0,
        indicators={"SMA_20": 188.0},
        fundamentals={"sector": "Technology"},
    )


def test_build_agent_input_anchors_to_ticker_and_v1_analyst_config() -> None:
    llm_config = TradingAgentsLLMConfig(
        provider="ollama",
        deep_model="qwen2.5:7b",
        quick_model="qwen2.5:7b",
        base_url="http://localhost:11434/v1",
    )
    run_config = AgentRunConfig(llm_provider="ollama")
    base_config = llm_config.to_tradingagents_config(run_config)

    agent_input = build_agent_input(
        _snapshot("SHOP.TO"),
        config=base_config,
        run_config=run_config,
    )

    assert agent_input.company_name == "SHOP.TO"
    assert agent_input.trade_date == "2026-06-05"
    assert agent_input.asset_type == "stock"
    assert agent_input.selected_analysts == ("market", "news", "fundamentals")
    assert agent_input.config["llm_provider"] == "ollama"
    assert "social" not in agent_input.selected_analysts


def test_live_graph_step_registers_platform_vendor_sets_config_and_runs_guards() -> None:
    snapshot = _snapshot("AAPL")
    fake_yfinance = SimpleNamespace(Ticker=lambda *_: "live-yf")
    modules = _fake_modules(fake_yfinance)
    config = {
        "llm_provider": "ollama",
        "deep_think_llm": "qwen2.5:7b",
        "quick_think_llm": "qwen2.5:7b",
        "backend_url": "http://localhost:11434/v1",
        "max_debate_rounds": 2,
        "max_risk_discuss_rounds": 2,
        "data_cache_dir": "C:/tmp/checkpoint-cache",
        "results_dir": "C:/tmp/results",
        "memory_log_path": "C:/tmp/memory/trading_memory.md",
    }

    def invoke() -> dict[str, object]:
        return run_live_tradingagents_graph(
            snapshot=snapshot,
            config=config,
            run_config=AgentRunConfig(llm_provider="ollama"),
            modules=modules,
            yfinance_module=fake_yfinance,
        )

    final_state = run_with_snapshot(snapshot, invoke)

    assert modules.config_module.seen_config is config
    assert "platform" in modules.interface_module.VENDOR_METHODS["get_stock_data"]
    assert modules.graph_class.seen_selected_analysts == ["market", "news", "fundamentals"]
    assert final_state["market_report"] == "Active ticker: AAPL"
    assert final_state["final_trade_decision"].startswith("**Rating**: Hold")


@pytest.mark.asyncio
async def test_live_e2e_graph_step_can_be_used_by_existing_runner(tmp_path) -> None:
    snapshot = _snapshot("SHOP")
    fake_yfinance = SimpleNamespace(Ticker=lambda *_: "live-yf")

    result = await run_live_tradingagents_e2e(
        snapshot=snapshot,
        analysis_run_id="analysis-1",
        run_id="run-1",
        runtime_base_dir=tmp_path / "runs",
        checkpoint_data_dir=tmp_path / "checkpoint-cache",
        llm_config=TradingAgentsLLMConfig(
            provider="ollama",
            deep_model="qwen2.5:7b",
            quick_model="qwen2.5:7b",
            base_url="http://localhost:11434/v1",
        ),
        run_config=AgentRunConfig(llm_provider="ollama"),
        modules=_fake_modules(fake_yfinance),
        yfinance_module=fake_yfinance,
    )

    assert result.signal == "HOLD"
    assert result.reports[-1].structured_json["signal"] == "HOLD"


def _fake_modules(yfinance_module: SimpleNamespace | None = None) -> TradingAgentsModules:
    class ConfigModule:
        seen_config = None

        @classmethod
        def set_config(cls, config):
            cls.seen_config = config

    class InterfaceModule:
        VENDOR_METHODS = {"get_stock_data": {}}

    def original_identity(_ticker: str):
        raise AssertionError("identity resolver should be snapshot patched")

    class AgentUtilsModule:
        resolve_instrument_identity = staticmethod(original_identity)

    class GraphModule:
        resolve_instrument_identity = staticmethod(original_identity)

    class FakeGraph:
        seen_selected_analysts = None

        def __init__(self, *, selected_analysts, debug, config):
            assert ConfigModule.seen_config is config
            assert "platform" in InterfaceModule.VENDOR_METHODS["get_stock_data"]
            self.config = config
            self.debug = debug
            self._resolve_pending_entries = self._pending_entries_should_be_disabled
            type(self).seen_selected_analysts = selected_analysts

        def _pending_entries_should_be_disabled(self, _ticker: str) -> None:
            raise AssertionError("pending memory resolution should be disabled")

        def propagate(self, company_name: str, trade_date: str, asset_type: str = "stock"):
            assert company_name == get_snapshot().ticker
            assert trade_date == get_snapshot().analysis_date
            assert asset_type == "stock"
            assert self._resolve_pending_entries(company_name) is None
            assert GraphModule.resolve_instrument_identity(company_name)["name"] == "Apple Inc."
            if yfinance_module is not None:
                with pytest.raises(MarketDataNetworkBlocked):
                    yfinance_module.Ticker(company_name)
            return (
                {
                    "market_report": f"Active ticker: {get_snapshot().ticker}",
                    "final_trade_decision": "**Rating**: Hold\n\nAnchored live graph.",
                },
                "Hold",
            )

    return TradingAgentsModules(
        graph_class=FakeGraph,
        config_module=ConfigModule,
        interface_module=InterfaceModule,
        agent_utils_module=AgentUtilsModule,
        graph_module=GraphModule,
    )
