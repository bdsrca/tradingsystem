from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SnapshotEvent:
    date: str
    description: str
    source: str | None = None


@dataclass(frozen=True)
class DataSnapshot:
    ticker: str
    exchange: str
    analysis_date: str
    display_name: str | None
    current_price: float
    indicators: dict[str, float | int | str | None]
    fundamentals: dict[str, Any] = field(default_factory=dict)
    news_items: list[SnapshotEvent] = field(default_factory=list)
    events: list[SnapshotEvent] = field(default_factory=list)

    def sourced_dates(self) -> set[str]:
        dates = {item.date for item in self.news_items}
        dates.update(item.date for item in self.events)
        for value in self.fundamentals.values():
            if isinstance(value, str) and _looks_like_iso_date(value):
                dates.add(value)
            elif isinstance(value, list):
                dates.update(item for item in value if isinstance(item, str) and _looks_like_iso_date(item))
        return dates

    def numeric_values(self) -> set[float]:
        values = {float(self.current_price)}
        values.update(_numeric_values(self.indicators))
        values.update(_numeric_values(self.fundamentals))
        return values


def _numeric_values(value: Any) -> set[float]:
    if isinstance(value, bool):
        return set()
    if isinstance(value, int | float):
        return {float(value)}
    if isinstance(value, dict):
        found: set[float] = set()
        for item in value.values():
            found.update(_numeric_values(item))
        return found
    if isinstance(value, list | tuple):
        found: set[float] = set()
        for item in value:
            found.update(_numeric_values(item))
        return found
    return set()


def _looks_like_iso_date(value: str) -> bool:
    parts = value.split("-")
    return (
        len(parts) == 3
        and len(parts[0]) == 4
        and len(parts[1]) == 2
        and len(parts[2]) == 2
        and all(part.isdigit() for part in parts)
    )

