from __future__ import annotations

from datetime import date

import pandas as pd

from trading_system_quant.kronos.adapter import adapt_kronos_output, prepare_kronos_input
from trading_system_quant.kronos.result import KronosDirection


def _bars(rows: int) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    return pd.DataFrame(
        {
            "open": [100.0 + i for i in range(rows)],
            "high": [101.0 + i for i in range(rows)],
            "low": [99.0 + i for i in range(rows)],
            "close": [100.0 + i for i in range(rows)],
            "volume": [1_000_000 + i for i in range(rows)],
        },
        index=dates,
    )


def test_prepare_kronos_input_requires_minimum_history() -> None:
    prepared = prepare_kronos_input(_bars(99), ticker="AAPL", exchange="NASDAQ")

    assert prepared.status == "skipped"
    assert prepared.error_message == "insufficient_history"


def test_prepare_kronos_input_zero_fills_amount_and_trims_context() -> None:
    prepared = prepare_kronos_input(_bars(600), ticker="AAPL", exchange="NASDAQ")

    assert prepared.status == "ok"
    assert len(prepared.frame) == 512
    assert "amount" in prepared.frame.columns
    assert prepared.frame["amount"].sum() == 0
    assert prepared.volatility_note == "amount_unavailable_zero_filled"


def test_kronos_dataframe_to_forecast_result() -> None:
    index = pd.date_range("2026-04-01", periods=30, freq="D")
    pred = pd.DataFrame(
        {
            "open": [101.0 + i for i in range(30)],
            "high": [102.0 + i for i in range(30)],
            "low": [100.0 + i for i in range(30)],
            "close": [101.0 + i for i in range(30)],
            "volume": [1_000_000] * 30,
            "amount": [0.0] * 30,
        },
        index=index,
    )

    result = adapt_kronos_output(
        ticker="AAPL",
        exchange="NASDAQ",
        analysis_date=date(2026, 3, 31),
        current_close=100.0,
        predicted=pred,
        model_name="NeoQuasar/Kronos-small",
        model_version="67b630e",
        lookback_bars=120,
        sample_count=1,
        runtime_ms=1234,
        volatility_note="amount_unavailable_zero_filled",
    )

    assert result.status == "ok"
    assert result.horizons[0].horizon_days == 5
    assert result.horizons[0].direction == KronosDirection.BULLISH
    assert result.horizons[0].expected_return_pct == 5.0
    assert result.horizons[-1].forecast_close == 130.0
    assert result.forecast_path[0]["time"] == "2026-04-01"
    assert result.volatility_note == "amount_unavailable_zero_filled"
