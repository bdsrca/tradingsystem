from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./trading_system.db"
    twelve_data_api_key: str | None = None
    kronos_service_url: str = "http://127.0.0.1:8001"
    kronos_model_name: str = "NeoQuasar/Kronos-small"
    kronos_model_version: str = "67b630e67f6a18c9e9be918d9b4337c960db1e9a"
    kronos_sample_count: int = 3
    kronos_timeout_seconds: float = 60
    agent_max_debate_rounds: int | None = None
    agent_max_risk_discuss_rounds: int | None = None
    scheduler_enabled: bool = False
    scheduler_timezone: str = "America/Toronto"
    daily_trigger_hour: int = 17
    daily_trigger_minute: int = 0
    daily_kronos_enabled: bool = False
    daily_email_enabled: bool = False
    daily_email_recipient: str | None = None
    email_debounce_days: int = 7
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
