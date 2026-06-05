from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@dataclass(frozen=True)
class SmokeConfig:
    api_base_url: str
    web_base_url: str
    database_url: str | None
    username: str | None
    password: str | None
    run_daily: bool


async def run_smoke(config: SmokeConfig) -> dict[str, object]:
    auth = httpx.BasicAuth(config.username, config.password) if config.username and config.password else None
    async with httpx.AsyncClient(auth=auth, timeout=30) as client:
        api_health = await _get_json(client, f"{config.api_base_url}/health")
        web_status = (await client.get(config.web_base_url)).status_code
        watchlist = await _get_json(client, f"{config.api_base_url}/watchlist")
        latest_daily = None
        if config.run_daily:
            daily_response = await client.post(f"{config.api_base_url}/daily/run")
            daily_response.raise_for_status()
            latest_daily = daily_response.json()

    db_version = await _read_alembic_version(config.database_url) if config.database_url else None
    return {
        "api_health": api_health,
        "web_status": web_status,
        "watchlist_count": len(watchlist),
        "daily_run_status": latest_daily["status"] if latest_daily else "skipped",
        "database_alembic_version": db_version,
    }


async def _get_json(client: httpx.AsyncClient, url: str) -> object:
    response = await client.get(url)
    response.raise_for_status()
    return response.json()


async def _read_alembic_version(database_url: str) -> str | None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("select version_num from alembic_version"))
            return result.scalar_one_or_none()
    finally:
        await engine.dispose()


def config_from_env(*, run_daily_override: bool | None = None) -> SmokeConfig:
    return SmokeConfig(
        api_base_url=os.getenv("SMOKE_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
        web_base_url=os.getenv("SMOKE_WEB_BASE_URL", "http://127.0.0.1:3000").rstrip("/"),
        database_url=os.getenv("DATABASE_URL"),
        username=os.getenv("BASIC_AUTH_USERNAME"),
        password=os.getenv("BASIC_AUTH_PASSWORD"),
        run_daily=_env_bool("SMOKE_RUN_DAILY", True)
        if run_daily_override is None
        else run_daily_override,
    )


async def async_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a cloud/local deployment smoke test.")
    parser.add_argument("--skip-daily-run", action="store_true")
    args = parser.parse_args(argv)
    result = await run_smoke(config_from_env(run_daily_override=not args.skip_daily_run))
    print(result)
    return 0


def main() -> int:
    return asyncio.run(async_main())


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
