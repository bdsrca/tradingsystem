from __future__ import annotations

from dataclasses import dataclass
from typing import Any


AGENT_REPORT_STAGES = frozenset(
    {
        "technical",
        "fundamental",
        "news",
        "bull",
        "bear",
        "risk",
        "final",
    }
)


class AgentReportError(ValueError):
    pass


@dataclass(frozen=True)
class AgentReport:
    analysis_run_id: str
    role: str
    stage: str
    content_text: str
    structured_json: dict[str, Any]
    prompt_version: str
    model_provider: str
    model_name: str
    duration_ms: int
    is_degraded: bool

    def __post_init__(self) -> None:
        if self.stage not in AGENT_REPORT_STAGES:
            raise AgentReportError(f"Unsupported agent report stage: {self.stage}")
