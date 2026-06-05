from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from trading_system_api.database import Base, get_session
from trading_system_api.main import create_app
from trading_system_api.models import MarketDataBar, Signal, SignalOutcome


@pytest.mark.asyncio
async def test_backfill_outcomes_uses_trading_days_and_persists_accuracy() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        signal = Signal(
            ticker="AAPL",
            exchange="NASDAQ",
            market="US",
            analysis_date=date(2026, 6, 5),
            signal="BUY",
            confidence=Decimal("0.8"),
            entry_price=Decimal("100"),
            reason="test",
            source="baseline",
            horizon_days=20,
            created_at=datetime(2026, 6, 5, 22, 0, tzinfo=timezone.utc),
        )
        session.add(signal)
        session.add(
            MarketDataBar(
                ticker="AAPL",
                exchange="NASDAQ",
                bar_date=date(2026, 6, 8),
                open=Decimal("109"),
                high=Decimal("111"),
                low=Decimal("108"),
                close=Decimal("110"),
                volume=1_000_000,
                source_provider="test",
                source_symbol="AAPL",
            )
        )
        await session.commit()

    app = create_app()
    app.dependency_overrides[get_session] = _override_session(session_factory)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        backfill = await client.post("/signals/outcomes/backfill?horizon_days=1")
        accuracy = await client.get("/signals/accuracy?ticker=AAPL&exchange=NASDAQ&window=1")

    assert backfill.status_code == 200
    assert backfill.json()["filled_count"] == 1
    assert accuracy.status_code == 200
    body = accuracy.json()
    assert body["window"] == 1
    assert body["evaluated_count"] == 1
    assert body["win_rate_pct"] == 100
    assert body["average_return_pct"] == 10
    assert body["trusted_count"] == 1

    async with session_factory() as session:
        outcomes = (await session.execute(select(SignalOutcome))).scalars().all()

    assert len(outcomes) == 1
    assert outcomes[0].target_date == date(2026, 6, 8)
    assert outcomes[0].evaluation_eligibility == "trusted"


@pytest.mark.asyncio
async def test_accuracy_excludes_backfilled_signals_by_default() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        trusted = Signal(
            ticker="AAPL",
            exchange="NASDAQ",
            market="US",
            analysis_date=date(2026, 6, 5),
            signal="BUY",
            confidence=Decimal("0.8"),
            entry_price=Decimal("100"),
            reason="trusted",
            source="baseline",
            created_at=datetime(2026, 6, 5, 22, 0, tzinfo=timezone.utc),
        )
        backfilled = Signal(
            ticker="AAPL",
            exchange="NASDAQ",
            market="US",
            analysis_date=date(2026, 3, 12),
            signal="BUY",
            confidence=Decimal("0.8"),
            entry_price=Decimal("100"),
            reason="backfilled",
            source="baseline",
            created_at=datetime(2026, 6, 5, 22, 0, tzinfo=timezone.utc),
        )
        session.add_all([trusted, backfilled])
        await session.flush()
        session.add_all(
            [
                SignalOutcome(
                    signal_id=trusted.id,
                    ticker="AAPL",
                    exchange="NASDAQ",
                    horizon_days=20,
                    target_date=date(2026, 7, 3),
                    realized_price=Decimal("110"),
                    realized_return_pct=Decimal("10"),
                    realized_outcome="win",
                    evaluation_eligibility="trusted",
                    lag_days=0,
                ),
                SignalOutcome(
                    signal_id=backfilled.id,
                    ticker="AAPL",
                    exchange="NASDAQ",
                    horizon_days=20,
                    target_date=date(2026, 4, 10),
                    realized_price=Decimal("110"),
                    realized_return_pct=Decimal("10"),
                    realized_outcome="win",
                    evaluation_eligibility="backfilled",
                    lag_days=85,
                ),
            ]
        )
        await session.commit()

    app = create_app()
    app.dependency_overrides[get_session] = _override_session(session_factory)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        default_response = await client.get("/signals/accuracy?ticker=AAPL&exchange=NASDAQ&window=20")
        included_response = await client.get(
            "/signals/accuracy?ticker=AAPL&exchange=NASDAQ&window=20&include_backfilled=true"
        )

    assert default_response.status_code == 200
    assert default_response.json()["evaluated_count"] == 1
    assert default_response.json()["backfilled_excluded_count"] == 1
    assert included_response.json()["evaluated_count"] == 2


def _override_session(session_factory):
    async def override_session():
        async with session_factory() as session:
            yield session

    return override_session
