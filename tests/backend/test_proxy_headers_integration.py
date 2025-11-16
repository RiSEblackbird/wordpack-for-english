from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi import Request
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

from backend.config import settings  # noqa: E402  # isort:skip
from backend.main import create_app  # noqa: E402  # isort:skip


@pytest.fixture()
def proxy_app_factory(monkeypatch: pytest.MonkeyPatch):
    """Provide a helper that builds apps with proxy/host settings overridden.

    なぜ: ProxyHeaders/TrustedHost の挙動を検証する統合テストでは、
    TestClient 固有の Host（`testserver`）やクライアント IP（`testclient`）を
    信頼対象として扱う必要があるため、各テストから安全に設定値を
    差し替えられるファクトリを用意する。
    """

    def _factory(**overrides: object):
        monkeypatch.setattr(
            settings,
            "trusted_proxy_ips",
            ("*",),
            raising=False,
        )
        monkeypatch.setattr(
            settings,
            "allowed_hosts",
            ("testserver",),
            raising=False,
        )
        for key, value in overrides.items():
            monkeypatch.setattr(settings, key, value, raising=False)
        return create_app()

    return _factory


def test_rate_limit_uses_forwarded_ip(proxy_app_factory) -> None:
    app = proxy_app_factory(
        rate_limit_per_min_ip=1,
        rate_limit_per_min_user=10,
    )

    with TestClient(app) as client:
        first = client.get("/healthz", headers={"X-Forwarded-For": "198.51.100.10"})
        second = client.get("/healthz", headers={"X-Forwarded-For": "198.51.100.11"})
        third = client.get("/healthz", headers={"X-Forwarded-For": "198.51.100.11"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429


def test_access_log_reports_forwarded_ip(
    proxy_app_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forwarded_ip = "203.0.113.42"
    observed: list[dict[str, object]] = []

    def capture(event: str, **kwargs: object) -> None:
        observed.append({"event": event, **kwargs})

    monkeypatch.setattr("backend.main.logger.info", capture, raising=False)

    app = proxy_app_factory(
        rate_limit_per_min_ip=1000,
        rate_limit_per_min_user=1000,
    )
    with TestClient(app) as client:
        response = client.get("/healthz", headers={"X-Forwarded-For": forwarded_ip})

    assert response.status_code == 200
    assert any(
        entry.get("event") == "request_complete" and entry.get("client_ip") == forwarded_ip
        for entry in observed
    )


def test_request_client_host_reflects_forwarded_for(proxy_app_factory) -> None:
    forwarded_ip = "198.51.100.200"
    app = proxy_app_factory()

    @app.get("/echo-client-ip")
    async def echo_client_ip(request: Request) -> dict[str, str | None]:
        """実際に FastAPI のハンドラから参照した client.host を検証する。"""

        client = request.client.host if request.client else None
        return {"client_ip": client}

    with TestClient(app) as client:
        response = client.get("/echo-client-ip", headers={"X-Forwarded-For": forwarded_ip})

    assert response.status_code == 200
    assert response.json().get("client_ip") == forwarded_ip
