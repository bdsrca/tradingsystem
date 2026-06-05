from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from trading_system_api.admin_service import (
    check_data_provider,
    check_email,
    check_llm,
    collect_admin_health,
    get_admin_settings,
    run_smoke_check,
    update_app_settings,
)
from trading_system_api.config import Settings, get_settings
from trading_system_api.dashboard_cache import clear_dashboard_summary_cache
from trading_system_api.database import get_session
from trading_system_api.schemas import (
    AdminActionResultRead,
    AdminHealthRead,
    AdminSettingsRead,
    AdminSettingsUpdate,
)

ADMIN_PASSCODE = "8888"


def require_admin_passcode(x_admin_passcode: str | None = Header(default=None)) -> None:
    if x_admin_passcode != ADMIN_PASSCODE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin passcode required",
        )


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_passcode)])


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


@router.post("/check-provider", response_model=AdminActionResultRead)
async def check_provider(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AdminActionResultRead:
    result = await check_data_provider(session, settings)
    clear_dashboard_summary_cache()
    return result


@router.post("/test-llm", response_model=AdminActionResultRead)
async def test_llm(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AdminActionResultRead:
    result = await check_llm(session, settings)
    clear_dashboard_summary_cache()
    return result


@router.post("/test-email", response_model=AdminActionResultRead)
async def test_email(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AdminActionResultRead:
    result = await check_email(session, settings)
    clear_dashboard_summary_cache()
    return result


@router.post("/run-smoke", response_model=AdminActionResultRead)
async def run_smoke(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AdminActionResultRead:
    result = await run_smoke_check(session, settings)
    clear_dashboard_summary_cache()
    return result
