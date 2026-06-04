from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from trading_system_data.symbols import SymbolIdentity, to_twelve_data_symbol


@dataclass(frozen=True)
class TimeSeriesBar:
    bar_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    source_provider: str
    source_symbol: str
    fetched_at: datetime
    adjustment_mode: str


class TwelveDataRateLimiter:
    def __init__(self, requests_per_minute: int = 8) -> None:
        self._interval_seconds = 60 / requests_per_minute
        self._lock = asyncio.Lock()
        self._last_request_at = 0.0

    async def wait(self) -> None:
        loop = asyncio.get_running_loop()
        async with self._lock:
            now = loop.time()
            wait_for = self._interval_seconds - (now - self._last_request_at)
            if wait_for > 0:
                await asyncio.sleep(wait_for)
            self._last_request_at = loop.time()


class TwelveDataClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.twelvedata.com",
        rate_limiter: TwelveDataRateLimiter | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._rate_limiter = rate_limiter or TwelveDataRateLimiter()

    async def fetch_daily_bars(
        self,
        identity: SymbolIdentity,
        *,
        outputsize: int = 500,
    ) -> list[TimeSeriesBar]:
        await self._rate_limiter.wait()
        provider_symbol = to_twelve_data_symbol(identity)
        async with httpx.AsyncClient(base_url=self._base_url, timeout=20) as client:
            response = await client.get(
                "/time_series",
                params={
                    "symbol": provider_symbol,
                    "interval": "1day",
                    "outputsize": outputsize,
                    "apikey": self._api_key,
                },
            )
            response.raise_for_status()
            payload = response.json()
        return parse_time_series(payload)


def parse_time_series(payload: dict[str, Any]) -> list[TimeSeriesBar]:
    if "values" not in payload:
        message = payload.get("message") or payload.get("code") or "Missing values in Twelve Data response"
        raise ValueError(str(message))

    meta = payload.get("meta", {})
    source_symbol = str(meta.get("symbol") or "")
    fetched_at = datetime.now(timezone.utc)
    bars: list[TimeSeriesBar] = []

    for value in payload["values"]:
        bars.append(
            TimeSeriesBar(
                bar_date=date.fromisoformat(value["datetime"]),
                open=Decimal(value["open"]),
                high=Decimal(value["high"]),
                low=Decimal(value["low"]),
                close=Decimal(value["close"]),
                volume=int(Decimal(str(value.get("volume") or "0"))),
                source_provider="twelve_data",
                source_symbol=source_symbol,
                fetched_at=fetched_at,
                adjustment_mode="split_adjusted",
            )
        )

    return bars

