from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import httpx

from trading_system_quant.calendar import get_trading_days_forward


class KronosHttpClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 60,
        transport: httpx.AsyncBaseTransport | httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def forecast(
        self,
        frame: pd.DataFrame,
        *,
        ticker: str,
        exchange: str,
        pred_len: int,
        sample_count: int,
        temperature: float,
        top_p: float,
    ) -> pd.DataFrame:
        future_times = _future_trading_days(frame, exchange, pred_len)
        payload = {
            "ticker": ticker,
            "exchange": exchange,
            "pred_len": pred_len,
            "sample_count": sample_count,
            "temperature": temperature,
            "top_p": top_p,
            "future_times": future_times,
            "bars": [
                {
                    "time": _index_to_iso(index),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                    "amount": float(row["amount"]),
                }
                for index, row in frame.iterrows()
            ],
        }
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            response = await client.post("/forecast", json=payload)
            response.raise_for_status()
            data = response.json()

        rows = data.get("forecast_path") or data.get("predictions") or []
        if not rows:
            raise ValueError("Kronos service returned no forecast_path")
        return pd.DataFrame(
            [
                {
                    "open": item.get("open", item["close"]),
                    "high": item.get("high", item["close"]),
                    "low": item.get("low", item["close"]),
                    "close": item["close"],
                    "volume": item.get("volume", 0),
                    "amount": item.get("amount", 0),
                }
                for item in rows
            ],
            index=pd.to_datetime([item["time"] for item in rows]),
        )


def _index_to_iso(value) -> str:
    if hasattr(value, "date"):
        return value.date().isoformat()
    return str(value)


def _future_trading_days(frame: pd.DataFrame, exchange: str, pred_len: int) -> list[str]:
    start = _index_to_date(frame.index[-1]) + timedelta(days=1)
    return [item.isoformat() for item in get_trading_days_forward(exchange, start, pred_len)]


def _index_to_date(value) -> date:
    if hasattr(value, "date"):
        return value.date()
    return date.fromisoformat(str(value))
