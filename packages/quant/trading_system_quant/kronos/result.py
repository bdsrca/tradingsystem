from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


KronosStatus = Literal["ok", "timeout", "error", "skipped"]


class KronosDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class KronosHorizonForecast:
    horizon_days: int
    expected_return_pct: float
    direction: KronosDirection
    confidence: float
    forecast_close: float
    forecast_low: float
    forecast_high: float


@dataclass(frozen=True)
class KronosForecastResult:
    ticker: str
    exchange: str
    analysis_date: str
    lookback_bars: int
    sample_count: int
    horizons: list[KronosHorizonForecast]
    forecast_path: list[dict[str, float | str]]
    volatility_note: str | None
    model_name: str
    model_version: str
    runtime_ms: int
    status: KronosStatus
    is_fallback: bool = False
    error_message: str | None = None

    def primary_horizon(self, horizon_days: int = 20) -> KronosHorizonForecast | None:
        return next(
            (forecast for forecast in self.horizons if forecast.horizon_days == horizon_days),
            None,
        )


def fallback_result(
    *,
    ticker: str,
    exchange: str,
    analysis_date: str,
    lookback_bars: int,
    sample_count: int,
    model_name: str,
    model_version: str,
    status: KronosStatus,
    error_message: str,
    runtime_ms: int = 0,
    volatility_note: str | None = None,
) -> KronosForecastResult:
    return KronosForecastResult(
        ticker=ticker,
        exchange=exchange,
        analysis_date=analysis_date,
        lookback_bars=lookback_bars,
        sample_count=sample_count,
        horizons=[],
        forecast_path=[],
        volatility_note=volatility_note,
        model_name=model_name,
        model_version=model_version,
        runtime_ms=runtime_ms,
        status=status,
        is_fallback=True,
        error_message=error_message,
    )
