from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PaperSignal:
    id: str
    ticker: str
    signal: str
    analysis_date: date
    entry_price: float
    risk_level: float | None


@dataclass(frozen=True)
class PaperBar:
    bar_date: date
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class SimConfig:
    initial_capital: float = 100_000
    position_size_pct: float = 0.05
    max_positions: int = 10
    max_holding_days: int = 30


@dataclass
class OpenPosition:
    ticker: str
    entry_date: date
    entry_price: float
    shares: float
    risk_level: float | None
    entry_signal_id: str


@dataclass(frozen=True)
class PaperTrade:
    ticker: str
    action: str
    trade_date: date
    price: float
    shares: float
    signal_id: str | None
    cash_after: float
    position_shares_after: float
    realized_pnl: float = 0.0
    exit_reason: str | None = None


@dataclass(frozen=True)
class PortfolioSnapshot:
    snapshot_date: date
    portfolio_value: float
    cash: float
    positions_value: float
    signal_snapshot_id: str
    benchmark_symbol: str | None = None
    benchmark_value: float | None = None


@dataclass(frozen=True)
class PaperMetrics:
    total_return_pct: float
    max_drawdown_pct: float
    win_rate_pct: float
    trade_count: int


def simulate_trades(
    signals: list[PaperSignal],
    bars_by_ticker: dict[str, dict[date, PaperBar]],
    config: SimConfig,
) -> list[PaperTrade]:
    cash = config.initial_capital
    positions: dict[str, OpenPosition] = {}
    trades: list[PaperTrade] = []
    signals_by_date = _group_signals_by_date(signals)
    all_dates = _all_dates(signals_by_date, bars_by_ticker)

    for current_date in all_dates:
        for ticker in list(positions):
            bar = bars_by_ticker.get(ticker, {}).get(current_date)
            if bar is None:
                continue
            position = positions[ticker]
            if position.risk_level is not None and bar.low <= position.risk_level:
                cash = _close_position(
                    trades=trades,
                    positions=positions,
                    ticker=ticker,
                    trade_date=current_date,
                    price=position.risk_level,
                    cash=cash,
                    signal_id=None,
                    exit_reason="stop_hit",
                )
            elif (current_date - position.entry_date).days >= config.max_holding_days:
                cash = _close_position(
                    trades=trades,
                    positions=positions,
                    ticker=ticker,
                    trade_date=current_date,
                    price=bar.close,
                    cash=cash,
                    signal_id=None,
                    exit_reason="max_holding_period",
                )

        for signal in signals_by_date.get(current_date, []):
            action = signal.signal.upper()
            if action == "BUY":
                cash = _handle_buy(signal, cash, positions, trades, config)
            elif action == "REDUCE" and signal.ticker in positions:
                cash = _handle_reduce(signal, cash, positions, trades)
            elif action == "SELL" and signal.ticker in positions:
                cash = _close_position(
                    trades=trades,
                    positions=positions,
                    ticker=signal.ticker,
                    trade_date=signal.analysis_date,
                    price=signal.entry_price,
                    cash=cash,
                    signal_id=signal.id,
                    exit_reason="signal_sell",
                )

    return trades


def create_portfolio_snapshots(
    *,
    trades: list[PaperTrade],
    bars_by_ticker: dict[str, dict[date, PaperBar]],
    config: SimConfig,
    signal_snapshot_id: str,
) -> list[PortfolioSnapshot]:
    cash = config.initial_capital
    shares_by_ticker: dict[str, float] = {}
    trades_by_date: dict[date, list[PaperTrade]] = {}
    for trade in trades:
        trades_by_date.setdefault(trade.trade_date, []).append(trade)

    snapshots: list[PortfolioSnapshot] = []
    for current_date in sorted({day for bars in bars_by_ticker.values() for day in bars}):
        for trade in trades_by_date.get(current_date, []):
            cash = trade.cash_after
            if trade.action == "BUY":
                shares_by_ticker[trade.ticker] = shares_by_ticker.get(trade.ticker, 0.0) + trade.shares
            elif trade.action in {"REDUCE", "SELL"}:
                shares_by_ticker[trade.ticker] = trade.position_shares_after

        positions_value = 0.0
        for ticker, shares in shares_by_ticker.items():
            bar = bars_by_ticker.get(ticker, {}).get(current_date)
            if bar is not None:
                positions_value += shares * bar.close

        snapshots.append(
            PortfolioSnapshot(
                snapshot_date=current_date,
                portfolio_value=round(cash + positions_value, 4),
                cash=round(cash, 4),
                positions_value=round(positions_value, 4),
                signal_snapshot_id=signal_snapshot_id,
            )
        )

    return snapshots


def compute_metrics(
    snapshots: list[object],
    *,
    initial_capital: float,
    closed_trades: list[PaperTrade],
) -> PaperMetrics:
    if not snapshots:
        return PaperMetrics(0.0, 0.0, 0.0, 0)

    ending_value = float(snapshots[-1].portfolio_value)
    peak = float(snapshots[0].portfolio_value)
    max_drawdown = 0.0
    for snapshot in snapshots:
        value = float(snapshot.portfolio_value)
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = min(max_drawdown, (value - peak) / peak)

    realized = [trade for trade in closed_trades if trade.action in {"REDUCE", "SELL"}]
    wins = [trade for trade in realized if trade.realized_pnl > 0]
    win_rate = (len(wins) / len(realized) * 100) if realized else 0.0

    return PaperMetrics(
        total_return_pct=round(((ending_value / initial_capital) - 1) * 100, 4),
        max_drawdown_pct=round(max_drawdown * 100, 4),
        win_rate_pct=round(win_rate, 4),
        trade_count=len(realized),
    )


def _handle_buy(
    signal: PaperSignal,
    cash: float,
    positions: dict[str, OpenPosition],
    trades: list[PaperTrade],
    config: SimConfig,
) -> float:
    if signal.ticker in positions:
        trades.append(
            PaperTrade(
                ticker=signal.ticker,
                action="CONFIRMATION",
                trade_date=signal.analysis_date,
                price=signal.entry_price,
                shares=0.0,
                signal_id=signal.id,
                cash_after=round(cash, 4),
                position_shares_after=round(positions[signal.ticker].shares, 8),
            )
        )
        return cash

    if len(positions) >= config.max_positions:
        trades.append(_skip(signal, cash, "max_positions"))
        return cash

    allocation = config.initial_capital * config.position_size_pct
    if allocation > cash:
        trades.append(_skip(signal, cash, "insufficient_cash"))
        return cash

    shares = allocation / signal.entry_price
    cash -= allocation
    positions[signal.ticker] = OpenPosition(
        ticker=signal.ticker,
        entry_date=signal.analysis_date,
        entry_price=signal.entry_price,
        shares=shares,
        risk_level=signal.risk_level,
        entry_signal_id=signal.id,
    )
    trades.append(
        PaperTrade(
            ticker=signal.ticker,
            action="BUY",
            trade_date=signal.analysis_date,
            price=signal.entry_price,
            shares=round(shares, 8),
            signal_id=signal.id,
            cash_after=round(cash, 4),
            position_shares_after=round(shares, 8),
        )
    )
    return cash


def _handle_reduce(
    signal: PaperSignal,
    cash: float,
    positions: dict[str, OpenPosition],
    trades: list[PaperTrade],
) -> float:
    position = positions[signal.ticker]
    shares = position.shares / 2
    realized_pnl = (signal.entry_price - position.entry_price) * shares
    cash += signal.entry_price * shares
    position.shares -= shares
    trades.append(
        PaperTrade(
            ticker=signal.ticker,
            action="REDUCE",
            trade_date=signal.analysis_date,
            price=signal.entry_price,
            shares=round(shares, 8),
            signal_id=signal.id,
            cash_after=round(cash, 4),
            position_shares_after=round(position.shares, 8),
            realized_pnl=round(realized_pnl, 4),
            exit_reason="signal_reduce",
        )
    )
    return cash


def _close_position(
    *,
    trades: list[PaperTrade],
    positions: dict[str, OpenPosition],
    ticker: str,
    trade_date: date,
    price: float,
    cash: float,
    signal_id: str | None,
    exit_reason: str,
) -> float:
    position = positions.pop(ticker)
    realized_pnl = (price - position.entry_price) * position.shares
    cash += price * position.shares
    trades.append(
        PaperTrade(
            ticker=ticker,
            action="SELL",
            trade_date=trade_date,
            price=round(price, 4),
            shares=round(position.shares, 8),
            signal_id=signal_id,
            cash_after=round(cash, 4),
            position_shares_after=0.0,
            realized_pnl=round(realized_pnl, 4),
            exit_reason=exit_reason,
        )
    )
    return cash


def _skip(signal: PaperSignal, cash: float, reason: str) -> PaperTrade:
    return PaperTrade(
        ticker=signal.ticker,
        action="SKIP",
        trade_date=signal.analysis_date,
        price=signal.entry_price,
        shares=0.0,
        signal_id=signal.id,
        cash_after=round(cash, 4),
        position_shares_after=0.0,
        exit_reason=reason,
    )


def _group_signals_by_date(signals: list[PaperSignal]) -> dict[date, list[PaperSignal]]:
    grouped: dict[date, list[PaperSignal]] = {}
    for signal in sorted(signals, key=lambda item: (item.analysis_date, item.ticker)):
        grouped.setdefault(signal.analysis_date, []).append(signal)
    return grouped


def _all_dates(
    signals_by_date: dict[date, list[PaperSignal]],
    bars_by_ticker: dict[str, dict[date, PaperBar]],
) -> list[date]:
    dates = set(signals_by_date)
    for bars in bars_by_ticker.values():
        dates.update(bars)
    return sorted(dates)
