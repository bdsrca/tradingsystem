from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from trading_system_api.dashboard_cache import clear_dashboard_summary_cache
from trading_system_api.database import Base, get_session
from trading_system_api.main import create_app
from trading_system_api.models import (
    DailyWorkerRun,
    DailyWorkerTickerResult,
    Signal,
    SignalOutcome,
    WatchlistItem,
)


@pytest.mark.anyio
async def test_dashboard_summary_orders_attention_and_reports_cache() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as session:
        watch = WatchlistItem(
            ticker="AAPL",
            exchange="NASDAQ",
            market="US",
            provider_symbol="AAPL",
            display_name="Apple",
        )
        stale_watch = WatchlistItem(
            ticker="WELL",
            exchange="TSX",
            market="CA",
            provider_symbol="WELL:TSX",
            display_name="WELL Health",
        )
        run = DailyWorkerRun(triggered_by="manual", status="completed")
        session.add_all([watch, stale_watch, run])
        await session.flush()
        session.add_all(
            [
                DailyWorkerTickerResult(
                    worker_run_id=run.id,
                    watchlist_item_id=watch.id,
                    ticker="AAPL",
                    exchange="NASDAQ",
                    market="US",
                    status="failed",
                    data_freshness="no_data",
                    signal=None,
                    confidence=None,
                    error_message="provider returned no bars",
                ),
                DailyWorkerTickerResult(
                    worker_run_id=run.id,
                    watchlist_item_id=stale_watch.id,
                    ticker="WELL",
                    exchange="TSX",
                    market="CA",
                    status="degraded",
                    data_freshness="stale_used",
                    signal="BUY",
                    confidence=0.68,
                    error_message="used cached bars",
                ),
            ]
        )
        await session.commit()

    app = create_app()

    async def override_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    clear_dashboard_summary_cache()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.get("/dashboard/summary?max_age_seconds=30")
        second = await client.get("/dashboard/summary?max_age_seconds=30")

    assert first.status_code == 200
    assert first.json()["cache_hit"] is False
    assert second.json()["cache_hit"] is True
    attention_by_ticker = {item["ticker"]: item for item in first.json()["attention_items"]}
    assert attention_by_ticker["AAPL"]["severity"] == "error"
    assert "no data" in attention_by_ticker["AAPL"]["reason"].lower()
    assert attention_by_ticker["WELL"]["severity"] == "warning"
    assert "stale" in attention_by_ticker["WELL"]["reason"].lower()
    assert any("no data" in warning.lower() for warning in first.json()["service_warnings"])
    assert any("stale cache" in warning.lower() for warning in first.json()["service_warnings"])


@pytest.mark.anyio
async def test_dashboard_force_refresh_bypasses_existing_cache() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()

    async def override_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    clear_dashboard_summary_cache()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.get("/dashboard/summary?max_age_seconds=30")
        cached = await client.get("/dashboard/summary?max_age_seconds=30")
        refreshed = await client.get("/dashboard/summary?force_refresh=true")

    assert first.status_code == 200
    assert cached.status_code == 200
    assert refreshed.status_code == 200
    assert first.json()["cache_hit"] is False
    assert cached.json()["cache_hit"] is True
    assert refreshed.json()["cache_hit"] is False


@pytest.mark.anyio
async def test_dashboard_summary_accuracy_excludes_backfilled_by_default() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as session:
        signal = Signal(
            ticker="AAPL",
            exchange="NASDAQ",
            analysis_date=datetime(2026, 6, 1, tzinfo=UTC).date(),
            signal="BUY",
            confidence=0.9,
            created_at=datetime(2026, 6, 20, tzinfo=UTC),
        )
        session.add(signal)
        await session.flush()
        session.add(
            SignalOutcome(
                signal_id=signal.id,
                ticker="AAPL",
                exchange="NASDAQ",
                horizon_days=20,
                target_date=datetime(2026, 6, 30, tzinfo=UTC).date(),
                realized_price=100,
                realized_return_pct=12,
                realized_outcome="win",
                evaluation_eligibility="backfilled",
                lag_days=19,
            )
        )
        await session.commit()

    app = create_app()

    async def override_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    clear_dashboard_summary_cache()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/dashboard/summary?force_refresh=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["accuracy_snapshot"]["evaluated_count"] == 0
    assert payload["accuracy_snapshot"]["backfilled_excluded_count"] == 1
