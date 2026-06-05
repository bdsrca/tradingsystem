from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from trading_system_agents.snapshot import DataSnapshot
from trading_system_agents.vendor_bridge import (
    MissingSnapshotError,
    get_snapshot,
    platform_vendor_config,
    register_platform_vendor,
    run_with_snapshot,
)


def _snapshot(ticker: str, price: float) -> DataSnapshot:
    return DataSnapshot(
        ticker=ticker,
        exchange="NASDAQ",
        analysis_date="2026-06-05",
        display_name=ticker,
        current_price=price,
        indicators={"SMA_20": price - 1},
        fundamentals={"pe_ratio": 22.5},
        news_items=[],
    )


def test_snapshot_context_is_reset_after_sync_run_on_reused_executor_thread() -> None:
    def read_ticker(snapshot: DataSnapshot) -> str:
        return run_with_snapshot(snapshot, lambda: get_snapshot().ticker)

    with ThreadPoolExecutor(max_workers=1) as executor:
        first = executor.submit(read_ticker, _snapshot("AAPL", 100)).result()
        second = executor.submit(read_ticker, _snapshot("SHOP", 80)).result()

    assert first == "AAPL"
    assert second == "SHOP"
    with pytest.raises(MissingSnapshotError):
        get_snapshot()


def test_register_platform_vendor_adds_snapshot_backed_methods() -> None:
    class InterfaceModule:
        VENDOR_METHODS = {
            "get_stock_data": {},
            "get_indicators": {},
            "get_fundamentals": {},
            "get_news": {},
        }

    register_platform_vendor(InterfaceModule)

    assert "platform" in InterfaceModule.VENDOR_METHODS["get_stock_data"]
    assert "platform" in InterfaceModule.VENDOR_METHODS["get_indicators"]
    assert "platform" in InterfaceModule.VENDOR_METHODS["get_fundamentals"]
    assert "platform" in InterfaceModule.VENDOR_METHODS["get_news"]


def test_platform_vendor_returns_no_data_sentinel_instead_of_raising_without_snapshot() -> None:
    fallback_called = False

    def yfinance_fallback() -> str:
        nonlocal fallback_called
        fallback_called = True
        return "yfinance"

    class InterfaceModule:
        VENDOR_METHODS = {
            "get_stock_data": {
                "yfinance": yfinance_fallback,
            },
        }

    register_platform_vendor(InterfaceModule)

    result = _route_like_tradingagents(InterfaceModule, "get_stock_data")

    assert result.startswith("NO_DATA_AVAILABLE:")
    assert fallback_called is False


def test_platform_vendor_config_routes_known_methods_to_platform() -> None:
    config = platform_vendor_config()

    assert config["data_vendors"] == {
        "core_stock_apis": "platform",
        "technical_indicators": "platform",
        "fundamental_data": "platform",
        "news_data": "platform",
    }
    assert config["tool_vendors"]["get_stock_data"] == "platform"
    assert config["tool_vendors"]["get_news"] == "platform"


def _route_like_tradingagents(interface_module, method_name: str) -> str:
    for vendor in ("platform", "yfinance"):
        if vendor not in interface_module.VENDOR_METHODS[method_name]:
            continue
        return interface_module.VENDOR_METHODS[method_name][vendor]()
    raise AssertionError("no vendor returned")
