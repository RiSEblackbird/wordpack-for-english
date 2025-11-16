from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import pytest
from google.cloud import firestore

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
        self._count_calls = 0

    def document(self, doc_id: str) -> FakeDocumentReference:
        return FakeDocumentReference(self._client, self._name, doc_id)

    def _all_snapshots(self) -> list[FakeDocumentSnapshot]:
        bucket = self._client._data.setdefault(self._name, {})
        return [
            FakeDocumentSnapshot(self._name, doc_id, dict(data), self._client)
            for doc_id, data in bucket.items()
        ]

    def stream(self):  # pragma: no cover - simple iterator
        for snapshot in self._all_snapshots():
            yield snapshot

    def order_by(self, field_path: str, direction=firestore.Query.ASCENDING):
        return FakeQuery(self, field_path, direction)

    @property
    def count_calls(self) -> int:
        return self._count_calls


class FakeQuery:
    def __init__(
        self,
        collection: FakeCollectionReference,
        field_path: str | None,
        direction,
    ) -> None:
        self._collection = collection
        self._field_path = field_path
        self._descending = direction == firestore.Query.DESCENDING
        self._limit: int | None = None
        self._offset = 0

    def order_by(self, field_path: str, direction=firestore.Query.ASCENDING) -> "FakeQuery":
        self._field_path = field_path
        self._descending = direction == firestore.Query.DESCENDING
        return self

    def limit(self, value: int) -> "FakeQuery":
        self._limit = max(0, int(value))
        return self

    def offset(self, value: int) -> "FakeQuery":
        self._offset = max(0, int(value))
        return self

    def _matching_snapshots(self) -> list[FakeDocumentSnapshot]:
        docs = self._collection._all_snapshots()
        if self._field_path:
            docs.sort(
                key=lambda snap: str((snap.to_dict() or {}).get(self._field_path) or ""),
                reverse=self._descending,
            )
        if self._offset:
            docs = docs[self._offset :]
        if self._limit is not None:
            docs = docs[: self._limit]
        return docs

    def stream(self):  # pragma: no cover - passthrough iterator
        for snapshot in self._matching_snapshots():
            yield snapshot

    def count(self, alias: str | None = None) -> "FakeAggregationQuery":
        self._collection._count_calls += 1
        return FakeAggregationQuery(self, alias or "count")


class FakeAggregationQuery:
    def __init__(self, query: FakeQuery, alias: str) -> None:
        self._query = query
        self._alias = alias

    def stream(self, *args: Any, **kwargs: Any):  # pragma: no cover - simple iterator
        total = len(self._query._matching_snapshots())
        yield FakeAggregationResult(self._alias, total)

    def get(self, *args: Any, **kwargs: Any) -> list["FakeAggregationResult"]:
        return list(self.stream(*args, **kwargs))


class FakeAggregationResult:
    def __init__(self, alias: str, value: int) -> None:
        self.alias = alias
        self.value = value


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


def test_list_word_packs_paginates_via_firestore_query(
    firestore_store: AppFirestoreStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    timestamps = iter(
        [
            "2024-01-01T00:00:01+00:00",
            "2024-01-01T00:00:02+00:00",
            "2024-01-01T00:00:03+00:00",
        ]
    )
    monkeypatch.setattr("backend.store.firestore_store._now_iso", lambda: next(timestamps))

    for idx, lemma in enumerate(["Alpha", "Beta", "Gamma"], start=1):
        firestore_store.save_word_pack(
            f"wp-{idx}",
            lemma,
            json.dumps({"lemma": lemma, "examples": {}}, ensure_ascii=False),
        )

    first_page = firestore_store.list_word_packs(limit=2, offset=0)
    assert [row[1] for row in first_page] == ["Gamma", "Beta"]

    second_page = firestore_store.list_word_packs(limit=2, offset=2)
    assert [row[1] for row in second_page] == ["Alpha"]

    flagged_page = firestore_store.list_word_packs_with_flags(limit=1, offset=1)
    assert [row[1] for row in flagged_page] == ["Beta"]


def test_count_word_packs_uses_server_side_aggregation(
    firestore_store: AppFirestoreStore,
) -> None:
    for idx, lemma in enumerate(["Delta", "Echo"], start=1):
        firestore_store.save_word_pack(
            f"pack-{idx}",
            lemma,
            json.dumps({"lemma": lemma, "examples": {}}, ensure_ascii=False),
        )

    total = firestore_store.count_word_packs()
    assert total == 2
    assert firestore_store.wordpacks._word_packs.count_calls == 1


def test_store_factory_switches_to_firestore(monkeypatch: pytest.MonkeyPatch) -> None:
    import backend.store as store_module

    monkeypatch.setattr(store_module.settings, "environment", "production")

    sentinel = object()
    monkeypatch.setattr(store_module, "AppFirestoreStore", lambda: sentinel)
    new_store = store_module._create_store()
    assert new_store is sentinel
