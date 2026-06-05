from __future__ import annotations

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def test_phase7_alembic_upgrade_creates_signal_outcomes(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "phase7.sqlite"
    _point_alembic_at(db_path, monkeypatch)

    command.upgrade(_alembic_config(), "head")

    engine = sa.create_engine(f"sqlite:///{db_path}")
    inspector = sa.inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("signal_outcomes")}
    checks = {constraint["name"] for constraint in inspector.get_check_constraints("signal_outcomes")}
    unique_constraints = {
        constraint["name"] for constraint in inspector.get_unique_constraints("signal_outcomes")
    }

    assert "signal_outcomes" in inspector.get_table_names()
    assert "signal_id" in columns
    assert "horizon_days" in columns
    assert "evaluation_eligibility" in columns
    assert "ck_signal_outcomes_evaluation_eligibility" in checks
    assert "uq_signal_outcomes_signal_horizon" in unique_constraints


def _alembic_config() -> Config:
    return Config("apps/api/alembic.ini")


def _point_alembic_at(db_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    from trading_system_api.config import get_settings

    get_settings.cache_clear()
