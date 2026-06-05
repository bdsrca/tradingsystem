from __future__ import annotations

from trading_system_agents.output_adapter import adapt_final_state_to_reports


def test_output_adapter_maps_real_tradingagents_state_keys() -> None:
    final_state = {
        "market_report": "Price is above the 20-day moving average.",
        "fundamentals_report": "Revenue growth remains positive.",
        "sentiment_report": "Social sentiment is mildly bullish.",
        "news_report": "No material negative news.",
        "investment_debate_state": {
            "bull_history": "Bull case: margins are expanding.",
            "bear_history": "Bear case: valuation is elevated.",
            "judge_decision": "Overweight after balancing both cases.",
        },
        "risk_debate_state": {
            "aggressive_history": "Aggressive: buy now.",
            "conservative_history": "Conservative: wait for pullback.",
            "neutral_history": "Neutral: position small.",
            "history": "Risk debate transcript.",
            "judge_decision": "Risk manager allows a small position.",
        },
        "final_trade_decision": "**Rating**: Buy\n\nTake a starter position.",
    }

    reports = adapt_final_state_to_reports(
        final_state,
        analysis_run_id="run-1",
        prompt_version="phase4-v1",
        model_provider="ollama",
        model_name="qwen2.5:7b",
    )

    by_stage = {report.stage: report for report in reports}
    assert list(by_stage) == ["technical", "fundamental", "news", "bull", "bear", "risk", "final"]
    assert by_stage["technical"].content_text == final_state["market_report"]
    assert by_stage["fundamental"].content_text == final_state["fundamentals_report"]
    assert by_stage["news"].content_text == final_state["news_report"]
    assert by_stage["news"].structured_json["sentiment_report"] == final_state["sentiment_report"]
    assert by_stage["bull"].content_text == "Bull case: margins are expanding."
    assert by_stage["bear"].content_text == "Bear case: valuation is elevated."
    assert by_stage["risk"].content_text == "Risk manager allows a small position."
    assert by_stage["risk"].structured_json["aggressive_history"] == "Aggressive: buy now."
    assert by_stage["final"].content_text == final_state["final_trade_decision"]
    assert by_stage["final"].structured_json["rating"] == "Buy"
    assert by_stage["final"].structured_json["signal"] == "BUY"
    assert all(not report.is_degraded for report in reports)


def test_output_adapter_degrades_missing_or_empty_fields_without_key_errors() -> None:
    reports = adapt_final_state_to_reports(
        {
            "market_report": None,
            "investment_debate_state": {},
            "risk_debate_state": None,
        },
        analysis_run_id="run-1",
        prompt_version="phase4-v1",
        model_provider="openai",
        model_name="gpt-4o-mini",
    )

    by_stage = {report.stage: report for report in reports}
    assert len(reports) == 7
    assert by_stage["technical"].content_text == ""
    assert by_stage["technical"].is_degraded is True
    assert by_stage["technical"].structured_json["missing"] is True
    assert by_stage["final"].content_text == ""
    assert by_stage["final"].structured_json["signal"] is None
    assert by_stage["final"].is_degraded is True


def test_output_adapter_stores_adapter_summary_not_parsed_llm_json() -> None:
    reports = adapt_final_state_to_reports(
        {
            "final_trade_decision": "**Rating**: Underweight\n\n- Trim half.\n- Reassess later.",
        },
        analysis_run_id="run-1",
        prompt_version="phase4-v1",
        model_provider="openai",
        model_name="gpt-4o-mini",
    )

    final = {report.stage: report for report in reports}["final"]
    assert final.structured_json["signal"] == "REDUCE"
    assert final.structured_json["confidence"] is None
    assert final.structured_json["key_points"] == ["**Rating**: Underweight", "- Trim half.", "- Reassess later."]
