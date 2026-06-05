from __future__ import annotations

import pytest

from trading_system_worker.daily import (
    DailyTickerInput,
    DailyTickerResult,
    DailyWorker,
    DailyWorkerLockRegistry,
)


@pytest.mark.asyncio
async def test_daily_worker_skips_ticker_when_lock_is_already_held() -> None:
    registry = DailyWorkerLockRegistry()
    lock = registry.get("MDA", "NYSE")
    await lock.acquire()

    async def analyze_ticker(item: DailyTickerInput) -> DailyTickerResult:
        raise AssertionError("locked ticker should not be analyzed")

    worker = DailyWorker(
        list_tickers=lambda: [DailyTickerInput(ticker="MDA", exchange="NYSE", market="US")],
        analyze_ticker=analyze_ticker,
        lock_registry=registry,
    )

    try:
        result = await worker.run_once(triggered_by="test")
    finally:
        lock.release()

    assert result.skipped_count == 1
    assert result.items[0].status == "skipped"
    assert result.items[0].error_message == "ticker already running"


@pytest.mark.asyncio
async def test_daily_worker_summary_counts_all_result_buckets() -> None:
    outcomes = {
        "AAA": DailyTickerResult(ticker="AAA", exchange="NASDAQ", status="succeeded"),
        "BBB": DailyTickerResult(ticker="BBB", exchange="NASDAQ", status="failed"),
        "CCC": DailyTickerResult(ticker="CCC", exchange="NASDAQ", status="skipped"),
        "DDD": DailyTickerResult(ticker="DDD", exchange="NASDAQ", status="stale"),
        "EEE": DailyTickerResult(ticker="EEE", exchange="NASDAQ", status="degraded"),
    }

    async def analyze_ticker(item: DailyTickerInput) -> DailyTickerResult:
        return outcomes[item.ticker]

    worker = DailyWorker(
        list_tickers=lambda: [
            DailyTickerInput(ticker=ticker, exchange="NASDAQ", market="US")
            for ticker in outcomes
        ],
        analyze_ticker=analyze_ticker,
    )

    result = await worker.run_once(triggered_by="test")

    assert result.succeeded_count == 1
    assert result.failed_count == 1
    assert result.skipped_count == 1
    assert result.stale_count == 1
    assert result.degraded_count == 1
    assert result.status == "degraded"
