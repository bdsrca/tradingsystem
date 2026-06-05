from sqlalchemy import UniqueConstraint

from trading_system_api.database import Base
from trading_system_api.models import SignalOutcome


def test_phase7_signal_outcome_schema_boundary() -> None:
    columns = SignalOutcome.__table__.columns

    assert "signal_id" in columns
    assert "horizon_days" in columns
    assert "target_date" in columns
    assert "realized_price" in columns
    assert "realized_return_pct" in columns
    assert "realized_outcome" in columns
    assert "evaluation_eligibility" in columns
    assert "lag_days" in columns
    assert "filled_at" in columns

    constraints = [
        constraint
        for constraint in SignalOutcome.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]
    assert any(
        {column.name for column in constraint.columns} == {"signal_id", "horizon_days"}
        for constraint in constraints
    )


def test_phase7_signal_outcome_model_is_registered() -> None:
    assert "signal_outcomes" in Base.metadata.tables
