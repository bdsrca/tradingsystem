from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.database import get_session
from trading_system_api.models import Signal
from trading_system_api.schemas import SignalMarkerRead

router = APIRouter(prefix="/signals", tags=["signals"])


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
        text=f"{signal_name} {float(signal.confidence or 0):.2f}",
    )
