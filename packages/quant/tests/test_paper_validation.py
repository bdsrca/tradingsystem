from __future__ import annotations

from datetime import date, timedelta

from trading_system_quant.paper import (
    PaperBar,
    PaperSignal,
    SimConfig,
    compute_metrics,
    create_portfolio_snapshots,
    simulate_trades,
)


def _bars(start: date, count: int, close: float = 100.0) -> dict[str, dict[date, PaperBar]]:
    return {
        "AAPL": {
            start + timedelta(days=index): PaperBar(
                bar_date=start + timedelta(days=index),
                open=close,
                high=close + 1,
                low=close - 1,
                close=close,
            )
            for index in range(count)
        }
    }


def test_paper_repeat_buy_is_confirmation() -> None:
    start = date(2026, 1, 2)
    signals = [
        PaperSignal("s1", "AAPL", "BUY", start, 100.0, 95.0),
        PaperSignal("s2", "AAPL", "BUY", start + timedelta(days=1), 101.0, 95.0),
    ]

    trades = simulate_trades(signals, _bars(start, 5), SimConfig(initial_capital=10_000))

    assert [trade.action for trade in trades] == ["BUY", "CONFIRMATION"]
    assert trades[0].shares == 5.0
    assert trades[1].shares == 0.0


def test_paper_reduce_exits_half() -> None:
    start = date(2026, 1, 2)
    signals = [
        PaperSignal("s1", "AAPL", "BUY", start, 100.0, 95.0),
        PaperSignal("s2", "AAPL", "REDUCE", start + timedelta(days=1), 110.0, 95.0),
    ]

    trades = simulate_trades(signals, _bars(start, 5), SimConfig(initial_capital=10_000))

    reduce = trades[1]
    assert reduce.action == "REDUCE"
    assert reduce.shares == 2.5
    assert reduce.position_shares_after == 2.5
    assert reduce.realized_pnl == 25.0


def test_paper_max_positions_skips_new_buy() -> None:
    start = date(2026, 1, 2)
    bars = _bars(start, 5)
    bars["MSFT"] = bars["AAPL"]
    signals = [
        PaperSignal("s1", "AAPL", "BUY", start, 100.0, 95.0),
        PaperSignal("s2", "MSFT", "BUY", start + timedelta(days=1), 100.0, 95.0),
    ]

    trades = simulate_trades(signals, bars, SimConfig(initial_capital=10_000, max_positions=1))

    assert [trade.action for trade in trades] == ["BUY", "SKIP"]
    assert trades[1].exit_reason == "max_positions"


def test_paper_stop_hit_exits_position() -> None:
    start = date(2026, 1, 2)
    bars = _bars(start, 3)
    bars["AAPL"][start + timedelta(days=1)] = PaperBar(
        bar_date=start + timedelta(days=1),
        open=100.0,
        high=101.0,
        low=94.0,
        close=95.0,
    )
    signals = [PaperSignal("s1", "AAPL", "BUY", start, 100.0, 95.0)]

    trades = simulate_trades(signals, bars, SimConfig(initial_capital=10_000))

    assert trades[-1].action == "SELL"
    assert trades[-1].exit_reason == "stop_hit"
    assert trades[-1].price == 95.0


def test_frozen_signal_snapshot_is_preserved_in_snapshots() -> None:
    start = date(2026, 1, 2)
    signals = [PaperSignal("s1", "AAPL", "BUY", start, 100.0, 95.0)]
    config = SimConfig(initial_capital=10_000)
    trades = simulate_trades(signals, _bars(start, 5), config)
    snapshots = create_portfolio_snapshots(
        trades=trades,
        bars_by_ticker=_bars(start, 5),
        config=config,
        signal_snapshot_id="snapshot-v1",
    )

    assert snapshots[0].signal_snapshot_id == "snapshot-v1"
    assert snapshots[0].benchmark_value is None
    assert snapshots[0].benchmark_symbol is None


def test_compute_metrics_uses_peak_to_trough_drawdown() -> None:
    snapshots = [
        type("Snapshot", (), {"portfolio_value": 100.0})(),
        type("Snapshot", (), {"portfolio_value": 120.0})(),
        type("Snapshot", (), {"portfolio_value": 90.0})(),
        type("Snapshot", (), {"portfolio_value": 110.0})(),
    ]

    metrics = compute_metrics(snapshots, initial_capital=100.0, closed_trades=[])

    assert metrics.total_return_pct == 10.0
    assert metrics.max_drawdown_pct == -25.0
