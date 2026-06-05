from __future__ import annotations

import inspect
import json
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, TypeVar


TickerStatus = Literal["succeeded", "failed", "skipped", "stale", "degraded"]
DataFreshness = Literal["fresh", "stale_used", "no_data"]
RunStatus = Literal["completed", "failed", "degraded"]
_LOGGER = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DailyTickerInput:
    ticker: str
    exchange: str
    market: str
    watchlist_item_id: str | None = None


@dataclass(frozen=True)
class DailyTickerResult:
    ticker: str
    exchange: str
    status: TickerStatus
    market: str | None = None
    watchlist_item_id: str | None = None
    signal: str | None = None
    confidence: float | None = None
    data_freshness: DataFreshness = "fresh"
    reason: str | None = None
    error_message: str | None = None
    started_at: datetime = field(default_factory=_utc_now)
    finished_at: datetime | None = None


@dataclass(frozen=True)
class DailyRunResult:
    triggered_by: str
    status: RunStatus
    started_at: datetime
    finished_at: datetime
    items: list[DailyTickerResult]

    @property
    def succeeded_count(self) -> int:
        return self._count("succeeded")

    @property
    def failed_count(self) -> int:
        return self._count("failed")

    @property
    def skipped_count(self) -> int:
        return self._count("skipped")

    @property
    def stale_count(self) -> int:
        return self._count("stale")

    @property
    def degraded_count(self) -> int:
        return self._count("degraded")

    def _count(self, status: TickerStatus) -> int:
        return sum(1 for item in self.items if item.status == status)

    def summary(self) -> dict[str, object]:
        return {
            "triggered_by": self.triggered_by,
            "status": self.status,
            "succeeded_count": self.succeeded_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "stale_count": self.stale_count,
            "degraded_count": self.degraded_count,
            "tickers": [f"{item.ticker}:{item.exchange}" for item in self.items],
        }


class DailyWorkerLockRegistry:
    def __init__(self) -> None:
        self._locks: dict[str, _AsyncLock] = {}

    def get(self, ticker: str, exchange: str) -> "_AsyncLock":
        key = _lock_key(ticker, exchange)
        if key not in self._locks:
            self._locks[key] = _AsyncLock()
        return self._locks[key]


class DailyWorker:
    def __init__(
        self,
        *,
        list_tickers: Callable[[], Sequence[DailyTickerInput] | Awaitable[Sequence[DailyTickerInput]]],
        analyze_ticker: Callable[[DailyTickerInput], Awaitable[DailyTickerResult]],
        lock_registry: DailyWorkerLockRegistry | None = None,
    ) -> None:
        self._list_tickers = list_tickers
        self._analyze_ticker = analyze_ticker
        self._lock_registry = lock_registry or DailyWorkerLockRegistry()

    async def run_once(
        self,
        *,
        triggered_by: str,
        worker_run_id: str | None = None,
    ) -> DailyRunResult:
        started_at = _utc_now()
        tickers = list(await _maybe_await(self._list_tickers()))
        _log_event(
            "daily_worker_started",
            worker_run_id=worker_run_id,
            triggered_by=triggered_by,
            ticker_count=len(tickers),
            started_at=started_at.isoformat(),
        )
        items: list[DailyTickerResult] = []

        for item in tickers:
            items.append(await self._run_ticker(item, worker_run_id=worker_run_id))

        finished_at = _utc_now()
        result = DailyRunResult(
            triggered_by=triggered_by,
            status=_run_status(items),
            started_at=started_at,
            finished_at=finished_at,
            items=items,
        )
        _log_event(
            "daily_worker_finished",
            worker_run_id=worker_run_id,
            triggered_by=triggered_by,
            status=result.status,
            succeeded_count=result.succeeded_count,
            failed_count=result.failed_count,
            skipped_count=result.skipped_count,
            stale_count=result.stale_count,
            degraded_count=result.degraded_count,
            duration_ms=_duration_ms(started_at, finished_at),
            finished_at=finished_at.isoformat(),
        )
        return result

    async def _run_ticker(
        self,
        item: DailyTickerInput,
        *,
        worker_run_id: str | None = None,
    ) -> DailyTickerResult:
        lock = self._lock_registry.get(item.ticker, item.exchange)
        if lock.locked():
            now = _utc_now()
            result = DailyTickerResult(
                ticker=item.ticker,
                exchange=item.exchange,
                market=item.market,
                watchlist_item_id=item.watchlist_item_id,
                status="skipped",
                error_message="ticker already running",
                started_at=now,
                finished_at=now,
            )
            _log_ticker_finished(result, worker_run_id=worker_run_id)
            return result

        await lock.acquire()
        started_at = _utc_now()
        result: DailyTickerResult | None = None
        try:
            result = await self._analyze_ticker(item)
            if result.finished_at is None:
                result = DailyTickerResult(
                    ticker=result.ticker,
                    exchange=result.exchange,
                    market=result.market,
                    watchlist_item_id=result.watchlist_item_id,
                    status=result.status,
                    signal=result.signal,
                    confidence=result.confidence,
                    data_freshness=result.data_freshness,
                    reason=result.reason,
                    error_message=result.error_message,
                    started_at=result.started_at,
                    finished_at=_utc_now(),
                )
            return result
        except Exception as exc:
            result = DailyTickerResult(
                ticker=item.ticker,
                exchange=item.exchange,
                market=item.market,
                watchlist_item_id=item.watchlist_item_id,
                status="failed",
                data_freshness="no_data",
                error_message=str(exc),
                started_at=started_at,
                finished_at=_utc_now(),
            )
            return result
        finally:
            if result is not None:
                _log_ticker_finished(result, worker_run_id=worker_run_id)
            lock.release()


class _AsyncLock:
    def __init__(self) -> None:
        import asyncio

        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        await self._lock.acquire()

    def release(self) -> None:
        self._lock.release()

    def locked(self) -> bool:
        return self._lock.locked()


T = TypeVar("T")


async def _maybe_await(value: T | Awaitable[T]) -> T:
    if inspect.isawaitable(value):
        return await value
    return value


def _run_status(items: Sequence[DailyTickerResult]) -> RunStatus:
    if not items:
        return "completed"
    if all(item.status == "failed" for item in items):
        return "failed"
    if any(item.status in {"failed", "stale", "degraded"} for item in items):
        return "degraded"
    return "completed"


def _lock_key(ticker: str, exchange: str) -> str:
    return f"{ticker.strip().upper()}::{exchange.strip().upper()}"


def _log_ticker_finished(
    result: DailyTickerResult,
    *,
    worker_run_id: str | None,
) -> None:
    finished_at = result.finished_at or _utc_now()
    _log_event(
        "daily_ticker_finished",
        worker_run_id=worker_run_id,
        ticker=result.ticker,
        exchange=result.exchange,
        market=result.market,
        watchlist_item_id=str(result.watchlist_item_id) if result.watchlist_item_id else None,
        status=result.status,
        data_freshness=result.data_freshness,
        signal=result.signal,
        confidence=result.confidence,
        error_message=result.error_message,
        duration_ms=_duration_ms(result.started_at, finished_at),
        finished_at=finished_at.isoformat(),
    )


def _log_event(event: str, **fields: object) -> None:
    payload = {"event": event}
    payload.update({key: value for key, value in fields.items() if value is not None})
    _LOGGER.info(json.dumps(payload, sort_keys=True))


def _duration_ms(started_at: datetime, finished_at: datetime) -> int:
    return max(0, round((finished_at - started_at).total_seconds() * 1000))
