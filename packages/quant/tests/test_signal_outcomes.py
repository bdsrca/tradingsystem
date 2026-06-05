from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from trading_system_quant.signal_outcomes import (
    classify_signal_evaluation,
    compute_signal_return_pct,
    target_trading_day,
)


def test_classify_signal_evaluation_flags_backfilled_signals() -> None:
    assert (
        classify_signal_evaluation(
            analysis_date=date(2026, 6, 4),
            created_at=datetime(2026, 6, 5, tzinfo=timezone.utc),
        ).eligibility
        == "trusted"
    )
    assert (
        classify_signal_evaluation(
            analysis_date=date(2026, 6, 4),
            created_at=datetime(2026, 6, 9, tzinfo=timezone.utc),
        ).eligibility
        == "delayed"
    )
    assert (
        classify_signal_evaluation(
            analysis_date=date(2026, 3, 12),
            created_at=datetime(2026, 6, 5, tzinfo=timezone.utc),
        ).eligibility
        == "backfilled"
    )


def test_target_trading_day_skips_weekends() -> None:
    assert target_trading_day("NASDAQ", date(2026, 6, 5), 1) == date(2026, 6, 8)


def test_compute_signal_return_pct_uses_signal_direction() -> None:
    assert compute_signal_return_pct("BUY", Decimal("100"), Decimal("110")) == Decimal("10")
    assert compute_signal_return_pct("SELL", Decimal("100"), Decimal("90")) == Decimal("10")
    assert compute_signal_return_pct("HOLD", Decimal("100"), Decimal("110")) == Decimal("0")
