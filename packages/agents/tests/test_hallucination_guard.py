from __future__ import annotations

from trading_system_agents.hallucination_guard import validate_agent_output
from trading_system_agents.snapshot import DataSnapshot, SnapshotEvent


def test_hallucination_guard_flags_unsupported_future_dates() -> None:
    snapshot = DataSnapshot(
        ticker="AAPL",
        exchange="NASDAQ",
        analysis_date="2026-06-05",
        display_name="Apple",
        current_price=100.0,
        indicators={},
    )

    result = validate_agent_output(
        "Management reports earnings on 2026-07-31.",
        snapshot=snapshot,
    )

    assert result.is_degraded is True
    assert result.warnings[0].kind == "unsupported_future_date"


def test_hallucination_guard_allows_sourced_future_dates() -> None:
    snapshot = DataSnapshot(
        ticker="AAPL",
        exchange="NASDAQ",
        analysis_date="2026-06-05",
        display_name="Apple",
        current_price=100.0,
        indicators={},
        news_items=[SnapshotEvent(date="2026-07-31", description="Earnings date")],
    )

    result = validate_agent_output(
        "Management reports earnings on 2026-07-31.",
        snapshot=snapshot,
    )

    assert result.is_degraded is False
    assert result.warnings == []


def test_hallucination_guard_flags_unsupported_numbers() -> None:
    snapshot = DataSnapshot(
        ticker="AAPL",
        exchange="NASDAQ",
        analysis_date="2026-06-05",
        display_name="Apple",
        current_price=100.0,
        indicators={"RSI_14": 55.0},
    )

    result = validate_agent_output("RSI is 77 and price is 100.", snapshot=snapshot)

    assert result.is_degraded is True
    assert any(warning.kind == "unsupported_number" for warning in result.warnings)

