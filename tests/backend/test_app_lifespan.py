from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[2] / "apps" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from backend import main as backend_main


def test_app_lifespan_runs_startup_and_shutdown_hooks(monkeypatch) -> None:
    """FastAPI の lifespan 経由で起動時/終了時処理が実行されることを検証する。"""

    events: list[str] = []

    async def fake_startup_seed() -> None:
        events.append("startup")

    async def fake_shutdown() -> None:
        events.append("shutdown")

    monkeypatch.setattr(backend_main, "_on_startup_seed", fake_startup_seed)
    monkeypatch.setattr(backend_main, "_on_shutdown", fake_shutdown)

    app = backend_main.create_app()

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert events == ["startup", "shutdown"]
