"""phase 3 kronos forecasts

Revision ID: 0003_phase3
Revises: 0002_phase2
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_phase3"
down_revision: str | None = "0002_phase2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kronos_forecasts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("analysis_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("lookback_bars", sa.Integer(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("runtime_ms", sa.Integer(), nullable=False),
        sa.Column("horizons", sa.JSON(), nullable=False),
        sa.Column("forecast_path", sa.JSON(), nullable=False),
        sa.Column("volatility_note", sa.String(length=128)),
        sa.Column("error_message", sa.Text()),
        sa.Column("is_fallback", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_kronos_forecasts_latest",
        "kronos_forecasts",
        ["ticker", "exchange", "analysis_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_kronos_forecasts_latest", table_name="kronos_forecasts")
    op.drop_table("kronos_forecasts")
