from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from trading_system_api.config import get_settings
from trading_system_api.daily_service import run_daily_analysis
from trading_system_api.database import SessionLocal
from trading_system_api.routers import analysis, daily, kronos, market_data, paper, signals, watchlist


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    scheduler: AsyncIOScheduler | None = None
    if settings.scheduler_enabled:
        scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
        scheduler.add_job(
            _scheduled_daily_job,
            "cron",
            hour=settings.daily_trigger_hour,
            minute=settings.daily_trigger_minute,
            id="daily-post-close-analysis",
            replace_existing=True,
        )
        scheduler.start()
        app.state.scheduler = scheduler
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    app = FastAPI(title="Trading System API", version="0.1.0", lifespan=lifespan)
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

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "trading-system-api"}

    app.include_router(watchlist.router)
    app.include_router(market_data.router)
    app.include_router(analysis.router)
    app.include_router(signals.router)
    app.include_router(paper.router)
    app.include_router(kronos.router)
    app.include_router(daily.router)

    return app


app = create_app()


async def _scheduled_daily_job() -> None:
    async with SessionLocal() as session:
        await run_daily_analysis(session, get_settings(), triggered_by="scheduler")
