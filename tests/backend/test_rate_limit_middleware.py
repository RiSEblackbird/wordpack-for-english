from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from starlette.requests import Request
from starlette.responses import Response

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

from backend.config import settings  # noqa: E402  # isort:skip
from backend.middleware import RateLimitMiddleware  # noqa: E402  # isort:skip
import backend.middleware as middleware_module  # noqa: E402  # isort:skip


async def _call_next(_: Request) -> Response:
    return Response("ok", media_type="text/plain")


def _dispatch(middleware: RateLimitMiddleware, request: Request) -> Response:
    return asyncio.run(middleware.dispatch(request, _call_next))


def _make_request(
    *,
    cookie_token: str | None = None,
    header_user: str | None = None,
    client_ip: str = "198.51.100.10",
    cookie_name: str | None = None,
) -> Request:
    resolved_cookie_name = cookie_name or settings.session_cookie_name or "wp_session"
    headers: list[tuple[bytes, bytes]] = []
    if cookie_token is not None:
        cookie_value = f"{resolved_cookie_name}={cookie_token}"
        headers.append((b"cookie", cookie_value.encode("latin-1")))
    if header_user is not None:
        headers.append((b"x-user-id", header_user.encode("latin-1")))
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/api/test",
        "raw_path": b"/api/test",
        "query_string": b"",
        "headers": headers,
        "client": (client_ip, 52314),
        "state": SimpleNamespace(),
    }
    return Request(scope)


def test_rate_limit_enforces_per_user_bucket_via_session_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    observed_tokens: list[str] = []

    def fake_verify(token: str) -> dict[str, str]:
        observed_tokens.append(token)
        if token != "session-token":
            raise RuntimeError("unexpected token")
        return {"sub": "user-123"}

    monkeypatch.setattr(middleware_module, "verify_session_token", fake_verify)

    middleware = RateLimitMiddleware(
        app=lambda scope, receive, send: None,
        ip_capacity_per_minute=100,
        user_capacity_per_minute=2,
        user_bucket_ttl_seconds=60,
        max_user_buckets=8,
    )

    first = _make_request(cookie_token="session-token")
    second = _make_request(cookie_token="session-token")
    third = _make_request(cookie_token="session-token")

    response1 = _dispatch(middleware, first)
    response2 = _dispatch(middleware, second)
    response3 = _dispatch(middleware, third)

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response3.status_code == 429
    assert observed_tokens == ["session-token", "session-token", "session-token"]


def test_rate_limit_ignores_user_header_without_session(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_verify(_: str) -> dict[str, str]:
        raise AssertionError("session verification should not be invoked without cookie")

    monkeypatch.setattr(middleware_module, "verify_session_token", fake_verify)

    middleware = RateLimitMiddleware(
        app=lambda scope, receive, send: None,
        ip_capacity_per_minute=100,
        user_capacity_per_minute=1,
        user_bucket_ttl_seconds=60,
        max_user_buckets=4,
    )

    first = _make_request(header_user="spoof-1")
    second = _make_request(header_user="spoof-2")

    response1 = _dispatch(middleware, first)
    response2 = _dispatch(middleware, second)

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert middleware._anon_bucket_key not in middleware._user_buckets


def test_rate_limit_prunes_stale_user_buckets(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"now": 0.0}

    def fake_time() -> float:
        return clock["now"]

    monkeypatch.setattr(middleware_module.time, "time", fake_time)

    def fake_verify(token: str) -> dict[str, str]:
        return {"sub": token}

    monkeypatch.setattr(middleware_module, "verify_session_token", fake_verify)

    middleware = RateLimitMiddleware(
        app=lambda scope, receive, send: None,
        ip_capacity_per_minute=100,
        user_capacity_per_minute=5,
        user_bucket_ttl_seconds=5,
        max_user_buckets=2,
    )

    req_a = _make_request(cookie_token="user-A")
    resp_a = _dispatch(middleware, req_a)
    assert resp_a.status_code == 200
    assert "user-A" in middleware._user_buckets

    clock["now"] = 1.0
    req_b = _make_request(cookie_token="user-B")
    resp_b = _dispatch(middleware, req_b)
    assert resp_b.status_code == 200
    assert "user-B" in middleware._user_buckets
    assert len(middleware._user_buckets) == 2

    clock["now"] = 6.5
    req_c = _make_request(cookie_token="user-C")
    resp_c = _dispatch(middleware, req_c)
    assert resp_c.status_code == 200

    assert "user-A" not in middleware._user_buckets
    assert len(middleware._user_buckets) <= 2
    assert "user-C" in middleware._user_buckets


def test_rate_limit_accepts_firebase_session_cookie_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    """__session しか届かない経路でもユーザー単位のバケットを活用できる。"""

    observed: list[str] = []

    def fake_verify(token: str) -> dict[str, str]:
        observed.append(token)
        return {"sub": f"user-{token}"}

    monkeypatch.setattr(middleware_module, "verify_session_token", fake_verify)

    middleware = RateLimitMiddleware(
        app=lambda scope, receive, send: None,
        ip_capacity_per_minute=10,
        user_capacity_per_minute=5,
        user_bucket_ttl_seconds=60,
        max_user_buckets=4,
    )

    request = _make_request(cookie_token="firebase", cookie_name="__session")
    response = _dispatch(middleware, request)

    assert response.status_code == 200
    assert observed == ["firebase"]
