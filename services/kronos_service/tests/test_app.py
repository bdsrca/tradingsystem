from __future__ import annotations

import pandas as pd
import pytest
from httpx import ASGITransport, AsyncClient

from trading_system_kronos_service.app import create_app


class FakeRunner:
    async def forecast(self, request):
        return pd.DataFrame(
            {
                "open": [101.0, 102.0],
                "high": [102.0, 103.0],
                "low": [100.0, 101.0],
                "close": [101.5, 102.5],
                "volume": [1_000_000, 1_100_000],
                "amount": [0.0, 0.0],
            },
            index=pd.to_datetime(request.future_times),
        )


@pytest.mark.asyncio
async def test_kronos_service_forecast_contract() -> None:
    app = create_app(runner=FakeRunner())
    payload = {
        "ticker": "AAPL",
        "exchange": "NASDAQ",
        "pred_len": 2,
        "sample_count": 3,
        "temperature": 0.6,
        "top_p": 0.9,
        "future_times": ["2026-06-08", "2026-06-09"],
        "bars": [
            {
                "time": "2026-06-05",
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 1_000_000,
                "amount": 0.0,
            }
        ],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/forecast", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["forecast_path"][0]["time"] == "2026-06-08"
    assert body["forecast_path"][1]["close"] == 102.5


@pytest.mark.asyncio
async def test_kronos_service_rejects_mismatched_future_times() -> None:
    app = create_app(runner=FakeRunner())
    payload = {
        "ticker": "AAPL",
        "exchange": "NASDAQ",
        "pred_len": 2,
        "sample_count": 3,
        "temperature": 0.6,
        "top_p": 0.9,
        "future_times": ["2026-06-08"],
        "bars": [
            {
                "time": "2026-06-05",
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 1_000_000,
                "amount": 0.0,
            }
        ],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/forecast", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "future_times length must equal pred_len"
