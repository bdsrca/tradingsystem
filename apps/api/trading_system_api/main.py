from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Trading System API", version="0.1.0")

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "trading-system-api"}

    return app


app = create_app()

