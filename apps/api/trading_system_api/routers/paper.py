from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.database import get_session
from trading_system_api.models import (
    MarketDataBar,
    PaperPortfolioSnapshot,
    PaperSimulationRun,
    PaperTrade,
    Signal,
    WatchlistItem,
)
from trading_system_api.schemas import (
    PaperMetricsRead,
    PaperOverviewRead,
    PaperOverviewRowRead,
    PaperOverviewWindowRead,
    PaperRunRead,
    PaperSnapshotRead,
)
from trading_system_data.symbols import normalize_symbol
from trading_system_quant.paper import (
    PaperBar,
    PaperSignal,
    SimConfig,
    compute_metrics,
    create_portfolio_snapshots,
    simulate_trades,
)

router = APIRouter(prefix="/paper", tags=["paper"])


@router.get("/overview", response_model=PaperOverviewRead)
async def get_paper_overview(session: AsyncSession = Depends(get_session)) -> PaperOverviewRead:
    watchlist = (
        await session.execute(
            select(WatchlistItem)
            .where(WatchlistItem.enabled.is_(True))
            .order_by(WatchlistItem.ticker, WatchlistItem.exchange)
        )
    ).scalars().all()
    rows = []
    for item in watchlist:
        rows.append(
            PaperOverviewRowRead(
                ticker=item.ticker,
                exchange=item.exchange,
                market=item.market,
                display_name=item.display_name,
                one_year=await _latest_paper_window(session, item, 1),
                two_year=await _latest_paper_window(session, item, 2),
                three_year=await _latest_paper_window(session, item, 3),
            )
        )
    return PaperOverviewRead(rows=rows)


@router.get("/{symbol}/latest", response_model=PaperRunRead)
async def get_latest_paper_validation(
    symbol: str,
    exchange: str | None = None,
    window_years: int = Query(1, ge=1, le=3),
    session: AsyncSession = Depends(get_session),
) -> PaperRunRead:
    identity = normalize_symbol(_symbol_with_optional_exchange(symbol, exchange))
    run = (
        await session.execute(
            select(PaperSimulationRun)
            .where(
                PaperSimulationRun.ticker == identity.ticker,
                PaperSimulationRun.exchange == identity.exchange,
                PaperSimulationRun.window_years == window_years,
            )
            .order_by(PaperSimulationRun.created_at.desc())
        )
    ).scalars().first()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No paper run found")

    snapshots = (
        await session.execute(
            select(PaperPortfolioSnapshot)
            .where(PaperPortfolioSnapshot.simulation_run_id == run.id)
            .order_by(PaperPortfolioSnapshot.snapshot_date.asc())
        )
    ).scalars().all()

    return PaperRunRead(
        id=run.id,
        ticker=run.ticker,
        exchange=run.exchange,
        window_years=run.window_years,
        signal_snapshot=run.signal_snapshot,
        metrics=PaperMetricsRead(**(run.metrics or _empty_metrics())),
        snapshots=[
            PaperSnapshotRead(
                time=snapshot.snapshot_date.isoformat(),
                portfolio_value=float(snapshot.portfolio_value),
                cash=float(snapshot.cash),
                positions_value=float(snapshot.positions_value),
                benchmark_symbol=snapshot.benchmark_symbol,
                benchmark_value=float(snapshot.benchmark_value)
                if snapshot.benchmark_value is not None
                else None,
            )
            for snapshot in snapshots
        ],
    )


@router.post("/{symbol}/run", response_model=PaperRunRead, status_code=status.HTTP_201_CREATED)
async def run_paper_validation(
    symbol: str,
    exchange: str | None = None,
    window_years: int = Query(1, ge=1, le=3),
    session: AsyncSession = Depends(get_session),
) -> PaperRunRead:
    identity = normalize_symbol(_symbol_with_optional_exchange(symbol, exchange))
    cutoff = date.today() - timedelta(days=365 * window_years)
    signals = (
        await session.execute(
            select(Signal)
            .where(
                Signal.ticker == identity.ticker,
                Signal.exchange == identity.exchange,
                Signal.analysis_date >= cutoff,
                Signal.is_superseded.is_(False),
                Signal.supersedes_signal_id.is_(None),
                Signal.source == "baseline",
            )
            .order_by(Signal.analysis_date.asc())
        )
    ).scalars().all()
    bars = (
        await session.execute(
            select(MarketDataBar)
            .where(
                MarketDataBar.ticker == identity.ticker,
                MarketDataBar.exchange == identity.exchange,
                MarketDataBar.bar_date >= cutoff,
            )
            .order_by(MarketDataBar.bar_date.asc())
        )
    ).scalars().all()
    if not bars:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No OHLCV bars found")

    config = SimConfig()
    signal_snapshot = {"signal_ids": [signal.id for signal in signals], "source": "baseline"}
    paper_signals = [
        PaperSignal(
            id=signal.id,
            ticker=signal.ticker,
            signal=signal.signal,
            analysis_date=signal.analysis_date,
            entry_price=float(signal.entry_price or 0),
            risk_level=float(signal.risk_level) if signal.risk_level is not None else None,
        )
        for signal in signals
        if signal.signal in {"BUY", "REDUCE", "SELL"}
    ]
    bars_by_ticker = {
        identity.ticker: {
            row.bar_date: PaperBar(
                bar_date=row.bar_date,
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
            )
            for row in bars
        }
    }
    trades = simulate_trades(paper_signals, bars_by_ticker, config)
    snapshots = create_portfolio_snapshots(
        trades=trades,
        bars_by_ticker=bars_by_ticker,
        config=config,
        signal_snapshot_id="pending",
    )
    metrics = compute_metrics(snapshots, initial_capital=config.initial_capital, closed_trades=trades)

    run = PaperSimulationRun(
        ticker=identity.ticker,
        exchange=identity.exchange,
        window_years=window_years,
        initial_capital=config.initial_capital,
        position_size_pct=config.position_size_pct,
        max_positions=config.max_positions,
        max_holding_days=config.max_holding_days,
        signal_snapshot=signal_snapshot,
        metrics=_metrics_dict(metrics),
    )
    session.add(run)
    await session.flush()

    for trade in trades:
        session.add(
            PaperTrade(
                simulation_run_id=run.id,
                ticker=trade.ticker,
                action=trade.action,
                signal_id=trade.signal_id,
                trade_date=trade.trade_date,
                price=trade.price,
                shares=trade.shares,
                cash_after=trade.cash_after,
                position_shares_after=trade.position_shares_after,
                realized_pnl=trade.realized_pnl,
                exit_reason=trade.exit_reason,
            )
        )
    for snapshot in snapshots:
        session.add(
            PaperPortfolioSnapshot(
                simulation_run_id=run.id,
                snapshot_date=snapshot.snapshot_date,
                portfolio_value=snapshot.portfolio_value,
                cash=snapshot.cash,
                positions_value=snapshot.positions_value,
                benchmark_symbol=snapshot.benchmark_symbol,
                benchmark_value=snapshot.benchmark_value,
                signal_snapshot_id=run.id,
            )
        )
    await session.commit()
    await session.refresh(run)

    return _paper_run_read(run, metrics, snapshots)


async def _latest_paper_window(
    session: AsyncSession,
    item: WatchlistItem,
    window_years: int,
) -> PaperOverviewWindowRead:
    run = (
        await session.execute(
            select(PaperSimulationRun)
            .where(
                PaperSimulationRun.ticker == item.ticker,
                PaperSimulationRun.exchange == item.exchange,
                PaperSimulationRun.window_years == window_years,
            )
            .order_by(desc(PaperSimulationRun.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    if run is None:
        return PaperOverviewWindowRead(
            status="not_simulated",
            total_return_pct=None,
            max_drawdown_pct=None,
            win_rate_pct=None,
            trade_count=None,
            simulation_run_id=None,
            created_at=None,
        )
    metrics = run.metrics or {}
    return PaperOverviewWindowRead(
        status="simulated",
        total_return_pct=metrics.get("total_return_pct"),
        max_drawdown_pct=metrics.get("max_drawdown_pct"),
        win_rate_pct=metrics.get("win_rate_pct"),
        trade_count=metrics.get("trade_count"),
        simulation_run_id=run.id,
        created_at=run.created_at,
    )


def _paper_run_read(
    run: PaperSimulationRun,
    metrics,
    snapshots,
) -> PaperRunRead:
    return PaperRunRead(
        id=run.id,
        ticker=run.ticker,
        exchange=run.exchange,
        window_years=run.window_years,
        signal_snapshot=run.signal_snapshot,
        metrics=PaperMetricsRead(**_metrics_dict(metrics)),
        snapshots=[
            PaperSnapshotRead(
                time=snapshot.snapshot_date.isoformat(),
                portfolio_value=snapshot.portfolio_value,
                cash=snapshot.cash,
                positions_value=snapshot.positions_value,
                benchmark_symbol=snapshot.benchmark_symbol,
                benchmark_value=snapshot.benchmark_value,
            )
            for snapshot in snapshots
        ],
    )


def _metrics_dict(metrics) -> dict[str, float | int]:
    return {
        "total_return_pct": metrics.total_return_pct,
        "max_drawdown_pct": metrics.max_drawdown_pct,
        "win_rate_pct": metrics.win_rate_pct,
        "trade_count": metrics.trade_count,
    }


def _empty_metrics() -> dict[str, float | int]:
    return {
        "total_return_pct": 0.0,
        "max_drawdown_pct": 0.0,
        "win_rate_pct": 0.0,
        "trade_count": 0,
    }


def _symbol_with_optional_exchange(symbol: str, exchange: str | None) -> str:
    if exchange and ":" not in symbol and "." not in symbol:
        return f"{symbol}:{exchange}"
    return symbol
