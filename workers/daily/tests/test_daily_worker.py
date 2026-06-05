from __future__ import annotations

import asyncio
import json
import logging

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
async def test_daily_worker_skips_conflicting_concurrent_run_for_same_ticker() -> None:
    registry = DailyWorkerLockRegistry()
    started = asyncio.Event()
    release = asyncio.Event()

    async def analyze_ticker(item: DailyTickerInput) -> DailyTickerResult:
        started.set()
        await release.wait()
        return DailyTickerResult(ticker=item.ticker, exchange=item.exchange, status="succeeded")

    worker = DailyWorker(
        list_tickers=lambda: [DailyTickerInput(ticker="MDA", exchange="NYSE", market="US")],
        analyze_ticker=analyze_ticker,
        lock_registry=registry,
    )

    first = asyncio.create_task(worker.run_once(triggered_by="manual"))
    await started.wait()

    second = await worker.run_once(triggered_by="manual")

    release.set()
    first_result = await first

    assert first_result.succeeded_count == 1
    assert second.skipped_count == 1
    assert second.items[0].error_message == "ticker already running"


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


@pytest.mark.asyncio
async def test_daily_worker_emits_structured_json_logs(caplog: pytest.LogCaptureFixture) -> None:
    async def analyze_ticker(item: DailyTickerInput) -> DailyTickerResult:
        return DailyTickerResult(
            ticker=item.ticker,
            exchange=item.exchange,
            status="succeeded",
            data_freshness="fresh",
        )

    worker = DailyWorker(
        list_tickers=lambda: [DailyTickerInput(ticker="NTSK", exchange="NASDAQ", market="US")],
        analyze_ticker=analyze_ticker,
    )

    with caplog.at_level(logging.INFO, logger="trading_system_worker.daily"):
        result = await worker.run_once(triggered_by="test", worker_run_id="run-1")

    messages = [json.loads(record.message) for record in caplog.records]

    assert result.succeeded_count == 1
    assert messages[0]["event"] == "daily_worker_started"
    assert messages[0]["worker_run_id"] == "run-1"
    assert messages[1]["event"] == "daily_ticker_finished"
    assert messages[1]["ticker"] == "NTSK"
    assert messages[1]["exchange"] == "NASDAQ"
    assert messages[1]["status"] == "succeeded"
    assert messages[1]["data_freshness"] == "fresh"
    assert messages[2]["event"] == "daily_worker_finished"
    assert messages[2]["status"] == "completed"
    assert messages[2]["succeeded_count"] == 1
