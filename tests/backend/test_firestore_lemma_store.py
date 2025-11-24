import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google.api_core.exceptions import AlreadyExists

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

from backend.store.firestore_store import FirestoreWordPackStore  # noqa: E402


class FakeSnapshot:
    """Firestore DocumentSnapshot 互換の最小実装。"""

    def __init__(self, reference: "FakeDocumentReference", data: dict[str, Any] | None):
        self.reference = reference
        self._data = data
        self.id = reference.id

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> dict[str, Any] | None:
        if self._data is None:
            return None
        return dict(self._data)


class FakeDocumentReference:
    """Firestore DocumentReference 互換の最小実装。"""

    def __init__(self, collection: "FakeCollection", doc_id: str):
        self._collection = collection
        self.id = doc_id

    def get(self) -> FakeSnapshot:
        return FakeSnapshot(self, self._collection._get(self.id))

    def set(self, data: dict[str, Any], merge: bool = False) -> None:
        self._collection._set(self.id, data, merge=merge)

    def create(self, data: dict[str, Any]) -> None:
        self._collection._create(self.id, data)

    def update(self, data: dict[str, Any]) -> None:
        self._collection._update(self.id, data)


class FakeQuery:
    """where + limit に対応した簡易クエリ。"""

    def __init__(self, collection: "FakeCollection", field: str, value: Any, limit: int | None = None):
        self._collection = collection
        self._field = field
        self._value = value
        self._limit = limit

    def limit(self, value: int) -> "FakeQuery":
        return FakeQuery(self._collection, self._field, self._value, limit=value)

    def stream(self):
        matched: list[FakeSnapshot] = []
        with self._collection._lock:
            for doc_id, data in self._collection._docs.items():
                if data.get(self._field) == self._value:
                    matched.append(
                        FakeSnapshot(FakeDocumentReference(self._collection, doc_id), dict(data))
                    )
                if self._limit is not None and len(matched) >= self._limit:
                    break
        return matched


class FakeCollection:
    """スレッドセーフなインメモリコレクション。"""

    def __init__(self):
        self._docs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def document(self, doc_id: str) -> FakeDocumentReference:
        return FakeDocumentReference(self, doc_id)

    def where(self, field_path: str, op: str, value: Any) -> FakeQuery:  # pylint: disable=unused-argument
        return FakeQuery(self, field_path, value)

    def _get(self, doc_id: str) -> dict[str, Any] | None:
        with self._lock:
            data = self._docs.get(doc_id)
            return dict(data) if data is not None else None

    def _set(self, doc_id: str, data: dict[str, Any], merge: bool = False) -> None:
        with self._lock:
            if merge and doc_id in self._docs:
                base = self._docs[doc_id]
                base.update(data)
                self._docs[doc_id] = base
            else:
                self._docs[doc_id] = dict(data)

    def _update(self, doc_id: str, data: dict[str, Any]) -> None:
        with self._lock:
            if doc_id not in self._docs:
                raise KeyError(doc_id)
            self._docs[doc_id].update(data)

    def _create(self, doc_id: str, data: dict[str, Any]) -> None:
        with self._lock:
            if doc_id in self._docs:
                raise AlreadyExists("document already exists")
            self._docs[doc_id] = dict(data)


class FakeTransaction:
    """create/commit だけをサポートするダミー Transaction。"""

    def __init__(self, client: "FakeFirestoreClient"):
        self._client = client

    def get(self, reference: FakeDocumentReference) -> FakeSnapshot:
        return reference.get()

    def create(self, reference: FakeDocumentReference, data: dict[str, Any]) -> None:
        reference.create(data)

    def set(self, reference: FakeDocumentReference, data: dict[str, Any], merge: bool = False) -> None:
        reference.set(data, merge=merge)

    def update(self, reference: FakeDocumentReference, data: dict[str, Any]) -> None:
        reference.update(data)

    def commit(self):
        return True


class FakeFirestoreClient:
    """FirestoreClient 互換の最小モック。"""

    def __init__(self):
        self._collections: dict[str, FakeCollection] = {}

    def collection(self, name: str) -> FakeCollection:
        if name not in self._collections:
            self._collections[name] = FakeCollection()
        return self._collections[name]

    def transaction(self) -> FakeTransaction:
        return FakeTransaction(self)


def test_upsert_reuses_normalized_id_and_updates_legacy_doc():
    client = FakeFirestoreClient()
    store = FirestoreWordPackStore(client)  # type: ignore[arg-type]
    now = datetime.now(UTC).isoformat()

    lemma_id = store._upsert_lemma(  # pylint: disable=protected-access
        label="Converge",
        sense_title="",
        llm_model=None,
        llm_params=None,
        now=now,
    )

    assert lemma_id == "converge"
    lemmas = client.collection("lemmas")._docs
    assert lemmas[lemma_id]["normalized_label"] == "converge"
    assert lemmas[lemma_id]["label"] == "Converge"

    client.collection("lemmas").document("legacy-id").set(
        {
            "label": "Legacy",
            "normalized_label": "legacy",
            "sense_title": "existing",
            "llm_model": "gpt-1",
            "llm_params": "{}",
        }
    )

    updated_id = store._upsert_lemma(  # pylint: disable=protected-access
        label="Legacy",
        sense_title="new",
        llm_model=None,
        llm_params=None,
        now=now,
    )

    assert updated_id == "legacy-id"
    assert lemmas[updated_id]["sense_title"] == "existing"
    assert lemmas[updated_id]["llm_model"] == "gpt-1"
    assert lemmas[updated_id]["normalized_label"] == "legacy"


def test_upsert_blocks_duplicate_creation_under_concurrency():
    client = FakeFirestoreClient()
    store = FirestoreWordPackStore(client)  # type: ignore[arg-type]
    now = datetime.now(UTC).isoformat()

    def _call():
        return store._upsert_lemma(  # pylint: disable=protected-access
            label="Race",
            sense_title="",
            llm_model=None,
            llm_params=None,
            now=now,
        )

    with ThreadPoolExecutor(max_workers=5) as executor:
        lemma_ids = list(executor.map(lambda _: _call(), range(5)))

    assert len(set(lemma_ids)) == 1
    stored = client.collection("lemmas")._docs
    assert len(stored) == 1
    assert next(iter(stored.values())).get("normalized_label") == "race"


def test_upsert_handles_transaction_get_generator():
    client = FakeFirestoreClient()
    store = FirestoreWordPackStore(client)  # type: ignore[arg-type]
    now = datetime.now(UTC).isoformat()

    class GeneratorTransaction(FakeTransaction):
        def get(self, reference: FakeDocumentReference):  # type: ignore[override]
            snapshot = super().get(reference)

            def _gen():
                yield snapshot

            return _gen()

    client.transaction = lambda: GeneratorTransaction(client)  # type: ignore[assignment]

    lemma_id = store._upsert_lemma(  # pylint: disable=protected-access
        label="Resilient",
        sense_title="",
        llm_model=None,
        llm_params=None,
        now=now,
    )

    assert lemma_id == "resilient"
    stored = client.collection("lemmas")._docs
    assert stored[lemma_id]["label"] == "Resilient"
