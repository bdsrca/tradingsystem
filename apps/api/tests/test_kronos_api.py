from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from trading_system_api.database import Base, get_session
from trading_system_api.main import create_app
from trading_system_api.models import KronosForecast, MarketDataBar
from trading_system_api.routers.kronos import get_kronos_engine
from trading_system_quant.kronos.result import (
    KronosDirection,
    KronosForecastResult,
    KronosHorizonForecast,
)


class StaticKronosEngine:
    async def forecast(self, _bars, *, ticker: str, exchange: str) -> KronosForecastResult:
        return KronosForecastResult(
            ticker=ticker,
            exchange=exchange,
            analysis_date="2026-03-12",
            lookback_bars=120,
            sample_count=3,
            horizons=[
                KronosHorizonForecast(
                    horizon_days=20,
                    expected_return_pct=4.5,
                    direction=KronosDirection.BULLISH,
                    confidence=0.45,
                    forecast_close=104.5,
                    forecast_low=101.0,
                    forecast_high=104.5,
                )
            ],
            forecast_path=[
                {"time": "2026-03-13", "close": 101.0},
                {"time": "2026-03-16", "close": 104.5},
            ],
            volatility_note="amount_unavailable_zero_filled",
            model_name="NeoQuasar/Kronos-small",
            model_version="67b630e",
            runtime_ms=123,
            status="ok",
        )


@pytest.mark.asyncio
async def test_kronos_forecast_api_persists_latest_result() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await _seed_bars(session_factory)

    app = create_app()
    app.dependency_overrides[get_session] = _override_session(session_factory)
    app.dependency_overrides[get_kronos_engine] = lambda: StaticKronosEngine()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/kronos/AAPL/forecast?exchange=NASDAQ")
        assert created.status_code == 201
        body = created.json()
        assert body["status"] == "ok"
        assert body["horizons"][0]["direction"] == "bullish"

        latest = await client.get("/kronos/AAPL/latest?exchange=NASDAQ")
        assert latest.status_code == 200
        assert latest.json()["forecast_path"][1]["close"] == 104.5

    async with session_factory() as session:
        rows = (await session.execute(select(KronosForecast))).scalars().all()
        assert len(rows) == 1
        assert rows[0].model_name == "NeoQuasar/Kronos-small"


def _override_session(session_factory):
    async def override_session():
        async with session_factory() as session:
            yield session

    return override_session


async def _seed_bars(session_factory) -> None:
    start = date(2025, 11, 13)
    async with session_factory() as session:
        for index in range(120):
            close = 100 + (index * 0.1)
            session.add(
                MarketDataBar(
                    ticker="AAPL",
                    exchange="NASDAQ",
                    bar_date=start + timedelta(days=index),
                    open=close - 0.5,
                    high=close + 1,
                    low=close - 1,
                    close=close,
                    volume=1_000_000,
                    source_provider="test",
                    source_symbol="AAPL",
                    fetched_at=datetime.now(timezone.utc),
                    adjustment_mode="split_adjusted",
                )
            )
        await session.commit()
