from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from time import perf_counter
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.config import Settings
from trading_system_api.models import AppSetting, DailyWorkerRun, ServiceHealthCheck, WatchlistItem, utc_now
from trading_system_api.schemas import (
    AdminActionResultRead,
    AdminHealthRead,
    AdminSecretsRead,
    AdminSettingsRead,
    AdminSettingsUpdate,
    ServiceHealthRead,
)

OLLAMA_STARTUP_RETRY_SECONDS = 8.0
OLLAMA_STARTUP_POLL_SECONDS = 1.0


async def get_or_create_app_setting(session: AsyncSession) -> AppSetting:
    row = (await session.execute(select(AppSetting).limit(1))).scalar_one_or_none()
    if row is not None:
        return row
    row = AppSetting()
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_admin_settings(session: AsyncSession, settings: Settings) -> AdminSettingsRead:
    row = await get_or_create_app_setting(session)
    return _settings_to_read(row, settings)


async def update_app_settings(
    session: AsyncSession,
    payload: AdminSettingsUpdate,
    settings: Settings,
) -> AdminSettingsRead:
    row = await get_or_create_app_setting(session)
    updates = payload.model_dump(exclude_unset=True)
    field_map = {
        "smtp_to": "daily_email_recipient",
        "daily_digest_enabled": "daily_email_enabled",
        "kronos_enabled": "daily_kronos_enabled",
    }
    for field, value in updates.items():
        target = field_map.get(field, field)
        setattr(row, target, value)
    row.updated_at = utc_now()
    await session.commit()
    await session.refresh(row)
    return _settings_to_read(row, settings)


async def collect_admin_health(session: AsyncSession, settings: Settings) -> AdminHealthRead:
    await upsert_service_health(
        session,
        "api",
        "ok",
        details={"service": "trading-system-api"},
    )
    start = perf_counter()
    await session.execute(select(AppSetting).limit(1))
    db_latency_ms = int((perf_counter() - start) * 1000)
    await upsert_service_health(
        session,
        "db",
        "ok",
        latency_ms=db_latency_ms,
        details={"connection": "ok"},
    )
    await upsert_service_health(
        session,
        "data_provider",
        "ok" if settings.twelve_data_api_key else "degraded",
        details={
            "provider": "twelve_data",
            "key": _secret_status(settings.twelve_data_api_key),
        },
    )
    await upsert_service_health(
        session,
        "kronos",
        "degraded",
        details={"url": settings.kronos_service_url, "last_error": "not checked"},
    )
    await upsert_service_health(
        session,
        "email",
        "ok" if settings.smtp_host and settings.smtp_password else "degraded",
        details={
            "host": settings.smtp_host,
            "password": _secret_status(settings.smtp_password),
        },
    )
    rows = (
        await session.execute(select(ServiceHealthCheck).order_by(ServiceHealthCheck.service_name))
    ).scalars().all()
    return AdminHealthRead(services=[_health_read(row) for row in rows])


async def check_data_provider(session: AsyncSession, settings: Settings) -> AdminActionResultRead:
    if not settings.twelve_data_api_key:
        row = await upsert_service_health(
            session,
            "data_provider",
            "unreachable",
            details={"last_error": "TWELVE_DATA_API_KEY missing"},
        )
        return _action_from_health(row, "Twelve Data key missing")
    row = await upsert_service_health(
        session,
        "data_provider",
        "ok",
        details={"provider": "twelve_data", "key": "configured"},
    )
    return _action_from_health(row, "Provider configured")


async def check_llm(session: AsyncSession, settings: Settings) -> AdminActionResultRead:
    row_settings = await get_or_create_app_setting(session)
    provider = row_settings.llm_provider_type
    if provider == "ollama":
        if not row_settings.llm_base_url or not row_settings.llm_model_name:
            status = "degraded"
            details = {
                "provider": provider,
                "base_url": row_settings.llm_base_url,
                "model": row_settings.llm_model_name,
                "last_error": "Ollama base URL or model missing",
            }
            message = "Ollama base URL or model missing"
        else:
            status, message, details = await _check_local_ollama(
                row_settings.llm_base_url,
                row_settings.llm_model_name,
            )
    else:
        remote_key = _remote_llm_api_key(settings, provider)
        status = "ok" if remote_key else "unreachable"
        details = {
            "provider": provider,
            "base_url": row_settings.llm_base_url,
            "model": row_settings.llm_model_name,
            "api_key": _secret_status(remote_key),
        }
        message = f"{provider} key configured" if status == "ok" else f"{provider} key missing"
    row = await upsert_service_health(session, "api", status, details=details)
    return _action_from_health(row, message)


async def check_email(session: AsyncSession, settings: Settings) -> AdminActionResultRead:
    row_settings = await get_or_create_app_setting(session)
    if not row_settings.smtp_host:
        row = await upsert_service_health(
            session,
            "email",
            "degraded",
            details={"last_error": "SMTP host missing"},
        )
        return _action_from_health(row, "SMTP host missing")
    if not settings.smtp_password:
        row = await upsert_service_health(
            session,
            "email",
            "unreachable",
            details={"host": row_settings.smtp_host, "last_error": "SMTP password missing"},
        )
        return _action_from_health(row, "SMTP password missing")
    row = await upsert_service_health(
        session,
        "email",
        "ok",
        details={"host": row_settings.smtp_host, "password": "configured"},
    )
    return _action_from_health(row, "Email settings configured")


async def run_smoke_check(session: AsyncSession, settings: Settings) -> AdminActionResultRead:
    start = perf_counter()
    app_settings = await get_or_create_app_setting(session)
    watchlist_count = len((await session.execute(select(WatchlistItem))).scalars().all())
    latest_run = (
        await session.execute(select(DailyWorkerRun).order_by(DailyWorkerRun.started_at.desc()).limit(1))
    ).scalar_one_or_none()
    latency_ms = int((perf_counter() - start) * 1000)
    row = await upsert_service_health(
        session,
        "api",
        "ok",
        latency_ms=latency_ms,
        details={
            "settings_id": app_settings.id,
            "watchlist_count": watchlist_count,
            "latest_daily_run_id": latest_run.id if latest_run else None,
            "twelve_data_key": _secret_status(settings.twelve_data_api_key),
        },
    )
    return _action_from_health(row, "Smoke check completed")


async def upsert_service_health(
    session: AsyncSession,
    service_name: str,
    status: str,
    *,
    latency_ms: int | None = None,
    details: dict | None = None,
) -> ServiceHealthCheck:
    row = (
        await session.execute(
            select(ServiceHealthCheck).where(ServiceHealthCheck.service_name == service_name)
        )
    ).scalar_one_or_none()
    if row is None:
        row = ServiceHealthCheck(service_name=service_name, status=status)
        session.add(row)
    row.status = status
    row.checked_at = utc_now()
    row.latency_ms = latency_ms
    row.details_json = details or {}
    await session.commit()
    await session.refresh(row)
    return row


def _settings_to_read(row: AppSetting, settings: Settings) -> AdminSettingsRead:
    return AdminSettingsRead(
        provider_preference=row.provider_preference,
        llm_provider_type=row.llm_provider_type,
        llm_base_url=row.llm_base_url,
        llm_model_name=row.llm_model_name,
        tradingagents_enabled=row.tradingagents_enabled,
        max_debate_rounds=row.max_debate_rounds,
        max_risk_discuss_rounds=row.max_risk_discuss_rounds,
        smtp_host=row.smtp_host,
        smtp_port=row.smtp_port,
        smtp_user=row.smtp_user,
        smtp_from=row.smtp_from,
        smtp_to=row.daily_email_recipient,
        daily_digest_enabled=row.daily_email_enabled,
        strong_signal_alert_threshold=float(row.strong_signal_alert_threshold),
        scheduler_enabled=row.scheduler_enabled,
        daily_trigger_hour=row.daily_trigger_hour,
        daily_trigger_minute=row.daily_trigger_minute,
        scheduler_timezone=row.scheduler_timezone,
        kronos_enabled=row.daily_kronos_enabled,
        email_debounce_days=row.email_debounce_days,
        secrets=AdminSecretsRead(
            twelve_data_api_key=_secret_status(settings.twelve_data_api_key),
            remote_llm_api_key=_secret_status(_remote_llm_api_key(settings)),
            smtp_password=_secret_status(settings.smtp_password),
        ),
    )


def _health_read(row: ServiceHealthCheck) -> ServiceHealthRead:
    return ServiceHealthRead(
        service_name=row.service_name,
        status=row.status,
        checked_at=row.checked_at,
        latency_ms=row.latency_ms,
        details_json=row.details_json or {},
    )


def _action_from_health(row: ServiceHealthCheck, message: str) -> AdminActionResultRead:
    return AdminActionResultRead(
        service_name=row.service_name,
        status=row.status,
        message=message,
        details_json=row.details_json or {},
    )


def _secret_status(value: str | None) -> str:
    return "configured" if value else "missing"


def _remote_llm_api_key(settings: Settings, provider: str | None = None) -> str | None:
    provider_key = (provider or "").lower()
    if provider_key == "openai":
        return settings.openai_api_key
    if provider_key == "deepseek":
        return settings.deepseek_api_key
    if provider_key == "anthropic":
        return settings.anthropic_api_key
    return settings.openai_api_key or settings.deepseek_api_key or settings.anthropic_api_key


async def _check_local_ollama(base_url: str, model_name: str) -> tuple[str, str, dict]:
    details = {
        "provider": "ollama",
        "base_url": base_url,
        "model": model_name,
        "auto_start_attempted": False,
        "auto_started": False,
    }
    model_names = await _read_ollama_model_names(base_url)
    if model_names is None:
        if not _is_local_ollama_url(base_url):
            details.update(
                {
                    "reachable": False,
                    "auto_start_skipped": "non_local_base_url",
                    "last_error": "Ollama is unreachable and base URL is not local",
                }
            )
            return "unreachable", "Ollama unreachable; auto-start skipped for non-local URL", details

        details["auto_start_attempted"] = True
        details["auto_started"] = _start_ollama_server()
        if details["auto_started"]:
            model_names = await _wait_for_ollama_model_names(base_url)

    if model_names is None:
        details.update({"reachable": False, "last_error": "Ollama is unreachable"})
        return "unreachable", "Ollama unreachable; auto-start failed", details

    model_installed = _model_installed(model_name, model_names)
    details.update(
        {
            "reachable": True,
            "model_installed": model_installed,
            "installed_models": model_names,
        }
    )
    if not model_installed:
        return "degraded", "Ollama reachable but model is missing", details
    return "ok", "Ollama reachable and model installed", details


async def _wait_for_ollama_model_names(base_url: str) -> list[str] | None:
    deadline = perf_counter() + OLLAMA_STARTUP_RETRY_SECONDS
    while True:
        model_names = await _read_ollama_model_names(base_url)
        if model_names is not None:
            return model_names
        if perf_counter() >= deadline:
            return None
        await asyncio.sleep(OLLAMA_STARTUP_POLL_SECONDS)


async def _read_ollama_model_names(base_url: str) -> list[str] | None:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{_ollama_api_root(base_url)}/api/tags")
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    models = payload.get("models", [])
    if not isinstance(models, list):
        return []
    return [model["name"] for model in models if isinstance(model, dict) and isinstance(model.get("name"), str)]


def _start_ollama_server() -> bool:
    executable = shutil.which("ollama")
    if executable is None:
        return False
    kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        kwargs["start_new_session"] = True
    try:
        subprocess.Popen([executable, "serve"], **kwargs)
    except OSError:
        return False
    return True


def _is_local_ollama_url(base_url: str) -> bool:
    parsed = urlparse(base_url)
    return (
        parsed.scheme in {"http", "https"}
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        and parsed.port == 11434
    )


def _ollama_api_root(base_url: str) -> str:
    parsed = urlparse(base_url)
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _model_installed(model_name: str, model_names: list[str]) -> bool:
    wanted = model_name.lower()
    return any(candidate.lower() == wanted for candidate in model_names)
