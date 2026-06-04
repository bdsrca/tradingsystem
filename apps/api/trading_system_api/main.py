from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from trading_system_api.routers import market_data, watchlist


def create_app() -> FastAPI:
    app = FastAPI(title="Trading System API", version="0.1.0")
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

    return app


app = create_app()
