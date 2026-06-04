from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.database import get_session
from trading_system_api.models import AnalysisRun, MarketDataBar, WatchlistItem
from trading_system_api.schemas import SignalRead
from trading_system_data.symbols import normalize_symbol
from trading_system_quant.baseline import generate_baseline_signal
from trading_system_quant.signal_store import SignalCreate, append_signal

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/{symbol}/baseline", response_model=SignalRead, status_code=status.HTTP_201_CREATED)
async def create_baseline_signal(
    symbol: str,
    exchange: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> SignalRead:
    identity = normalize_symbol(_symbol_with_optional_exchange(symbol, exchange))
    rows = (
        await session.execute(
            select(MarketDataBar)
            .where(
                MarketDataBar.ticker == identity.ticker,
                MarketDataBar.exchange == identity.exchange,
            )
            .order_by(MarketDataBar.bar_date.asc())
        )
    ).scalars().all()
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No OHLCV bars found")

    watchlist_item = (
        await session.execute(
            select(WatchlistItem).where(
                WatchlistItem.ticker == identity.ticker,
                WatchlistItem.exchange == identity.exchange,
            )
        )
    ).scalar_one_or_none()
    run = AnalysisRun(
        watchlist_item_id=watchlist_item.id if watchlist_item else None,
        status="completed",
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    result = generate_baseline_signal(_bars_to_frame(rows))
    signal = await append_signal(
        session,
        SignalCreate(
            watchlist_item_id=watchlist_item.id if watchlist_item else None,
            analysis_run_id=run.id,
            ticker=identity.ticker,
            exchange=identity.exchange,
            market=identity.market,
            analysis_date=rows[-1].bar_date,
            signal=result.signal,
            confidence=result.confidence,
            entry_price=result.entry_price,
            risk_level=result.risk_level,
            reason=result.reason,
            indicators=result.indicators,
            layer_scores=result.layer_scores,
            source="baseline",
        ),
    )
    return _signal_read(signal)


def _bars_to_frame(rows: list[MarketDataBar]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": float(row.volume or 0),
            }
            for row in rows
        ]
    )


def _signal_read(signal) -> SignalRead:
    return SignalRead(
        id=signal.id,
        ticker=signal.ticker,
        exchange=signal.exchange,
        market=signal.market,
        analysis_date=signal.analysis_date,
        signal=signal.signal,
        confidence=float(signal.confidence),
        entry_price=float(signal.entry_price) if signal.entry_price is not None else None,
        risk_level=float(signal.risk_level) if signal.risk_level is not None else None,
        reason=signal.reason,
        indicators=signal.indicators or {},
        layer_scores=signal.layer_scores or {},
        source=signal.source,
        horizon_days=signal.horizon_days,
    )


def _symbol_with_optional_exchange(symbol: str, exchange: str | None) -> str:
    if exchange and ":" not in symbol and "." not in symbol:
        return f"{symbol}:{exchange}"
    return symbol
