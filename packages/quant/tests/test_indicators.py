from __future__ import annotations

import pandas as pd

from trading_system_quant.indicators import compute_indicators


def _trend_frame(rows: int = 60) -> pd.DataFrame:
    close = pd.Series(range(1, rows + 1), dtype="float")
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": pd.Series(range(100, 100 + rows), dtype="float"),
        }
    )


def test_indicator_calculations_add_expected_columns() -> None:
    result = compute_indicators(_trend_frame())

    for column in [
        "SMA_20",
        "SMA_50",
        "EMA_20",
        "RSI_14",
        "MACD_12_26_9",
        "MACDs_12_26_9",
        "MACDh_12_26_9",
        "ATR_14",
        "VOLUME_SMA_20",
        "VOLUME_RATIO_20",
    ]:
        assert column in result.columns


def test_indicator_calculations_match_known_simple_values() -> None:
    result = compute_indicators(_trend_frame())
    latest = result.iloc[-1]

    assert latest["SMA_20"] == 50.5
    assert latest["SMA_50"] == 35.5
    assert latest["RSI_14"] == 100.0
    assert latest["ATR_14"] == 2.0
    assert round(latest["VOLUME_RATIO_20"], 4) == round(159 / 149.5, 4)
