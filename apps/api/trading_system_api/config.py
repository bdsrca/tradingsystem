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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
