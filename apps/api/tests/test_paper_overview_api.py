import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from trading_system_api.database import Base, get_session
from trading_system_api.main import create_app
from trading_system_api.models import PaperSimulationRun, WatchlistItem


@pytest.mark.anyio
async def test_paper_overview_returns_latest_runs_and_empty_state() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as session:
        session.add_all(
            [
                WatchlistItem(
                    ticker="AAPL",
                    exchange="NASDAQ",
                    market="US",
                    provider_symbol="AAPL",
                ),
                WatchlistItem(
                    ticker="WELL",
                    exchange="TSX",
                    market="CA",
                    provider_symbol="WELL:TSX",
                ),
            ]
        )
        session.add(
            PaperSimulationRun(
                ticker="AAPL",
                exchange="NASDAQ",
                window_years=1,
                initial_capital=100000,
                position_size_pct=0.05,
                max_positions=10,
                max_holding_days=30,
                signal_snapshot={"signal_ids": ["s1"]},
                metrics={
                    "total_return_pct": 12.5,
                    "max_drawdown_pct": -4.2,
                    "win_rate_pct": 60.0,
                    "trade_count": 5,
                },
            )
        )
        await session.commit()

    app = create_app()

    async def override_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/paper/overview")

    assert response.status_code == 200
    rows = response.json()["rows"]
    assert rows[0]["ticker"] == "AAPL"
    assert rows[0]["one_year"]["status"] == "simulated"
    assert rows[0]["one_year"]["total_return_pct"] == 12.5
    assert rows[1]["ticker"] == "WELL"
    assert rows[1]["one_year"]["status"] == "not_simulated"
