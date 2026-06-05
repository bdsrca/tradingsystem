from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_agents.checkpoint import TradingAgentsCheckpointPointer
from trading_system_agents.decision_memory import DecisionMemoryLesson
from trading_system_agents.report import AgentReport as AgentReportResult
from trading_system_api.models import (
    AgentCheckpointPointer,
    AgentReport,
    AnalysisRun,
    DecisionMemory,
)


AGENT_RUN_PENDING = "pending"
AGENT_RUN_RUNNING = "running"
AGENT_RUN_COMPLETED = "completed"
AGENT_RUN_FAILED = "failed"
AGENT_RUN_DEGRADED = "degraded"

AGENT_RUN_STATUSES = frozenset(
    {
        AGENT_RUN_PENDING,
        AGENT_RUN_RUNNING,
        AGENT_RUN_COMPLETED,
        AGENT_RUN_FAILED,
        AGENT_RUN_DEGRADED,
    }
)


async def mark_agent_run_running(
    session: AsyncSession,
    analysis_run_id: str,
    *,
    data_snapshot_id: str | None = None,
) -> None:
    values: dict[str, object] = {"agent_run_status": AGENT_RUN_RUNNING}
    if data_snapshot_id is not None:
        values["data_snapshot_id"] = data_snapshot_id
    await _update_analysis_run(session, analysis_run_id, values)


async def mark_agent_run_completed(
    session: AsyncSession,
    analysis_run_id: str,
    *,
    kronos_duration_ms: int | None = None,
    llm_duration_ms: int | None = None,
) -> None:
    values = _duration_values(kronos_duration_ms, llm_duration_ms)
    values["agent_run_status"] = AGENT_RUN_COMPLETED
    await _update_analysis_run(session, analysis_run_id, values)


async def mark_agent_run_degraded(
    session: AsyncSession,
    analysis_run_id: str,
    *,
    kronos_duration_ms: int | None = None,
    llm_duration_ms: int | None = None,
) -> None:
    values = _duration_values(kronos_duration_ms, llm_duration_ms)
    values["agent_run_status"] = AGENT_RUN_DEGRADED
    await _update_analysis_run(session, analysis_run_id, values)


async def mark_agent_run_failed(session: AsyncSession, analysis_run_id: str) -> None:
    await _update_analysis_run(session, analysis_run_id, {"agent_run_status": AGENT_RUN_FAILED})


async def append_agent_reports(
    session: AsyncSession,
    reports: Sequence[AgentReportResult],
) -> list[AgentReport]:
    rows: list[AgentReport] = []
    for report in reports:
        attempt_number = await _next_attempt_number(
            session,
            analysis_run_id=report.analysis_run_id,
            stage=report.stage,
        )
        await session.execute(
            update(AgentReport)
            .where(
                AgentReport.analysis_run_id == report.analysis_run_id,
                AgentReport.stage == report.stage,
                AgentReport.is_current.is_(True),
            )
            .values(is_current=False)
        )
        row = AgentReport(
            analysis_run_id=report.analysis_run_id,
            role=report.role,
            stage=report.stage,
            content_text=report.content_text,
            structured_json=report.structured_json,
            prompt_version=report.prompt_version,
            model_provider=report.model_provider,
            model_name=report.model_name,
            duration_ms=report.duration_ms,
            is_degraded=report.is_degraded,
            attempt_number=attempt_number,
            is_current=True,
        )
        session.add(row)
        rows.append(row)

    await session.commit()
    return rows


async def persist_checkpoint_pointer(
    session: AsyncSession,
    *,
    analysis_run_id: str,
    pointer: TradingAgentsCheckpointPointer,
    checkpoint_skipped: bool = False,
    skip_reason: str | None = None,
) -> AgentCheckpointPointer:
    row = AgentCheckpointPointer(
        analysis_run_id=analysis_run_id,
        checkpoint_db_path=str(pointer.checkpoint_db_path),
        thread_id=pointer.thread_id,
        checkpoint_ns=pointer.checkpoint_ns,
        checkpoint_skipped=checkpoint_skipped,
        skip_reason=skip_reason,
    )
    session.add(row)
    await session.commit()
    return row


async def save_memory(
    session: AsyncSession,
    *,
    ticker: str,
    lesson_text: str,
    exchange: str | None = None,
    analysis_run_id: str | None = None,
    signal: str | None = None,
    decision_text: str | None = None,
    source: str = "platform",
) -> DecisionMemory:
    row = DecisionMemory(
        ticker=ticker.upper(),
        exchange=exchange,
        analysis_run_id=analysis_run_id,
        signal=signal,
        decision_text=decision_text,
        lesson_text=lesson_text,
        source=source,
        is_active=True,
    )
    session.add(row)
    await session.commit()
    return row


async def get_relevant_memories(
    session: AsyncSession,
    *,
    ticker: str,
    limit: int = 5,
) -> list[DecisionMemoryLesson]:
    rows = (
        await session.execute(
            select(DecisionMemory)
            .where(
                DecisionMemory.ticker == ticker.upper(),
                DecisionMemory.is_active.is_(True),
            )
            .order_by(DecisionMemory.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [
        DecisionMemoryLesson(
            ticker=row.ticker,
            exchange=row.exchange,
            signal=row.signal,
            decision_text=row.decision_text,
            lesson_text=row.lesson_text,
        )
        for row in rows
    ]


async def _update_analysis_run(
    session: AsyncSession,
    analysis_run_id: str,
    values: dict[str, object],
) -> None:
    run = await session.get(AnalysisRun, analysis_run_id)
    if run is None:
        return
    for key, value in values.items():
        setattr(run, key, value)
    await session.commit()


async def _next_attempt_number(
    session: AsyncSession,
    *,
    analysis_run_id: str,
    stage: str,
) -> int:
    result = await session.execute(
        select(func.max(AgentReport.attempt_number)).where(
            AgentReport.analysis_run_id == analysis_run_id,
            AgentReport.stage == stage,
        )
    )
    current = result.scalar_one_or_none()
    return int(current or 0) + 1


def _duration_values(
    kronos_duration_ms: int | None,
    llm_duration_ms: int | None,
) -> dict[str, object]:
    values: dict[str, object] = {}
    if kronos_duration_ms is not None:
        values["kronos_duration_ms"] = kronos_duration_ms
    if llm_duration_ms is not None:
        values["llm_duration_ms"] = llm_duration_ms
    return values
