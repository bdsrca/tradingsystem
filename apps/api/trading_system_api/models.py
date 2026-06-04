from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from trading_system_api.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    market: Mapped[str] = mapped_column(String(8), nullable=False)
    provider_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    alert_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    alert_threshold: Mapped[float | None] = mapped_column(Numeric(5, 2))
    data_stale_after_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MarketDataBar(Base):
    __tablename__ = "market_data_bars"
    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "exchange",
            "bar_date",
            "source_provider",
            name="uq_market_data_bars_identity",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    bar_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    adjusted_close: Mapped[float | None] = mapped_column(Numeric(18, 6))
    volume: Mapped[int | None] = mapped_column(BigInteger)
    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    source_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    adjustment_mode: Mapped[str] = mapped_column(String(64), default="split_adjusted")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    watchlist_item_id: Mapped[str | None] = mapped_column(ForeignKey("watchlist_items.id"))
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    watchlist_item_id: Mapped[str | None] = mapped_column(ForeignKey("watchlist_items.id"))
    analysis_run_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_runs.id"))
    ticker: Mapped[str | None] = mapped_column(String(32))
    exchange: Mapped[str | None] = mapped_column(String(32))
    market: Mapped[str | None] = mapped_column(String(8))
    analysis_date: Mapped[date | None] = mapped_column(Date)
    signal: Mapped[str | None] = mapped_column(String(16))
    confidence: Mapped[float | None] = mapped_column(Numeric(6, 4))
    entry_price: Mapped[float | None] = mapped_column(Numeric(18, 6))
    risk_level: Mapped[float | None] = mapped_column(Numeric(18, 6))
    reason: Mapped[str | None] = mapped_column(Text)
    indicators: Mapped[dict | None] = mapped_column(JSON)
    layer_scores: Mapped[dict | None] = mapped_column(JSON)
    source: Mapped[str | None] = mapped_column(String(32))
    horizon_days: Mapped[int | None] = mapped_column(Integer)
    disagreement_level: Mapped[str | None] = mapped_column(String(16))
    supersedes_signal_id: Mapped[str | None] = mapped_column(ForeignKey("signals.id"))
    is_superseded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    realized_return_pct: Mapped[float | None] = mapped_column(Numeric(12, 6))
    realized_outcome: Mapped[str | None] = mapped_column(String(32))
    realized_at: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PaperSimulationRun(Base):
    __tablename__ = "paper_simulation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    window_years: Mapped[int] = mapped_column(Integer, nullable=False)
    initial_capital: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    position_size_pct: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False)
    max_positions: Mapped[int] = mapped_column(Integer, nullable=False)
    max_holding_days: Mapped[int] = mapped_column(Integer, nullable=False)
    signal_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    metrics: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    simulation_run_id: Mapped[str] = mapped_column(ForeignKey("paper_simulation_runs.id"))
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    signal_id: Mapped[str | None] = mapped_column(ForeignKey("signals.id"))
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    shares: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    cash_after: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    position_shares_after: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    exit_reason: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PaperPortfolioSnapshot(Base):
    __tablename__ = "paper_portfolio_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    simulation_run_id: Mapped[str] = mapped_column(ForeignKey("paper_simulation_runs.id"))
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    portfolio_value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    cash: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    positions_value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    benchmark_symbol: Mapped[str | None] = mapped_column(String(32))
    benchmark_value: Mapped[float | None] = mapped_column(Numeric(18, 6))
    signal_snapshot_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class KronosForecast(Base):
    __tablename__ = "kronos_forecasts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    lookback_bars: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    runtime_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    horizons: Mapped[list] = mapped_column(JSON, nullable=False)
    forecast_path: Mapped[list] = mapped_column(JSON, nullable=False)
    volatility_note: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
