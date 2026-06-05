from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import Executor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trading_system_agents.checkpoint import (
    CheckpointSetupResult,
    TradingAgentsCheckpointPointer,
    configure_checkpoint_or_degrade,
)
from trading_system_agents.config import AgentRunConfig
from trading_system_agents.llm_adapter import TradingAgentsLLMConfig, tradingagents_llm_environment
from trading_system_agents.output_adapter import adapt_final_state_to_reports
from trading_system_agents.report import AgentReport
from trading_system_agents.runner import (
    AgentRunnerResult,
    AgentRunnerTimeouts,
    AgentStepStatus,
    run_graph_and_extract_signal,
)
from trading_system_agents.snapshot import DataSnapshot
from trading_system_agents.tradingagents_runtime import (
    TradingAgentsRuntimeDirs,
    prepare_isolated_runtime_dirs,
)
from trading_system_agents.vendor_bridge import platform_vendor_config, run_with_snapshot


@dataclass(frozen=True)
class TradingAgentsE2EResult:
    final_state: Mapping[str, Any] | None
    signal: str
    reports: list[AgentReport]
    status: AgentStepStatus
    is_degraded: bool
    degraded_reason: str | None
    config: dict[str, object]
    runtime_dirs: TradingAgentsRuntimeDirs
    checkpoint_pointer: TradingAgentsCheckpointPointer | None
    checkpoint_skipped: bool
    checkpoint_skip_reason: str | None


async def run_tradingagents_e2e(
    *,
    snapshot: DataSnapshot,
    analysis_run_id: str,
    run_id: str,
    runtime_base_dir: str | Path,
    checkpoint_data_dir: str | Path,
    llm_config: TradingAgentsLLMConfig,
    run_config: AgentRunConfig,
    graph_step: Callable[[dict[str, object]], Mapping[str, Any]],
    baseline_signal: str = "HOLD",
    prompt_version: str = "phase4-v1",
    timeouts: AgentRunnerTimeouts = AgentRunnerTimeouts(),
    executor: Executor | None = None,
    checkpoint_initialize: Callable[
        [dict[str, object], TradingAgentsCheckpointPointer], None
    ]
    | None = None,
    duration_ms_by_stage: Mapping[str, int] | None = None,
    tradingagents_config_module: object | None = None,
) -> TradingAgentsE2EResult:
    runtime_dirs = prepare_isolated_runtime_dirs(runtime_base_dir, run_id=run_id)
    checkpoint_setup = _configure_checkpoint(
        runtime_dirs=runtime_dirs,
        checkpoint_data_dir=checkpoint_data_dir,
        snapshot=snapshot,
        llm_config=llm_config,
        run_config=run_config,
        checkpoint_initialize=checkpoint_initialize,
    )
    config = checkpoint_setup.config

    def run_graph_in_worker() -> Mapping[str, Any]:
        def invoke() -> Mapping[str, Any]:
            with tradingagents_llm_environment(llm_config):
                _set_tradingagents_global_config(tradingagents_config_module, config)
                return graph_step(config)

        return run_with_snapshot(snapshot, invoke)

    runner_result = await run_graph_and_extract_signal(
        run_graph_in_worker,
        lambda state: _extract_signal(
            state,
            analysis_run_id=analysis_run_id,
            prompt_version=prompt_version,
            model_provider=llm_config.provider,
            model_name=llm_config.quick_model,
            baseline_signal=baseline_signal,
            duration_ms_by_stage=duration_ms_by_stage,
        ),
        baseline_signal=baseline_signal,
        timeouts=timeouts,
        executor=executor,
    )
    reports = _adapt_reports(
        runner_result,
        analysis_run_id=analysis_run_id,
        prompt_version=prompt_version,
        llm_config=llm_config,
        duration_ms_by_stage=duration_ms_by_stage,
    )

    return TradingAgentsE2EResult(
        final_state=_as_mapping_or_none(runner_result.final_state),
        signal=runner_result.signal,
        reports=reports,
        status=runner_result.status,
        is_degraded=runner_result.is_degraded or checkpoint_setup.checkpoint_skipped,
        degraded_reason=runner_result.degraded_reason,
        config=config,
        runtime_dirs=runtime_dirs,
        checkpoint_pointer=checkpoint_setup.pointer,
        checkpoint_skipped=checkpoint_setup.checkpoint_skipped,
        checkpoint_skip_reason=checkpoint_setup.checkpoint_skip_reason,
    )


def _configure_checkpoint(
    *,
    runtime_dirs: TradingAgentsRuntimeDirs,
    checkpoint_data_dir: str | Path,
    snapshot: DataSnapshot,
    llm_config: TradingAgentsLLMConfig,
    run_config: AgentRunConfig,
    checkpoint_initialize: Callable[
        [dict[str, object], TradingAgentsCheckpointPointer], None
    ]
    | None,
) -> CheckpointSetupResult:
    base_config = llm_config.to_tradingagents_config(run_config)
    base_config["selected_analysts"] = run_config.selected_analysts
    base_config.update(platform_vendor_config())
    return configure_checkpoint_or_degrade(
        runtime_dirs,
        checkpoint_data_dir=checkpoint_data_dir,
        ticker=snapshot.ticker,
        trade_date=snapshot.analysis_date,
        base_config=base_config,
        initialize=checkpoint_initialize,
    )


def _extract_signal(
    final_state: Mapping[str, Any],
    *,
    analysis_run_id: str,
    prompt_version: str,
    model_provider: str,
    model_name: str,
    baseline_signal: str,
    duration_ms_by_stage: Mapping[str, int] | None,
) -> str:
    reports = adapt_final_state_to_reports(
        final_state,
        analysis_run_id=analysis_run_id,
        prompt_version=prompt_version,
        model_provider=model_provider,
        model_name=model_name,
        duration_ms_by_stage=duration_ms_by_stage,
    )
    final_report = next((report for report in reports if report.stage == "final"), None)
    if final_report is None:
        return baseline_signal
    signal = final_report.structured_json.get("signal")
    return signal if isinstance(signal, str) else baseline_signal


def _adapt_reports(
    runner_result: AgentRunnerResult,
    *,
    analysis_run_id: str,
    prompt_version: str,
    llm_config: TradingAgentsLLMConfig,
    duration_ms_by_stage: Mapping[str, int] | None,
) -> list[AgentReport]:
    final_state = _as_mapping_or_none(runner_result.final_state)
    if final_state is None:
        return []
    return adapt_final_state_to_reports(
        final_state,
        analysis_run_id=analysis_run_id,
        prompt_version=prompt_version,
        model_provider=llm_config.provider,
        model_name=llm_config.quick_model,
        duration_ms_by_stage=duration_ms_by_stage,
    )


def _as_mapping_or_none(value: object | None) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _set_tradingagents_global_config(config_module: object | None, config: dict[str, object]) -> None:
    if config_module is None:
        return
    set_config = getattr(config_module, "set_config")
    set_config(config)
