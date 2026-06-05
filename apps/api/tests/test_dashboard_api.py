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
        run = DailyWorkerRun(triggered_by="manual", status="completed")
        session.add_all([watch, run])
        await session.flush()
        session.add(
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
        first = await client.get("/dashboard/summary?max_age_seconds=30")
        second = await client.get("/dashboard/summary?max_age_seconds=30")

    assert first.status_code == 200
    assert first.json()["cache_hit"] is False
    assert second.json()["cache_hit"] is True
    item = first.json()["attention_items"][0]
    assert item["ticker"] == "AAPL"
    assert item["severity"] == "error"
    assert "no data" in item["reason"].lower()


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
