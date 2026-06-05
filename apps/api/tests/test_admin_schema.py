from sqlalchemy import CheckConstraint, UniqueConstraint

from trading_system_api.models import AppSetting, Base, ServiceHealthCheck


def test_admin_settings_columns_exist() -> None:
    columns = AppSetting.__table__.columns
    for name in [
        "provider_preference",
        "llm_provider_type",
        "llm_base_url",
        "llm_model_name",
        "tradingagents_enabled",
        "max_debate_rounds",
        "max_risk_discuss_rounds",
        "smtp_host",
        "smtp_port",
        "smtp_user",
        "smtp_from",
        "strong_signal_alert_threshold",
    ]:
        assert name in columns

    assert "daily_email_enabled" in columns
    assert "daily_email_recipient" in columns
    assert "daily_kronos_enabled" in columns


def test_service_health_checks_schema() -> None:
    assert ServiceHealthCheck.__tablename__ == "service_health_checks"
    assert "service_health_checks" in Base.metadata.tables
    constraints = ServiceHealthCheck.__table__.constraints
    assert any(
        isinstance(constraint, UniqueConstraint)
        and set(constraint.columns.keys()) == {"service_name"}
        for constraint in constraints
    )
    assert any(
        isinstance(constraint, CheckConstraint) and "status" in str(constraint.sqltext)
        for constraint in constraints
    )
