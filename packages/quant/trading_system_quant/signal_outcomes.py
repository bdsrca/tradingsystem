from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from trading_system_quant.calendar import get_trading_days_forward

EvaluationEligibility = str


@dataclass(frozen=True)
class SignalEvaluation:
    eligibility: EvaluationEligibility
    lag_days: int


def classify_signal_evaluation(*, analysis_date: date, created_at: datetime) -> SignalEvaluation:
    lag_days = (created_at.date() - analysis_date).days
    if lag_days <= 1:
        eligibility = "trusted"
    elif lag_days <= 7:
        eligibility = "delayed"
    else:
        eligibility = "backfilled"
    return SignalEvaluation(eligibility=eligibility, lag_days=lag_days)


def target_trading_day(exchange: str, analysis_date: date, horizon_days: int) -> date:
    if horizon_days <= 0:
        raise ValueError("horizon_days must be positive")
    start = analysis_date + timedelta(days=1)
    return get_trading_days_forward(exchange, start, horizon_days)[-1]


def compute_signal_return_pct(
    signal: str,
    entry_price: Decimal,
    realized_price: Decimal,
) -> Decimal:
    if entry_price <= 0:
        raise ValueError("entry_price must be positive")
    signal_name = signal.upper()
    if signal_name in {"BUY", "WATCH"}:
        return ((realized_price - entry_price) / entry_price) * Decimal("100")
    if signal_name in {"SELL", "REDUCE"}:
        return ((entry_price - realized_price) / entry_price) * Decimal("100")
    return Decimal("0")


def realized_outcome(return_pct: Decimal) -> str:
    if return_pct > 0:
        return "win"
    if return_pct < 0:
        return "loss"
    return "flat"
