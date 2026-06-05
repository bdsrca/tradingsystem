from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.database import get_session
from trading_system_api.models import Signal
from trading_system_api.outcome_service import backfill_signal_outcomes, calculate_accuracy
from trading_system_api.schemas import (
    SignalAccuracyRead,
    SignalMarkerRead,
    SignalOutcomeBackfillRead,
)

router = APIRouter(prefix="/signals", tags=["signals"])


@router.post("/outcomes/backfill", response_model=SignalOutcomeBackfillRead)
async def backfill_outcomes(
    horizon_days: int = 20,
    ticker: str | None = None,
    exchange: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> SignalOutcomeBackfillRead:
    result = await backfill_signal_outcomes(
        session,
        horizon_days=horizon_days,
        ticker=ticker,
        exchange=exchange,
    )
    return SignalOutcomeBackfillRead(
        horizon_days=result.horizon_days,
        filled_count=result.filled_count,
        skipped_count=result.skipped_count,
    )


@router.get("/accuracy", response_model=SignalAccuracyRead)
async def signal_accuracy(
    window: int = 20,
    ticker: str | None = None,
    exchange: str | None = None,
    include_backfilled: bool = False,
    session: AsyncSession = Depends(get_session),
) -> SignalAccuracyRead:
    result = await calculate_accuracy(
        session,
        window=window,
        ticker=ticker,
        exchange=exchange,
        include_backfilled=include_backfilled,
    )
    return SignalAccuracyRead(
        ticker=result.ticker,
        exchange=result.exchange,
        window=result.window,
        evaluated_count=result.evaluated_count,
        trusted_count=result.trusted_count,
        delayed_count=result.delayed_count,
        backfilled_count=result.backfilled_count,
        backfilled_excluded_count=result.backfilled_excluded_count,
        win_rate_pct=result.win_rate_pct,
        average_return_pct=result.average_return_pct,
    )


@router.get("/{ticker}/markers", response_model=list[SignalMarkerRead])
async def list_signal_markers(
    ticker: str,
    exchange: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[SignalMarkerRead]:
    statement = select(Signal).where(
        Signal.ticker == ticker.upper(),
        Signal.analysis_date.is_not(None),
        Signal.is_superseded.is_(False),
    )
    if exchange:
        statement = statement.where(Signal.exchange == exchange.upper())
    rows = (await session.execute(statement.order_by(Signal.analysis_date.asc()))).scalars().all()
    return [_marker(row) for row in rows if row.signal]


def _marker(signal: Signal) -> SignalMarkerRead:
    signal_name = str(signal.signal)
    bearish = signal_name in {"SELL", "REDUCE"}
    color = "#b42318" if bearish else "#1f7a5c"
    shape = "arrowDown" if bearish else ("arrowUp" if signal_name == "BUY" else "circle")
    return SignalMarkerRead(
        time=signal.analysis_date.isoformat(),
        signal=signal_name,
        position="aboveBar" if bearish else "belowBar",
        color=color,
        shape=shape,
        text=_marker_text(signal_name, signal),
    )


def _marker_text(signal_name: str, signal: Signal) -> str:
    text = f"{signal_name} {float(signal.confidence or 0):.2f}"
    if signal.source and "kronos" in signal.source.lower():
        return f"{text} - Kronos cross-market caveat"
    return text
