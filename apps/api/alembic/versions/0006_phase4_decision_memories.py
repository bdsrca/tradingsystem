"""phase 4 decision memories

Revision ID: 0006_phase4
Revises: 0005_phase4
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_phase4"
down_revision: str | None = "0005_phase4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decision_memories",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("exchange", sa.String(length=32)),
        sa.Column("analysis_run_id", sa.String(length=36), sa.ForeignKey("analysis_runs.id")),
        sa.Column("signal", sa.String(length=16)),
        sa.Column("decision_text", sa.Text()),
        sa.Column("lesson_text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="platform"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_decision_memories_ticker_active_created",
        "decision_memories",
        ["ticker", "is_active", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_decision_memories_ticker_active_created", table_name="decision_memories")
    op.drop_table("decision_memories")
