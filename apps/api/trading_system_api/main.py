from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from trading_system_api.auth import add_basic_auth_if_enabled
from trading_system_api.config import get_settings
from trading_system_api.daily_service import run_daily_analysis
from trading_system_api.database import SessionLocal
from trading_system_api.routers import (
    admin,
    analysis,
    daily,
    dashboard,
    kronos,
    market_data,
    paper,
    signals,
    watchlist,
)
from trading_system_api.scheduler import build_daily_scheduler, reschedule_daily_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    scheduler = None
    if settings.scheduler_enabled:
        scheduler = build_daily_scheduler(settings, _scheduled_daily_job)
        scheduler.start()
        app.state.scheduler = scheduler
    try:
        yield
    finally:
        active_scheduler = getattr(app.state, "scheduler", None)
        if active_scheduler is not None:
            active_scheduler.shutdown(wait=False)
            app.state.scheduler = None


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Trading System API", version="0.1.0", lifespan=lifespan)
    app.state.scheduler = None
    app.state.reschedule_daily_scheduler = lambda saved_settings: reschedule_daily_scheduler(
        app.state,
        saved_settings,
        _scheduled_daily_job,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:3001",
            "http://localhost:3001",
            "http://127.0.0.1:3002",
            "http://localhost:3002",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    add_basic_auth_if_enabled(app, settings)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "trading-system-api"}

    app.include_router(watchlist.router)
    app.include_router(market_data.router)
    app.include_router(admin.router)
    app.include_router(analysis.router)
    app.include_router(signals.router)
    app.include_router(dashboard.router)
    app.include_router(paper.router)
    app.include_router(kronos.router)
    app.include_router(daily.router)

    return app


app = create_app()


async def _scheduled_daily_job() -> None:
    async with SessionLocal() as session:
        await run_daily_analysis(session, get_settings(), triggered_by="scheduler")
