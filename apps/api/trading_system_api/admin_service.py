from __future__ import annotations

import os
from time import perf_counter

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
    remote_key = _remote_llm_api_key()
    if provider == "ollama":
        status = "ok" if row_settings.llm_base_url and row_settings.llm_model_name else "degraded"
        details = {
            "provider": provider,
            "base_url": row_settings.llm_base_url,
            "model": row_settings.llm_model_name,
        }
        message = "Ollama settings present" if status == "ok" else "Ollama base URL or model missing"
    else:
        status = "ok" if remote_key else "unreachable"
        details = {"provider": provider, "api_key": _secret_status(remote_key)}
        message = "Remote LLM key configured" if status == "ok" else "Remote LLM key missing"
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
            remote_llm_api_key=_secret_status(_remote_llm_api_key()),
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


def _remote_llm_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
