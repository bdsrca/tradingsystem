from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from trading_system_api.database import Base
from trading_system_api.models import Signal
from trading_system_quant.signal_store import SignalCreate, append_signal


@pytest.mark.asyncio
async def test_append_signal_only_inserts_rows() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        first = await append_signal(
            session,
            SignalCreate(
                ticker="AAPL",
                exchange="NASDAQ",
                market="US",
                analysis_date=date(2026, 6, 3),
                signal="BUY",
                confidence=0.8,
                entry_price=100.0,
                risk_level=94.0,
                reason="baseline",
                indicators={"RSI_14": 60.0},
                layer_scores={"trend": 0.2},
                source="baseline",
            ),
        )
        second = await append_signal(
            session,
            SignalCreate(
                ticker="AAPL",
                exchange="NASDAQ",
                market="US",
                analysis_date=date(2026, 6, 4),
                signal="HOLD",
                confidence=0.2,
                entry_price=101.0,
                risk_level=95.0,
                reason="baseline",
                indicators={},
                layer_scores={},
                source="baseline",
            ),
        )

        rows = (await session.execute(select(Signal).order_by(Signal.analysis_date))).scalars().all()

    assert [row.id for row in rows] == [first.id, second.id]
    assert rows[0].signal == "BUY"
    assert rows[0].is_superseded is False
