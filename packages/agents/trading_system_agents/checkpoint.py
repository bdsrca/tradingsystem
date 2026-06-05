from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from trading_system_agents.tradingagents_runtime import TradingAgentsRuntimeDirs


_TICKER_PATH_RE = re.compile(r"^[A-Za-z0-9._\-\^=+]+$")


@dataclass(frozen=True)
class TradingAgentsCheckpointPointer:
    checkpoint_db_path: Path
    thread_id: str
    checkpoint_ns: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "checkpoint_db_path": str(self.checkpoint_db_path),
            "thread_id": self.thread_id,
            "checkpoint_ns": self.checkpoint_ns,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, str]) -> TradingAgentsCheckpointPointer:
        return cls(
            checkpoint_db_path=Path(value["checkpoint_db_path"]).resolve(),
            thread_id=value["thread_id"],
            checkpoint_ns=value.get("checkpoint_ns", ""),
        )


@dataclass(frozen=True)
class CheckpointSetupResult:
    config: dict[str, object]
    pointer: TradingAgentsCheckpointPointer | None
    checkpoint_skipped: bool
    checkpoint_skip_reason: str | None = None


def build_checkpoint_pointer(
    data_cache_dir: str | Path,
    *,
    ticker: str,
    trade_date: str,
    checkpoint_ns: str = "",
) -> TradingAgentsCheckpointPointer:
    safe_ticker = _safe_ticker_component(ticker).upper()
    db_path = (Path(data_cache_dir).resolve() / "checkpoints" / f"{safe_ticker}.db").resolve()
    return TradingAgentsCheckpointPointer(
        checkpoint_db_path=db_path,
        thread_id=tradingagents_thread_id(ticker, trade_date),
        checkpoint_ns=checkpoint_ns,
    )


def tradingagents_thread_id(ticker: str, trade_date: str) -> str:
    return hashlib.sha256(f"{ticker.upper()}:{trade_date}".encode()).hexdigest()[:16]


def configure_checkpoint_or_degrade(
    runtime_dirs: TradingAgentsRuntimeDirs,
    *,
    checkpoint_data_dir: str | Path,
    ticker: str,
    trade_date: str,
    base_config: Mapping[str, object] | None = None,
    initialize: Callable[[dict[str, object], TradingAgentsCheckpointPointer], None] | None = None,
) -> CheckpointSetupResult:
    pointer = build_checkpoint_pointer(
        checkpoint_data_dir,
        ticker=ticker,
        trade_date=trade_date,
    )
    config = dict(base_config or {})
    config.update(runtime_dirs.config_values(data_cache_dir=checkpoint_data_dir))
    config["checkpoint_enabled"] = True

    try:
        if initialize is not None:
            initialize(config, pointer)
    except Exception as exc:
        degraded_config = dict(config)
        degraded_config["checkpoint_enabled"] = False
        return CheckpointSetupResult(
            config=degraded_config,
            pointer=None,
            checkpoint_skipped=True,
            checkpoint_skip_reason=f"checkpoint initialization failed: {exc}",
        )

    return CheckpointSetupResult(
        config=config,
        pointer=pointer,
        checkpoint_skipped=False,
    )


def _safe_ticker_component(value: str, *, max_len: int = 32) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"ticker must be a non-empty string, got {value!r}")
    if len(value) > max_len:
        raise ValueError(f"ticker exceeds {max_len} chars: {value!r}")
    if not _TICKER_PATH_RE.fullmatch(value):
        raise ValueError(
            f"ticker contains characters not allowed in a filesystem path: {value!r}"
        )
    if set(value) == {"."}:
        raise ValueError(f"ticker cannot consist solely of dots: {value!r}")
    return value
