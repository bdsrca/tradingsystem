from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_agents.hallucination_guard import validate_agent_output
from trading_system_agents.report import AgentReport
from trading_system_agents.snapshot import DataSnapshot
from trading_system_api.agent_run_store import (
    append_agent_reports,
    mark_agent_run_completed,
    mark_agent_run_degraded,
    mark_agent_run_failed,
    mark_agent_run_running,
    persist_checkpoint_pointer,
)


class AgentRunAttemptResult(Protocol):
    signal: str
    reports: list[AgentReport]
    is_degraded: bool
    degraded_reason: str | None
    checkpoint_pointer: object | None
    checkpoint_skipped: bool
    checkpoint_skip_reason: str | None


RunOnce = Callable[[int], Awaitable[AgentRunAttemptResult]]


@dataclass(frozen=True)
class AgentRunServiceResult:
    signal: str
    is_degraded: bool
    degraded_reason: str | None
    attempts: int


async def run_agent_analysis_with_retry(
    session: AsyncSession,
    *,
    analysis_run_id: str,
    snapshot: DataSnapshot,
    run_once: RunOnce,
    max_hallucination_retries: int = 1,
    data_snapshot_id: str | None = None,
) -> AgentRunServiceResult:
    await mark_agent_run_running(
        session,
        analysis_run_id,
        data_snapshot_id=data_snapshot_id,
    )
    last_result: AgentRunAttemptResult | None = None
    max_attempts = max_hallucination_retries + 1

    try:
        for attempt_number in range(1, max_attempts + 1):
            last_result = await run_once(attempt_number)
            await _persist_attempt(session, analysis_run_id=analysis_run_id, result=last_result)

            validation = validate_agent_output(_joined_report_text(last_result.reports), snapshot=snapshot)
            if not validation.is_degraded and not last_result.is_degraded:
                await mark_agent_run_completed(session, analysis_run_id)
                return AgentRunServiceResult(
                    signal=last_result.signal,
                    is_degraded=False,
                    degraded_reason=None,
                    attempts=attempt_number,
                )

            if validation.is_degraded and attempt_number < max_attempts:
                continue

            reason = _degraded_reason(getattr(last_result, "degraded_reason", None), validation)
            await mark_agent_run_degraded(session, analysis_run_id)
            return AgentRunServiceResult(
                signal=last_result.signal,
                is_degraded=True,
                degraded_reason=reason,
                attempts=attempt_number,
            )
    except Exception:
        await mark_agent_run_failed(session, analysis_run_id)
        raise

    await mark_agent_run_degraded(session, analysis_run_id)
    return AgentRunServiceResult(
        signal=last_result.signal if last_result else "HOLD",
        is_degraded=True,
        degraded_reason="agent run ended without a completed attempt",
        attempts=max_attempts,
    )


async def _persist_attempt(
    session: AsyncSession,
    *,
    analysis_run_id: str,
    result: AgentRunAttemptResult,
) -> None:
    await append_agent_reports(session, result.reports)
    if result.checkpoint_pointer is not None:
        await persist_checkpoint_pointer(
            session,
            analysis_run_id=analysis_run_id,
            pointer=result.checkpoint_pointer,
            checkpoint_skipped=result.checkpoint_skipped,
            skip_reason=result.checkpoint_skip_reason,
        )


def _joined_report_text(reports: list[AgentReport]) -> str:
    return "\n\n".join(report.content_text for report in reports)


def _degraded_reason(
    runner_reason: str | None,
    validation,
) -> str:
    warning_kinds = ",".join(warning.kind for warning in validation.warnings)
    if runner_reason and warning_kinds:
        return f"{runner_reason}; hallucination_guard={warning_kinds}"
    if runner_reason:
        return runner_reason
    if warning_kinds:
        return f"hallucination_guard={warning_kinds}"
    return "agent run degraded"
