from __future__ import annotations

from datetime import date, timedelta

import pandas_market_calendars as mcal


EXCHANGE_TO_CALENDAR = {
    "NASDAQ": "NASDAQ",
    "NYSE": "NYSE",
    "TSX": "XTSE",
    "TSXV": "XTSE",
}


def get_trading_days_forward(exchange: str, from_date: date, n_days: int) -> list[date]:
    if n_days <= 0:
        return []

    cal = _get_calendar(exchange)
    window_days = max(n_days * 3, 14)

    while True:
        schedule = cal.schedule(
            start_date=from_date.isoformat(),
            end_date=(from_date + timedelta(days=window_days)).isoformat(),
        )
        days = [item.date() for item in schedule.index]
        days = [_apply_exchange_overrides(exchange, day) for day in days]
        unique_days = sorted(set(days))
        if len(unique_days) >= n_days:
            return unique_days[:n_days]
        window_days *= 2


def is_trading_day(exchange: str, day: date) -> bool:
    if _is_tsx_remembrance_day(exchange, day):
        return True

    cal = _get_calendar(exchange)
    schedule = cal.schedule(start_date=day.isoformat(), end_date=day.isoformat())
    return not schedule.empty


def _get_calendar(exchange: str):
    exchange_key = exchange.upper()
    cal_name = EXCHANGE_TO_CALENDAR.get(exchange_key)
    if cal_name is None:
        raise ValueError(f"Unsupported exchange: {exchange}")

    try:
        return mcal.get_calendar(cal_name)
    except RuntimeError:
        if cal_name == "NASDAQ":
            return mcal.get_calendar("NYSE")
        raise


def _apply_exchange_overrides(exchange: str, day: date) -> date:
    return day


def _is_tsx_remembrance_day(exchange: str, day: date) -> bool:
    return exchange.upper() in {"TSX", "TSXV"} and day.month == 11 and day.day == 11

