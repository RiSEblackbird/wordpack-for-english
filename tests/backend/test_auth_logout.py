"""Unit tests for the logout endpoint ensuring cookie invalidation."""

from http import HTTPStatus
from http.cookies import SimpleCookie
from pathlib import Path
import sys

import pytest

# apps/backend 配下のモジュールを直接インポートできるようパスを明示的に追加する。
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import create_app
from backend.store import AppSQLiteStore


def _stub_google_verifier(monkeypatch, payload_factory):
    """google.oauth2.id_token.verify_oauth2_token をテスト用に差し替える。"""

    from google.oauth2 import id_token

    def _verify(token: str, request: object, audience: str, **kwargs):
        assert audience == settings.google_client_id
        return payload_factory()

    monkeypatch.setattr(id_token, "verify_oauth2_token", _verify)


@pytest.fixture()
def test_client(tmp_path, monkeypatch):
    """ログアウト関連の挙動を検証するための分離済み TestClient を構築する。"""

    db_path = tmp_path / "logout.sqlite3"
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
    monkeypatch.setattr(settings, "disable_session_auth", False)
    monkeypatch.setattr(
        settings,
        "admin_email_allowlist",
        ("logout@example.com",),
    )

    app = create_app()
    return TestClient(app)


def test_logout_deletes_session_cookie(test_client, monkeypatch):
    """ログアウト時にサーバがセッション Cookie を失効させることを検証する。"""

    _stub_google_verifier(
        monkeypatch,
        lambda: {
            "sub": "sub-logout",
            "email": "logout@example.com",
            "name": "Logout Tester",
            "hd": "example.com",
            "email_verified": True,
        },
    )

    login_response = test_client.post("/api/auth/google", json={"id_token": "valid"})
    assert login_response.status_code == HTTPStatus.OK
    primary_cookie_name = settings.session_cookie_name or "wp_session"
    assert test_client.cookies.get(primary_cookie_name)
    assert test_client.cookies.get("__session")

    logout_response = test_client.post("/api/auth/logout")
    assert logout_response.status_code == HTTPStatus.NO_CONTENT

    header = logout_response.headers.get("set-cookie")
    assert header, "logout should instruct the browser to clear the cookie"

    cookie = SimpleCookie()
    cookie.load(header)
    morsel = cookie[primary_cookie_name]
    assert morsel.value == ""
    assert morsel["max-age"] == "0"
    assert str(morsel["httponly"]).lower() == "true"

    # Requests の CookieJar も削除指示を反映していることを確認する。
    assert test_client.cookies.get(primary_cookie_name) is None
    assert test_client.cookies.get("__session") is None

    protected_response = test_client.get("/api/word/")
    assert protected_response.status_code == HTTPStatus.UNAUTHORIZED


def test_logout_requires_authentication(test_client):
    """認証済みでないとログアウト API が 401 を返すことを確認する。"""

    response = test_client.post("/api/auth/logout")
    assert response.status_code == HTTPStatus.UNAUTHORIZED
