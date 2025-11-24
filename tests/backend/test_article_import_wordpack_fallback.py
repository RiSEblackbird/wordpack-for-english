"""ArticleImportFlow の WordPack 紐付けフォールバックを検証する。"""

import sys
from pathlib import Path

import pytest
from google.api_core import exceptions as gexc

# backend モジュールを直接 import できるようにパスを追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "backend"))

import backend.flows.article_import as article_module
from backend.flows.article_import import ArticleImportFlow
from backend.store.firestore_store import AppFirestoreStore
from tests.firestore_fakes import FakeFirestoreClient


@pytest.fixture()
def firestore_store() -> AppFirestoreStore:
    return AppFirestoreStore(client=FakeFirestoreClient())


def test_link_or_create_wordpacks_creates_placeholder_with_warning(
    firestore_store: AppFirestoreStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """検索に失敗してもプレースホルダーを作成し、警告を返す。"""

    monkeypatch.setattr(article_module, "store", firestore_store)

    def raise_lookup(_: str, **kwargs: object) -> str | None:
        raise gexc.GoogleAPIError("lookup failed")

    monkeypatch.setattr(firestore_store, "find_word_pack_id_by_lemma", raise_lookup)

    flow = ArticleImportFlow()
    links, warnings = flow._link_or_create_wordpacks_state(["Resilient"])

    assert links
    assert links[0].status == "created"
    assert links[0].warning
    assert any("Resilient" in w for w in warnings)


def test_link_or_create_wordpacks_skips_when_save_fails(
    firestore_store: AppFirestoreStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """保存が失敗した場合はレマをスキップし、警告を残す。"""

    monkeypatch.setattr(article_module, "store", firestore_store)

    def fail_save(*args, **kwargs):
        raise gexc.GoogleAPIError("write failed")

    monkeypatch.setattr(firestore_store, "save_word_pack", fail_save)

    flow = ArticleImportFlow()
    links, warnings = flow._link_or_create_wordpacks_state(["Throughput"])

    assert links == []
    assert warnings
    assert "Throughput" in warnings[0]
