from __future__ import annotations

import pytest

from trading_system_quant.kronos.batching import (
    KronosBatchItem,
    group_kronos_batch_jobs,
    validate_batch_compatible,
)


def test_kronos_batch_grouping_by_lookback_length() -> None:
    jobs = [
        KronosBatchItem(ticker="AAPL", exchange="NASDAQ", lookback_bars=120, pred_len=30),
        KronosBatchItem(ticker="MSFT", exchange="NASDAQ", lookback_bars=120, pred_len=30),
        KronosBatchItem(ticker="SHOP", exchange="TSX", lookback_bars=90, pred_len=30),
        KronosBatchItem(ticker="RY", exchange="TSX", lookback_bars=120, pred_len=20),
    ]

    grouped = group_kronos_batch_jobs(jobs)

    assert list(grouped) == [(120, 30), (90, 30), (120, 20)]
    assert [item.ticker for item in grouped[(120, 30)]] == ["AAPL", "MSFT"]


def test_kronos_batch_validation_rejects_mixed_shapes() -> None:
    jobs = [
        KronosBatchItem(ticker="AAPL", exchange="NASDAQ", lookback_bars=120, pred_len=30),
        KronosBatchItem(ticker="SHOP", exchange="TSX", lookback_bars=90, pred_len=30),
    ]

    with pytest.raises(ValueError, match="same lookback"):
        validate_batch_compatible(jobs)
