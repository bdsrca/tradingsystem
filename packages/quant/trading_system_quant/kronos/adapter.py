from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

import pandas as pd

from trading_system_quant.kronos.result import (
    KronosDirection,
    KronosForecastResult,
    KronosHorizonForecast,
)


MIN_KRONOS_BARS = 100
MAX_KRONOS_CONTEXT = 512
DEFAULT_HORIZONS = [5, 10, 20, 30]
REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]


@dataclass(frozen=True)
class PreparedKronosInput:
    ticker: str
    exchange: str
    frame: pd.DataFrame
    status: Literal["ok", "skipped"]
    volatility_note: str | None
    error_message: str | None = None


def prepare_kronos_input(
    bars: pd.DataFrame,
    *,
    ticker: str,
    exchange: str,
) -> PreparedKronosInput:
    missing = [column for column in REQUIRED_COLUMNS if column not in bars.columns]
    if missing:
        raise ValueError(f"Missing Kronos OHLCV columns: {', '.join(missing)}")
    if len(bars) < MIN_KRONOS_BARS:
        return PreparedKronosInput(
            ticker=ticker,
            exchange=exchange,
            frame=bars.copy(),
            status="skipped",
            volatility_note=None,
            error_message="insufficient_history",
        )

    frame = bars.tail(MAX_KRONOS_CONTEXT).copy()
    volatility_note = None
    if "amount" not in frame.columns:
        frame["amount"] = 0.0
        volatility_note = "amount_unavailable_zero_filled"
    return PreparedKronosInput(
        ticker=ticker,
        exchange=exchange,
        frame=frame[["open", "high", "low", "close", "volume", "amount"]],
        status="ok",
        volatility_note=volatility_note,
    )


def adapt_kronos_output(
    *,
    ticker: str,
    exchange: str,
    analysis_date: date,
    current_close: float,
    predicted: pd.DataFrame,
    model_name: str,
    model_version: str,
    lookback_bars: int,
    sample_count: int,
    runtime_ms: int,
    volatility_note: str | None,
    neutral_threshold_pct: float = 0.5,
) -> KronosForecastResult:
    if "close" not in predicted.columns:
        raise ValueError("Kronos prediction must include close column")

    horizons: list[KronosHorizonForecast] = []
    for horizon_days in DEFAULT_HORIZONS:
        if len(predicted) < horizon_days:
            continue
        window = predicted.iloc[:horizon_days]
        forecast_close = float(window.iloc[-1]["close"])
        expected_return_pct = round(((forecast_close - current_close) / current_close) * 100, 2)
        horizons.append(
            KronosHorizonForecast(
                horizon_days=horizon_days,
                expected_return_pct=expected_return_pct,
                direction=_direction(expected_return_pct, neutral_threshold_pct),
                confidence=_conservative_confidence(expected_return_pct),
                forecast_close=round(forecast_close, 4),
                forecast_low=round(float(window["close"].min()), 4),
                forecast_high=round(float(window["close"].max()), 4),
            )
        )

    return KronosForecastResult(
        ticker=ticker,
        exchange=exchange,
        analysis_date=analysis_date.isoformat(),
        lookback_bars=lookback_bars,
        sample_count=sample_count,
        horizons=horizons,
        forecast_path=[
            {"time": _iso_index_value(index), "close": round(float(row["close"]), 4)}
            for index, row in predicted.iterrows()
        ],
        volatility_note=volatility_note,
        model_name=model_name,
        model_version=model_version,
        runtime_ms=runtime_ms,
        status="ok",
    )


def _direction(expected_return_pct: float, threshold_pct: float) -> KronosDirection:
    if expected_return_pct > threshold_pct:
        return KronosDirection.BULLISH
    if expected_return_pct < -threshold_pct:
        return KronosDirection.BEARISH
    return KronosDirection.NEUTRAL


def _conservative_confidence(expected_return_pct: float) -> float:
    return round(max(0.1, min(0.8, abs(expected_return_pct) / 10)), 3)


def _iso_index_value(value) -> str:
    if hasattr(value, "date"):
        return value.date().isoformat()
    return str(value)
