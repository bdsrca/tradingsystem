from __future__ import annotations

from dataclasses import dataclass
from math import isnan
from typing import Any

import pandas as pd

from trading_system_quant.indicators import compute_indicators


MIN_BARS_FOR_BASELINE = 60
SIGNAL_COLUMNS = [
    "SMA_20",
    "SMA_50",
    "EMA_20",
    "RSI_14",
    "MACD_12_26_9",
    "MACDs_12_26_9",
    "MACDh_12_26_9",
    "ATR_14",
    "VOLUME_RATIO_20",
]


@dataclass(frozen=True)
class SignalResult:
    signal: str
    confidence: float
    reason: str
    entry_price: float | None
    risk_level: float | None
    indicators: dict[str, float]
    layer_scores: dict[str, float]


def generate_baseline_signal(bars: pd.DataFrame) -> SignalResult:
    if len(bars) < MIN_BARS_FOR_BASELINE:
        return _hold("insufficient_history")

    frame = _ensure_indicators(bars)
    latest = frame.iloc[-1]
    previous = frame.iloc[-2]

    if any(_is_missing(latest[column]) for column in SIGNAL_COLUMNS):
        return _hold("indicator_warmup")

    close = float(latest["close"])
    atr = float(latest["ATR_14"])
    indicators = {column: float(latest[column]) for column in SIGNAL_COLUMNS}

    buy_layers = {
        "trend": _score(
            latest["SMA_20"] > latest["SMA_50"] and close > float(latest["EMA_20"])
        ),
        "momentum": _score(40 <= float(latest["RSI_14"]) <= 70 and latest["RSI_14"] >= previous["RSI_14"]),
        "confirmation": _score(
            latest["MACD_12_26_9"] > latest["MACDs_12_26_9"]
            and previous["MACD_12_26_9"] <= previous["MACDs_12_26_9"]
        ),
        "risk": _score(atr > 0 and atr / close <= 0.08),
        "volume": _score(float(latest["VOLUME_RATIO_20"]) >= 1.2),
    }
    sell_layers = {
        "trend": _score(
            latest["SMA_20"] < latest["SMA_50"] and close < float(latest["EMA_20"])
        ),
        "momentum": _score(float(latest["RSI_14"]) <= 35 or latest["RSI_14"] < previous["RSI_14"]),
        "confirmation": _score(latest["MACD_12_26_9"] < latest["MACDs_12_26_9"]),
        "risk": _score(atr > 0 and atr / close >= 0.10),
        "volume": _score(float(latest["VOLUME_RATIO_20"]) >= 1.2),
    }

    buy_score = round(sum(buy_layers.values()), 4)
    sell_score = round(sum(sell_layers.values()), 4)

    if sell_score >= 0.6:
        return _result("SELL", sell_score, close, atr, indicators, sell_layers, "bearish_baseline")
    if sell_score >= 0.4:
        return _result("REDUCE", sell_score, close, atr, indicators, sell_layers, "bearish_caution")
    if buy_score >= 0.6:
        return _result("BUY", buy_score, close, atr, indicators, buy_layers, "bullish_baseline")
    if buy_score >= 0.4:
        return _result("WATCH", buy_score, close, atr, indicators, buy_layers, "bullish_watch")

    return _result("HOLD", max(buy_score, sell_score), close, atr, indicators, buy_layers, "mixed_baseline")


def _ensure_indicators(bars: pd.DataFrame) -> pd.DataFrame:
    if all(column in bars.columns for column in SIGNAL_COLUMNS):
        return bars.copy()
    return compute_indicators(bars)


def _score(condition: Any) -> float:
    return 0.2 if bool(condition) else 0.0


def _result(
    signal: str,
    confidence: float,
    close: float,
    atr: float,
    indicators: dict[str, float],
    layer_scores: dict[str, float],
    reason: str,
) -> SignalResult:
    return SignalResult(
        signal=signal,
        confidence=confidence,
        reason=reason,
        entry_price=close,
        risk_level=round(close - (2 * atr), 4) if atr > 0 else None,
        indicators=indicators,
        layer_scores=layer_scores,
    )


def _hold(reason: str) -> SignalResult:
    return SignalResult(
        signal="HOLD",
        confidence=0.0,
        reason=reason,
        entry_price=None,
        risk_level=None,
        indicators={},
        layer_scores={},
    )


def _is_missing(value: Any) -> bool:
    try:
        return bool(pd.isna(value) or isnan(float(value)))
    except (TypeError, ValueError):
        return True
