"""ゲストモードの判定と書き込み制限ミドルウェアの契約テスト。"""

from __future__ import annotations

import json
import os
import sys
from http import HTTPStatus
from pathlib import Path

import pytest

# Firestore エミュレータを利用して認証不要のクライアントを使う。
os.environ.setdefault("FIRESTORE_EMULATOR_HOST", "localhost:8080")
os.environ.setdefault("FIRESTORE_PROJECT_ID", "test-project")
os.environ.setdefault("GCP_PROJECT_ID", "test-project")

# apps/backend 配下のモジュールを直接インポートできるようパスを明示的に追加する。
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

from fastapi.testclient import TestClient

from backend.config import settings
from backend.store import AppFirestoreStore
from tests.firestore_fakes import (
    FakeFirestoreClient,
    ensure_firestore_test_env,
    use_fake_firestore_client,
)


@pytest.fixture()
def guest_test_client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, AppFirestoreStore]:
    """ゲストモード関連の API を検証するための TestClient を構築する。"""

    ensure_firestore_test_env(monkeypatch)
    store_instance = AppFirestoreStore(client=use_fake_firestore_client(monkeypatch))
    assert isinstance(store_instance._client, FakeFirestoreClient)

    import backend.store as store_module
    import backend.auth as auth_module
    import backend.routers.word as word_router_module
    import backend.routers.article as article_router_module

    monkeypatch.setattr(settings, "environment", "test")
    monkeypatch.setattr(settings, "firestore_emulator_host", "localhost:8080")
    monkeypatch.setattr(settings, "firestore_project_id", "test-project")
    monkeypatch.setattr(settings, "gcp_project_id", "test-project")
    monkeypatch.setattr(settings, "session_secret_key", "guest-secret-key")
    monkeypatch.setattr(settings, "session_max_age_seconds", 3600)
    monkeypatch.setattr(settings, "guest_session_cookie_name", "wp_guest")
    monkeypatch.setattr(settings, "guest_session_max_age_seconds", 1800)
    monkeypatch.setattr(settings, "strict_mode", False)
    monkeypatch.setattr(settings, "disable_session_auth", False)
    monkeypatch.setattr(store_module, "AppFirestoreStore", lambda *args, **kwargs: store_instance)
    monkeypatch.setattr(store_module, "store", store_instance)
    monkeypatch.setattr(auth_module, "store", store_instance)
    monkeypatch.setattr(word_router_module, "store", store_instance)
    monkeypatch.setattr(article_router_module, "store", store_instance)

    from backend.main import create_app

    app = create_app()
    return TestClient(app), store_instance


def _seed_wordpack(store: AppFirestoreStore, lemma: str) -> None:
    """ゲスト閲覧の対象になる WordPack データを最小構成で保存する。"""

    payload = {
        "lemma": lemma,
        "sense_title": f"{lemma} title",
        "examples": {},
    }
    store.save_word_pack(f"wp-{lemma}", lemma, json.dumps(payload, ensure_ascii=False))


def test_guest_session_cookie_is_issued(guest_test_client: tuple[TestClient, AppFirestoreStore]) -> None:
    """ゲストセッション発行エンドポイントが署名済み Cookie を返すことを確認する。"""

    client, _store = guest_test_client

    response = client.post("/api/auth/guest")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"mode": "guest"}

    cookie_name = settings.guest_session_cookie_name
    assert client.cookies.get(cookie_name)


def test_guest_can_access_readonly_endpoint(guest_test_client: tuple[TestClient, AppFirestoreStore]) -> None:
    """ゲストセッションで WordPack の閲覧系 API が利用できることを確認する。"""

    client, store = guest_test_client
    _seed_wordpack(store, "guest")

    response = client.post("/api/auth/guest")
    assert response.status_code == HTTPStatus.OK

    lookup = client.get("/api/word/", params={"lemma": "guest"})
    assert lookup.status_code == HTTPStatus.OK
    assert lookup.json()["lemma"] == "guest"


def test_guest_write_is_denied(guest_test_client: tuple[TestClient, AppFirestoreStore]) -> None:
    """ゲストセッションは書き込み系の API を 403 で拒否される。"""

    client, _store = guest_test_client

    response = client.post("/api/auth/guest")
    assert response.status_code == HTTPStatus.OK

    denied = client.post("/api/word/packs", json={"lemma": "blocked"})
    assert denied.status_code == HTTPStatus.FORBIDDEN
    assert denied.json()["detail"] == "Guest mode cannot perform write operations"
