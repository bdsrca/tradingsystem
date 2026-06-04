from __future__ import annotations

import asyncio

import pandas as pd
import pytest

from trading_system_quant.kronos.engine import KronosEngine


class SlowClient:
    async def forecast(self, *_args, **_kwargs):
        await asyncio.sleep(0.2)


class StaticClient:
    async def forecast(self, *_args, **_kwargs):
        index = pd.date_range("2026-05-01", periods=30, freq="D")
        return pd.DataFrame(
            {
                "open": [101.0] * 30,
                "high": [102.0] * 30,
                "low": [100.0] * 30,
                "close": [101.0] * 30,
                "volume": [1_000_000] * 30,
                "amount": [0.0] * 30,
            },
            index=index,
        )


def _bars(rows: int = 120) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    return pd.DataFrame(
        {
            "open": [100.0] * rows,
            "high": [101.0] * rows,
            "low": [99.0] * rows,
            "close": [100.0] * rows,
            "volume": [1_000_000] * rows,
        },
        index=dates,
    )


@pytest.mark.asyncio
async def test_kronos_engine_timeout_returns_degraded_result() -> None:
    engine = KronosEngine(client=SlowClient(), timeout_seconds=0.01)

    result = await engine.forecast(_bars(), ticker="AAPL", exchange="NASDAQ")

    assert result.status == "timeout"
    assert result.is_fallback is True
    assert "timeout" in result.error_message


@pytest.mark.asyncio
async def test_kronos_engine_static_client_returns_forecast_result() -> None:
    engine = KronosEngine(client=StaticClient(), timeout_seconds=1)

    result = await engine.forecast(_bars(), ticker="AAPL", exchange="NASDAQ")

    assert result.status == "ok"
    assert result.analysis_date == "2026-04-30"
    assert result.horizons[0].forecast_close == 101.0
