from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from trading_system_agents.config import AgentConfigError, AgentRunConfig


SUPPORTED_LLM_PROVIDERS = frozenset({"openai", "ollama"})


@dataclass(frozen=True)
class TradingAgentsLLMConfig:
    provider: str
    deep_model: str
    quick_model: str
    base_url: str | None = None
    api_key: str | None = None

    def __post_init__(self) -> None:
        provider = self.provider.lower()
        if provider not in SUPPORTED_LLM_PROVIDERS:
            raise AgentConfigError(
                f"Unsupported LLM provider for V1: {self.provider}. "
                f"Allowed providers: {', '.join(sorted(SUPPORTED_LLM_PROVIDERS))}"
            )
        if not self.deep_model.strip():
            raise AgentConfigError("deep_model must not be empty")
        if not self.quick_model.strip():
            raise AgentConfigError("quick_model must not be empty")
        object.__setattr__(self, "provider", provider)

    def to_tradingagents_config(self, run_config: AgentRunConfig) -> dict[str, object]:
        return {
            "llm_provider": self.provider,
            "deep_think_llm": self.deep_model,
            "quick_think_llm": self.quick_model,
            "backend_url": self.base_url,
            "max_debate_rounds": run_config.max_debate_rounds,
            "max_risk_discuss_rounds": run_config.max_risk_discuss_rounds,
        }

    def environment_overrides(self) -> dict[str, str]:
        overrides = {
            "TRADINGAGENTS_LLM_PROVIDER": self.provider,
            "TRADINGAGENTS_DEEP_THINK_LLM": self.deep_model,
            "TRADINGAGENTS_QUICK_THINK_LLM": self.quick_model,
        }
        if self.base_url:
            overrides["TRADINGAGENTS_LLM_BACKEND_URL"] = self.base_url

        if self.provider == "openai":
            if self.api_key:
                overrides["OPENAI_API_KEY"] = self.api_key
            if self.base_url:
                overrides["OPENAI_BASE_URL"] = self.base_url
        elif self.provider == "ollama" and self.base_url:
            overrides["OLLAMA_BASE_URL"] = self.base_url

        return overrides


@contextmanager
def tradingagents_llm_environment(config: TradingAgentsLLMConfig) -> Iterator[None]:
    overrides = config.environment_overrides()
    previous = {key: os.environ.get(key) for key in overrides}
    try:
        for key, value in overrides.items():
            os.environ[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
