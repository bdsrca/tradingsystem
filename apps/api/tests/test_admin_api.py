import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from trading_system_api.config import get_settings
from trading_system_api.database import Base, get_session
from trading_system_api.main import create_app
from trading_system_api.models import AppSetting, ServiceHealthCheck


@pytest.mark.anyio
async def test_admin_settings_patch_saves_non_secret_and_masks_secrets(monkeypatch) -> None:
    monkeypatch.setenv("TWELVE_DATA_API_KEY", "secret-key")
    get_settings.cache_clear()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()

    async def override_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        rejected = await client.patch(
            "/admin/settings",
            json={"twelve_data_api_key": "must-not-save"},
        )
        response = await client.patch(
            "/admin/settings",
            json={
                "llm_provider_type": "ollama",
                "llm_base_url": "http://127.0.0.1:11434",
                "llm_model_name": "qwen3:8b",
                "smtp_to": "me@example.com",
            },
        )

    assert rejected.status_code == 422
    assert response.status_code == 200
    payload = response.json()
    assert "twelve_data_api_key" not in payload
    assert payload["secrets"]["twelve_data_api_key"] == "configured"
    assert payload["smtp_to"] == "me@example.com"

    async with Session() as session:
        row = (await session.execute(select(AppSetting))).scalar_one()
        assert row.llm_model_name == "qwen3:8b"
        assert row.daily_email_recipient == "me@example.com"


@pytest.mark.anyio
async def test_admin_health_upserts_one_row_per_service() -> None:
    get_settings.cache_clear()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()

    async def override_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.get("/admin/health")
        second = await client.get("/admin/health")

    assert first.status_code == 200
    assert second.status_code == 200
    async with Session() as session:
        rows = (await session.execute(select(ServiceHealthCheck))).scalars().all()
        assert len({row.service_name for row in rows}) == len(rows)
        assert {"api", "db"}.issubset({row.service_name for row in rows})
