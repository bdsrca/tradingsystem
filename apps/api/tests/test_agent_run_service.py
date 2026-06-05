from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from trading_system_agents.report import AgentReport
from trading_system_agents.snapshot import DataSnapshot
from trading_system_api.agent_run_service import run_agent_analysis_with_retry
from trading_system_api.database import Base
from trading_system_api.models import AgentReport as AgentReportRow
from trading_system_api.models import AnalysisRun


def _snapshot() -> DataSnapshot:
    return DataSnapshot(
        ticker="AAPL",
        exchange="NASDAQ",
        analysis_date="2026-06-05",
        display_name="Apple Inc.",
        current_price=100.0,
        indicators={"RSI_14": 55.0},
    )


@pytest.mark.asyncio
async def test_agent_run_service_retries_hallucinated_numeric_output_and_appends_attempts() -> None:
    session_factory = await _session_factory()
    attempts: list[int] = []

    async with session_factory() as session:
        run = AnalysisRun()
        session.add(run)
        await session.commit()

        async def run_once(attempt_number: int):
            attempts.append(attempt_number)
            decision = (
                "**Rating**: Buy\n\nUnsupported target 999."
                if attempt_number == 1
                else "**Rating**: Hold\n\nCurrent price 100."
            )
            return SimpleNamespace(
                signal="BUY" if attempt_number == 1 else "HOLD",
                reports=[_final_report(run.id, decision)],
                is_degraded=False,
                checkpoint_pointer=None,
                checkpoint_skipped=False,
                checkpoint_skip_reason=None,
            )

        result = await run_agent_analysis_with_retry(
            session,
            analysis_run_id=run.id,
            snapshot=_snapshot(),
            run_once=run_once,
            max_hallucination_retries=1,
        )

        rows = (
            await session.execute(
                select(AgentReportRow)
                .where(AgentReportRow.analysis_run_id == run.id)
                .order_by(AgentReportRow.attempt_number)
            )
        ).scalars().all()
        refreshed_run = await session.get(AnalysisRun, run.id)

    assert attempts == [1, 2]
    assert result.signal == "HOLD"
    assert [row.attempt_number for row in rows] == [1, 2]
    assert [row.is_current for row in rows] == [False, True]
    assert refreshed_run.agent_run_status == "completed"


@pytest.mark.asyncio
async def test_agent_run_service_marks_degraded_after_retry_budget_is_exhausted() -> None:
    session_factory = await _session_factory()

    async with session_factory() as session:
        run = AnalysisRun()
        session.add(run)
        await session.commit()

        async def run_once(_attempt_number: int):
            return SimpleNamespace(
                signal="BUY",
                reports=[_final_report(run.id, "**Rating**: Buy\n\nUnsupported target 999.")],
                is_degraded=False,
                checkpoint_pointer=None,
                checkpoint_skipped=False,
                checkpoint_skip_reason=None,
            )

        result = await run_agent_analysis_with_retry(
            session,
            analysis_run_id=run.id,
            snapshot=_snapshot(),
            run_once=run_once,
            max_hallucination_retries=1,
        )

        refreshed_run = await session.get(AnalysisRun, run.id)

    assert result.is_degraded is True
    assert "unsupported_number" in result.degraded_reason
    assert refreshed_run.agent_run_status == "degraded"


@pytest.mark.asyncio
async def test_agent_run_service_marks_failed_when_runner_raises() -> None:
    session_factory = await _session_factory()

    async with session_factory() as session:
        run = AnalysisRun()
        session.add(run)
        await session.commit()

        async def run_once(_attempt_number: int):
            raise RuntimeError("agent graph crashed")

        with pytest.raises(RuntimeError, match="agent graph crashed"):
            await run_agent_analysis_with_retry(
                session,
                analysis_run_id=run.id,
                snapshot=_snapshot(),
                run_once=run_once,
            )

        refreshed_run = await session.get(AnalysisRun, run.id)

    assert refreshed_run.agent_run_status == "failed"


async def _session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return session_factory


def _final_report(analysis_run_id: str, decision: str) -> AgentReport:
    return AgentReport(
        analysis_run_id=analysis_run_id,
        role="portfolio_manager",
        stage="final",
        content_text=decision,
        structured_json={"signal": "BUY"},
        prompt_version="phase4-v1",
        model_provider="ollama",
        model_name="qwen2.5:7b",
        duration_ms=100,
        is_degraded=False,
    )
