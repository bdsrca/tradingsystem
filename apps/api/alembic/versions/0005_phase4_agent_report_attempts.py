"""phase 4 agent report retry attempts

Revision ID: 0005_phase4
Revises: 0004_phase4
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_phase4"
down_revision: str | None = "0004_phase4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_reports",
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "agent_reports",
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index(
        "ix_agent_reports_current_stage",
        "agent_reports",
        ["analysis_run_id", "stage", "is_current"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_reports_current_stage", table_name="agent_reports")
    op.drop_column("agent_reports", "is_current")
    op.drop_column("agent_reports", "attempt_number")
