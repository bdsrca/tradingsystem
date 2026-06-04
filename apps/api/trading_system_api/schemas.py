from datetime import datetime

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
