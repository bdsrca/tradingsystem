from sqlalchemy import Boolean, DateTime, Integer, Numeric, Text

from trading_system_api.models import (
    AppSetting,
    DailyWorkerRun,
    DailyWorkerTickerResult,
    EmailNotification,
)


def test_phase5_daily_worker_run_schema_boundary() -> None:
    columns = DailyWorkerRun.__table__.columns

    for name in [
        "id",
        "triggered_by",
        "status",
        "started_at",
        "finished_at",
        "succeeded_count",
        "failed_count",
        "skipped_count",
        "stale_count",
        "degraded_count",
        "email_sent",
        "summary",
    ]:
        assert name in columns

    assert columns["triggered_by"].nullable is False
    assert columns["status"].nullable is False
    assert isinstance(columns["started_at"].type, DateTime)
    assert isinstance(columns["finished_at"].type, DateTime)
    assert isinstance(columns["succeeded_count"].type, Integer)
    assert columns["email_sent"].nullable is False


def test_phase5_daily_worker_ticker_result_schema_boundary() -> None:
    columns = DailyWorkerTickerResult.__table__.columns

    for name in [
        "id",
        "worker_run_id",
        "watchlist_item_id",
        "ticker",
        "exchange",
        "status",
        "data_freshness",
        "signal",
        "confidence",
        "error_message",
        "started_at",
        "finished_at",
    ]:
        assert name in columns

    assert columns["worker_run_id"].nullable is False
    assert columns["ticker"].nullable is False
    assert columns["exchange"].nullable is False
    assert columns["status"].nullable is False
    assert columns["data_freshness"].nullable is False
    assert isinstance(columns["confidence"].type, Numeric)
    assert _has_fk(columns["worker_run_id"].foreign_keys, "daily_worker_runs.id")


def test_phase5_email_notification_schema_boundary() -> None:
    columns = EmailNotification.__table__.columns

    for name in [
        "id",
        "worker_run_id",
        "ticker",
        "exchange",
        "signal",
        "recipient",
        "subject",
        "body",
        "status",
        "debounce_key",
        "sent_at",
        "created_at",
    ]:
        assert name in columns

    assert columns["worker_run_id"].nullable is True
    assert columns["ticker"].nullable is True
    assert columns["exchange"].nullable is True
    assert columns["signal"].nullable is True
    assert columns["debounce_key"].nullable is True
    assert columns["status"].nullable is False
    assert isinstance(columns["body"].type, Text)
    assert _has_fk(columns["worker_run_id"].foreign_keys, "daily_worker_runs.id")


def test_phase5_email_notification_defaults_to_not_digest_duplicate() -> None:
    columns = EmailNotification.__table__.columns

    assert "is_digest" in columns
    assert isinstance(columns["is_digest"].type, Boolean)
    assert columns["is_digest"].nullable is False


def test_phase5_app_settings_reserve_scheduler_fields() -> None:
    columns = AppSetting.__table__.columns

    for name in [
        "id",
        "scheduler_enabled",
        "scheduler_timezone",
        "daily_trigger_hour",
        "daily_trigger_minute",
        "daily_kronos_enabled",
        "daily_email_enabled",
        "daily_email_recipient",
        "email_debounce_days",
        "updated_at",
    ]:
        assert name in columns

    assert columns["scheduler_enabled"].nullable is False
    assert columns["scheduler_timezone"].nullable is False
    assert columns["daily_trigger_hour"].nullable is False
    assert columns["daily_trigger_minute"].nullable is False
    assert columns["daily_email_recipient"].nullable is True


def _has_fk(foreign_keys, target: str) -> bool:
    return any(f"{fk.column.table.name}.{fk.column.name}" == target for fk in foreign_keys)
