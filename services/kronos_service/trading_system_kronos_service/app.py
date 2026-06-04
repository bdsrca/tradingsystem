from __future__ import annotations

import inspect

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from trading_system_kronos_service.runner import LazyKronosRunner
from trading_system_kronos_service.schemas import (
    KronosForecastRequest,
    KronosForecastResponse,
)


def create_app(runner=None) -> FastAPI:
    app = FastAPI(title="Trading System Kronos Service")
    app.state.runner = runner or LazyKronosRunner()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "kronos"}

    @app.post("/forecast", response_model=KronosForecastResponse)
    async def forecast(request: KronosForecastRequest) -> KronosForecastResponse:
        if len(request.future_times) != request.pred_len:
            raise HTTPException(status_code=400, detail="future_times length must equal pred_len")

        try:
            result = app.state.runner.forecast(request)
            if inspect.isawaitable(result):
                result = await result
        except ValidationError:
            raise
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return KronosForecastResponse(
            ticker=request.ticker,
            exchange=request.exchange,
            forecast_path=_forecast_path(result),
        )

    return app


def _forecast_path(frame: pd.DataFrame) -> list[dict]:
    return [
        {
            "time": _index_to_iso(index),
            "open": float(row.get("open", row["close"])),
            "high": float(row.get("high", row["close"])),
            "low": float(row.get("low", row["close"])),
            "close": float(row["close"]),
            "volume": float(row.get("volume", 0)),
            "amount": float(row.get("amount", 0)),
        }
        for index, row in frame.iterrows()
    ]


def _index_to_iso(value) -> str:
    if hasattr(value, "date"):
        return value.date().isoformat()
    return str(value)
