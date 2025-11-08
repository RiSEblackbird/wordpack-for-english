from __future__ import annotations

from http.cookies import SimpleCookie
from pathlib import Path
from typing import Callable

from http.cookies import SimpleCookie
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Callable

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
    monkeypatch.setattr(settings, "session_cookie_name", "wp_session_test")
    monkeypatch.setattr(settings, "session_cookie_secure", False)
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
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch
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

    resp = test_client.post("/api/auth/google", json={"id_token": "valid"})
    assert resp.status_code == 403


def test_google_auth_invalid_signature(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Invalid token signature should produce HTTP 401."""

    from google.oauth2 import id_token

    def _raise(token: str, request: object, audience: str) -> dict[str, str]:
        raise ValueError("bad signature")

    monkeypatch.setattr(id_token, "verify_oauth2_token", _raise)

    resp = test_client.post("/api/auth/google", json={"id_token": "invalid"})
    assert resp.status_code == 401


def test_protected_endpoint_requires_cookie(test_client: TestClient) -> None:
    """Requests without a valid session cookie must fail with 401."""

    # Ensure cookie jar is cleared before hitting protected endpoint
    test_client.cookies.clear()
    resp = test_client.get("/api/word/")
    assert resp.status_code == 401
