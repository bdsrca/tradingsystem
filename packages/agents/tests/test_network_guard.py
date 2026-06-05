from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from trading_system_agents.network_guard import (
    MarketDataNetworkBlocked,
    MarketDataBlockingAsyncTransport,
    assert_httpx_request_allowed,
    assert_market_data_url_allowed,
    install_yfinance_block,
)


def test_install_yfinance_block_rejects_download_and_ticker() -> None:
    module = SimpleNamespace(download=lambda *_args, **_kwargs: None, Ticker=lambda *_args: None)

    install_yfinance_block(module)

    with pytest.raises(MarketDataNetworkBlocked):
        module.download("AAPL")
    with pytest.raises(MarketDataNetworkBlocked):
        module.Ticker("AAPL")


def test_market_data_http_hosts_are_blocked_but_llm_hosts_are_allowed() -> None:
    with pytest.raises(MarketDataNetworkBlocked):
        assert_market_data_url_allowed("https://query1.finance.yahoo.com/v8/finance/chart/AAPL")
    with pytest.raises(MarketDataNetworkBlocked):
        assert_market_data_url_allowed("https://api.twelvedata.com/time_series")

    assert_market_data_url_allowed("https://api.openai.com/v1/chat/completions")
    assert_market_data_url_allowed("http://localhost:11434/v1/chat/completions")


def test_httpx_request_guard_blocks_market_data_hosts() -> None:
    request = httpx.Request("GET", "https://finance.yahoo.com/quote/AAPL")

    with pytest.raises(MarketDataNetworkBlocked):
        assert_httpx_request_allowed(request)


@pytest.mark.asyncio
async def test_httpx_transport_guard_blocks_market_data_hosts() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    transport = MarketDataBlockingAsyncTransport(httpx.MockTransport(handler))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(MarketDataNetworkBlocked):
            await client.get("https://finance.yahoo.com/quote/AAPL")

        response = await client.get("https://api.openai.com/v1/models")

    assert response.status_code == 200
