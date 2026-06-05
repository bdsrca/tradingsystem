from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.models import MarketDataBar, Signal, SignalOutcome, utc_now
from trading_system_quant.signal_outcomes import (
    classify_signal_evaluation,
    compute_signal_return_pct,
    realized_outcome,
    target_trading_day,
)


@dataclass(frozen=True)
class BackfillResult:
    horizon_days: int
    filled_count: int
    skipped_count: int


@dataclass(frozen=True)
class AccuracyResult:
    ticker: str | None
    exchange: str | None
    window: int
    evaluated_count: int
    trusted_count: int
    delayed_count: int
    backfilled_count: int
    backfilled_excluded_count: int
    win_rate_pct: float
    average_return_pct: float


async def backfill_signal_outcomes(
    session: AsyncSession,
    *,
    horizon_days: int,
    ticker: str | None = None,
    exchange: str | None = None,
) -> BackfillResult:
    statement = select(Signal).where(
        Signal.is_superseded.is_(False),
        Signal.analysis_date.is_not(None),
        Signal.signal.is_not(None),
        Signal.ticker.is_not(None),
        Signal.exchange.is_not(None),
    )
    if ticker:
        statement = statement.where(Signal.ticker == ticker.upper())
    if exchange:
        statement = statement.where(Signal.exchange == exchange.upper())

    signals = (await session.execute(statement)).scalars().all()
    filled_count = 0
    skipped_count = 0

    for signal in signals:
        outcome = await _build_outcome(session, signal, horizon_days=horizon_days)
        if outcome is None:
            skipped_count += 1
            continue
        existing = (
            await session.execute(
                select(SignalOutcome).where(
                    SignalOutcome.signal_id == signal.id,
                    SignalOutcome.horizon_days == horizon_days,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            session.add(outcome)
        else:
            _copy_outcome(existing, outcome)
        _sync_signal_realized_fields(signal, outcome)
        filled_count += 1

    await session.commit()
    return BackfillResult(
        horizon_days=horizon_days,
        filled_count=filled_count,
        skipped_count=skipped_count,
    )


async def calculate_accuracy(
    session: AsyncSession,
    *,
    window: int,
    ticker: str | None = None,
    exchange: str | None = None,
    include_backfilled: bool = False,
) -> AccuracyResult:
    statement = select(SignalOutcome).where(SignalOutcome.horizon_days == window)
    if ticker:
        statement = statement.where(SignalOutcome.ticker == ticker.upper())
    if exchange:
        statement = statement.where(SignalOutcome.exchange == exchange.upper())

    all_outcomes = (await session.execute(statement)).scalars().all()
    backfilled_count = sum(
        1 for outcome in all_outcomes if outcome.evaluation_eligibility == "backfilled"
    )
    outcomes = (
        all_outcomes
        if include_backfilled
        else [
            outcome
            for outcome in all_outcomes
            if outcome.evaluation_eligibility != "backfilled"
        ]
    )
    evaluated_count = len(outcomes)
    wins = sum(1 for outcome in outcomes if Decimal(str(outcome.realized_return_pct)) > 0)
    total_return = sum(
        (Decimal(str(outcome.realized_return_pct)) for outcome in outcomes),
        Decimal("0"),
    )

    return AccuracyResult(
        ticker=ticker.upper() if ticker else None,
        exchange=exchange.upper() if exchange else None,
        window=window,
        evaluated_count=evaluated_count,
        trusted_count=sum(1 for item in outcomes if item.evaluation_eligibility == "trusted"),
        delayed_count=sum(1 for item in outcomes if item.evaluation_eligibility == "delayed"),
        backfilled_count=backfilled_count,
        backfilled_excluded_count=0 if include_backfilled else backfilled_count,
        win_rate_pct=float((Decimal(wins) / Decimal(evaluated_count)) * Decimal("100"))
        if evaluated_count
        else 0.0,
        average_return_pct=float(total_return / Decimal(evaluated_count))
        if evaluated_count
        else 0.0,
    )


async def _build_outcome(
    session: AsyncSession,
    signal: Signal,
    *,
    horizon_days: int,
) -> SignalOutcome | None:
    target_date = target_trading_day(str(signal.exchange), signal.analysis_date, horizon_days)
    target_bar = await _bar_for_date(session, str(signal.ticker), str(signal.exchange), target_date)
    if target_bar is None:
        return None

    entry_price = await _entry_price(session, signal)
    if entry_price is None:
        return None

    realized_price = Decimal(str(target_bar.close))
    return_pct = compute_signal_return_pct(str(signal.signal), entry_price, realized_price)
    evaluation = classify_signal_evaluation(
        analysis_date=signal.analysis_date,
        created_at=signal.created_at,
    )
    return SignalOutcome(
        signal_id=signal.id,
        ticker=str(signal.ticker),
        exchange=str(signal.exchange),
        horizon_days=horizon_days,
        target_date=target_date,
        realized_price=realized_price,
        realized_return_pct=return_pct,
        realized_outcome=realized_outcome(return_pct),
        evaluation_eligibility=evaluation.eligibility,
        lag_days=evaluation.lag_days,
        filled_at=utc_now(),
    )


async def _entry_price(session: AsyncSession, signal: Signal) -> Decimal | None:
    if signal.entry_price is not None:
        return Decimal(str(signal.entry_price))
    bar = await _bar_for_date(
        session,
        str(signal.ticker),
        str(signal.exchange),
        signal.analysis_date,
    )
    if bar is None:
        return None
    return Decimal(str(bar.close))


async def _bar_for_date(
    session: AsyncSession,
    ticker: str,
    exchange: str,
    bar_date,
) -> MarketDataBar | None:
    return (
        await session.execute(
            select(MarketDataBar).where(
                MarketDataBar.ticker == ticker,
                MarketDataBar.exchange == exchange,
                MarketDataBar.bar_date == bar_date,
            )
        )
    ).scalars().first()


def _copy_outcome(existing: SignalOutcome, outcome: SignalOutcome) -> None:
    existing.ticker = outcome.ticker
    existing.exchange = outcome.exchange
    existing.target_date = outcome.target_date
    existing.realized_price = outcome.realized_price
    existing.realized_return_pct = outcome.realized_return_pct
    existing.realized_outcome = outcome.realized_outcome
    existing.evaluation_eligibility = outcome.evaluation_eligibility
    existing.lag_days = outcome.lag_days
    existing.filled_at = outcome.filled_at


def _sync_signal_realized_fields(signal: Signal, outcome: SignalOutcome) -> None:
    signal.realized_return_pct = outcome.realized_return_pct
    signal.realized_outcome = outcome.realized_outcome
    signal.realized_at = outcome.target_date
