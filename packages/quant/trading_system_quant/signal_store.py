from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.models import Signal


@dataclass(frozen=True)
class SignalCreate:
    ticker: str
    exchange: str
    market: str
    analysis_date: date
    signal: str
    confidence: float
    entry_price: float | None
    risk_level: float | None
    reason: str
    indicators: dict[str, float] = field(default_factory=dict)
    layer_scores: dict[str, float] = field(default_factory=dict)
    source: str = "baseline"
    horizon_days: int = 20
    watchlist_item_id: str | None = None
    analysis_run_id: str | None = None
    disagreement_level: str | None = None
    supersedes_signal_id: str | None = None


async def append_signal(session: AsyncSession, signal: SignalCreate) -> Signal:
    row = Signal(
        watchlist_item_id=signal.watchlist_item_id,
        analysis_run_id=signal.analysis_run_id,
        ticker=signal.ticker,
        exchange=signal.exchange,
        market=signal.market,
        analysis_date=signal.analysis_date,
        signal=signal.signal,
        confidence=signal.confidence,
        entry_price=signal.entry_price,
        risk_level=signal.risk_level,
        reason=signal.reason,
        indicators=signal.indicators,
        layer_scores=signal.layer_scores,
        source=signal.source,
        horizon_days=signal.horizon_days,
        disagreement_level=signal.disagreement_level,
        supersedes_signal_id=signal.supersedes_signal_id,
        is_superseded=False,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row
