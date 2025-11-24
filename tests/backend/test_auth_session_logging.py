"""セッション検証失敗時の構造化ログを検証するユニットテスト。"""

from __future__ import annotations

import asyncio
import json
import sys
from http.cookies import SimpleCookie
from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from itsdangerous import BadSignature, SignatureExpired

# apps/backend 配下のモジュールを直接インポートできるようパスを明示的に追加する。
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

from backend.auth import get_current_user, verify_session_token  # noqa: E402
from backend.logging import configure_logging  # noqa: E402


@pytest.fixture(autouse=True)
def _configure_structlog() -> None:
    """Structlog を JSON 出力に統一し、caplog で検証しやすくする。"""

    configure_logging()


def _structlog_events(caplog: pytest.LogCaptureFixture, event: str) -> list[dict[str, object]]:
    """指定イベント名の structlog ペイロードを抽出する。"""

    matches: list[dict[str, object]] = []
    for record in caplog.records:
        raw = record.getMessage()
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(payload, dict) and payload.get("event") == event:
            matches.append(payload)
    return matches


def _build_request(
    path: str = "/api/protected",
    *,
    cookie_header: str | None = None,
    user_agent: str = "pytest-agent",
    client_ip: str = "203.0.113.5",
    request_id: str = "req-123",
) -> Request:
    """モックリクエストを生成し、セッション検証で利用するコンテキストを付与する。"""

    headers = [(b"host", b"testserver")]
    if user_agent:
        headers.append((b"user-agent", user_agent.encode()))
    if cookie_header:
        headers.append((b"cookie", cookie_header.encode()))

    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": headers,
        "query_string": b"",
        "client": (client_ip, 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "app": None,
    }
    request = Request(scope)
    request.state.request_id = request_id
    return request


def _cookie_header(token: str, cookie_name: str = "wp_session") -> str:
    """URL セーフな Cookie ヘッダー文字列を構築する。"""

    cookie = SimpleCookie()
    cookie[cookie_name] = token
    return cookie.output(header="", sep=";").strip()


def test_logs_missing_cookie_context(caplog: pytest.LogCaptureFixture) -> None:
    """セッションクッキー欠如時のログにリクエストコンテキストが含まれる。"""

    request = _build_request()

    with caplog.at_level("WARNING"):
        with pytest.raises(HTTPException):
            asyncio.run(get_current_user(request))

    payloads = _structlog_events(caplog, "session_validation_failed")
    assert payloads
    payload = payloads[0]
    assert payload["reason"] == "missing_cookie"
    assert payload["path"] == "/api/protected"
    assert payload["client_ip"] == "203.0.113.5"
    assert payload["user_agent"] == "pytest-agent"
    assert payload["request_id"] == "req-123"


def test_logs_expired_cookie_context(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """期限切れセッションの警告ログに共通フィールドが揃う。"""

    def _raise_expired(_token: str) -> dict:
        raise SignatureExpired("expired")

    monkeypatch.setattr("backend.auth.verify_session_token", _raise_expired)

    cookie_value = _cookie_header("expired-token")
    request = _build_request(cookie_header=cookie_value)

    with caplog.at_level("WARNING"):
        with pytest.raises(HTTPException):
            asyncio.run(get_current_user(request))

    payloads = _structlog_events(caplog, "session_validation_failed")
    assert payloads
    payload = payloads[0]
    assert payload["reason"] == "expired"
    assert payload["path"] == "/api/protected"
    assert payload["client_ip"] == "203.0.113.5"
    assert payload["user_agent"] == "pytest-agent"
    assert payload["request_id"] == "req-123"

    monkeypatch.setattr("backend.auth.verify_session_token", verify_session_token)


def test_logs_bad_signature_context(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """署名不正時も AccessLog と揃ったフィールドで警告される。"""

    def _raise_bad_signature(_token: str) -> dict:
        raise BadSignature("bad")

    monkeypatch.setattr("backend.auth.verify_session_token", _raise_bad_signature)

    cookie_value = _cookie_header("tampered-token")
    request = _build_request(cookie_header=cookie_value, client_ip="198.51.100.7")

    with caplog.at_level("WARNING"):
        with pytest.raises(HTTPException):
            asyncio.run(get_current_user(request))

    payloads = _structlog_events(caplog, "session_validation_failed")
    assert payloads
    payload = payloads[0]
    assert payload["reason"] == "bad_signature"
    assert payload["path"] == "/api/protected"
    assert payload["client_ip"] == "198.51.100.7"
    assert payload["user_agent"] == "pytest-agent"
    assert payload["request_id"] == "req-123"
