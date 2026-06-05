from __future__ import annotations

import asyncio
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.config import Settings
from trading_system_api.models import (
    AnalysisRun,
    DailyWorkerRun,
    DailyWorkerTickerResult,
    EmailNotification,
    MarketDataBar,
    WatchlistItem,
    utc_now,
)
from trading_system_data.symbols import SymbolIdentity
from trading_system_data.twelve_data import TimeSeriesBar, TwelveDataClient
from trading_system_email.digest import EmailDigest, EmailDigestItem, render_digest_text
from trading_system_quant.baseline import generate_baseline_signal
from trading_system_quant.signal_store import SignalCreate, append_signal
from trading_system_worker.daily import (
    DailyTickerInput,
    DailyTickerResult,
    DailyWorker,
    DailyWorkerLockRegistry,
)


_LOCK_REGISTRY = DailyWorkerLockRegistry()


async def run_daily_analysis(
    session: AsyncSession,
    settings: Settings,
    *,
    triggered_by: str = "manual",
) -> DailyWorkerRun:
    run = DailyWorkerRun(triggered_by=triggered_by, status="running", started_at=utc_now())
    session.add(run)
    await session.commit()
    await session.refresh(run)

    async def list_tickers() -> list[DailyTickerInput]:
        rows = (
            await session.execute(
                select(WatchlistItem)
                .where(WatchlistItem.enabled.is_(True))
                .order_by(WatchlistItem.created_at.asc())
            )
        ).scalars().all()
        return [
            DailyTickerInput(
                ticker=row.ticker,
                exchange=row.exchange,
                market=row.market,
                watchlist_item_id=row.id,
            )
            for row in rows
        ]

    async def analyze_ticker(item: DailyTickerInput) -> DailyTickerResult:
        return await _analyze_ticker(session, settings, item)

    worker = DailyWorker(
        list_tickers=list_tickers,
        analyze_ticker=analyze_ticker,
        lock_registry=_LOCK_REGISTRY,
    )
    result = await worker.run_once(triggered_by=triggered_by)

    for item in result.items:
        session.add(
            DailyWorkerTickerResult(
                worker_run_id=run.id,
                watchlist_item_id=item.watchlist_item_id,
                ticker=item.ticker,
                exchange=item.exchange,
                market=item.market,
                status=item.status,
                signal=item.signal,
                confidence=item.confidence,
                error_message=item.error_message,
                started_at=item.started_at,
                finished_at=item.finished_at,
            )
        )

    run.status = result.status
    run.finished_at = result.finished_at
    run.succeeded_count = result.succeeded_count
    run.failed_count = result.failed_count
    run.skipped_count = result.skipped_count
    run.stale_count = result.stale_count
    run.degraded_count = result.degraded_count
    run.summary = result.summary()
    if settings.daily_email_enabled and settings.daily_email_recipient:
        await _send_and_record_digest(session, settings, run, result)
    await session.commit()
    await session.refresh(run)
    return run


async def _analyze_ticker(
    session: AsyncSession,
    settings: Settings,
    item: DailyTickerInput,
) -> DailyTickerResult:
    started_at = utc_now()
    if not settings.twelve_data_api_key:
        return DailyTickerResult(
            ticker=item.ticker,
            exchange=item.exchange,
            market=item.market,
            watchlist_item_id=item.watchlist_item_id,
            status="stale",
            error_message="TWELVE_DATA_API_KEY is not configured",
            started_at=started_at,
            finished_at=utc_now(),
        )

    identity = SymbolIdentity(ticker=item.ticker, exchange=item.exchange, market=item.market)
    refresh_error: str | None = None
    try:
        bars = await TwelveDataClient(settings.twelve_data_api_key).fetch_daily_bars(identity)
    except Exception as exc:
        bars = []
        refresh_error = str(exc)

    if bars:
        await _upsert_bars(session, identity, bars)
    else:
        refresh_error = refresh_error or "No OHLCV bars returned"

    rows = await _load_bars(session, item.ticker, item.exchange)
    if not rows:
        return DailyTickerResult(
            ticker=item.ticker,
            exchange=item.exchange,
            market=item.market,
            watchlist_item_id=item.watchlist_item_id,
            status="stale",
            error_message=refresh_error,
            started_at=started_at,
            finished_at=utc_now(),
        )

    baseline = generate_baseline_signal(_bars_to_frame(rows))
    analysis_run = AnalysisRun(watchlist_item_id=item.watchlist_item_id, status="completed")
    session.add(analysis_run)
    await session.commit()
    await session.refresh(analysis_run)

    signal = await append_signal(
        session,
        SignalCreate(
            watchlist_item_id=item.watchlist_item_id,
            analysis_run_id=analysis_run.id,
            ticker=item.ticker,
            exchange=item.exchange,
            market=item.market,
            analysis_date=rows[-1].bar_date,
            signal=baseline.signal,
            confidence=baseline.confidence,
            entry_price=baseline.entry_price,
            risk_level=baseline.risk_level,
            reason=baseline.reason,
            indicators=baseline.indicators,
            layer_scores=baseline.layer_scores,
            source="baseline",
        ),
    )

    watchlist_item = await session.get(WatchlistItem, item.watchlist_item_id)
    if watchlist_item is not None:
        watchlist_item.last_analyzed_at = datetime.now(timezone.utc)
        await session.commit()

    return DailyTickerResult(
        ticker=item.ticker,
        exchange=item.exchange,
        market=item.market,
        watchlist_item_id=item.watchlist_item_id,
        status="degraded" if refresh_error else "succeeded",
        signal=signal.signal,
        confidence=float(signal.confidence or 0),
        reason=signal.reason,
        error_message=f"price refresh failed; used existing bars: {refresh_error}"
        if refresh_error
        else None,
        started_at=started_at,
        finished_at=utc_now(),
    )


async def _upsert_bars(
    session: AsyncSession,
    identity: SymbolIdentity,
    bars: list[TimeSeriesBar],
) -> None:
    for bar in bars:
        existing = (
            await session.execute(
                select(MarketDataBar).where(
                    MarketDataBar.ticker == identity.ticker,
                    MarketDataBar.exchange == identity.exchange,
                    MarketDataBar.bar_date == bar.bar_date,
                    MarketDataBar.source_provider == bar.source_provider,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            session.add(
                MarketDataBar(
                    ticker=identity.ticker,
                    exchange=identity.exchange,
                    bar_date=bar.bar_date,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                    source_provider=bar.source_provider,
                    source_symbol=bar.source_symbol,
                    fetched_at=bar.fetched_at,
                    adjustment_mode=bar.adjustment_mode,
                )
            )
        else:
            existing.open = bar.open
            existing.high = bar.high
            existing.low = bar.low
            existing.close = bar.close
            existing.volume = bar.volume
            existing.source_symbol = bar.source_symbol
            existing.fetched_at = bar.fetched_at
            existing.adjustment_mode = bar.adjustment_mode
    await session.commit()


async def _load_bars(session: AsyncSession, ticker: str, exchange: str) -> list[MarketDataBar]:
    return list(
        (
            await session.execute(
                select(MarketDataBar)
                .where(MarketDataBar.ticker == ticker, MarketDataBar.exchange == exchange)
                .order_by(MarketDataBar.bar_date.asc())
            )
        )
        .scalars()
        .all()
    )


def _bars_to_frame(rows: list[MarketDataBar]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": float(row.volume or 0),
            }
            for row in rows
        ]
    )


async def _send_and_record_digest(
    session: AsyncSession,
    settings: Settings,
    run: DailyWorkerRun,
    result,
) -> None:
    recipient = settings.daily_email_recipient
    if not recipient:
        return

    digest = EmailDigest(
        run_id=run.id,
        triggered_by=run.triggered_by,
        started_at=result.started_at,
        finished_at=result.finished_at,
        succeeded_count=result.succeeded_count,
        failed_count=result.failed_count,
        skipped_count=result.skipped_count,
        stale_count=result.stale_count,
        degraded_count=result.degraded_count,
        items=[
            EmailDigestItem(
                ticker=item.ticker,
                exchange=item.exchange,
                status=item.status,
                signal=item.signal,
                confidence=item.confidence,
                reason=item.reason,
                error_message=item.error_message,
            )
            for item in result.items
        ],
    )
    subject = f"Trading System daily digest: {result.status}"
    body = render_digest_text(digest)
    notification = EmailNotification(
        worker_run_id=run.id,
        recipient=recipient,
        subject=subject,
        body=body,
        status="pending",
        is_digest=True,
    )
    session.add(notification)

    try:
        await send_digest_email(
            recipient=recipient,
            subject=subject,
            body=body,
            settings=settings,
        )
    except Exception as exc:
        notification.status = "failed"
        notification.error_message = str(exc)
        run.email_sent = False
    else:
        notification.status = "sent"
        notification.sent_at = utc_now()
        run.email_sent = True


async def send_digest_email(
    *,
    recipient: str,
    subject: str,
    body: str,
    settings: Settings,
) -> None:
    await asyncio.to_thread(_send_digest_email_sync, recipient, subject, body, settings)


def _send_digest_email_sync(
    recipient: str,
    subject: str,
    body: str,
    settings: Settings,
) -> None:
    if not settings.smtp_host:
        raise ValueError("SMTP_HOST is not configured")
    sender = settings.smtp_from_email or settings.smtp_username
    if not sender:
        raise ValueError("SMTP_FROM_EMAIL or SMTP_USERNAME is required")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password or "")
        smtp.send_message(message)
