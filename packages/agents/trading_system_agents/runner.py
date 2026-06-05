from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from concurrent.futures import Executor
from dataclasses import dataclass
from enum import StrEnum
from typing import TypeVar


FinalStateT = TypeVar("FinalStateT")


class AgentStepStatus(StrEnum):
    OK = "ok"
    GRAPH_TIMEOUT = "graph_timeout"
    GRAPH_ERROR = "graph_error"
    SIGNAL_TIMEOUT = "signal_timeout"
    SIGNAL_ERROR = "signal_error"


@dataclass(frozen=True)
class AgentRunnerTimeouts:
    graph_seconds: float = 240
    signal_extract_seconds: float = 30
    total_seconds: float = 280

    def __post_init__(self) -> None:
        if self.graph_seconds <= 0:
            raise ValueError("graph_seconds must be positive")
        if self.signal_extract_seconds <= 0:
            raise ValueError("signal_extract_seconds must be positive")
        if self.total_seconds <= 0:
            raise ValueError("total_seconds must be positive")
        if self.total_seconds < self.graph_seconds + self.signal_extract_seconds:
            raise ValueError("total_seconds must cover graph_seconds plus signal_extract_seconds")


@dataclass(frozen=True)
class AgentRunnerResult:
    final_state: object | None
    signal: str
    status: AgentStepStatus
    is_degraded: bool
    degraded_reason: str | None = None


async def run_graph_and_extract_signal(
    graph_step: Callable[[], FinalStateT],
    signal_step: Callable[[FinalStateT], str],
    *,
    baseline_signal: str,
    timeouts: AgentRunnerTimeouts = AgentRunnerTimeouts(),
    executor: Executor | None = None,
) -> AgentRunnerResult:
    started = time.monotonic()
    try:
        final_state = await _run_sync_with_timeout(
            graph_step,
            timeout_seconds=timeouts.graph_seconds,
            executor=executor,
        )
    except TimeoutError:
        return AgentRunnerResult(
            final_state=None,
            signal=baseline_signal,
            status=AgentStepStatus.GRAPH_TIMEOUT,
            is_degraded=True,
            degraded_reason="agent graph timed out before producing final_state",
        )
    except Exception as exc:
        return AgentRunnerResult(
            final_state=None,
            signal=baseline_signal,
            status=AgentStepStatus.GRAPH_ERROR,
            is_degraded=True,
            degraded_reason=f"agent graph failed: {exc}",
        )

    remaining_total = timeouts.total_seconds - (time.monotonic() - started)
    signal_timeout = min(timeouts.signal_extract_seconds, remaining_total)
    if signal_timeout <= 0:
        return AgentRunnerResult(
            final_state=final_state,
            signal=baseline_signal,
            status=AgentStepStatus.SIGNAL_TIMEOUT,
            is_degraded=True,
            degraded_reason="runner timeout expired before signal extraction",
        )

    try:
        signal = await _run_sync_with_timeout(
            lambda: signal_step(final_state),
            timeout_seconds=signal_timeout,
            executor=executor,
        )
    except TimeoutError:
        return AgentRunnerResult(
            final_state=final_state,
            signal=baseline_signal,
            status=AgentStepStatus.SIGNAL_TIMEOUT,
            is_degraded=True,
            degraded_reason="signal extraction timed out after final_state was produced",
        )
    except Exception as exc:
        return AgentRunnerResult(
            final_state=final_state,
            signal=baseline_signal,
            status=AgentStepStatus.SIGNAL_ERROR,
            is_degraded=True,
            degraded_reason=f"signal extraction failed: {exc}",
        )

    return AgentRunnerResult(
        final_state=final_state,
        signal=signal,
        status=AgentStepStatus.OK,
        is_degraded=False,
    )


async def _run_sync_with_timeout(
    func: Callable[[], FinalStateT],
    *,
    timeout_seconds: float,
    executor: Executor | None,
) -> FinalStateT:
    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(executor, func)
    try:
        return await asyncio.wait_for(future, timeout=timeout_seconds)
    except asyncio.TimeoutError as exc:
        raise TimeoutError from exc
