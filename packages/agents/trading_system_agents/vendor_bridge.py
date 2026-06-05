from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar, Token
from typing import TypeVar

from trading_system_agents.snapshot import DataSnapshot


class MissingSnapshotError(RuntimeError):
    pass


PLATFORM_VENDOR_METHODS = (
    "get_stock_data",
    "get_indicators",
    "get_fundamentals",
    "get_balance_sheet",
    "get_cashflow",
    "get_income_statement",
    "get_news",
    "get_global_news",
    "get_insider_transactions",
)


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
    method_names = set(PLATFORM_VENDOR_METHODS)
    method_names.update(getattr(interface_module, "VENDOR_METHODS", {}).keys())
    for method_name in sorted(method_names):
        interface_module.VENDOR_METHODS.setdefault(method_name, {})[vendor_name] = _method(method_name)


def platform_vendor_config(vendor_name: str = "platform") -> dict[str, dict[str, str]]:
    return {
        "data_vendors": {
            "core_stock_apis": vendor_name,
            "technical_indicators": vendor_name,
            "fundamental_data": vendor_name,
            "news_data": vendor_name,
        },
        "tool_vendors": {method_name: vendor_name for method_name in PLATFORM_VENDOR_METHODS},
    }


def _method(method_name: str):
    def call(*_args, **_kwargs):
        try:
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
            return _no_data_available(method_name)
        except Exception as exc:
            return _no_data_available(method_name, exc)

    return call


def _no_data_available(method_name: str, exc: Exception | None = None) -> str:
    reason = "" if exc is None else f" Platform snapshot adapter error: {exc}"
    return (
        f"NO_DATA_AVAILABLE: Platform snapshot data is unavailable for '{method_name}'."
        f"{reason} Do not estimate or fabricate values; report that data is unavailable."
    )
