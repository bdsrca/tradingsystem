from __future__ import annotations

import pytest

from trading_system_agents.report import AgentReport, AgentReportError


def test_agent_report_contract_accepts_v1_stages() -> None:
    report = AgentReport(
        analysis_run_id="run-1",
        role="analyst",
        stage="technical",
        content_text="Trend is improving.",
        structured_json={"signal": "WATCH"},
        prompt_version="phase4-v1",
        model_provider="openai",
        model_name="gpt",
        duration_ms=123,
        is_degraded=False,
    )

    assert report.stage == "technical"


def test_agent_report_contract_rejects_unknown_stage() -> None:
    with pytest.raises(AgentReportError, match="Unsupported agent report stage"):
        AgentReport(
            analysis_run_id="run-1",
            role="analyst",
            stage="social_media",
            content_text="Unsupported.",
            structured_json={},
            prompt_version="phase4-v1",
            model_provider="openai",
            model_name="gpt",
            duration_ms=123,
            is_degraded=False,
        )
