from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar, Token
from typing import TypeVar

from trading_system_agents.snapshot import DataSnapshot


class MissingSnapshotError(RuntimeError):
    pass


_current_snapshot: ContextVar[DataSnapshot | None] = ContextVar(
    "trading_system_agent_snapshot",
    default=None,
)
T = TypeVar("T")


def set_snapshot(snapshot: DataSnapshot) -> Token[DataSnapshot | None]:
    return _current_snapshot.set(snapshot)


def reset_snapshot(token: Token[DataSnapshot | None]) -> None:
    _current_snapshot.reset(token)


def get_snapshot() -> DataSnapshot:
    snapshot = _current_snapshot.get()
    if snapshot is None:
        raise MissingSnapshotError("No agent data snapshot is active")
    return snapshot


def run_with_snapshot(snapshot: DataSnapshot, func: Callable[[], T]) -> T:
    token = set_snapshot(snapshot)
    try:
        return func()
    finally:
        reset_snapshot(token)


def register_platform_vendor(interface_module, vendor_name: str = "platform") -> None:
    for method_name in ("get_stock_data", "get_indicators", "get_fundamentals", "get_news"):
        interface_module.VENDOR_METHODS.setdefault(method_name, {})[vendor_name] = _method(method_name)


def _method(method_name: str):
    def call(*_args, **_kwargs):
        snapshot = get_snapshot()
        if method_name == "get_stock_data":
            return {
                "ticker": snapshot.ticker,
                "exchange": snapshot.exchange,
                "current_price": snapshot.current_price,
            }
        if method_name == "get_indicators":
            return snapshot.indicators
        if method_name == "get_fundamentals":
            return snapshot.fundamentals
        if method_name == "get_news":
            return [
                {
                    "date": item.date,
                    "description": item.description,
                    "source": item.source,
                }
                for item in snapshot.news_items
            ]
        raise ValueError(f"Unsupported platform vendor method: {method_name}")

    return call
