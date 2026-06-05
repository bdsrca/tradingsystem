from __future__ import annotations

from trading_system_agents.decision_memory import (
    DecisionMemoryLesson,
    format_decision_memory_context,
)


def test_format_decision_memory_context_lists_prior_lessons() -> None:
    context = format_decision_memory_context(
        [
            DecisionMemoryLesson(
                ticker="AAPL",
                exchange="NASDAQ",
                signal="BUY",
                lesson_text="Breakouts worked only when volume confirmed.",
                decision_text="Bought breakout.",
            )
        ]
    )

    assert "Prior decision lessons:" in context
    assert "AAPL" in context
    assert "BUY" in context
    assert "Breakouts worked only when volume confirmed." in context


def test_format_decision_memory_context_handles_empty_memory() -> None:
    assert format_decision_memory_context([]) == "No prior decision lessons are available."
