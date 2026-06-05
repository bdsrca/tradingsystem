from __future__ import annotations

import base64
import binascii
import secrets
from collections.abc import Awaitable, Callable

from starlette.datastructures import Headers
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from trading_system_api.config import Settings

AUTH_REALM = "Trading System"


class BasicAuthMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        username: str,
        password: str,
        realm: str = AUTH_REALM,
    ) -> None:
        self.app = app
        self.username = username
        self.password = password
        self.realm = realm

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        credentials = _credentials_from_headers(Headers(scope=scope))
        if credentials is not None:
            username, password = credentials
            if secrets.compare_digest(username, self.username) and secrets.compare_digest(
                password,
                self.password,
            ):
                await self.app(scope, receive, send)
                return

        response = _unauthorized_response(self.realm)
        await response(scope, receive, send)


def add_basic_auth_if_enabled(
    app,
    settings: Settings,
    *,
    middleware_factory: Callable[..., Awaitable[Message]] | None = None,
) -> None:
    if not settings.basic_auth_required:
        return
    if not settings.basic_auth_username or not settings.basic_auth_password:
        raise ValueError(
            "BASIC_AUTH_USERNAME and BASIC_AUTH_PASSWORD are required when cloud/basic auth is enabled"
        )
    app.add_middleware(
        middleware_factory or BasicAuthMiddleware,
        username=settings.basic_auth_username,
        password=settings.basic_auth_password,
    )


def _credentials_from_headers(headers: Headers) -> tuple[str, str] | None:
    value = headers.get("authorization")
    if not value or not value.lower().startswith("basic "):
        return None
    try:
        decoded = base64.b64decode(value[6:].strip()).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None
    username, separator, password = decoded.partition(":")
    if not separator:
        return None
    return username, password


def _unauthorized_response(realm: str) -> Response:
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": f'Basic realm="{realm}"'},
    )
