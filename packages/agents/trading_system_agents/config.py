from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ALLOWED_ANALYSTS = frozenset({"market", "news", "fundamentals"})
REMOTE_PROVIDERS = frozenset({"openai", "deepseek", "anthropic", "google"})
LOCAL_PROVIDERS = frozenset({"ollama", "local"})


class AgentConfigError(ValueError):
    pass


@dataclass(frozen=True)
class AgentRunConfig:
    selected_analysts: tuple[str, ...] = ("market", "news", "fundamentals")
    llm_provider: str = "openai"
    max_debate_rounds: int | None = None
    max_risk_discuss_rounds: int | None = None

    def __post_init__(self) -> None:
        unsupported = sorted(set(self.selected_analysts) - ALLOWED_ANALYSTS)
        if unsupported:
            raise AgentConfigError(
                f"Unsupported analysts for V1: {', '.join(unsupported)}. "
                f"Allowed analysts: {', '.join(sorted(ALLOWED_ANALYSTS))}"
            )

        if self.max_debate_rounds is None:
            object.__setattr__(
                self,
                "max_debate_rounds",
                default_discussion_rounds(self.llm_provider),
            )
        if self.max_risk_discuss_rounds is None:
            object.__setattr__(
                self,
                "max_risk_discuss_rounds",
                default_discussion_rounds(self.llm_provider),
            )


def default_discussion_rounds(provider: str) -> Literal[1, 2]:
    provider_key = provider.lower()
    if provider_key in LOCAL_PROVIDERS:
        return 2
    if provider_key in REMOTE_PROVIDERS:
        return 1
    return 1

