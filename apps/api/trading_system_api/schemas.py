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


class SignalOutcomeBackfillRead(BaseModel):
    horizon_days: int
    filled_count: int
    skipped_count: int


class SignalAccuracyRead(BaseModel):
    ticker: str | None
    exchange: str | None
    window: int
    evaluated_count: int
    trusted_count: int
    delayed_count: int
    backfilled_count: int
    backfilled_excluded_count: int
    win_rate_pct: float
    average_return_pct: float


class DashboardLatestRunRead(BaseModel):
    id: str | None
    status: str
    started_at: datetime | None
    succeeded_count: int
    failed_count: int
    skipped_count: int
    stale_count: int
    degraded_count: int
    email_sent: bool


class DashboardAttentionItemRead(BaseModel):
    ticker: str
    exchange: str
    severity: str
    reason: str
    signal: str | None
    confidence: float | None
    href: str


class DashboardWatchlistRowRead(BaseModel):
    ticker: str
    exchange: str
    market: str
    display_name: str | None
    latest_signal: str | None
    confidence: float | None
    data_freshness: str
    last_analyzed_at: datetime | None
    accuracy_20d_win_rate_pct: float | None
    paper_1y_return_pct: float | None
    paper_1y_max_drawdown_pct: float | None
    caveat: str | None


class DashboardAccuracySnapshotRead(BaseModel):
    window: int
    evaluated_count: int
    win_rate_pct: float
    average_return_pct: float
    backfilled_excluded_count: int


class DashboardSummaryRead(BaseModel):
    latest_run: DashboardLatestRunRead | None
    attention_items: list[DashboardAttentionItemRead]
    watchlist_rows: list[DashboardWatchlistRowRead]
    accuracy_snapshot: DashboardAccuracySnapshotRead
    paper_snapshot: dict
    service_warnings: list[str]
    generated_at: datetime
    cache_hit: bool


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


class KronosHorizonRead(BaseModel):
    horizon_days: int
    expected_return_pct: float
    direction: str
    confidence: float
    forecast_close: float
    forecast_low: float
    forecast_high: float


class KronosForecastRead(BaseModel):
    id: str | None = None
    ticker: str
    exchange: str
    analysis_date: str
    lookback_bars: int
    sample_count: int
    horizons: list[KronosHorizonRead]
    forecast_path: list[dict]
    volatility_note: str | None
    model_name: str
    model_version: str
    runtime_ms: int
    status: str
    is_fallback: bool
    error_message: str | None


class DailyTickerResultRead(BaseModel):
    id: str
    ticker: str
    exchange: str
    market: str | None
    status: str
    data_freshness: str
    signal: str | None
    confidence: float | None
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class DailyRunRead(BaseModel):
    id: str
    triggered_by: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    succeeded_count: int
    failed_count: int
    skipped_count: int
    stale_count: int
    degraded_count: int
    email_sent: bool
    summary: dict
    items: list[DailyTickerResultRead]

    model_config = {"from_attributes": True}
