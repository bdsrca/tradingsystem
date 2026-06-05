from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass
class DashboardCacheEntry:
    key: tuple[str]
    value: dict[str, Any]
    expires_at: datetime


_entry: DashboardCacheEntry | None = None


def get_cached_dashboard_summary(key: tuple[str]) -> dict[str, Any] | None:
    if _entry is None:
        return None
    if _entry.key != key:
        return None
    if datetime.now(UTC) >= _entry.expires_at:
        return None
    cached = dict(_entry.value)
    cached["cache_hit"] = True
    return cached


def set_cached_dashboard_summary(
    key: tuple[str],
    value: dict[str, Any],
    *,
    max_age_seconds: int,
) -> dict[str, Any]:
    global _entry
    fresh = dict(value)
    fresh["cache_hit"] = False
    _entry = DashboardCacheEntry(
        key=key,
        value=fresh,
        expires_at=datetime.now(UTC) + timedelta(seconds=max_age_seconds),
    )
    return fresh


def clear_dashboard_summary_cache() -> None:
    global _entry
    _entry = None
