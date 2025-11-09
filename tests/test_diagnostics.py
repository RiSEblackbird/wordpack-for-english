from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend"))

from backend.config import settings  # noqa: E402  # isort:skip
from backend.main import create_app  # noqa: E402  # isort:skip


@pytest.fixture()
def diagnostics_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """FastAPI クライアントを生成し、診断用ルーターのテスト環境を用意する。"""

    monkeypatch.setattr(settings, "strict_mode", False)
    monkeypatch.setattr(settings, "disable_session_auth", True)
    app = create_app()
    return TestClient(app)


def test_oauth_telemetry_masks_sensitive_fields(
    diagnostics_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """ID トークン欠落時の診断エンドポイントが機密値をマスクして警告ログを出力することを検証する。"""

    caplog.set_level("WARNING")
    payload = {
        "event": "google_login_missing_id_token",
        "googleClientId": "frontend-client",
        "errorCategory": "missing_id_token",
        "tokenResponse": {
            "access_token": "mock-access-token",
            "email": "user@example.com",
            "scope": "openid profile email",
        },
    }

    response = diagnostics_client.post("/api/diagnostics/oauth-telemetry", json=payload)

    assert response.status_code == 204
    lines = [ln for ln in caplog.text.splitlines() if ln.strip()]
    telemetry_line = next(
        (
            ln
            for ln in lines
            if ln.strip().startswith("{") and "google_login_missing_id_token" in ln
        ),
        None,
    )
    assert telemetry_line is not None, "expected warning log not emitted"

    parsed = json.loads(telemetry_line)
    token_response = parsed.get("token_response", {})
    assert token_response.get("access_token") != "mock-access-token"
    assert "user@example.com" not in json.dumps(token_response)
    assert parsed.get("google_client_id") == "frontend-client"
    assert parsed.get("error_category") == "missing_id_token"
