from datetime import date

from trading_system_quant.calendar import get_trading_days_forward, is_trading_day


def test_get_trading_days_forward_for_nasdaq_week() -> None:
    days = get_trading_days_forward("NASDAQ", date(2026, 6, 1), 5)

    assert days == [
        date(2026, 6, 1),
        date(2026, 6, 2),
        date(2026, 6, 3),
        date(2026, 6, 4),
        date(2026, 6, 5),
    ]


def test_tsx_remembrance_day_is_trading_day() -> None:
    assert is_trading_day("TSX", date(2026, 11, 11))

