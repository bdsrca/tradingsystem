from __future__ import annotations

from trading_system_api.models import PaperPortfolioSnapshot, PaperSimulationRun, PaperTrade, Signal


def test_phase2_signal_columns_exist() -> None:
    columns = Signal.__table__.columns

    for name in [
        "ticker",
        "exchange",
        "market",
        "analysis_date",
        "confidence",
        "entry_price",
        "risk_level",
        "reason",
        "indicators",
        "layer_scores",
        "source",
        "horizon_days",
        "supersedes_signal_id",
        "is_superseded",
        "realized_return_pct",
        "realized_outcome",
        "realized_at",
    ]:
        assert name in columns


def test_phase2_paper_tables_exist_with_benchmark_columns() -> None:
    assert PaperSimulationRun.__tablename__ == "paper_simulation_runs"
    assert PaperTrade.__tablename__ == "paper_trades"
    assert PaperPortfolioSnapshot.__tablename__ == "paper_portfolio_snapshots"
    assert "benchmark_symbol" in PaperPortfolioSnapshot.__table__.columns
    assert "benchmark_value" in PaperPortfolioSnapshot.__table__.columns
