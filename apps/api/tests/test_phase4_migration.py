from __future__ import annotations

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def test_phase4_alembic_upgrade_creates_agent_tables_and_run_columns(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "phase4.sqlite"
    _point_alembic_at(db_path, monkeypatch)

    command.upgrade(_alembic_config(), "head")

    engine = sa.create_engine(f"sqlite:///{db_path}")
    inspector = sa.inspect(engine)

    assert "agent_reports" in inspector.get_table_names()
    assert "agent_checkpoint_pointers" in inspector.get_table_names()

    analysis_columns = {column["name"]: column for column in inspector.get_columns("analysis_runs")}
    assert "data_snapshot_id" in analysis_columns
    assert "kronos_duration_ms" in analysis_columns
    assert "llm_duration_ms" in analysis_columns
    assert analysis_columns["agent_run_status"]["nullable"] is False

    report_columns = {column["name"]: column for column in inspector.get_columns("agent_reports")}
    assert report_columns["analysis_run_id"]["nullable"] is False
    assert report_columns["is_degraded"]["nullable"] is False
    assert report_columns["duration_ms"]["nullable"] is True

    pointer_columns = {
        column["name"]: column for column in inspector.get_columns("agent_checkpoint_pointers")
    }
    assert pointer_columns["checkpoint_db_path"]["nullable"] is False
    assert pointer_columns["checkpoint_skipped"]["nullable"] is False
    assert "checkpoint_enabled" not in pointer_columns

    report_checks = {
        constraint["name"] for constraint in inspector.get_check_constraints("agent_reports")
    }
    assert "ck_agent_reports_role" in report_checks
    assert "ck_agent_reports_stage" in report_checks


def test_phase4_alembic_upgrade_preserves_existing_analysis_runs(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "phase4-existing.sqlite"
    _point_alembic_at(db_path, monkeypatch)
    config = _alembic_config()

    command.upgrade(config, "0003_phase3")
    engine = sa.create_engine(f"sqlite:///{db_path}")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO analysis_runs (id, status, created_at) "
                "VALUES ('run-1', 'completed', '2026-06-04 00:00:00')"
            )
        )

    command.upgrade(config, "head")

    with engine.begin() as connection:
        row = connection.execute(
            sa.text("SELECT status, agent_run_status FROM analysis_runs WHERE id = 'run-1'")
        ).one()

    assert row.status == "completed"
    assert row.agent_run_status == "pending"


def _alembic_config() -> Config:
    return Config("apps/api/alembic.ini")


def _point_alembic_at(db_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    from trading_system_api.config import get_settings

    get_settings.cache_clear()
