from __future__ import annotations

import json
import hashlib
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, Callable

import pytest
from fastapi.testclient import TestClient

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

from backend.config import settings
from backend.main import create_app
from backend.store import AppSQLiteStore


@pytest.fixture()
def test_client(tmp_path, monkeypatch) -> TestClient:
    """Create an isolated FastAPI test client with a dedicated SQLite store."""

    db_path = tmp_path / "auth.sqlite3"
    store_instance = AppSQLiteStore(str(db_path))

    import backend.store as store_module
    import backend.auth as auth_module
    import backend.routers.auth as auth_router_module
    import backend.routers.word as word_router_module
    import backend.routers.article as article_router_module
    monkeypatch.setattr(store_module, "store", store_instance)
    monkeypatch.setattr(auth_module, "store", store_instance)
    monkeypatch.setattr(auth_router_module, "store", store_instance)
    monkeypatch.setattr(word_router_module, "store", store_instance)
    monkeypatch.setattr(article_router_module, "store", store_instance)

    monkeypatch.setattr(settings, "google_client_id", "test-client-id")
    monkeypatch.setattr(settings, "google_allowed_hd", "example.com")
    monkeypatch.setattr(settings, "session_secret_key", "super-secret-key")
    monkeypatch.setattr(settings, "session_max_age_seconds", 3600)
    monkeypatch.setattr(settings, "strict_mode", False)

    # Recreate the app after patching shared modules to ensure new dependencies are wired.
    app = create_app()
    return TestClient(app)


def _stub_verifier(monkeypatch: pytest.MonkeyPatch, factory: Callable[[], dict[str, str]]) -> None:
    from google.oauth2 import id_token

    def _verify(token: str, request: object, audience: str) -> dict[str, str]:
        assert audience == settings.google_client_id
        return factory()

    monkeypatch.setattr(id_token, "verify_oauth2_token", _verify)


def _structlog_events(caplog: pytest.LogCaptureFixture, event: str) -> list[dict[str, Any]]:
    """Collect structlog JSON payloads matching the specified event name."""

    matches: list[dict[str, Any]] = []
    for record in caplog.records:
        raw = record.getMessage()
        try:
            if isinstance(raw, str):
                payload = json.loads(raw)
            elif isinstance(raw, dict):
                payload = raw
            else:
                continue
        except (json.JSONDecodeError, TypeError):
            continue
        if payload.get("event") == event:
            matches.append(payload)
    return matches


def test_google_auth_success_flow(test_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Successful Google sign-in returns cookie and allows protected access."""

    _stub_verifier(
        monkeypatch,
        lambda: {
            "sub": "sub-123",
            "email": "user@example.com",
            "name": "Example User",
            "hd": "example.com",
        },
    )

    login_response = test_client.post("/api/auth/google", json={"id_token": "valid"})
    assert login_response.status_code == 200
    body = login_response.json()
    assert body["user"]["google_sub"] == "sub-123"
    assert "last_login_at" in body["user"]

    cookie = SimpleCookie()
    cookie.load(login_response.headers["set-cookie"])
    assert settings.session_cookie_name in cookie

    protected = test_client.get("/api/word/")
    assert protected.status_code in {200, 501}
    # Both 200 (non-strict) and 501 (strict placeholder) imply auth succeeded; ensure not 401.
    assert protected.status_code != 401


def test_google_auth_rejects_wrong_domain(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Hosted domain mismatch should result in HTTP 403."""

    _stub_verifier(
        monkeypatch,
        lambda: {
            "sub": "sub-456",
            "email": "user@other.com",
            "name": "Other Domain",
            "hd": "other.com",
        },
    )

    with caplog.at_level("WARNING"):
        resp = test_client.post("/api/auth/google", json={"id_token": "valid"})
    assert resp.status_code == 403

    log_entries = _structlog_events(caplog, "google_auth_denied")
    assert log_entries, "expected google_auth_denied log entry"
    log = log_entries[-1]
    assert log["reason"] == "domain_mismatch"
    assert log["hosted_domain"] == "other.com"
    assert log["allowed_domain"] == "example.com"
    expected_hash = hashlib.sha256("user@other.com".lower().encode("utf-8")).hexdigest()[:12]
    assert log["email_hash"] == expected_hash


def test_google_auth_invalid_signature(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Invalid token signature should produce HTTP 401."""

    from google.oauth2 import id_token

    def _raise(token: str, request: object, audience: str) -> dict[str, str]:
        raise ValueError("bad signature")

    monkeypatch.setattr(id_token, "verify_oauth2_token", _raise)

    with caplog.at_level("WARNING"):
        resp = test_client.post("/api/auth/google", json={"id_token": "invalid"})
    assert resp.status_code == 401

    log_entries = _structlog_events(caplog, "google_auth_failed")
    assert log_entries, "expected google_auth_failed log entry"
    log = log_entries[-1]
    assert log["reason"] == "invalid_token"
    assert "bad signature" in log["error"]


def test_google_auth_missing_claims_logs_details(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Ensure missing claims branch records claim names and hashed email."""

    _stub_verifier(
        monkeypatch,
        lambda: {
            "sub": "sub-789",
            "email": "",
            "name": None,
            "hd": "example.com",
        },
    )

    with caplog.at_level("WARNING"):
        resp = test_client.post("/api/auth/google", json={"id_token": "valid"})
    assert resp.status_code == 401

    log_entries = _structlog_events(caplog, "google_auth_failed")
    filtered = [entry for entry in log_entries if entry.get("reason") == "missing_claims"]
    assert filtered, "expected missing_claims log entry"
    log = filtered[-1]
    assert log["missing_claims"] == ["email"]
    assert log.get("email_hash") is None


def test_protected_endpoint_requires_cookie(test_client: TestClient) -> None:
    """Requests without a valid session cookie must fail with 401."""

    # Ensure cookie jar is cleared before hitting protected endpoint
    test_client.cookies.clear()
    resp = test_client.get("/api/word/")
    assert resp.status_code == 401


def test_http_session_cookie_visible_for_document_cookie(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HTTP ローカル環境でも document.cookie から wp_session を参照できることを保証する。"""

    _stub_verifier(
        monkeypatch,
        lambda: {
            "sub": "sub-http",
            "email": "document@example.com",
            "name": "Doc Cookie",
            "hd": "example.com",
        },
    )

    login_response = test_client.post("/api/auth/google", json={"id_token": "valid"})
    assert login_response.status_code == 200

    set_cookie_header = login_response.headers["set-cookie"]
    assert "Secure" not in set_cookie_header

    # document.cookie で参照できる前提条件: CookieJar へ平文HTTPでも保存されていること
    session_cookie_value = test_client.cookies.get(settings.session_cookie_name)
    assert session_cookie_value
