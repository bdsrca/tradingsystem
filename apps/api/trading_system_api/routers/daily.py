from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.config import Settings, get_settings
from trading_system_api.daily_service import run_daily_analysis
from trading_system_api.database import get_session
from trading_system_api.models import DailyWorkerRun, DailyWorkerTickerResult
from trading_system_api.schemas import DailyRunRead, DailyTickerResultRead

router = APIRouter(prefix="/daily", tags=["daily"])


@router.post("/run", response_model=DailyRunRead, status_code=status.HTTP_201_CREATED)
async def run_daily_now(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> DailyRunRead:
    run = await run_daily_analysis(session, settings, triggered_by="manual")
    return await _read_run(session, run.id)


@router.get("/latest", response_model=DailyRunRead)
async def get_latest_daily_run(session: AsyncSession = Depends(get_session)) -> DailyRunRead:
    run = (
        await session.execute(
            select(DailyWorkerRun).order_by(DailyWorkerRun.created_at.desc()).limit(1)
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No daily run found")
    return await _read_run(session, run.id)


async def _read_run(session: AsyncSession, run_id: str) -> DailyRunRead:
    run = await session.get(DailyWorkerRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Daily run not found")
    items = (
        await session.execute(
            select(DailyWorkerTickerResult)
            .where(DailyWorkerTickerResult.worker_run_id == run.id)
            .order_by(DailyWorkerTickerResult.created_at.asc())
        )
    ).scalars().all()
    return DailyRunRead(
        id=run.id,
        triggered_by=run.triggered_by,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        succeeded_count=run.succeeded_count,
        failed_count=run.failed_count,
        skipped_count=run.skipped_count,
        stale_count=run.stale_count,
        degraded_count=run.degraded_count,
        email_sent=run.email_sent,
        summary=run.summary or {},
        items=[DailyTickerResultRead.model_validate(item) for item in items],
    )
