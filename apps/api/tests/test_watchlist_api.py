from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from trading_system_api.config import get_settings
from trading_system_api.database import Base, get_session
from trading_system_api.main import create_app
from trading_system_api.models import MarketDataBar
from trading_system_data.twelve_data import TimeSeriesBar


@pytest.mark.asyncio
async def test_watchlist_crud_flow() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_session():
        async with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/watchlist", json={"symbol": "SHOP.TO", "tags": ["growth"]})
        assert created.status_code == 201
        body = created.json()
        assert body["ticker"] == "SHOP"
        assert body["exchange"] == "TSX"
        assert body["market"] == "CA"
        assert body["provider_symbol"] == "SHOP:TSX"

        listed = await client.get("/watchlist")
        assert listed.status_code == 200
        assert listed.json()[0]["ticker"] == "SHOP"

        updated = await client.patch(f"/watchlist/{body['id']}", json={"enabled": False})
        assert updated.status_code == 200
        assert updated.json()["enabled"] is False

        deleted = await client.delete(f"/watchlist/{body['id']}")
        assert deleted.status_code == 204

        listed_again = await client.get("/watchlist")
        assert listed_again.json() == []


@pytest.mark.asyncio
async def test_watchlist_create_resolves_bare_us_symbol_exchange(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_session():
        async with session_factory() as session:
            yield session

    class FakeTwelveDataClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def search_symbols(self, symbol: str):
            assert symbol == "MDA"
            return [
                SimpleNamespace(symbol="MDA", exchange="TSX", country="Canada"),
                SimpleNamespace(symbol="MDA", exchange="NYSE", country="United States"),
            ]

    monkeypatch.setenv("TWELVE_DATA_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "trading_system_api.routers.watchlist.TwelveDataClient",
        FakeTwelveDataClient,
        raising=False,
    )
    app = create_app()
    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/watchlist", json={"symbol": "MDA"})

    assert created.status_code == 201
    body = created.json()
    assert body["ticker"] == "MDA"
    assert body["exchange"] == "NYSE"
    assert body["market"] == "US"
    assert body["provider_symbol"] == "MDA:NYSE"


@pytest.mark.asyncio
async def test_market_data_refresh_upserts_daily_bars(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_session():
        async with session_factory() as session:
            yield session

    class FakeTwelveDataClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def fetch_daily_bars(self, identity, *, outputsize: int = 500):
            assert identity.ticker == "SHOP"
            assert identity.exchange == "TSX"
            assert outputsize == 1
            return [
                TimeSeriesBar(
                    bar_date=date(2026, 6, 3),
                    open=Decimal("95.10"),
                    high=Decimal("97.25"),
                    low=Decimal("94.80"),
                    close=Decimal("96.40"),
                    volume=1234567,
                    source_provider="twelve_data",
                    source_symbol="SHOP:TSX",
                    fetched_at=datetime(2026, 6, 4, tzinfo=timezone.utc),
                    adjustment_mode="split_adjusted",
                )
            ]

    monkeypatch.setenv("TWELVE_DATA_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "trading_system_api.routers.market_data.TwelveDataClient",
        FakeTwelveDataClient,
        raising=False,
    )
    app = create_app()
    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post("/market-data/SHOP:TSX/refresh?outputsize=1")
        assert first.status_code == 200
        assert first.json()["bars_upserted"] == 1

        second = await client.post("/market-data/SHOP:TSX/refresh?outputsize=1")
        assert second.status_code == 200

    async with session_factory() as session:
        rows = (await session.execute(select(MarketDataBar))).scalars().all()
        assert len(rows) == 1
        assert rows[0].ticker == "SHOP"
        assert rows[0].exchange == "TSX"
        assert rows[0].source_symbol == "SHOP:TSX"
