from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.admin_service import (
    collect_admin_health,
    get_admin_settings,
    update_app_settings,
)
from trading_system_api.config import Settings, get_settings
from trading_system_api.dashboard_cache import clear_dashboard_summary_cache
from trading_system_api.database import get_session
from trading_system_api.schemas import AdminHealthRead, AdminSettingsRead, AdminSettingsUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/settings", response_model=AdminSettingsRead)
async def read_admin_settings(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AdminSettingsRead:
    return await get_admin_settings(session, settings)


@router.patch("/settings", response_model=AdminSettingsRead)
async def patch_admin_settings(
    payload: AdminSettingsUpdate,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AdminSettingsRead:
    result = await update_app_settings(session, payload, settings)
    clear_dashboard_summary_cache()
    return result


@router.get("/health", response_model=AdminHealthRead)
async def admin_health(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AdminHealthRead:
    result = await collect_admin_health(session, settings)
    clear_dashboard_summary_cache()
    return result
