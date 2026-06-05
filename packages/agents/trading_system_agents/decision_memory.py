from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionMemoryLesson:
    ticker: str
    exchange: str | None
    lesson_text: str
    signal: str | None = None
    decision_text: str | None = None


def format_decision_memory_context(memories: list[DecisionMemoryLesson]) -> str:
    if not memories:
        return "No prior decision lessons are available."

    lines = ["Prior decision lessons:"]
    for index, memory in enumerate(memories, start=1):
        exchange = f"/{memory.exchange}" if memory.exchange else ""
        signal = f" {memory.signal}" if memory.signal else ""
        lines.append(f"{index}. {memory.ticker}{exchange}{signal}: {memory.lesson_text}")
        if memory.decision_text:
            lines.append(f"   Prior decision: {memory.decision_text}")
    return "\n".join(lines)
