from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.models import (
    DailyWorkerRun,
    DailyWorkerTickerResult,
    PaperSimulationRun,
    Signal,
    SignalOutcome,
    WatchlistItem,
)

STRONG_SIGNAL_THRESHOLD = 0.7


async def build_dashboard_summary(session: AsyncSession) -> dict[str, Any]:
    latest_run = (
        await session.execute(
            select(DailyWorkerRun).order_by(desc(DailyWorkerRun.started_at)).limit(1)
        )
    ).scalar_one_or_none()
    latest_results = await _latest_daily_results(session, latest_run.id if latest_run else None)
    rows = await _watchlist_rows(session, latest_results)
    attention = _attention_items(rows, latest_results)
    accuracy = await _accuracy_snapshot(session)

    return {
        "latest_run": _latest_run_payload(latest_run),
        "attention_items": attention,
        "watchlist_rows": rows,
        "accuracy_snapshot": accuracy,
        "paper_snapshot": {"window_years": 1},
        "service_warnings": _service_warnings(rows),
        "generated_at": datetime.now(UTC),
        "cache_hit": False,
    }


async def _latest_daily_results(
    session: AsyncSession,
    run_id: str | None,
) -> dict[tuple[str, str], DailyWorkerTickerResult]:
    if run_id is None:
        return {}
    results = (
        await session.execute(
            select(DailyWorkerTickerResult).where(DailyWorkerTickerResult.worker_run_id == run_id)
        )
    ).scalars().all()
    return {(row.ticker, row.exchange): row for row in results}


async def _watchlist_rows(
    session: AsyncSession,
    latest_results: dict[tuple[str, str], DailyWorkerTickerResult],
) -> list[dict[str, Any]]:
    watchlist = (
        await session.execute(
            select(WatchlistItem)
            .where(WatchlistItem.enabled.is_(True))
            .order_by(WatchlistItem.ticker, WatchlistItem.exchange)
        )
    ).scalars().all()
    signals = await _latest_signals(session)
    paper_runs = await _latest_one_year_paper_runs(session)

    rows: list[dict[str, Any]] = []
    for item in watchlist:
        key = (item.ticker, item.exchange)
        result = latest_results.get(key)
        signal = signals.get(key)
        paper_run = paper_runs.get(key)
        metrics = paper_run.metrics if paper_run and paper_run.metrics else {}
        data_freshness = result.data_freshness if result else "unknown"
        caveat = _row_caveat(data_freshness, signal)
        rows.append(
            {
                "ticker": item.ticker,
                "exchange": item.exchange,
                "market": item.market,
                "display_name": item.display_name,
                "latest_signal": result.signal if result and result.signal else signal.signal if signal else None,
                "confidence": result.confidence
                if result and result.confidence is not None
                else float(signal.confidence)
                if signal and signal.confidence is not None
                else None,
                "data_freshness": data_freshness,
                "last_analyzed_at": item.last_analyzed_at,
                "accuracy_20d_win_rate_pct": None,
                "paper_1y_return_pct": _metric(metrics, "total_return_pct"),
                "paper_1y_max_drawdown_pct": _metric(metrics, "max_drawdown_pct"),
                "caveat": caveat,
            }
        )
    return sorted(rows, key=_row_sort_key)


async def _latest_signals(session: AsyncSession) -> dict[tuple[str, str], Signal]:
    signals = (
        await session.execute(
            select(Signal)
            .where(
                Signal.is_superseded.is_(False),
                Signal.ticker.is_not(None),
                Signal.exchange.is_not(None),
            )
            .order_by(desc(Signal.created_at))
        )
    ).scalars().all()
    latest: dict[tuple[str, str], Signal] = {}
    for signal in signals:
        key = (str(signal.ticker), str(signal.exchange))
        latest.setdefault(key, signal)
    return latest


async def _latest_one_year_paper_runs(
    session: AsyncSession,
) -> dict[tuple[str, str], PaperSimulationRun]:
    runs = (
        await session.execute(
            select(PaperSimulationRun)
            .where(PaperSimulationRun.window_years == 1)
            .order_by(desc(PaperSimulationRun.created_at))
        )
    ).scalars().all()
    latest: dict[tuple[str, str], PaperSimulationRun] = {}
    for run in runs:
        latest.setdefault((run.ticker, run.exchange), run)
    return latest


async def _accuracy_snapshot(session: AsyncSession) -> dict[str, float | int]:
    outcomes = (
        await session.execute(select(SignalOutcome).where(SignalOutcome.horizon_days == 20))
    ).scalars().all()
    backfilled_count = sum(
        1 for outcome in outcomes if outcome.evaluation_eligibility == "backfilled"
    )
    trusted = [outcome for outcome in outcomes if outcome.evaluation_eligibility != "backfilled"]
    evaluated_count = len(trusted)
    wins = sum(1 for outcome in trusted if Decimal(str(outcome.realized_return_pct)) > 0)
    total_return = sum(
        (Decimal(str(outcome.realized_return_pct)) for outcome in trusted),
        Decimal("0"),
    )
    return {
        "window": 20,
        "evaluated_count": evaluated_count,
        "win_rate_pct": float((Decimal(wins) / Decimal(evaluated_count)) * Decimal("100"))
        if evaluated_count
        else 0.0,
        "average_return_pct": float(total_return / Decimal(evaluated_count))
        if evaluated_count
        else 0.0,
        "backfilled_excluded_count": backfilled_count,
    }


def _latest_run_payload(run: DailyWorkerRun | None) -> dict[str, Any] | None:
    if run is None:
        return None
    return {
        "id": run.id,
        "status": run.status,
        "started_at": run.started_at,
        "succeeded_count": run.succeeded_count,
        "failed_count": run.failed_count,
        "skipped_count": run.skipped_count,
        "stale_count": run.stale_count,
        "degraded_count": run.degraded_count,
        "email_sent": run.email_sent,
    }


def _attention_items(
    rows: list[dict[str, Any]],
    latest_results: dict[tuple[str, str], DailyWorkerTickerResult],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in rows:
        result = latest_results.get((row["ticker"], row["exchange"]))
        if result and (result.status == "failed" or result.data_freshness == "no_data"):
            reason = result.error_message or "No data available"
            if result.data_freshness == "no_data" and "no data" not in reason.lower():
                reason = f"No data: {reason}"
            items.append(_attention(row, "error", reason))
            continue
        if result and (result.status == "degraded" or result.data_freshness == "stale_used"):
            reason = result.error_message or "Stale cache or degraded analysis"
            items.append(_attention(row, "warning", reason))
            continue
        if (
            row["latest_signal"] in {"BUY", "SELL", "REDUCE"}
            and row["confidence"] is not None
            and row["confidence"] >= STRONG_SIGNAL_THRESHOLD
        ):
            items.append(
                _attention(
                    row,
                    "signal",
                    f"Strong {row['latest_signal']} signal at {row['confidence']:.2f}",
                )
            )
    severity_rank = {"error": 0, "warning": 1, "signal": 2}
    return sorted(items, key=lambda item: (severity_rank[item["severity"]], item["ticker"]))


def _attention(row: dict[str, Any], severity: str, reason: str) -> dict[str, Any]:
    return {
        "ticker": row["ticker"],
        "exchange": row["exchange"],
        "severity": severity,
        "reason": reason,
        "signal": row["latest_signal"],
        "confidence": row["confidence"],
        "href": f"/stock/{row['ticker']}?exchange={row['exchange']}",
    }


def _service_warnings(rows: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    no_data = sum(1 for row in rows if row["data_freshness"] == "no_data")
    stale = sum(1 for row in rows if row["data_freshness"] == "stale_used")
    if no_data:
        warnings.append(f"{no_data} tickers have no data")
    if stale:
        warnings.append(f"{stale} tickers used stale cache")
    return warnings


def _row_caveat(data_freshness: str, signal: Signal | None) -> str | None:
    if data_freshness == "no_data":
        return "No fresh bars"
    if data_freshness == "stale_used":
        return "Used stale cache"
    if signal and signal.source and "kronos" in signal.source.lower():
        return "Kronos cross-market caveat"
    return None


def _row_sort_key(row: dict[str, Any]) -> tuple[int, str]:
    if row["data_freshness"] == "no_data":
        return (0, row["ticker"])
    if row["caveat"] and "stale" in row["caveat"].lower():
        return (2, row["ticker"])
    if (
        row["latest_signal"] in {"BUY", "SELL", "REDUCE"}
        and row["confidence"] is not None
        and row["confidence"] >= STRONG_SIGNAL_THRESHOLD
    ):
        return (1, row["ticker"])
    return (3, row["ticker"])


def _metric(metrics: dict[str, Any], key: str) -> float | None:
    value = metrics.get(key)
    return float(value) if value is not None else None
