from __future__ import annotations

from base64 import b64encode

import pytest
from fastapi.testclient import TestClient

from trading_system_api.config import get_settings
from trading_system_api.main import create_app


def test_basic_auth_blocks_api_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BASIC_AUTH_ENABLED", "true")
    monkeypatch.setenv("BASIC_AUTH_USERNAME", "me")
    monkeypatch.setenv("BASIC_AUTH_PASSWORD", "secret")
    get_settings.cache_clear()

    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == 'Basic realm="Trading System"'


def test_basic_auth_allows_api_with_valid_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BASIC_AUTH_ENABLED", "true")
    monkeypatch.setenv("BASIC_AUTH_USERNAME", "me")
    monkeypatch.setenv("BASIC_AUTH_PASSWORD", "secret")
    get_settings.cache_clear()
    token = b64encode(b"me:secret").decode()

    client = TestClient(create_app())

    response = client.get("/health", headers={"Authorization": f"Basic {token}"})

    assert response.status_code == 200


def test_cloud_mode_requires_basic_auth_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUD_MODE", "true")
    monkeypatch.delenv("BASIC_AUTH_USERNAME", raising=False)
    monkeypatch.delenv("BASIC_AUTH_PASSWORD", raising=False)
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="BASIC_AUTH_USERNAME and BASIC_AUTH_PASSWORD"):
        create_app()
