from __future__ import annotations

from trading_system_api.config import Settings
from trading_system_api.scheduler import build_daily_scheduler


async def _noop_daily_job() -> None:
    return None


def test_daily_scheduler_uses_configured_timezone_and_trigger_time() -> None:
    settings = Settings(
        scheduler_timezone="America/Vancouver",
        daily_trigger_hour=14,
        daily_trigger_minute=45,
    )

    scheduler = build_daily_scheduler(settings, _noop_daily_job)
    [job] = scheduler.get_jobs()

    assert scheduler.timezone.key == "America/Vancouver"
    assert job.id == "daily-post-close-analysis"
    assert job.trigger.fields[5].expressions[0].first == 14
    assert job.trigger.fields[6].expressions[0].first == 45
    assert job.trigger.timezone.key == "America/Vancouver"
