from __future__ import annotations

from urllib.parse import urlparse

import httpx


MARKET_DATA_HOSTS = frozenset(
    {
        "finance.yahoo.com",
        "query1.finance.yahoo.com",
        "query2.finance.yahoo.com",
        "api.twelvedata.com",
        "twelvedata.com",
        "finnhub.io",
        "api.finnhub.io",
    }
)


class MarketDataNetworkBlocked(RuntimeError):
    pass


def install_yfinance_block(yfinance_module) -> None:
    yfinance_module.download = _blocked_yfinance_call
    yfinance_module.Ticker = _blocked_yfinance_call


def assert_market_data_url_allowed(url: str) -> None:
    hostname = (urlparse(url).hostname or "").lower()
    if hostname in MARKET_DATA_HOSTS:
        raise MarketDataNetworkBlocked(f"Blocked market-data network call to {hostname}")


def assert_httpx_request_allowed(request: httpx.Request) -> None:
    assert_market_data_url_allowed(str(request.url))


class MarketDataBlockingAsyncTransport(httpx.AsyncBaseTransport):
    def __init__(self, wrapped: httpx.AsyncBaseTransport) -> None:
        self.wrapped = wrapped

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        assert_httpx_request_allowed(request)
        return await self.wrapped.handle_async_request(request)


def _blocked_yfinance_call(*_args, **_kwargs):
    raise MarketDataNetworkBlocked("Blocked direct yfinance call during agent workflow")
