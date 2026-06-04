from sqlalchemy import BigInteger, UniqueConstraint

from trading_system_api.models import MarketDataBar, Signal, WatchlistItem


def test_watchlist_item_schema_has_phase_one_fields() -> None:
    columns = WatchlistItem.__table__.columns

    for name in [
        "id",
        "ticker",
        "exchange",
        "market",
        "provider_symbol",
        "display_name",
        "enabled",
        "tags",
        "alert_enabled",
        "alert_threshold",
        "data_stale_after_hours",
        "last_analyzed_at",
        "created_at",
        "updated_at",
    ]:
        assert name in columns


def test_market_data_bar_unique_constraint_exists() -> None:
    constraints = [
        constraint
        for constraint in MarketDataBar.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert any(
        {column.name for column in constraint.columns}
        == {"ticker", "exchange", "bar_date", "source_provider"}
        for constraint in constraints
    )


def test_market_data_volume_uses_big_integer() -> None:
    assert isinstance(MarketDataBar.__table__.columns["volume"].type, BigInteger)


def test_signals_include_disagreement_level() -> None:
    assert "disagreement_level" in Signal.__table__.columns
