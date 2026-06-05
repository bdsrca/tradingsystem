from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from trading_system_agents.report import AgentReport


_RATING_PATTERN = re.compile(
    r"(?:\*\*)?\s*Rating\s*(?:\*\*)?\s*:\s*(Buy|Overweight|Hold|Underweight|Sell)",
    re.IGNORECASE,
)
_CONFIDENCE_PATTERN = re.compile(
    r"(?:\*\*)?\s*Confidence\s*(?:\*\*)?\s*:\s*(low|medium|high|[0-9]+(?:\.[0-9]+)?)",
    re.IGNORECASE,
)
_SIGNAL_BY_RATING = {
    "buy": "BUY",
    "overweight": "WATCH",
    "hold": "HOLD",
    "underweight": "REDUCE",
    "sell": "SELL",
}


def adapt_final_state_to_reports(
    final_state: Mapping[str, Any],
    *,
    analysis_run_id: str,
    prompt_version: str,
    model_provider: str,
    model_name: str,
    duration_ms_by_stage: Mapping[str, int] | None = None,
) -> list[AgentReport]:
    durations = duration_ms_by_stage or {}
    investment_debate_state = _mapping(final_state.get("investment_debate_state"))
    risk_debate_state = _mapping(final_state.get("risk_debate_state"))

    specs = [
        _ReportSpec(
            stage="technical",
            role="market_analyst",
            source_key="market_report",
            content=_text(final_state.get("market_report")),
        ),
        _ReportSpec(
            stage="fundamental",
            role="fundamentals_analyst",
            source_key="fundamentals_report",
            content=_text(final_state.get("fundamentals_report")),
        ),
        _ReportSpec(
            stage="news",
            role="news_analyst",
            source_key="news_report",
            content=_text(final_state.get("news_report")),
            extra={"sentiment_report": _text(final_state.get("sentiment_report"))},
        ),
        _ReportSpec(
            stage="bull",
            role="bull_researcher",
            source_key="investment_debate_state.bull_history",
            content=_text(investment_debate_state.get("bull_history")),
            extra={"judge_decision": _text(investment_debate_state.get("judge_decision"))},
        ),
        _ReportSpec(
            stage="bear",
            role="bear_researcher",
            source_key="investment_debate_state.bear_history",
            content=_text(investment_debate_state.get("bear_history")),
            extra={"judge_decision": _text(investment_debate_state.get("judge_decision"))},
        ),
        _ReportSpec(
            stage="risk",
            role="risk_manager",
            source_key="risk_debate_state.judge_decision",
            content=_text(risk_debate_state.get("judge_decision"))
            or _text(risk_debate_state.get("history")),
            extra={
                "aggressive_history": _text(risk_debate_state.get("aggressive_history")),
                "conservative_history": _text(risk_debate_state.get("conservative_history")),
                "neutral_history": _text(risk_debate_state.get("neutral_history")),
            },
        ),
        _ReportSpec(
            stage="final",
            role="portfolio_manager",
            source_key="final_trade_decision",
            content=_text(final_state.get("final_trade_decision")),
        ),
    ]

    return [
        AgentReport(
            analysis_run_id=analysis_run_id,
            role=spec.role,
            stage=spec.stage,
            content_text=spec.content,
            structured_json=_structured_summary(spec),
            prompt_version=prompt_version,
            model_provider=model_provider,
            model_name=model_name,
            duration_ms=int(durations.get(spec.stage, 0)),
            is_degraded=not bool(spec.content.strip()),
        )
        for spec in specs
    ]


class _ReportSpec:
    def __init__(
        self,
        *,
        stage: str,
        role: str,
        source_key: str,
        content: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.stage = stage
        self.role = role
        self.source_key = source_key
        self.content = content
        self.extra = extra or {}


def _structured_summary(spec: _ReportSpec) -> dict[str, Any]:
    rating = _extract_rating(spec.content)
    summary = {
        "source_key": spec.source_key,
        "missing": not bool(spec.content.strip()),
        "key_points": _key_points(spec.content),
        "confidence": _extract_confidence(spec.content),
    }
    if rating is not None:
        summary["rating"] = rating
        summary["signal"] = _SIGNAL_BY_RATING[rating.lower()]
    elif spec.stage == "final":
        summary["rating"] = None
        summary["signal"] = None
    summary.update(spec.extra)
    return summary


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _extract_rating(text: str) -> str | None:
    match = _RATING_PATTERN.search(text)
    if not match:
        return None
    value = match.group(1).lower()
    return {
        "buy": "Buy",
        "overweight": "Overweight",
        "hold": "Hold",
        "underweight": "Underweight",
        "sell": "Sell",
    }[value]


def _extract_confidence(text: str) -> float | None:
    match = _CONFIDENCE_PATTERN.search(text)
    if not match:
        return None
    value = match.group(1).lower()
    if value == "low":
        return 0.25
    if value == "medium":
        return 0.5
    if value == "high":
        return 0.75
    number = float(value)
    return number if number <= 1 else number / 100


def _key_points(text: str, *, limit: int = 3) -> list[str]:
    points: list[str] = []
    for line in text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        points.append(cleaned[:240])
        if len(points) >= limit:
            break
    return points
