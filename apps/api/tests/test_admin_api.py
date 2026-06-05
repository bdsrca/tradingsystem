import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import trading_system_api.admin_service as admin_service
from trading_system_api.config import get_settings
from trading_system_api.database import Base, get_session
from trading_system_api.main import create_app
from trading_system_api.models import AppSetting, ServiceHealthCheck


ADMIN_HEADERS = {"X-Admin-Passcode": "8888"}


@pytest.mark.anyio
async def test_admin_endpoints_require_hardcoded_passcode() -> None:
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
        missing = await client.get("/admin/settings")
        wrong = await client.get("/admin/settings", headers={"X-Admin-Passcode": "1234"})
        allowed = await client.get("/admin/settings", headers=ADMIN_HEADERS)

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert allowed.status_code == 200


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
            headers=ADMIN_HEADERS,
            json={"twelve_data_api_key": "must-not-save"},
        )
        response = await client.patch(
            "/admin/settings",
            headers=ADMIN_HEADERS,
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
        first = await client.get("/admin/health", headers=ADMIN_HEADERS)
        second = await client.get("/admin/health", headers=ADMIN_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 200
    async with Session() as session:
        rows = (await session.execute(select(ServiceHealthCheck))).scalars().all()
        assert len({row.service_name for row in rows}) == len(rows)
        assert {"api", "db"}.issubset({row.service_name for row in rows})


@pytest.mark.anyio
async def test_admin_provider_action_upserts_existing_health_row(monkeypatch) -> None:
    monkeypatch.setenv("TWELVE_DATA_API_KEY", "fake")
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
        first = await client.post("/admin/check-provider", headers=ADMIN_HEADERS)
        second = await client.post("/admin/check-provider", headers=ADMIN_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 200
    async with Session() as session:
        rows = (
            await session.execute(
                select(ServiceHealthCheck).where(ServiceHealthCheck.service_name == "data_provider")
            )
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].status == "ok"


@pytest.mark.anyio
async def test_admin_scheduler_settings_patch_triggers_reschedule() -> None:
    get_settings.cache_clear()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()
    rescheduled: list[tuple[bool, int, int, str]] = []

    def record_reschedule(settings) -> None:
        rescheduled.append(
            (
                settings.scheduler_enabled,
                settings.daily_trigger_hour,
                settings.daily_trigger_minute,
                settings.scheduler_timezone,
            )
        )

    app.state.reschedule_daily_scheduler = record_reschedule

    async def override_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/admin/settings",
            headers=ADMIN_HEADERS,
            json={
                "scheduler_enabled": True,
                "daily_trigger_hour": 18,
                "daily_trigger_minute": 15,
                "scheduler_timezone": "America/Toronto",
            },
        )

    assert response.status_code == 200
    assert rescheduled == [(True, 18, 15, "America/Toronto")]


@pytest.mark.anyio
async def test_admin_provider_check_updates_health(monkeypatch) -> None:
    monkeypatch.setenv("TWELVE_DATA_API_KEY", "fake")
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
        response = await client.post("/admin/check-provider", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    assert response.json()["service_name"] == "data_provider"
    assert response.json()["status"] == "ok"


@pytest.mark.anyio
async def test_admin_llm_check_auto_starts_local_ollama(monkeypatch) -> None:
    get_settings.cache_clear()
    model_name = "nexusriot/Qwen3.5-Uncensored-HauhauCS-Aggressive:9b"
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    tag_calls: list[str] = []
    starts: list[bool] = []

    async def fake_read_ollama_model_names(base_url: str) -> list[str] | None:
        tag_calls.append(base_url)
        if len(tag_calls) == 1:
            return None
        return [model_name]

    def fake_start_ollama_server() -> bool:
        starts.append(True)
        return True

    monkeypatch.setattr(admin_service, "_read_ollama_model_names", fake_read_ollama_model_names)
    monkeypatch.setattr(admin_service, "_start_ollama_server", fake_start_ollama_server)
    monkeypatch.setattr(admin_service, "OLLAMA_STARTUP_RETRY_SECONDS", 0)

    app = create_app()

    async def override_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.patch(
            "/admin/settings",
            headers=ADMIN_HEADERS,
            json={
                "llm_provider_type": "ollama",
                "llm_base_url": "http://127.0.0.1:11434",
                "llm_model_name": model_name,
            },
        )
        response = await client.post("/admin/test-llm", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["details_json"]["auto_start_attempted"] is True
    assert body["details_json"]["auto_started"] is True
    assert body["details_json"]["model_installed"] is True
    assert starts == [True]
    assert tag_calls == ["http://127.0.0.1:11434", "http://127.0.0.1:11434"]


@pytest.mark.anyio
async def test_admin_llm_check_does_not_auto_start_remote_ollama(monkeypatch) -> None:
    get_settings.cache_clear()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def fake_read_ollama_model_names(_base_url: str) -> list[str] | None:
        return None

    def fail_start_ollama_server() -> bool:
        raise AssertionError("remote Ollama URL must not be auto-started")

    monkeypatch.setattr(admin_service, "_read_ollama_model_names", fake_read_ollama_model_names)
    monkeypatch.setattr(admin_service, "_start_ollama_server", fail_start_ollama_server)

    app = create_app()

    async def override_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.patch(
            "/admin/settings",
            headers=ADMIN_HEADERS,
            json={
                "llm_provider_type": "ollama",
                "llm_base_url": "http://192.168.1.10:11434",
                "llm_model_name": "qwen3:8b",
            },
        )
        response = await client.post("/admin/test-llm", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unreachable"
    assert body["details_json"]["auto_start_attempted"] is False
    assert body["details_json"]["auto_start_skipped"] == "non_local_base_url"


@pytest.mark.anyio
async def test_admin_smoke_action_clears_dashboard_cache() -> None:
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
        await client.get("/dashboard/summary?max_age_seconds=30")
        cached = await client.get("/dashboard/summary?max_age_seconds=30")
        smoke = await client.post("/admin/run-smoke", headers=ADMIN_HEADERS)
        after = await client.get("/dashboard/summary?max_age_seconds=30")

    assert cached.json()["cache_hit"] is True
    assert smoke.status_code == 200
    assert after.json()["cache_hit"] is False
