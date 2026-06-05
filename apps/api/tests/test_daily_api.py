from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from trading_system_api.config import get_settings
from trading_system_api.database import Base, get_session
from trading_system_api.main import create_app
from trading_system_api.models import (
    DailyWorkerRun,
    DailyWorkerTickerResult,
    EmailNotification,
    MarketDataBar,
    Signal,
    WatchlistItem,
)
from trading_system_data.twelve_data import TimeSeriesBar


@pytest.mark.asyncio
async def test_daily_run_refreshes_data_creates_signal_and_persists_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        session.add(
            WatchlistItem(
                ticker="NTSK",
                exchange="NASDAQ",
                market="US",
                provider_symbol="NTSK",
                enabled=True,
                tags=[],
            )
        )
        await session.commit()

    class FakeTwelveDataClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def fetch_daily_bars(self, identity, *, outputsize: int = 500):
            assert identity.ticker == "NTSK"
            return _fake_bars(identity.ticker, outputsize=70)

    async def override_session():
        async with session_factory() as session:
            yield session

    monkeypatch.setenv("TWELVE_DATA_API_KEY", "test-key")
    monkeypatch.setenv("DAILY_KRONOS_ENABLED", "false")
    monkeypatch.setenv("DAILY_EMAIL_ENABLED", "false")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "trading_system_api.daily_service.TwelveDataClient",
        FakeTwelveDataClient,
        raising=False,
    )

    app = create_app()
    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/daily/run")
        assert created.status_code == 201
        body = created.json()
        assert body["triggered_by"] == "manual"
        assert body["status"] == "completed"
        assert body["succeeded_count"] == 1
        assert body["items"][0]["ticker"] == "NTSK"
        assert body["items"][0]["status"] == "succeeded"
        assert body["items"][0]["data_freshness"] == "fresh"

        latest = await client.get("/daily/latest")
        assert latest.status_code == 200
        assert latest.json()["id"] == body["id"]

    async with session_factory() as session:
        runs = (await session.execute(select(DailyWorkerRun))).scalars().all()
        results = (await session.execute(select(DailyWorkerTickerResult))).scalars().all()
        signals = (await session.execute(select(Signal))).scalars().all()

    assert len(runs) == 1
    assert runs[0].succeeded_count == 1
    assert len(results) == 1
    assert results[0].signal in {"BUY", "WATCH", "HOLD", "REDUCE", "SELL"}
    assert len(signals) == 1


def _fake_bars(ticker: str, *, outputsize: int) -> list[TimeSeriesBar]:
    start = date(2026, 1, 2)
    fetched_at = datetime(2026, 6, 5, tzinfo=timezone.utc)
    bars: list[TimeSeriesBar] = []
    for index in range(outputsize):
        close = Decimal(100 + index)
        bars.append(
            TimeSeriesBar(
                bar_date=start + timedelta(days=index),
                open=close - Decimal("0.50"),
                high=close + Decimal("1.00"),
                low=close - Decimal("1.00"),
                close=close,
                volume=1_000_000 + index,
                source_provider="twelve_data",
                source_symbol=ticker,
                fetched_at=fetched_at,
                adjustment_mode="split_adjusted",
            )
        )
    return bars


@pytest.mark.asyncio
async def test_daily_run_retries_refresh_before_using_cached_freshness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        session.add(
            WatchlistItem(
                ticker="NTSK",
                exchange="NASDAQ",
                market="US",
                provider_symbol="NTSK",
                enabled=True,
                tags=[],
            )
        )
        await session.commit()

    class FlakyTwelveDataClient:
        attempts = 0

        def __init__(self, *args, **kwargs) -> None:
            pass

        async def fetch_daily_bars(self, identity, *, outputsize: int = 500):
            FlakyTwelveDataClient.attempts += 1
            if FlakyTwelveDataClient.attempts == 1:
                raise RuntimeError("temporary upstream error")
            return _fake_bars(identity.ticker, outputsize=70)

    async def override_session():
        async with session_factory() as session:
            yield session

    monkeypatch.setenv("TWELVE_DATA_API_KEY", "test-key")
    monkeypatch.setenv("DAILY_EMAIL_ENABLED", "false")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "trading_system_api.daily_service.TwelveDataClient",
        FlakyTwelveDataClient,
        raising=False,
    )

    app = create_app()
    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/daily/run")

    body = created.json()
    assert created.status_code == 201
    assert FlakyTwelveDataClient.attempts == 2
    assert body["status"] == "completed"
    assert body["items"][0]["status"] == "succeeded"
    assert body["items"][0]["data_freshness"] == "fresh"
    assert body["items"][0]["error_message"] is None


@pytest.mark.asyncio
async def test_daily_run_degrades_to_existing_bars_when_refresh_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        item = WatchlistItem(
            ticker="WELL",
            exchange="TSX",
            market="CA",
            provider_symbol="WELL:TSX",
            enabled=True,
            tags=[],
        )
        session.add(item)
        for bar in _fake_bars("WELL:TSX", outputsize=70):
            session.add(
                MarketDataBar(
                    ticker="WELL",
                    exchange="TSX",
                    bar_date=bar.bar_date,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                    source_provider="yfinance_manual",
                    source_symbol="WELL.TO",
                    fetched_at=bar.fetched_at,
                    adjustment_mode="split_adjusted",
                )
            )
        await session.commit()

    class FailingTwelveDataClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def fetch_daily_bars(self, identity, *, outputsize: int = 500):
            raise ValueError("plan does not include this exchange")

    async def override_session():
        async with session_factory() as session:
            yield session

    monkeypatch.setenv("TWELVE_DATA_API_KEY", "test-key")
    monkeypatch.setenv("DAILY_KRONOS_ENABLED", "false")
    monkeypatch.setenv("DAILY_EMAIL_ENABLED", "false")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "trading_system_api.daily_service.TwelveDataClient",
        FailingTwelveDataClient,
        raising=False,
    )

    app = create_app()
    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/daily/run")

    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "degraded"
    assert body["degraded_count"] == 1
    assert body["failed_count"] == 0
    assert body["items"][0]["status"] == "degraded"
    assert body["items"][0]["data_freshness"] == "stale_used"
    assert body["items"][0]["signal"] in {"BUY", "WATCH", "HOLD", "REDUCE", "SELL"}
    assert "used existing bars" in body["items"][0]["error_message"]


@pytest.mark.asyncio
async def test_daily_run_sends_digest_email_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        session.add(
            WatchlistItem(
                ticker="NTSK",
                exchange="NASDAQ",
                market="US",
                provider_symbol="NTSK",
                enabled=True,
                tags=[],
            )
        )
        await session.commit()

    sent: list[dict[str, str]] = []

    class FakeTwelveDataClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def fetch_daily_bars(self, identity, *, outputsize: int = 500):
            return _fake_bars(identity.ticker, outputsize=70)

    async def fake_send_digest_email(*, recipient: str, subject: str, body: str, settings):
        sent.append({"recipient": recipient, "subject": subject, "body": body})

    async def override_session():
        async with session_factory() as session:
            yield session

    monkeypatch.setenv("TWELVE_DATA_API_KEY", "test-key")
    monkeypatch.setenv("DAILY_EMAIL_ENABLED", "true")
    monkeypatch.setenv("DAILY_EMAIL_RECIPIENT", "me@example.com")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "trading_system_api.daily_service.TwelveDataClient",
        FakeTwelveDataClient,
        raising=False,
    )
    monkeypatch.setattr(
        "trading_system_api.daily_service.send_digest_email",
        fake_send_digest_email,
        raising=False,
    )

    app = create_app()
    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/daily/run")

    assert created.status_code == 201
    body = created.json()
    assert body["email_sent"] is True
    assert sent[0]["recipient"] == "me@example.com"
    assert "Daily trading-system digest" in sent[0]["body"]

    async with session_factory() as session:
        notifications = (await session.execute(select(EmailNotification))).scalars().all()

    assert any(item.status == "sent" and item.is_digest for item in notifications)
    assert any(item.status == "sent" and not item.is_digest for item in notifications)
    assert all(item.recipient == "me@example.com" for item in notifications)


@pytest.mark.asyncio
async def test_daily_email_debounce_applies_to_manual_reruns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        session.add(
            WatchlistItem(
                ticker="NTSK",
                exchange="NASDAQ",
                market="US",
                provider_symbol="NTSK",
                enabled=True,
                tags=[],
            )
        )
        await session.commit()

    sent: list[dict[str, str]] = []

    class FakeTwelveDataClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def fetch_daily_bars(self, identity, *, outputsize: int = 500):
            return _fake_bars(identity.ticker, outputsize=70)

    async def fake_send_digest_email(*, recipient: str, subject: str, body: str, settings):
        sent.append({"recipient": recipient, "subject": subject, "body": body})

    async def override_session():
        async with session_factory() as session:
            yield session

    monkeypatch.setenv("TWELVE_DATA_API_KEY", "test-key")
    monkeypatch.setenv("DAILY_EMAIL_ENABLED", "true")
    monkeypatch.setenv("DAILY_EMAIL_RECIPIENT", "me@example.com")
    monkeypatch.setenv("EMAIL_DEBOUNCE_DAYS", "7")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "trading_system_api.daily_service.TwelveDataClient",
        FakeTwelveDataClient,
        raising=False,
    )
    monkeypatch.setattr(
        "trading_system_api.daily_service.send_digest_email",
        fake_send_digest_email,
        raising=False,
    )

    app = create_app()
    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post("/daily/run")
        second = await client.post("/daily/run")

    assert first.json()["email_sent"] is True
    assert second.json()["email_sent"] is False
    assert len(sent) == 1

    async with session_factory() as session:
        notifications = (await session.execute(select(EmailNotification))).scalars().all()

    assert any(item.status == "sent" and not item.is_digest for item in notifications)
    assert any(item.status == "suppressed" and not item.is_digest for item in notifications)
