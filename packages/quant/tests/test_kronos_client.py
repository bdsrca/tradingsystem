from __future__ import annotations

import json

import httpx
import pandas as pd
import pytest

from trading_system_quant.kronos.client import KronosHttpClient


@pytest.mark.asyncio
async def test_kronos_http_client_sends_future_trading_days() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content.decode("utf-8")))
        return httpx.Response(
            200,
            json={
                "forecast_path": [
                    {"time": item, "close": 101.0}
                    for item in captured["future_times"]
                ]
            },
        )

    frame = pd.DataFrame(
        {
            "open": [100.0] * 3,
            "high": [101.0] * 3,
            "low": [99.0] * 3,
            "close": [100.0] * 3,
            "volume": [1_000_000] * 3,
            "amount": [0.0] * 3,
        },
        index=pd.to_datetime(["2026-06-03", "2026-06-04", "2026-06-05"]),
    )
    client = KronosHttpClient("http://kronos.test", transport=httpx.MockTransport(handler))

    result = await client.forecast(
        frame,
        ticker="AAPL",
        exchange="NASDAQ",
        pred_len=3,
        sample_count=3,
        temperature=0.6,
        top_p=0.9,
    )

    assert captured["future_times"] == ["2026-06-08", "2026-06-09", "2026-06-10"]
    assert [item.strftime("%Y-%m-%d") for item in result.index] == captured["future_times"]
