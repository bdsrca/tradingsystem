"""phase 5 freshness and scheduler settings

Revision ID: 0008_phase5
Revises: 0007_phase5
Create Date: 2026-06-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_phase5"
down_revision: str | None = "0007_phase5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("daily_worker_ticker_results") as batch:
        batch.add_column(
            sa.Column(
                "data_freshness",
                sa.String(length=16),
                nullable=False,
                server_default="fresh",
            )
        )
        batch.create_check_constraint(
            "ck_daily_worker_ticker_results_data_freshness",
            "data_freshness IN ('fresh', 'stale_used', 'no_data')",
        )

    op.create_table(
        "app_settings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("scheduler_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "scheduler_timezone",
            sa.String(length=64),
            nullable=False,
            server_default="America/Toronto",
        ),
        sa.Column("daily_trigger_hour", sa.Integer(), nullable=False, server_default="17"),
        sa.Column("daily_trigger_minute", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("daily_kronos_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("daily_email_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("daily_email_recipient", sa.String(length=255)),
        sa.Column("email_debounce_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    with op.batch_alter_table("daily_worker_ticker_results") as batch:
        batch.drop_constraint(
            "ck_daily_worker_ticker_results_data_freshness",
            type_="check",
        )
        batch.drop_column("data_freshness")
