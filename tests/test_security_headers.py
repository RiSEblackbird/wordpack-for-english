from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sys

from fastapi.testclient import TestClient

_BACKEND_ROOT = Path(__file__).resolve().parents[1] / "apps" / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

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
