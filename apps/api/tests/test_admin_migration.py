from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_admin_alembic_upgrade_preserves_existing_settings(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "admin.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    from trading_system_api.config import get_settings

    get_settings.cache_clear()
    config = Config("apps/api/alembic.ini")

    command.upgrade(config, "0009_phase7")
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO app_settings ("
                "id, scheduler_enabled, scheduler_timezone, daily_trigger_hour, "
                "daily_trigger_minute, daily_kronos_enabled, daily_email_enabled, "
                "email_debounce_days, updated_at"
                ") VALUES ("
                "'settings', 0, 'America/Toronto', 17, 0, 0, 0, 7, CURRENT_TIMESTAMP"
                ")"
            )
        )

    command.upgrade(config, "head")
    inspector = inspect(engine)
    assert "service_health_checks" in inspector.get_table_names()
    settings_columns = {column["name"] for column in inspector.get_columns("app_settings")}
    assert "llm_provider_type" in settings_columns
    assert "provider_preference" in settings_columns

    with engine.connect() as conn:
        value = conn.execute(
            text("SELECT llm_provider_type FROM app_settings WHERE id='settings'")
        ).scalar_one()
    assert value == "ollama"
