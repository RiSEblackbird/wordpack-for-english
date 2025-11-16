from __future__ import annotations

import json
from typing import Any

import pytest

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

from backend.store.firestore_store import AppFirestoreStore  # noqa: E402


class FakeDocumentSnapshot:
    def __init__(self, collection: str, doc_id: str, data: dict[str, Any] | None, client: "FakeFirestoreClient") -> None:
        self._collection = collection
        self.id = doc_id
        self._data = data
        self._client = client

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> dict[str, Any] | None:
        return None if self._data is None else dict(self._data)

    @property
    def reference(self) -> "FakeDocumentReference":
        return FakeDocumentReference(self._client, self._collection, self.id)


class FakeDocumentReference:
    def __init__(self, client: "FakeFirestoreClient", collection: str, doc_id: str) -> None:
        self._client = client
        self._collection = collection
        self.id = doc_id

    def set(self, data: dict[str, Any], merge: bool = False) -> None:
        bucket = self._client._data.setdefault(self._collection, {})
        if merge and self.id in bucket:
            bucket[self.id].update(data)
        else:
            bucket[self.id] = dict(data)

    def update(self, data: dict[str, Any]) -> None:
        bucket = self._client._data.setdefault(self._collection, {})
        if self.id not in bucket:
            raise KeyError(f"document {self._collection}/{self.id} not found")
        bucket[self.id].update(data)

    def get(self, transaction: "FakeTransaction" | None = None) -> FakeDocumentSnapshot:
        bucket = self._client._data.setdefault(self._collection, {})
        payload = dict(bucket[self.id]) if self.id in bucket else None
        return FakeDocumentSnapshot(self._collection, self.id, payload, self._client)

    def delete(self) -> None:
        bucket = self._client._data.setdefault(self._collection, {})
        bucket.pop(self.id, None)


class FakeCollectionReference:
    def __init__(self, client: "FakeFirestoreClient", name: str) -> None:
        self._client = client
        self._name = name

    def document(self, doc_id: str) -> FakeDocumentReference:
        return FakeDocumentReference(self._client, self._name, doc_id)

    def stream(self):  # pragma: no cover - simple iterator
        bucket = self._client._data.setdefault(self._name, {})
        for doc_id, data in bucket.items():
            yield FakeDocumentSnapshot(self._name, doc_id, dict(data), self._client)


class FakeTransaction:
    def __init__(self, client: "FakeFirestoreClient") -> None:
        self._client = client

    def get(self, doc_ref: FakeDocumentReference) -> FakeDocumentSnapshot:
        return doc_ref.get()

    def set(self, doc_ref: FakeDocumentReference, data: dict[str, Any], merge: bool = False) -> None:
        doc_ref.set(data, merge=merge)

    def update(self, doc_ref: FakeDocumentReference, data: dict[str, Any]) -> None:
        doc_ref.update(data)

    def commit(self) -> None:  # pragma: no cover - no-op
        return None


class FakeFirestoreClient:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, dict[str, Any]]] = {}

    def collection(self, name: str) -> FakeCollectionReference:
        return FakeCollectionReference(self, name)

    def transaction(self) -> FakeTransaction:
        return FakeTransaction(self)


@pytest.fixture()
def firestore_store() -> AppFirestoreStore:
    return AppFirestoreStore(client=FakeFirestoreClient())


def test_firestore_word_pack_roundtrip(firestore_store: AppFirestoreStore) -> None:
    payload = {
        "lemma": "Converge",
        "sense_title": "まとまる",
        "examples": {
            "Dev": [
                {"en": "Converge the commits", "ja": "コミットをまとめる", "checked_only_count": 2},
                {"en": "Signals converge", "ja": "信号が収束する"},
            ]
        },
    }
    firestore_store.save_word_pack("wp-1", payload["lemma"], json.dumps(payload, ensure_ascii=False))

    stored = firestore_store.get_word_pack("wp-1")
    assert stored is not None
    lemma, data_json, created_at, updated_at = stored
    assert lemma == "Converge"
    assert created_at <= updated_at
    data = json.loads(data_json)
    assert data["examples"]["Dev"][0]["en"] == "Converge the commits"
    assert data["examples"]["Dev"][0]["checked_only_count"] == 2


def test_firestore_example_progress_and_deletion(firestore_store: AppFirestoreStore) -> None:
    payload = {
        "lemma": "Refine",
        "examples": {
            "Dev": [{"en": "Refine the UI", "ja": "UIを磨く"}],
            "CS": [{"en": "Refine search", "ja": "検索精度を上げる"}],
        },
    }
    firestore_store.save_word_pack("wp-2", payload["lemma"], json.dumps(payload, ensure_ascii=False))
    listed = firestore_store.list_examples(limit=10)
    assert len(listed) == 2
    first_example_id = listed[0][0]

    pack_id, next_checked, next_learned = firestore_store.update_example_study_progress(
        first_example_id, 3, 1
    )
    assert pack_id == "wp-2"
    assert next_checked == 3
    assert next_learned == 1

    remaining = firestore_store.delete_example("wp-2", "Dev", 0)
    assert remaining == 0
    counts = firestore_store.wordpacks.list_word_packs_with_flags(limit=1)[0][6]
    assert counts["Dev"] == 0
    assert counts["CS"] == 1


def test_store_factory_switches_to_firestore(monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.store as store_module

    monkeypatch.setattr(store_module.settings, "environment", "production")

    sentinel = object()
    monkeypatch.setattr(store_module, "AppFirestoreStore", lambda: sentinel)
    new_store = store_module._create_store()
    assert new_store is sentinel
