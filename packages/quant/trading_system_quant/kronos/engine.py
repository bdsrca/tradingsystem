from __future__ import annotations

import asyncio
import time
from datetime import date
from typing import Protocol

import pandas as pd

from trading_system_quant.kronos.adapter import adapt_kronos_output, prepare_kronos_input
from trading_system_quant.kronos.result import KronosForecastResult, fallback_result


class KronosForecastClient(Protocol):
    async def forecast(
        self,
        frame: pd.DataFrame,
        *,
        ticker: str,
        exchange: str,
        pred_len: int,
        sample_count: int,
        temperature: float,
        top_p: float,
    ) -> pd.DataFrame: ...


class KronosEngine:
    def __init__(
        self,
        *,
        client: KronosForecastClient,
        model_name: str = "NeoQuasar/Kronos-small",
        model_version: str = "67b630e67f6a18c9e9be918d9b4337c960db1e9a",
        sample_count: int = 3,
        pred_len: int = 30,
        timeout_seconds: float = 60,
        temperature: float = 0.6,
        top_p: float = 0.9,
    ) -> None:
        self.client = client
        self.model_name = model_name
        self.model_version = model_version
        self.sample_count = sample_count
        self.pred_len = pred_len
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.top_p = top_p

    async def forecast(
        self,
        bars: pd.DataFrame,
        *,
        ticker: str,
        exchange: str,
    ) -> KronosForecastResult:
        started = time.monotonic()
        prepared = prepare_kronos_input(bars, ticker=ticker, exchange=exchange)
        analysis_date = _analysis_date(bars)
        if prepared.status == "skipped":
            return fallback_result(
                ticker=ticker,
                exchange=exchange,
                analysis_date=analysis_date.isoformat(),
                lookback_bars=len(bars),
                sample_count=self.sample_count,
                model_name=self.model_name,
                model_version=self.model_version,
                status="skipped",
                error_message=prepared.error_message or "skipped",
                volatility_note=prepared.volatility_note,
            )

        try:
            predicted = await asyncio.wait_for(
                self.client.forecast(
                    prepared.frame,
                    ticker=ticker,
                    exchange=exchange,
                    pred_len=self.pred_len,
                    sample_count=self.sample_count,
                    temperature=self.temperature,
                    top_p=self.top_p,
                ),
                timeout=self.timeout_seconds,
            )
        except TimeoutError:
            runtime_ms = round((time.monotonic() - started) * 1000)
            return fallback_result(
                ticker=ticker,
                exchange=exchange,
                analysis_date=analysis_date.isoformat(),
                lookback_bars=len(prepared.frame),
                sample_count=self.sample_count,
                model_name=self.model_name,
                model_version=self.model_version,
                status="timeout",
                error_message=f"Kronos timeout after {self.timeout_seconds}s",
                runtime_ms=runtime_ms,
                volatility_note=prepared.volatility_note,
            )
        except Exception as exc:
            runtime_ms = round((time.monotonic() - started) * 1000)
            return fallback_result(
                ticker=ticker,
                exchange=exchange,
                analysis_date=analysis_date.isoformat(),
                lookback_bars=len(prepared.frame),
                sample_count=self.sample_count,
                model_name=self.model_name,
                model_version=self.model_version,
                status="error",
                error_message=str(exc),
                runtime_ms=runtime_ms,
                volatility_note=prepared.volatility_note,
            )

        runtime_ms = round((time.monotonic() - started) * 1000)
        return adapt_kronos_output(
            ticker=ticker,
            exchange=exchange,
            analysis_date=analysis_date,
            current_close=float(prepared.frame.iloc[-1]["close"]),
            predicted=predicted,
            model_name=self.model_name,
            model_version=self.model_version,
            lookback_bars=len(prepared.frame),
            sample_count=self.sample_count,
            runtime_ms=runtime_ms,
            volatility_note=prepared.volatility_note,
        )


def _analysis_date(frame: pd.DataFrame) -> date:
    index_value = frame.index[-1]
    if hasattr(index_value, "date"):
        return index_value.date()
    return date.fromisoformat(str(index_value))
