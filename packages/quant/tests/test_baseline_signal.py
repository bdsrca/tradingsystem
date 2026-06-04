from __future__ import annotations

import pandas as pd

from trading_system_quant.baseline import MIN_BARS_FOR_BASELINE, generate_baseline_signal


def _base_frame(rows: int = MIN_BARS_FOR_BASELINE) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [100.0] * rows,
            "high": [102.0] * rows,
            "low": [98.0] * rows,
            "close": [100.0] * rows,
            "volume": [1000.0] * rows,
            "SMA_20": [100.0] * rows,
            "SMA_50": [100.0] * rows,
            "EMA_20": [100.0] * rows,
            "RSI_14": [50.0] * rows,
            "MACD_12_26_9": [0.0] * rows,
            "MACDs_12_26_9": [0.0] * rows,
            "MACDh_12_26_9": [0.0] * rows,
            "ATR_14": [2.0] * rows,
            "VOLUME_RATIO_20": [1.0] * rows,
        }
    )


def test_baseline_returns_hold_for_insufficient_history() -> None:
    result = generate_baseline_signal(_base_frame(rows=20))

    assert result.signal == "HOLD"
    assert result.confidence == 0.0
    assert result.reason == "insufficient_history"


def test_baseline_signal_labels_buy_watch_hold_reduce_sell() -> None:
    buy = _base_frame()
    buy.loc[buy.index[-2], ["RSI_14", "MACD_12_26_9", "MACDs_12_26_9"]] = [55.0, 0.5, 0.7]
    buy.loc[buy.index[-1], [
        "close",
        "SMA_20",
        "SMA_50",
        "EMA_20",
        "RSI_14",
        "MACD_12_26_9",
        "MACDs_12_26_9",
        "ATR_14",
        "VOLUME_RATIO_20",
    ]] = [100.0, 105.0, 90.0, 95.0, 62.0, 1.2, 0.8, 2.0, 1.4]
    assert generate_baseline_signal(buy).signal == "BUY"

    watch = _base_frame()
    watch.loc[watch.index[-1], [
        "close",
        "SMA_20",
        "SMA_50",
        "EMA_20",
        "RSI_14",
        "MACD_12_26_9",
        "MACDs_12_26_9",
        "ATR_14",
        "VOLUME_RATIO_20",
    ]] = [100.0, 105.0, 90.0, 95.0, 80.0, 0.1, 0.1, 2.0, 0.8]
    assert generate_baseline_signal(watch).signal == "WATCH"

    hold = _base_frame()
    hold.loc[hold.index[-1], ["RSI_14", "ATR_14"]] = [80.0, 20.0]
    assert generate_baseline_signal(hold).signal == "HOLD"

    reduce = _base_frame()
    reduce.loc[reduce.index[-2], ["RSI_14", "MACD_12_26_9", "MACDs_12_26_9"]] = [55.0, 0.4, 0.2]
    reduce.loc[reduce.index[-1], [
        "close",
        "SMA_20",
        "SMA_50",
        "EMA_20",
        "RSI_14",
        "MACD_12_26_9",
        "MACDs_12_26_9",
        "ATR_14",
        "VOLUME_RATIO_20",
    ]] = [90.0, 85.0, 100.0, 95.0, 45.0, 0.1, 0.1, 4.0, 1.0]
    assert generate_baseline_signal(reduce).signal == "REDUCE"

    sell = _base_frame()
    sell.loc[sell.index[-2], ["RSI_14", "MACD_12_26_9", "MACDs_12_26_9"]] = [45.0, 0.5, 0.2]
    sell.loc[sell.index[-1], [
        "close",
        "SMA_20",
        "SMA_50",
        "EMA_20",
        "RSI_14",
        "MACD_12_26_9",
        "MACDs_12_26_9",
        "ATR_14",
        "VOLUME_RATIO_20",
    ]] = [80.0, 85.0, 100.0, 90.0, 30.0, -0.4, 0.1, 12.0, 1.4]
    assert generate_baseline_signal(sell).signal == "SELL"


def test_baseline_signal_includes_atr_stop_level() -> None:
    frame = _base_frame()
    frame.loc[frame.index[-1], [
        "close",
        "SMA_20",
        "SMA_50",
        "EMA_20",
        "RSI_14",
        "MACD_12_26_9",
        "MACDs_12_26_9",
        "ATR_14",
        "VOLUME_RATIO_20",
    ]] = [100.0, 105.0, 90.0, 95.0, 62.0, 1.2, 0.8, 3.0, 1.4]

    result = generate_baseline_signal(frame)

    assert result.entry_price == 100.0
    assert result.risk_level == 94.0
