from __future__ import annotations

import os

import pytest

from trading_system_agents.config import AgentRunConfig
from trading_system_agents.llm_adapter import (
    TradingAgentsLLMConfig,
    tradingagents_llm_environment,
)


def test_ollama_config_uses_upstream_ollama_provider_and_backend_url() -> None:
    llm = TradingAgentsLLMConfig(
        provider="ollama",
        deep_model="llama3.1:8b",
        quick_model="llama3.1:8b",
        base_url="http://localhost:11434/v1",
    )

    config = llm.to_tradingagents_config(AgentRunConfig(llm_provider="ollama"))

    assert config["llm_provider"] == "ollama"
    assert config["deep_think_llm"] == "llama3.1:8b"
    assert config["quick_think_llm"] == "llama3.1:8b"
    assert config["backend_url"] == "http://localhost:11434/v1"
    assert config["max_debate_rounds"] == 2
    assert config["max_risk_discuss_rounds"] == 2


def test_openai_environment_sets_and_restores_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("TRADINGAGENTS_LLM_PROVIDER", raising=False)
    llm = TradingAgentsLLMConfig(
        provider="openai",
        deep_model="gpt-4o",
        quick_model="gpt-4o-mini",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
    )

    with tradingagents_llm_environment(llm):
        assert os.environ["OPENAI_API_KEY"] == "sk-test"
        assert os.environ["OPENAI_BASE_URL"] == "https://api.openai.com/v1"
        assert os.environ["TRADINGAGENTS_LLM_PROVIDER"] == "openai"

    assert "OPENAI_API_KEY" not in os.environ
    assert "TRADINGAGENTS_LLM_PROVIDER" not in os.environ


def test_ollama_environment_uses_ollama_base_url_without_openai_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    llm = TradingAgentsLLMConfig(
        provider="ollama",
        deep_model="qwen2.5:7b",
        quick_model="qwen2.5:7b",
        base_url="http://localhost:11434/v1",
    )

    with tradingagents_llm_environment(llm):
        assert os.environ["OLLAMA_BASE_URL"] == "http://localhost:11434/v1"
        assert os.environ["TRADINGAGENTS_LLM_PROVIDER"] == "ollama"
        assert "OPENAI_API_KEY" not in os.environ

    assert "OLLAMA_BASE_URL" not in os.environ
