"""FastAPI の CORS 応答ヘッダーを検証するテスト。"""

from fastapi.testclient import TestClient

from backend.config import Settings
from backend import main as backend_main


def _build_app_with_settings(settings: Settings) -> TestClient:
    """Inject temporary settings into `create_app` and return a test client.

    なぜ: グローバル設定はモジュール読み込み時に確定するため、テストごとに
    `backend.main.settings` を差し替えて CORS 設定のバリエーションを安全に
    検証する。
    """

    original_settings = backend_main.settings
    backend_main.settings = settings
    try:
        app = backend_main.create_app()
        return TestClient(app)
    finally:
        backend_main.settings = original_settings


def test_cors_allows_only_configured_origin() -> None:
    """許可オリジンにはヘッダーが付き、未許可には付かないことを確認する。"""

    client = _build_app_with_settings(
        Settings(
            allowed_cors_origins=(
                "https://app.example.com",
                "https://admin.example.com",
            ),
            _env_file=None,
        )
    )

    allowed = client.options(
        "/healthz",
        headers={
            "Origin": "https://app.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://app.example.com"
    assert allowed.headers["access-control-allow-credentials"] == "true"

    denied = client.options(
        "/healthz",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers


def test_cors_wildcard_disables_credentials() -> None:
    """許可オリジン未設定時はワイルドカードと `allow_credentials=false` を返す。"""

    client = _build_app_with_settings(Settings(_env_file=None))

    preflight = client.options(
        "/healthz",
        headers={
            "Origin": "https://anywhere.example",  # 任意オリジン
            "Access-Control-Request-Method": "GET",
        },
    )

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in preflight.headers
