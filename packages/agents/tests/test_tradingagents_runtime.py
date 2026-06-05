from __future__ import annotations

import functools
from types import SimpleNamespace

import pytest

from trading_system_agents.network_guard import MarketDataNetworkBlocked
from trading_system_agents.snapshot import DataSnapshot
from trading_system_agents.tradingagents_runtime import (
    RuntimePathError,
    disable_pending_entry_resolution,
    patch_resolve_instrument_identity,
    prepare_isolated_runtime_dirs,
)


def _snapshot() -> DataSnapshot:
    return DataSnapshot(
        ticker="AAPL",
        exchange="NASDAQ",
        analysis_date="2026-06-05",
        display_name="Apple Inc.",
        current_price=190.0,
        indicators={},
        fundamentals={
            "business_summary": "Consumer hardware and services company.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
        },
    )


def test_identity_patch_clears_lru_cache_and_replaces_imported_references() -> None:
    @functools.lru_cache(maxsize=256)
    def resolve_instrument_identity(ticker: str) -> dict[str, str]:
        return {"name": f"stale {ticker}"}

    agent_utils = SimpleNamespace(resolve_instrument_identity=resolve_instrument_identity)
    graph_module = SimpleNamespace(resolve_instrument_identity=resolve_instrument_identity)
    agent_utils.resolve_instrument_identity("AAPL")
    assert resolve_instrument_identity.cache_info().currsize == 1

    with patch_resolve_instrument_identity(agent_utils, _snapshot(), graph_module=graph_module):
        assert resolve_instrument_identity.cache_info().currsize == 0
        assert agent_utils.resolve_instrument_identity("MSFT")["name"] == "Apple Inc."
        assert graph_module.resolve_instrument_identity("SHOP")["name"] == "Apple Inc."
        assert agent_utils.resolve_instrument_identity("MSFT")["sector"] == "Technology"

    assert agent_utils.resolve_instrument_identity is resolve_instrument_identity
    assert graph_module.resolve_instrument_identity is resolve_instrument_identity


def test_pending_entry_resolution_can_be_disabled_for_agent_run() -> None:
    class Graph:
        def _resolve_pending_entries(self, ticker: str) -> None:
            raise MarketDataNetworkBlocked(f"unexpected yfinance path for {ticker}")

    graph = Graph()

    with disable_pending_entry_resolution(graph):
        assert graph._resolve_pending_entries("AAPL") is None

    with pytest.raises(MarketDataNetworkBlocked):
        graph._resolve_pending_entries("AAPL")


def test_isolated_runtime_dirs_fail_closed_when_run_dir_exists(tmp_path) -> None:
    dirs = prepare_isolated_runtime_dirs(tmp_path, run_id="analysis-aapl-20260605")

    assert dirs.data_cache_dir.is_dir()
    assert dirs.results_dir.is_dir()
    assert dirs.data_cache_dir.parent == dirs.run_dir
    assert dirs.results_dir.parent == dirs.run_dir

    with pytest.raises(RuntimePathError):
        prepare_isolated_runtime_dirs(tmp_path, run_id="analysis-aapl-20260605")
