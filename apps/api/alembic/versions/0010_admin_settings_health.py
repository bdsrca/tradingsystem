"""admin settings and service health

Revision ID: 0010_admin
Revises: 0009_phase7
Create Date: 2026-06-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_admin"
down_revision: str | None = "0009_phase7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "app_settings",
        sa.Column(
            "provider_preference",
            sa.String(length=32),
            nullable=False,
            server_default="twelve_data",
        ),
    )
    op.add_column(
        "app_settings",
        sa.Column("llm_provider_type", sa.String(length=32), nullable=False, server_default="ollama"),
    )
    op.add_column("app_settings", sa.Column("llm_base_url", sa.String(length=255), nullable=True))
    op.add_column("app_settings", sa.Column("llm_model_name", sa.String(length=128), nullable=True))
    op.add_column(
        "app_settings",
        sa.Column("tradingagents_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "app_settings",
        sa.Column("max_debate_rounds", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "app_settings",
        sa.Column("max_risk_discuss_rounds", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("app_settings", sa.Column("smtp_host", sa.String(length=255), nullable=True))
    op.add_column(
        "app_settings",
        sa.Column("smtp_port", sa.Integer(), nullable=False, server_default="587"),
    )
    op.add_column("app_settings", sa.Column("smtp_user", sa.String(length=255), nullable=True))
    op.add_column("app_settings", sa.Column("smtp_from", sa.String(length=255), nullable=True))
    op.add_column(
        "app_settings",
        sa.Column(
            "strong_signal_alert_threshold",
            sa.Numeric(5, 4),
            nullable=False,
            server_default="0.7000",
        ),
    )
    op.create_table(
        "service_health_checks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("service_name", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.UniqueConstraint("service_name", name="uq_service_health_checks_service_name"),
        sa.CheckConstraint(
            "service_name IN ('api', 'db', 'kronos', 'email', 'data_provider')",
            name="ck_service_health_checks_service_name",
        ),
        sa.CheckConstraint(
            "status IN ('ok', 'degraded', 'unreachable')",
            name="ck_service_health_checks_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("service_health_checks")
    for column_name in [
        "strong_signal_alert_threshold",
        "smtp_from",
        "smtp_user",
        "smtp_port",
        "smtp_host",
        "max_risk_discuss_rounds",
        "max_debate_rounds",
        "tradingagents_enabled",
        "llm_model_name",
        "llm_base_url",
        "llm_provider_type",
        "provider_preference",
    ]:
        op.drop_column("app_settings", column_name)
