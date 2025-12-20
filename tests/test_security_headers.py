from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
import pytest
from pytest import MonkeyPatch

_BACKEND_ROOT = Path(__file__).resolve().parents[1] / "apps" / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

# CI 環境では Firestore/Google 認証用のデフォルト資格情報がないため、
# backend モジュールを読み込む前に認証系パッケージをモックし、
# Import 時の資格情報検出をスキップする。
google_module = ModuleType("google")
sys.modules["google"] = google_module

google_auth_module = ModuleType("google.auth")
google_auth_module._default = MagicMock()
sys.modules["google.auth"] = google_auth_module

google_auth_exceptions = ModuleType("google.auth.exceptions")
google_auth_exceptions.DefaultCredentialsError = Exception
sys.modules["google.auth.exceptions"] = google_auth_exceptions

google_auth_transport = ModuleType("google.auth.transport")
sys.modules["google.auth.transport"] = google_auth_transport
google_auth_transport_requests = ModuleType("google.auth.transport.requests")
google_auth_transport_requests.Request = MagicMock()
sys.modules["google.auth.transport.requests"] = google_auth_transport_requests
google_auth_transport.requests = google_auth_transport_requests
google_auth_module.transport = google_auth_transport
google_auth_module.exceptions = google_auth_exceptions

firestore_mock = MagicMock()
firestore_mock.Client.return_value = MagicMock()
google_cloud_module = ModuleType("google.cloud")
google_cloud_module.firestore = firestore_mock
sys.modules["google.cloud"] = google_cloud_module
sys.modules["google.cloud.firestore"] = firestore_mock
google_module.auth = google_auth_module
google_module.cloud = google_cloud_module

google_oauth2_module = ModuleType("google.oauth2")
google_oauth2_id_token = ModuleType("google.oauth2.id_token")
google_oauth2_id_token.verify_oauth2_token = MagicMock(return_value={})
google_oauth2_id_token.verify_token = MagicMock(return_value={})
sys.modules["google.oauth2"] = google_oauth2_module
sys.modules["google.oauth2.id_token"] = google_oauth2_id_token
google_oauth2_module.id_token = google_oauth2_id_token
google_module.oauth2 = google_oauth2_module

api_core_exceptions = SimpleNamespace(AlreadyExists=Exception)
api_core_module = ModuleType("google.api_core")
api_core_module.exceptions = api_core_exceptions
sys.modules["google.api_core"] = api_core_module
sys.modules["google.api_core.exceptions"] = api_core_exceptions

# backend.config 読み込み時のバリデーションを安全に通すため、Firestore/セッション関連の
# ダミー環境変数を注入する。元の値は下部のフィクスチャで復元し、他テストへの波及を
# 防ぐ。
_DUMMY_ENV_VARS: dict[str, str] = {
    "FIRESTORE_PROJECT_ID": "test-firestore",
    # Validators では 32 文字以上の乱数文字列を要求するため十分な長さの値を用意する。
    "SESSION_SECRET_KEY": "dummy-session-secret-key-1234567890-abcdef",
    # 環境変数経由で strict_mode を緩和し、未設定項目での起動失敗を避ける。
    "STRICT_MODE": "false",
}
_ORIGINAL_ENV_VARS: dict[str, str | None] = {
    key: os.environ.get(key) for key in _DUMMY_ENV_VARS
}
for key, value in _DUMMY_ENV_VARS.items():
    os.environ.setdefault(key, value)

from backend.config import settings
from backend.main import create_app


@contextmanager
def override_settings(**overrides: object) -> Iterator[None]:
    """Temporarily override backend settings for the duration of a test.

    なぜ: `backend.config.settings` はモジュール読み込み時に確定するシングルトンのため、
    テスト内で値を変更した場合は必ず元に戻さないと他ケースへ影響する。`with` 文で
    一時的に差し替えて終了時に復元するヘルパーを用意し、改修者が安全に設定を操作
    できるようにする。
    """

    original: dict[str, object] = {}
    try:
        for key, value in overrides.items():
            original[key] = getattr(settings, key)
            setattr(settings, key, value)
        yield
    finally:
        for key, value in original.items():
            setattr(settings, key, value)


@pytest.fixture(scope="module", autouse=True)
def _restore_environ() -> Iterator[None]:
    """テスト終了後に環境変数を元の状態へ戻す。"""

    # なぜ: ダミーの環境変数を残したままだと他モジュールの設定読込が意図せず緩和される。
    # ここで復元し、セキュリティ設定の前提がズレないようにする。
    patcher = MonkeyPatch()
    yield
    for key, original in _ORIGINAL_ENV_VARS.items():
        if original is None:
            patcher.delenv(key, raising=False)
        else:
            patcher.setenv(key, original)
    patcher.undo()


@pytest.fixture(scope="module", autouse=True)
def _force_development_settings() -> Iterator[None]:
    """CI/ローカルいずれでも設定バリデーションを安全に通過させる。"""

    # なぜ: CI では ENVIRONMENT=production で実行するため、許可リスト未設定だと
    # Settings モデルの strict バリデーションが Import 時に例外を投げてテストが
    # 開始できない。開発環境相当の設定に強制し、空許可リストによる起動失敗を防ぐ。
    with override_settings(
        environment="development",
        admin_email_allowlist=("test@example.com",),
    ):
        yield


def test_security_headers_are_added_to_primary_endpoints() -> None:
    """主要エンドポイントが想定したセキュリティヘッダを返却することを検証する。"""

    custom_default = ("'self'", "https://cdn.example.com")
    custom_connect = ("'self'", "https://api.example.com")
    with override_settings(
        security_hsts_max_age_seconds=10800,
        security_hsts_preload=True,
        security_csp_default_src=custom_default,
        security_csp_connect_src=custom_connect,
    ):
        app = create_app()
        with TestClient(app) as client:
            for path in ("/healthz", "/api/config"):
                response = client.get(path)
                assert response.status_code == 200
                headers = response.headers
                assert (
                    headers["Strict-Transport-Security"]
                    == "max-age=10800; includeSubDomains; preload"
                )
                csp = headers["Content-Security-Policy"]
                assert "default-src 'self' https://cdn.example.com" in csp
                assert "connect-src 'self' https://api.example.com" in csp
                assert "img-src 'self' https://cdn.example.com data:" in csp
                assert "style-src 'self' https://cdn.example.com 'unsafe-inline'" in csp
                assert "Permissions-Policy" in headers
                assert headers["Permissions-Policy"] == (
                    "camera=(), microphone=(), geolocation=()"
                )
                assert headers["X-Frame-Options"] == "DENY"
                assert headers["X-Content-Type-Options"] == "nosniff"
                assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_rate_limited_response_keeps_security_headers() -> None:
    """429 応答でもセキュリティヘッダが保持されることを確認する。"""

    with override_settings(
        rate_limit_per_min_ip=1,
        rate_limit_per_min_user=1,
        security_hsts_max_age_seconds=3600,
        security_csp_default_src=("'self'",),
        security_csp_connect_src=("'self'",),
    ):
        app = create_app()
        with TestClient(app) as client:
            first = client.get("/healthz")
            assert first.status_code == 200

            second = client.get("/healthz")
            assert second.status_code == 429
            headers = second.headers
            assert headers["Strict-Transport-Security"] == "max-age=3600; includeSubDomains"
            assert headers["Content-Security-Policy"].startswith("default-src 'self'")
            assert headers["X-Frame-Options"] == "DENY"
