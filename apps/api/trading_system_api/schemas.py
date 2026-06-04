from datetime import date, datetime

from pydantic import BaseModel, Field


class WatchlistCreate(BaseModel):
    symbol: str = Field(min_length=1)
    display_name: str | None = None
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)
    alert_enabled: bool = False
    alert_threshold: float | None = None
    data_stale_after_hours: int = 24


class WatchlistUpdate(BaseModel):
    display_name: str | None = None
    enabled: bool | None = None
    tags: list[str] | None = None
    alert_enabled: bool | None = None
    alert_threshold: float | None = None
    data_stale_after_hours: int | None = None


class WatchlistRead(BaseModel):
    id: str
    ticker: str
    exchange: str
    market: str
    provider_symbol: str
    display_name: str | None
    enabled: bool
    tags: list[str]
    alert_enabled: bool
    alert_threshold: float | None
    data_stale_after_hours: int
    last_analyzed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MarketDataBarRead(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int | None


class MarketDataRefreshResult(BaseModel):
    ticker: str
    exchange: str
    source_provider: str
    source_symbol: str
    bars_upserted: int
    latest_bar_date: str | None


class SignalRead(BaseModel):
    id: str
    ticker: str
    exchange: str
    market: str
    analysis_date: date
    signal: str
    confidence: float
    entry_price: float | None
    risk_level: float | None
    reason: str
    indicators: dict
    layer_scores: dict
    source: str
    horizon_days: int


class SignalMarkerRead(BaseModel):
    time: str
    signal: str
    position: str
    color: str
    shape: str
    text: str


class PaperMetricsRead(BaseModel):
    total_return_pct: float
    max_drawdown_pct: float
    win_rate_pct: float
    trade_count: int


class PaperSnapshotRead(BaseModel):
    time: str
    portfolio_value: float
    cash: float
    positions_value: float
    benchmark_symbol: str | None
    benchmark_value: float | None


class PaperRunRead(BaseModel):
    id: str
    ticker: str
    exchange: str
    window_years: int
    signal_snapshot: dict
    metrics: PaperMetricsRead
    snapshots: list[PaperSnapshotRead]
