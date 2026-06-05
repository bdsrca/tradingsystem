from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey

from trading_system_api.models import AgentCheckpointPointer, AgentReport, AnalysisRun, Signal


def test_phase4_analysis_run_columns_exist() -> None:
    columns = AnalysisRun.__table__.columns

    assert "data_snapshot_id" in columns
    assert "kronos_duration_ms" in columns
    assert "llm_duration_ms" in columns
    assert "agent_run_status" in columns
    assert columns["agent_run_status"].nullable is False


def test_phase4_agent_reports_schema_boundary() -> None:
    columns = AgentReport.__table__.columns

    for name in [
        "id",
        "analysis_run_id",
        "role",
        "stage",
        "content_text",
        "structured_json",
        "prompt_version",
        "model_provider",
        "model_name",
        "duration_ms",
        "is_degraded",
        "attempt_number",
        "is_current",
        "created_at",
    ]:
        assert name in columns

    assert columns["analysis_run_id"].nullable is False
    assert columns["role"].type.length == 32
    assert columns["duration_ms"].nullable is True
    assert columns["is_degraded"].nullable is False
    assert columns["attempt_number"].nullable is False
    assert columns["is_current"].nullable is False
    assert _has_fk(columns["analysis_run_id"].foreign_keys, "analysis_runs.id")
    assert _has_check(AgentReport, "ck_agent_reports_role")


def test_phase4_checkpoint_pointer_schema_boundary() -> None:
    columns = AgentCheckpointPointer.__table__.columns

    for name in [
        "id",
        "analysis_run_id",
        "checkpoint_db_path",
        "thread_id",
        "checkpoint_ns",
        "checkpoint_skipped",
        "skip_reason",
        "created_at",
    ]:
        assert name in columns

    assert "checkpoint_enabled" not in columns
    assert columns["analysis_run_id"].nullable is False
    assert columns["checkpoint_db_path"].nullable is False
    assert columns["thread_id"].type.length == 16
    assert columns["checkpoint_ns"].type.length == 64
    assert columns["checkpoint_skipped"].nullable is False
    assert columns["skip_reason"].nullable is True
    assert _has_fk(columns["analysis_run_id"].foreign_keys, "analysis_runs.id")


def test_phase4_does_not_put_prompt_metadata_on_signals() -> None:
    columns = Signal.__table__.columns

    assert "prompt_version" not in columns
    assert "model_name" not in columns


def _has_fk(foreign_keys: set[ForeignKey], target: str) -> bool:
    return any(fk.target_fullname == target for fk in foreign_keys)


def _has_check(model: type, name: str) -> bool:
    return any(
        isinstance(constraint, CheckConstraint) and constraint.name == name
        for constraint in model.__table__.constraints
    )
