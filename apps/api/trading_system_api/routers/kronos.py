from __future__ import annotations

from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.config import Settings, get_settings
from trading_system_api.database import get_session
from trading_system_api.models import KronosForecast, MarketDataBar
from trading_system_api.schemas import KronosForecastRead
from trading_system_data.symbols import normalize_symbol
from trading_system_quant.kronos.client import KronosHttpClient
from trading_system_quant.kronos.engine import KronosEngine
from trading_system_quant.kronos.result import KronosForecastResult

router = APIRouter(prefix="/kronos", tags=["kronos"])


def get_kronos_engine(settings: Settings = Depends(get_settings)) -> KronosEngine:
    return KronosEngine(
        client=KronosHttpClient(
            settings.kronos_service_url,
            timeout_seconds=settings.kronos_timeout_seconds,
        ),
        model_name=settings.kronos_model_name,
        model_version=settings.kronos_model_version,
        sample_count=settings.kronos_sample_count,
        timeout_seconds=settings.kronos_timeout_seconds,
    )


@router.post("/{symbol}/forecast", response_model=KronosForecastRead, status_code=status.HTTP_201_CREATED)
async def create_kronos_forecast(
    symbol: str,
    exchange: str | None = None,
    session: AsyncSession = Depends(get_session),
    engine: KronosEngine = Depends(get_kronos_engine),
) -> KronosForecastRead:
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

    result = await engine.forecast(_bars_to_frame(rows), ticker=identity.ticker, exchange=identity.exchange)
    row = _model_from_result(result)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _read_from_model(row)


@router.get("/{symbol}/latest", response_model=KronosForecastRead)
async def get_latest_kronos_forecast(
    symbol: str,
    exchange: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> KronosForecastRead:
    identity = normalize_symbol(_symbol_with_optional_exchange(symbol, exchange))
    row = (
        await session.execute(
            select(KronosForecast)
            .where(
                KronosForecast.ticker == identity.ticker,
                KronosForecast.exchange == identity.exchange,
            )
            .order_by(KronosForecast.analysis_date.desc(), KronosForecast.created_at.desc())
        )
    ).scalars().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No Kronos forecast found")
    return _read_from_model(row)


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
        ],
        index=pd.to_datetime([row.bar_date for row in rows]),
    )


def _model_from_result(result: KronosForecastResult) -> KronosForecast:
    return KronosForecast(
        ticker=result.ticker,
        exchange=result.exchange,
        analysis_date=date.fromisoformat(result.analysis_date),
        status=result.status,
        model_name=result.model_name,
        model_version=result.model_version,
        lookback_bars=result.lookback_bars,
        sample_count=result.sample_count,
        runtime_ms=result.runtime_ms,
        horizons=[
            {
                "horizon_days": item.horizon_days,
                "expected_return_pct": item.expected_return_pct,
                "direction": item.direction.value,
                "confidence": item.confidence,
                "forecast_close": item.forecast_close,
                "forecast_low": item.forecast_low,
                "forecast_high": item.forecast_high,
            }
            for item in result.horizons
        ],
        forecast_path=result.forecast_path,
        volatility_note=result.volatility_note,
        error_message=result.error_message,
        is_fallback=result.is_fallback,
    )


def _read_from_model(row: KronosForecast) -> KronosForecastRead:
    return KronosForecastRead(
        id=row.id,
        ticker=row.ticker,
        exchange=row.exchange,
        analysis_date=row.analysis_date.isoformat(),
        lookback_bars=row.lookback_bars,
        sample_count=row.sample_count,
        horizons=row.horizons,
        forecast_path=row.forecast_path,
        volatility_note=row.volatility_note,
        model_name=row.model_name,
        model_version=row.model_version,
        runtime_ms=row.runtime_ms,
        status=row.status,
        is_fallback=row.is_fallback,
        error_message=row.error_message,
    )


def _symbol_with_optional_exchange(symbol: str, exchange: str | None) -> str:
    if exchange and ":" not in symbol and "." not in symbol:
        return f"{symbol}:{exchange}"
    return symbol
