from __future__ import annotations

import sys
from collections.abc import Callable, Mapping
from concurrent.futures import Executor
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from trading_system_agents.checkpoint import TradingAgentsCheckpointPointer
from trading_system_agents.config import AgentRunConfig
from trading_system_agents.decision_memory import DecisionMemoryLesson
from trading_system_agents.llm_adapter import TradingAgentsLLMConfig
from trading_system_agents.network_guard import block_yfinance_network
from trading_system_agents.runner import AgentRunnerTimeouts
from trading_system_agents.snapshot import DataSnapshot
from trading_system_agents.tradingagents_runtime import (
    disable_pending_entry_resolution,
    patch_resolve_instrument_identity,
)
from trading_system_agents.vendor_bridge import register_platform_vendor


@dataclass(frozen=True)
class TradingAgentsGraphInput:
    company_name: str
    trade_date: str
    asset_type: str
    selected_analysts: tuple[str, ...]
    config: dict[str, object]


@dataclass(frozen=True)
class TradingAgentsModules:
    graph_class: type
    config_module: object
    interface_module: object
    agent_utils_module: object
    graph_module: object


def build_agent_input(
    snapshot: DataSnapshot,
    *,
    config: Mapping[str, object],
    run_config: AgentRunConfig,
) -> TradingAgentsGraphInput:
    return TradingAgentsGraphInput(
        company_name=snapshot.ticker,
        trade_date=snapshot.analysis_date,
        asset_type="stock",
        selected_analysts=tuple(run_config.selected_analysts),
        config=config if isinstance(config, dict) else dict(config),
    )


def live_tradingagents_graph_step(
    *,
    snapshot: DataSnapshot,
    run_config: AgentRunConfig,
    modules: TradingAgentsModules | None = None,
    yfinance_module: object | None = None,
    debug: bool = False,
) -> Callable[[dict[str, object]], Mapping[str, Any]]:
    def graph_step(config: dict[str, object]) -> Mapping[str, Any]:
        return run_live_tradingagents_graph(
            snapshot=snapshot,
            config=config,
            run_config=run_config,
            modules=modules,
            yfinance_module=yfinance_module,
            debug=debug,
        )

    return graph_step


async def run_live_tradingagents_e2e(
    *,
    snapshot: DataSnapshot,
    analysis_run_id: str,
    run_id: str,
    runtime_base_dir: str | Path,
    checkpoint_data_dir: str | Path,
    llm_config: TradingAgentsLLMConfig,
    run_config: AgentRunConfig,
    baseline_signal: str = "HOLD",
    prompt_version: str = "phase4-v1",
    timeouts: AgentRunnerTimeouts = AgentRunnerTimeouts(),
    executor: Executor | None = None,
    checkpoint_initialize: Callable[
        [dict[str, object], TradingAgentsCheckpointPointer], None
    ]
    | None = None,
    decision_memory: list[DecisionMemoryLesson] | None = None,
    duration_ms_by_stage: Mapping[str, int] | None = None,
    modules: TradingAgentsModules | None = None,
    yfinance_module: object | None = None,
    debug: bool = False,
):
    from trading_system_agents.tradingagents_e2e import run_tradingagents_e2e

    return await run_tradingagents_e2e(
        snapshot=snapshot,
        analysis_run_id=analysis_run_id,
        run_id=run_id,
        runtime_base_dir=runtime_base_dir,
        checkpoint_data_dir=checkpoint_data_dir,
        llm_config=llm_config,
        run_config=run_config,
        graph_step=live_tradingagents_graph_step(
            snapshot=snapshot,
            run_config=run_config,
            modules=modules,
            yfinance_module=yfinance_module,
            debug=debug,
        ),
        baseline_signal=baseline_signal,
        prompt_version=prompt_version,
        timeouts=timeouts,
        executor=executor,
        checkpoint_initialize=checkpoint_initialize,
        decision_memory=decision_memory,
        duration_ms_by_stage=duration_ms_by_stage,
    )


def run_live_tradingagents_graph(
    *,
    snapshot: DataSnapshot,
    config: dict[str, object],
    run_config: AgentRunConfig,
    modules: TradingAgentsModules | None = None,
    yfinance_module: object | None = None,
    debug: bool = False,
) -> Mapping[str, Any]:
    active_modules = modules or load_tradingagents_modules()
    agent_input = build_agent_input(snapshot, config=config, run_config=run_config)
    active_yfinance = yfinance_module or _optional_yfinance_module()

    register_platform_vendor(active_modules.interface_module)
    active_modules.config_module.set_config(agent_input.config)

    with patch_resolve_instrument_identity(
        active_modules.agent_utils_module,
        snapshot,
        graph_module=active_modules.graph_module,
    ):
        with _maybe_block_yfinance(active_yfinance):
            graph = active_modules.graph_class(
                selected_analysts=list(agent_input.selected_analysts),
                debug=debug,
                config=agent_input.config,
            )
            with disable_pending_entry_resolution(graph):
                raw_result = graph.propagate(
                    agent_input.company_name,
                    agent_input.trade_date,
                    asset_type=agent_input.asset_type,
                )

    return _final_state_from_propagate_result(raw_result)


def load_tradingagents_modules(vendor_path: str | Path | None = None) -> TradingAgentsModules:
    _ensure_tradingagents_importable(vendor_path)
    graph_module = import_module("tradingagents.graph.trading_graph")
    return TradingAgentsModules(
        graph_class=getattr(graph_module, "TradingAgentsGraph"),
        config_module=import_module("tradingagents.dataflows.config"),
        interface_module=import_module("tradingagents.dataflows.interface"),
        agent_utils_module=import_module("tradingagents.agents.utils.agent_utils"),
        graph_module=graph_module,
    )


def _ensure_tradingagents_importable(vendor_path: str | Path | None) -> None:
    try:
        import_module("tradingagents")
        return
    except ModuleNotFoundError as exc:
        if exc.name != "tradingagents":
            raise

    path = Path(vendor_path).resolve() if vendor_path else _default_vendor_path()
    if path.is_dir():
        sys.path.insert(0, str(path))
    import_module("tradingagents")


def _default_vendor_path() -> Path:
    return Path(__file__).resolve().parents[3] / "vendor" / "TradingAgents"


def _optional_yfinance_module() -> object | None:
    try:
        return import_module("yfinance")
    except ModuleNotFoundError:
        return None


def _maybe_block_yfinance(yfinance_module: object | None):
    if yfinance_module is None:
        return _null_context()
    return block_yfinance_network(yfinance_module)


class _null_context:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *_exc_info: object) -> None:
        return None


def _final_state_from_propagate_result(raw_result: object) -> Mapping[str, Any]:
    if isinstance(raw_result, tuple) and raw_result:
        candidate = raw_result[0]
    else:
        candidate = raw_result
    if not isinstance(candidate, Mapping):
        raise TypeError("TradingAgentsGraph.propagate() did not return a final_state mapping")
    return candidate
