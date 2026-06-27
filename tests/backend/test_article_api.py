from __future__ import annotations

from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

from tests.firestore_fakes import FakeFirestoreClient
from tests.test_api import _reload_backend_app

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "backend"))


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    backend_main = _reload_backend_app(
        monkeypatch,
        strict=False,
        firestore_client=FakeFirestoreClient(),
    )
    return TestClient(backend_main.app)


def _seed_article(article_id: str = "article:api") -> None:
    from backend.store import store as backend_store

    backend_store.save_article(
        article_id,
        title_en="Reliable Article",
        body_en="Public readers can inspect this article.",
        body_ja="公開読者はこの記事を確認できます。",
        notes_ja=None,
        related_word_packs=[],
    )


def test_article_guest_public_update_endpoint(client: TestClient) -> None:
    _seed_article()

    response = client.post(
        "/api/article/article:api/guest-public",
        json={"guest_public": True},
    )

    assert response.status_code == 200
    assert response.json() == {"article_id": "article:api", "guest_public": True}

    listed = client.get("/api/article")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["guest_public"] is True

    detail = client.get("/api/article/article:api")
    assert detail.status_code == 200
    assert detail.json()["guest_public"] is True


def test_article_guest_public_update_returns_404_for_missing_article(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/article/missing/guest-public",
        json={"guest_public": True},
    )

    assert response.status_code == 404
