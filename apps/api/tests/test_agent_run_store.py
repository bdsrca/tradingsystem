from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from trading_system_agents.checkpoint import TradingAgentsCheckpointPointer
from trading_system_agents.report import AgentReport as AgentReportResult
from trading_system_api.agent_run_store import (
    append_agent_reports,
    mark_agent_run_completed,
    mark_agent_run_degraded,
    mark_agent_run_failed,
    mark_agent_run_running,
    persist_checkpoint_pointer,
)
from trading_system_api.database import Base
from trading_system_api.models import AgentCheckpointPointer, AgentReport, AnalysisRun


@pytest.mark.asyncio
async def test_agent_run_store_status_transitions() -> None:
    session_factory = await _session_factory()

    async with session_factory() as session:
        completed_run = AnalysisRun()
        degraded_run = AnalysisRun()
        failed_run = AnalysisRun()
        session.add_all([completed_run, degraded_run, failed_run])
        await session.commit()

        await mark_agent_run_running(session, completed_run.id, data_snapshot_id="snapshot-1")
        await mark_agent_run_completed(
            session,
            completed_run.id,
            kronos_duration_ms=45,
            llm_duration_ms=678,
        )
        await mark_agent_run_running(session, degraded_run.id)
        await mark_agent_run_degraded(session, degraded_run.id, llm_duration_ms=123)
        await mark_agent_run_running(session, failed_run.id)
        await mark_agent_run_failed(session, failed_run.id)

        completed = await session.get(AnalysisRun, completed_run.id)
        degraded = await session.get(AnalysisRun, degraded_run.id)
        failed = await session.get(AnalysisRun, failed_run.id)

    assert completed is not None
    assert completed.data_snapshot_id == "snapshot-1"
    assert completed.agent_run_status == "completed"
    assert completed.kronos_duration_ms == 45
    assert completed.llm_duration_ms == 678
    assert degraded is not None
    assert degraded.agent_run_status == "degraded"
    assert degraded.llm_duration_ms == 123
    assert failed is not None
    assert failed.agent_run_status == "failed"


@pytest.mark.asyncio
async def test_append_agent_reports_appends_retry_attempts_without_upsert() -> None:
    session_factory = await _session_factory()

    async with session_factory() as session:
        run = AnalysisRun()
        session.add(run)
        await session.commit()

        await append_agent_reports(session, [_report(run.id, "first")])
        await append_agent_reports(session, [_report(run.id, "retry")])

        rows = (
            await session.execute(
                select(AgentReport)
                .where(AgentReport.analysis_run_id == run.id)
                .order_by(AgentReport.attempt_number)
            )
        ).scalars().all()

    assert [row.content_text for row in rows] == ["first", "retry"]
    assert [row.attempt_number for row in rows] == [1, 2]
    assert [row.is_current for row in rows] == [False, True]


@pytest.mark.asyncio
async def test_persist_checkpoint_pointer_writes_pointer_metadata_only() -> None:
    session_factory = await _session_factory()

    async with session_factory() as session:
        run = AnalysisRun()
        session.add(run)
        await session.commit()

        await persist_checkpoint_pointer(
            session,
            analysis_run_id=run.id,
            pointer=TradingAgentsCheckpointPointer(
                checkpoint_db_path=Path("C:/tmp/checkpoints/AAPL.db"),
                thread_id="1234567890abcdef",
                checkpoint_ns="",
            ),
            checkpoint_skipped=True,
            skip_reason="checkpoint initialization failed: readonly",
        )

        row = (
            await session.execute(
                select(AgentCheckpointPointer).where(AgentCheckpointPointer.analysis_run_id == run.id)
            )
        ).scalar_one()

    assert row.checkpoint_db_path.endswith("AAPL.db")
    assert row.thread_id == "1234567890abcdef"
    assert row.checkpoint_ns == ""
    assert row.checkpoint_skipped is True
    assert row.skip_reason == "checkpoint initialization failed: readonly"
    assert not hasattr(row, "checkpoint_enabled")


async def _session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return session_factory


def _report(analysis_run_id: str, content: str) -> AgentReportResult:
    return AgentReportResult(
        analysis_run_id=analysis_run_id,
        role="portfolio_manager",
        stage="final",
        content_text=content,
        structured_json={"signal": "HOLD"},
        prompt_version="phase4-v1",
        model_provider="ollama",
        model_name="llama3",
        duration_ms=100,
        is_degraded=False,
    )
