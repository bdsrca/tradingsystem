from __future__ import annotations

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def test_phase5_alembic_upgrade_creates_daily_worker_and_email_tables(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "phase5.sqlite"
    _point_alembic_at(db_path, monkeypatch)

    command.upgrade(_alembic_config(), "head")

    engine = sa.create_engine(f"sqlite:///{db_path}")
    inspector = sa.inspect(engine)

    assert "daily_worker_runs" in inspector.get_table_names()
    assert "daily_worker_ticker_results" in inspector.get_table_names()
    assert "email_notifications" in inspector.get_table_names()

    run_columns = {column["name"]: column for column in inspector.get_columns("daily_worker_runs")}
    assert run_columns["triggered_by"]["nullable"] is False
    assert run_columns["status"]["nullable"] is False
    assert run_columns["email_sent"]["nullable"] is False
    assert run_columns["summary"]["nullable"] is False

    result_columns = {
        column["name"]: column for column in inspector.get_columns("daily_worker_ticker_results")
    }
    assert result_columns["worker_run_id"]["nullable"] is False
    assert result_columns["ticker"]["nullable"] is False
    assert result_columns["exchange"]["nullable"] is False
    assert result_columns["status"]["nullable"] is False

    notification_columns = {
        column["name"]: column for column in inspector.get_columns("email_notifications")
    }
    assert notification_columns["worker_run_id"]["nullable"] is True
    assert notification_columns["subject"]["nullable"] is False
    assert notification_columns["body"]["nullable"] is False
    assert notification_columns["status"]["nullable"] is False
    assert notification_columns["is_digest"]["nullable"] is False

    run_checks = {
        constraint["name"] for constraint in inspector.get_check_constraints("daily_worker_runs")
    }
    result_checks = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("daily_worker_ticker_results")
    }
    notification_checks = {
        constraint["name"] for constraint in inspector.get_check_constraints("email_notifications")
    }
    assert "ck_daily_worker_runs_triggered_by" in run_checks
    assert "ck_daily_worker_runs_status" in run_checks
    assert "ck_daily_worker_ticker_results_status" in result_checks
    assert "ck_email_notifications_status" in notification_checks


def _alembic_config() -> Config:
    return Config("apps/api/alembic.ini")


def _point_alembic_at(db_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    from trading_system_api.config import get_settings

    get_settings.cache_clear()
