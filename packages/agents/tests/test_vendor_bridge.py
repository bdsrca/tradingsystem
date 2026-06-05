from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from trading_system_agents.snapshot import DataSnapshot
from trading_system_agents.vendor_bridge import (
    MissingSnapshotError,
    get_snapshot,
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
