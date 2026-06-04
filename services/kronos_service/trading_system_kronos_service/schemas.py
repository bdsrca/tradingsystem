from __future__ import annotations

from pydantic import BaseModel, Field


class KronosBar(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float = 0.0


class KronosForecastRequest(BaseModel):
    ticker: str = Field(min_length=1)
    exchange: str = Field(min_length=1)
    pred_len: int = Field(gt=0, le=60)
    sample_count: int = Field(default=3, ge=1, le=20)
    temperature: float = Field(default=0.6, gt=0)
    top_p: float = Field(default=0.9, gt=0, le=1)
    future_times: list[str]
    bars: list[KronosBar] = Field(min_length=1)


class KronosForecastPoint(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float


class KronosForecastResponse(BaseModel):
    ticker: str
    exchange: str
    forecast_path: list[KronosForecastPoint]
