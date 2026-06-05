from __future__ import annotations

import time

import pytest

from trading_system_agents.runner import (
    AgentRunnerTimeouts,
    AgentStepStatus,
    run_graph_and_extract_signal,
)


@pytest.mark.asyncio
async def test_runner_keeps_final_state_when_signal_extraction_times_out() -> None:
    final_state = {"final_trade_decision": "**Rating**: Buy", "market_report": "anchored"}

    def graph_step() -> dict[str, str]:
        return final_state

    def signal_step(_state: dict[str, str]) -> str:
        time.sleep(0.05)
        return "BUY"

    result = await run_graph_and_extract_signal(
        graph_step,
        signal_step,
        baseline_signal="HOLD",
        timeouts=AgentRunnerTimeouts(
            graph_seconds=0.5,
            signal_extract_seconds=0.01,
            total_seconds=0.6,
        ),
    )

    assert result.status == AgentStepStatus.SIGNAL_TIMEOUT
    assert result.final_state == final_state
    assert result.signal == "HOLD"
    assert result.is_degraded is True


@pytest.mark.asyncio
async def test_runner_graph_timeout_has_no_final_state() -> None:
    def graph_step() -> dict[str, str]:
        time.sleep(0.05)
        return {"final_trade_decision": "**Rating**: Buy"}

    def signal_step(_state: dict[str, str]) -> str:
        return "BUY"

    result = await run_graph_and_extract_signal(
        graph_step,
        signal_step,
        baseline_signal="HOLD",
        timeouts=AgentRunnerTimeouts(
            graph_seconds=0.01,
            signal_extract_seconds=0.5,
            total_seconds=0.6,
        ),
    )

    assert result.status == AgentStepStatus.GRAPH_TIMEOUT
    assert result.final_state is None
    assert result.signal == "HOLD"
    assert result.is_degraded is True


@pytest.mark.asyncio
async def test_runner_success_returns_signal_and_final_state() -> None:
    final_state = {"final_trade_decision": "**Rating**: Sell"}

    result = await run_graph_and_extract_signal(
        lambda: final_state,
        lambda state: state["final_trade_decision"],
        baseline_signal="HOLD",
        timeouts=AgentRunnerTimeouts(
            graph_seconds=0.5,
            signal_extract_seconds=0.5,
            total_seconds=1.1,
        ),
    )

    assert result.status == AgentStepStatus.OK
    assert result.final_state == final_state
    assert result.signal == "**Rating**: Sell"
    assert result.is_degraded is False
