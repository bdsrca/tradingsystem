from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from starlette.datastructures import State

from trading_system_api.config import Settings

DAILY_JOB_ID = "daily-post-close-analysis"


def build_daily_scheduler(
    settings: Settings,
    daily_job: Callable[[], Coroutine[Any, Any, None]],
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
    scheduler.add_job(
        daily_job,
        "cron",
        hour=settings.daily_trigger_hour,
        minute=settings.daily_trigger_minute,
        timezone=settings.scheduler_timezone,
        id=DAILY_JOB_ID,
        replace_existing=True,
    )
    return scheduler


def reschedule_daily_scheduler(
    state: State,
    settings: Settings,
    daily_job: Callable[[], Coroutine[Any, Any, None]],
) -> AsyncIOScheduler | None:
    scheduler = getattr(state, "scheduler", None)
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        state.scheduler = None

    if not settings.scheduler_enabled:
        return None

    scheduler = build_daily_scheduler(settings, daily_job)
    scheduler.start()
    state.scheduler = scheduler
    return scheduler
