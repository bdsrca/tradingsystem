from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from trading_system_kronos_service.schemas import KronosForecastRequest


@dataclass(frozen=True)
class KronosServiceConfig:
    source_path: Path
    model_name: str
    tokenizer_name: str
    model_revision: str | None
    tokenizer_revision: str | None
    device: str
    max_context: int

    @classmethod
    def from_env(cls) -> "KronosServiceConfig":
        return cls(
            source_path=Path(os.getenv("KRONOS_SOURCE_PATH", "vendor/Kronos")),
            model_name=os.getenv("KRONOS_MODEL_NAME", "NeoQuasar/Kronos-small"),
            tokenizer_name=os.getenv("KRONOS_TOKENIZER_NAME", "NeoQuasar/Kronos-Tokenizer-base"),
            model_revision=os.getenv("KRONOS_MODEL_REVISION") or None,
            tokenizer_revision=os.getenv("KRONOS_TOKENIZER_REVISION") or None,
            device=os.getenv("KRONOS_DEVICE", "cpu"),
            max_context=int(os.getenv("KRONOS_MAX_CONTEXT", "512")),
        )


class LazyKronosRunner:
    def __init__(self, config: KronosServiceConfig | None = None) -> None:
        self.config = config or KronosServiceConfig.from_env()
        self._predictor: Any | None = None

    async def forecast(self, request: KronosForecastRequest) -> pd.DataFrame:
        predictor = self._get_predictor()
        frame = _request_to_frame(request)
        return predictor.predict(
            df=frame,
            x_timestamp=pd.Series(frame.index),
            y_timestamp=pd.Series(pd.to_datetime(request.future_times)),
            pred_len=request.pred_len,
            T=request.temperature,
            top_p=request.top_p,
            sample_count=request.sample_count,
            verbose=False,
        )

    def _get_predictor(self):
        if self._predictor is not None:
            return self._predictor

        source_path = self.config.source_path.resolve()
        if not source_path.exists():
            raise RuntimeError(
                f"Kronos source path does not exist: {source_path}. "
                "Clone shiyu-coder/Kronos at the pinned commit or set KRONOS_SOURCE_PATH."
            )
        sys.path.insert(0, str(source_path))

        from model import Kronos, KronosPredictor, KronosTokenizer  # type: ignore

        tokenizer = _from_pretrained(
            KronosTokenizer,
            self.config.tokenizer_name,
            self.config.tokenizer_revision,
        )
        model = _from_pretrained(Kronos, self.config.model_name, self.config.model_revision)
        self._predictor = KronosPredictor(
            model,
            tokenizer,
            device=self.config.device,
            max_context=self.config.max_context,
        )
        return self._predictor


def _from_pretrained(factory, name: str, revision: str | None):
    if revision:
        return factory.from_pretrained(name, revision=revision)
    return factory.from_pretrained(name)


def _request_to_frame(request: KronosForecastRequest) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "open": item.open,
                "high": item.high,
                "low": item.low,
                "close": item.close,
                "volume": item.volume,
                "amount": item.amount,
            }
            for item in request.bars
        ],
        index=pd.to_datetime([item.time for item in request.bars]),
    )
