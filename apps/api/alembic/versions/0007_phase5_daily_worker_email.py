"""phase 5 daily worker and email notifications

Revision ID: 0007_phase5
Revises: 0006_phase4
Create Date: 2026-06-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_phase5"
down_revision: str | None = "0006_phase4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_worker_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("triggered_by", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("succeeded_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stale_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("degraded_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("email_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("summary", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "triggered_by IN ('manual', 'scheduler', 'test')",
            name="ck_daily_worker_runs_triggered_by",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'degraded')",
            name="ck_daily_worker_runs_status",
        ),
    )

    op.create_table(
        "daily_worker_ticker_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "worker_run_id",
            sa.String(length=36),
            sa.ForeignKey("daily_worker_runs.id"),
            nullable=False,
        ),
        sa.Column("watchlist_item_id", sa.String(length=36), sa.ForeignKey("watchlist_items.id")),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("market", sa.String(length=8)),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("signal", sa.String(length=16)),
        sa.Column("confidence", sa.Numeric(6, 4)),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('succeeded', 'failed', 'skipped', 'stale', 'degraded')",
            name="ck_daily_worker_ticker_results_status",
        ),
    )
    op.create_index(
        "ix_daily_worker_ticker_results_run",
        "daily_worker_ticker_results",
        ["worker_run_id", "ticker", "exchange"],
    )

    op.create_table(
        "email_notifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("worker_run_id", sa.String(length=36), sa.ForeignKey("daily_worker_runs.id")),
        sa.Column("ticker", sa.String(length=32)),
        sa.Column("exchange", sa.String(length=32)),
        sa.Column("signal", sa.String(length=16)),
        sa.Column("recipient", sa.String(length=255)),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("debounce_key", sa.String(length=128)),
        sa.Column("is_digest", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'suppressed', 'failed')",
            name="ck_email_notifications_status",
        ),
    )
    op.create_index(
        "ix_email_notifications_debounce",
        "email_notifications",
        ["debounce_key", "status", "sent_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_email_notifications_debounce", table_name="email_notifications")
    op.drop_table("email_notifications")
    op.drop_index("ix_daily_worker_ticker_results_run", table_name="daily_worker_ticker_results")
    op.drop_table("daily_worker_ticker_results")
    op.drop_table("daily_worker_runs")
