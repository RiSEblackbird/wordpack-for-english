from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Firestore クライアントの生成に必要な最小限の環境を先に整える。
os.environ.setdefault("FIRESTORE_EMULATOR_HOST", "localhost:8080")
os.environ.setdefault("FIRESTORE_PROJECT_ID", "test-project")

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

from backend.config import settings
from backend.main import create_app
from backend.models.article import ARTICLE_IMPORT_TEXT_MAX_LENGTH
from backend.store import AppFirestoreStore
from tests.firestore_fakes import FakeFirestoreClient


@pytest.fixture()
def article_client(monkeypatch) -> TestClient:
    """413の検証に必要な最小構成でFastAPIクライアントを生成する。"""

    store_instance = AppFirestoreStore(client=FakeFirestoreClient())

    import backend.store as store_module
    import backend.routers.article as article_router_module

    monkeypatch.setattr(store_module, "store", store_instance)
    monkeypatch.setattr(article_router_module, "store", store_instance)

    monkeypatch.setattr(settings, "session_secret_key", "test-secret-key")
    monkeypatch.setattr(settings, "disable_session_auth", True)
    monkeypatch.setattr(settings, "strict_mode", False)

    app = create_app()
    return TestClient(app)


def test_article_import_rejects_text_over_limit(article_client: TestClient) -> None:
    """文字数上限を超えた文章はHTTP 413で拒否されることを検証する。"""

    payload = {"text": "a" * (ARTICLE_IMPORT_TEXT_MAX_LENGTH + 1)}

    response = article_client.post("/api/article/import", json=payload)

    assert response.status_code == 413
    detail = response.json()["detail"]
    assert detail["error"] == "article_import_text_too_long"
    assert detail["max_length"] == ARTICLE_IMPORT_TEXT_MAX_LENGTH
    assert str(ARTICLE_IMPORT_TEXT_MAX_LENGTH) in detail["message"]
