"""phase 4 agent reports and checkpoint pointers

Revision ID: 0004_phase4
Revises: 0003_phase3
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_phase4"
down_revision: str | None = "0003_phase3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("analysis_runs", sa.Column("data_snapshot_id", sa.String(length=36)))
    op.add_column("analysis_runs", sa.Column("kronos_duration_ms", sa.Integer()))
    op.add_column("analysis_runs", sa.Column("llm_duration_ms", sa.Integer()))
    op.add_column(
        "analysis_runs",
        sa.Column(
            "agent_run_status",
            sa.String(length=32),
            nullable=False,
            server_default="pending",
        ),
    )

    op.create_table(
        "agent_reports",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "analysis_run_id",
            sa.String(length=36),
            sa.ForeignKey("analysis_runs.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("structured_json", sa.JSON(), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("model_provider", sa.String(length=32), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("is_degraded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ("
            "'market_analyst', "
            "'fundamentals_analyst', "
            "'news_analyst', "
            "'bull_researcher', "
            "'bear_researcher', "
            "'risk_manager', "
            "'portfolio_manager'"
            ")",
            name="ck_agent_reports_role",
        ),
        sa.CheckConstraint(
            "stage IN ('technical', 'fundamental', 'news', 'bull', 'bear', 'risk', 'final')",
            name="ck_agent_reports_stage",
        ),
    )
    op.create_index("ix_agent_reports_analysis_run_id", "agent_reports", ["analysis_run_id"])

    op.create_table(
        "agent_checkpoint_pointers",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "analysis_run_id",
            sa.String(length=36),
            sa.ForeignKey("analysis_runs.id"),
            nullable=False,
        ),
        sa.Column("checkpoint_db_path", sa.Text(), nullable=False),
        sa.Column("thread_id", sa.String(length=16), nullable=False),
        sa.Column("checkpoint_ns", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("checkpoint_skipped", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("skip_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_agent_checkpoint_pointers_analysis_run_id",
        "agent_checkpoint_pointers",
        ["analysis_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_checkpoint_pointers_analysis_run_id",
        table_name="agent_checkpoint_pointers",
    )
    op.drop_table("agent_checkpoint_pointers")
    op.drop_index("ix_agent_reports_analysis_run_id", table_name="agent_reports")
    op.drop_table("agent_reports")
    for column in [
        "agent_run_status",
        "llm_duration_ms",
        "kronos_duration_ms",
        "data_snapshot_id",
    ]:
        op.drop_column("analysis_runs", column)
