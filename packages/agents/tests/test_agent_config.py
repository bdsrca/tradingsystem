from __future__ import annotations

import pytest

from trading_system_agents.config import (
    AgentConfigError,
    AgentRunConfig,
    default_discussion_rounds,
)


def test_agent_config_allows_only_v1_analysts() -> None:
    config = AgentRunConfig(selected_analysts=("market", "news", "fundamentals"))

    assert config.selected_analysts == ("market", "news", "fundamentals")


def test_agent_config_rejects_unsupported_analysts_before_graph_creation() -> None:
    with pytest.raises(AgentConfigError, match="Unsupported analysts"):
        AgentRunConfig(selected_analysts=("market", "social_media"))


def test_discussion_round_defaults_by_provider() -> None:
    assert default_discussion_rounds("openai") == 1
    assert default_discussion_rounds("anthropic") == 1
    assert default_discussion_rounds("ollama") == 2
    assert default_discussion_rounds("local") == 2

