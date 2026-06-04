from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from trading_system_api.database import Base, get_session
from trading_system_api.main import create_app
from trading_system_api.models import MarketDataBar, PaperPortfolioSnapshot, PaperSimulationRun, Signal


@pytest.mark.asyncio
async def test_manual_baseline_analysis_creates_signal_and_marker() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await _seed_bars(session_factory, "AAPL", "NASDAQ")

    app = create_app()
    app.dependency_overrides[get_session] = _override_session(session_factory)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/analysis/AAPL/baseline?exchange=NASDAQ")
        assert created.status_code == 201
        body = created.json()
        assert body["ticker"] == "AAPL"
        assert body["exchange"] == "NASDAQ"
        assert body["source"] == "baseline"
        assert body["signal"] in {"BUY", "WATCH", "HOLD", "REDUCE", "SELL"}

        markers = await client.get("/signals/AAPL/markers?exchange=NASDAQ")
        assert markers.status_code == 200
        assert markers.json()[0]["time"] == body["analysis_date"]

    async with session_factory() as session:
        rows = (await session.execute(select(Signal))).scalars().all()
        assert len(rows) == 1
        assert rows[0].indicators


@pytest.mark.asyncio
async def test_paper_run_uses_frozen_signal_snapshot() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await _seed_bars(session_factory, "AAPL", "NASDAQ")
    await _seed_signal(session_factory, "s-fixed", "AAPL", "NASDAQ", date(2026, 1, 2))

    app = create_app()
    app.dependency_overrides[get_session] = _override_session(session_factory)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/paper/AAPL/run?exchange=NASDAQ&window_years=1")
        assert response.status_code == 201
        body = response.json()
        assert body["metrics"]["trade_count"] >= 0
        assert body["snapshots"]
        assert body["signal_snapshot"]["signal_ids"] == ["s-fixed"]

        latest = await client.get("/paper/AAPL/latest?exchange=NASDAQ&window_years=1")
        assert latest.status_code == 200
        assert latest.json()["id"] == body["id"]

    async with session_factory() as session:
        runs = (await session.execute(select(PaperSimulationRun))).scalars().all()
        snapshots = (await session.execute(select(PaperPortfolioSnapshot))).scalars().all()
        assert len(runs) == 1
        assert runs[0].signal_snapshot["signal_ids"] == ["s-fixed"]
        assert snapshots[0].benchmark_value is None


def _override_session(session_factory):
    async def override_session():
        async with session_factory() as session:
            yield session

    return override_session


async def _seed_bars(session_factory, ticker: str, exchange: str) -> None:
    start = date(2026, 1, 2)
    async with session_factory() as session:
        for index in range(70):
            close = 100 + index
            session.add(
                MarketDataBar(
                    ticker=ticker,
                    exchange=exchange,
                    bar_date=start + timedelta(days=index),
                    open=close - 0.5,
                    high=close + 1,
                    low=close - 1,
                    close=close,
                    volume=1_000_000 + (index * 10_000),
                    source_provider="test",
                    source_symbol=ticker,
                    fetched_at=datetime.now(timezone.utc),
                    adjustment_mode="split_adjusted",
                )
            )
        await session.commit()


async def _seed_signal(
    session_factory,
    signal_id: str,
    ticker: str,
    exchange: str,
    analysis_date: date,
) -> None:
    async with session_factory() as session:
        session.add(
            Signal(
                id=signal_id,
                ticker=ticker,
                exchange=exchange,
                market="US",
                analysis_date=analysis_date,
                signal="BUY",
                confidence=0.8,
                entry_price=100,
                risk_level=95,
                reason="baseline",
                indicators={},
                layer_scores={},
                source="baseline",
                horizon_days=20,
                is_superseded=False,
            )
        )
        await session.commit()
