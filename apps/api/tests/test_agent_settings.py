from __future__ import annotations

from trading_system_api.config import Settings


def test_agent_debate_round_settings_are_configurable() -> None:
    settings = Settings(agent_max_debate_rounds=3, agent_max_risk_discuss_rounds=2)

    assert settings.agent_max_debate_rounds == 3
    assert settings.agent_max_risk_discuss_rounds == 2
