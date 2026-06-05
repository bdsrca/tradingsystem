from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.dashboard_cache import (
    get_cached_dashboard_summary,
    set_cached_dashboard_summary,
)
from trading_system_api.dashboard_service import build_dashboard_summary
from trading_system_api.database import get_session
from trading_system_api.schemas import DashboardSummaryRead

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryRead)
async def dashboard_summary(
    max_age_seconds: int = 30,
    force_refresh: bool = False,
    session: AsyncSession = Depends(get_session),
) -> DashboardSummaryRead:
    max_age_seconds = max(0, min(max_age_seconds, 300))
    key = ("summary",)
    if not force_refresh and max_age_seconds > 0:
        cached = get_cached_dashboard_summary(key)
        if cached is not None:
            return DashboardSummaryRead(**cached)

    payload = await build_dashboard_summary(session)
    if max_age_seconds > 0:
        payload = set_cached_dashboard_summary(key, payload, max_age_seconds=max_age_seconds)
    return DashboardSummaryRead(**payload)
