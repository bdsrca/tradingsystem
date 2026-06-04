from __future__ import annotations

import pandas as pd


REQUIRED_BAR_COLUMNS = {"open", "high", "low", "close", "volume"}


def compute_indicators(bars: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_BAR_COLUMNS - set(bars.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {', '.join(sorted(missing))}")

    frame = bars.copy()
    close = frame["close"].astype(float)
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    volume = frame["volume"].astype(float)

    frame["SMA_20"] = close.rolling(window=20, min_periods=20).mean()
    frame["SMA_50"] = close.rolling(window=50, min_periods=50).mean()
    frame["EMA_20"] = close.ewm(span=20, adjust=False, min_periods=20).mean()
    frame["RSI_14"] = _rsi(close, length=14)

    macd = close.ewm(span=12, adjust=False, min_periods=12).mean() - close.ewm(
        span=26, adjust=False, min_periods=26
    ).mean()
    signal = macd.ewm(span=9, adjust=False, min_periods=9).mean()
    frame["MACD_12_26_9"] = macd
    frame["MACDs_12_26_9"] = signal
    frame["MACDh_12_26_9"] = macd - signal

    frame["ATR_14"] = _atr(high=high, low=low, close=close, length=14)
    frame["VOLUME_SMA_20"] = volume.rolling(window=20, min_periods=20).mean()
    frame["VOLUME_RATIO_20"] = volume / frame["VOLUME_SMA_20"]

    return frame


def _rsi(close: pd.Series, *, length: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=length, min_periods=length).mean()
    avg_loss = loss.rolling(window=length, min_periods=length).mean()
    relative_strength = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + relative_strength))
    return rsi.fillna(100).where(avg_loss == 0, rsi)


def _atr(*, high: pd.Series, low: pd.Series, close: pd.Series, length: int) -> pd.Series:
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window=length, min_periods=length).mean()
