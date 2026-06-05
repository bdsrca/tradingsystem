"""phase 7 signal outcomes

Revision ID: 0009_phase7
Revises: 0008_phase5
Create Date: 2026-06-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_phase7"
down_revision: str | None = "0008_phase5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "signal_outcomes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("signal_id", sa.String(length=36), sa.ForeignKey("signals.id"), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("realized_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("realized_return_pct", sa.Numeric(12, 6), nullable=False),
        sa.Column("realized_outcome", sa.String(length=16), nullable=False),
        sa.Column("evaluation_eligibility", sa.String(length=16), nullable=False),
        sa.Column("lag_days", sa.Integer(), nullable=False),
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("signal_id", "horizon_days", name="uq_signal_outcomes_signal_horizon"),
        sa.CheckConstraint(
            "evaluation_eligibility IN ('trusted', 'delayed', 'backfilled')",
            name="ck_signal_outcomes_evaluation_eligibility",
        ),
        sa.CheckConstraint(
            "realized_outcome IN ('win', 'loss', 'flat')",
            name="ck_signal_outcomes_realized_outcome",
        ),
    )
    op.create_index(
        "ix_signal_outcomes_accuracy",
        "signal_outcomes",
        ["ticker", "exchange", "horizon_days", "evaluation_eligibility"],
    )


def downgrade() -> None:
    op.drop_index("ix_signal_outcomes_accuracy", table_name="signal_outcomes")
    op.drop_table("signal_outcomes")
