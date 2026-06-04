"""phase 2 signals and paper validation

Revision ID: 0002_phase2
Revises: 0001_phase1
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_phase2"
down_revision: str | None = "0001_phase1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("signals", sa.Column("ticker", sa.String(length=32)))
    op.add_column("signals", sa.Column("exchange", sa.String(length=32)))
    op.add_column("signals", sa.Column("market", sa.String(length=8)))
    op.add_column("signals", sa.Column("analysis_date", sa.Date()))
    op.add_column("signals", sa.Column("confidence", sa.Numeric(6, 4)))
    op.add_column("signals", sa.Column("entry_price", sa.Numeric(18, 6)))
    op.add_column("signals", sa.Column("risk_level", sa.Numeric(18, 6)))
    op.add_column("signals", sa.Column("reason", sa.Text()))
    op.add_column("signals", sa.Column("indicators", sa.JSON()))
    op.add_column("signals", sa.Column("layer_scores", sa.JSON()))
    op.add_column("signals", sa.Column("source", sa.String(length=32)))
    op.add_column("signals", sa.Column("horizon_days", sa.Integer()))
    op.add_column("signals", sa.Column("supersedes_signal_id", sa.String(length=36)))
    op.add_column("signals", sa.Column("is_superseded", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("signals", sa.Column("realized_return_pct", sa.Numeric(12, 6)))
    op.add_column("signals", sa.Column("realized_outcome", sa.String(length=32)))
    op.add_column("signals", sa.Column("realized_at", sa.Date()))
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key(
            "fk_signals_supersedes_signal_id",
            "signals",
            "signals",
            ["supersedes_signal_id"],
            ["id"],
        )

    op.create_table(
        "paper_simulation_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("window_years", sa.Integer(), nullable=False),
        sa.Column("initial_capital", sa.Numeric(18, 6), nullable=False),
        sa.Column("position_size_pct", sa.Numeric(8, 6), nullable=False),
        sa.Column("max_positions", sa.Integer(), nullable=False),
        sa.Column("max_holding_days", sa.Integer(), nullable=False),
        sa.Column("signal_snapshot", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "paper_trades",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("simulation_run_id", sa.String(length=36), sa.ForeignKey("paper_simulation_runs.id")),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("signal_id", sa.String(length=36), sa.ForeignKey("signals.id")),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("price", sa.Numeric(18, 6), nullable=False),
        sa.Column("shares", sa.Numeric(18, 8), nullable=False),
        sa.Column("cash_after", sa.Numeric(18, 6), nullable=False),
        sa.Column("position_shares_after", sa.Numeric(18, 8), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(18, 6), nullable=False),
        sa.Column("exit_reason", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "paper_portfolio_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("simulation_run_id", sa.String(length=36), sa.ForeignKey("paper_simulation_runs.id")),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("portfolio_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("cash", sa.Numeric(18, 6), nullable=False),
        sa.Column("positions_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("benchmark_symbol", sa.String(length=32)),
        sa.Column("benchmark_value", sa.Numeric(18, 6)),
        sa.Column("signal_snapshot_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("paper_portfolio_snapshots")
    op.drop_table("paper_trades")
    op.drop_table("paper_simulation_runs")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_signals_supersedes_signal_id", "signals", type_="foreignkey")
    for column in [
        "realized_at",
        "realized_outcome",
        "realized_return_pct",
        "is_superseded",
        "supersedes_signal_id",
        "horizon_days",
        "source",
        "layer_scores",
        "indicators",
        "reason",
        "risk_level",
        "entry_price",
        "confidence",
        "analysis_date",
        "market",
        "exchange",
        "ticker",
    ]:
        op.drop_column("signals", column)
