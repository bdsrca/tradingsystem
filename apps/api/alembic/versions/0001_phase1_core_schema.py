"""phase 1 core schema

Revision ID: 0001_phase1
Revises:
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_phase1"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("market", sa.String(length=8), nullable=False),
        sa.Column("provider_symbol", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255)),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("alert_enabled", sa.Boolean(), nullable=False),
        sa.Column("alert_threshold", sa.Numeric(5, 2)),
        sa.Column("data_stale_after_hours", sa.Integer(), nullable=False),
        sa.Column("last_analyzed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "market_data_bars",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("bar_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(18, 6), nullable=False),
        sa.Column("high", sa.Numeric(18, 6), nullable=False),
        sa.Column("low", sa.Numeric(18, 6), nullable=False),
        sa.Column("close", sa.Numeric(18, 6), nullable=False),
        sa.Column("adjusted_close", sa.Numeric(18, 6)),
        sa.Column("volume", sa.BigInteger()),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("source_symbol", sa.String(length=64), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("adjustment_mode", sa.String(length=64), nullable=False),
        sa.UniqueConstraint(
            "ticker",
            "exchange",
            "bar_date",
            "source_provider",
            name="uq_market_data_bars_identity",
        ),
    )
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("watchlist_item_id", sa.String(length=36), sa.ForeignKey("watchlist_items.id")),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "signals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("watchlist_item_id", sa.String(length=36), sa.ForeignKey("watchlist_items.id")),
        sa.Column("analysis_run_id", sa.String(length=36), sa.ForeignKey("analysis_runs.id")),
        sa.Column("signal", sa.String(length=16)),
        sa.Column("disagreement_level", sa.String(length=16)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("signals")
    op.drop_table("analysis_runs")
    op.drop_table("market_data_bars")
    op.drop_table("watchlist_items")
