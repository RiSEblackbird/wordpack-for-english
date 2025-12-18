import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

from backend.store.firestore_store import FirestoreWordPackStore  # noqa: E402
from tests.firestore_fakes import FakeFirestoreClient  # noqa: E402


def _lemma_payload(store: FirestoreWordPackStore, lemma_id: str) -> dict:
    doc = store._lemmas.document(lemma_id).get()  # pylint: disable=protected-access
    assert doc.exists
    return doc.to_dict() or {}


def test_upsert_preserves_original_label():
    client = FakeFirestoreClient()
    store = FirestoreWordPackStore(client)  # type: ignore[arg-type]

    now = datetime.now(UTC).isoformat()
    lemma_id = store._upsert_lemma(  # pylint: disable=protected-access
        label="Converge",
        sense_title="Sense Title",
        llm_model="gpt-x",
        llm_params='{"temperature": 0.2}',
        now=now,
    )
    payload = _lemma_payload(store, lemma_id)
    assert payload["label"] == "Converge"
    assert payload["sense_title"] == "Sense Title"
    assert payload["llm_model"] == "gpt-x"
    assert payload["llm_params"] == '{"temperature": 0.2}'

    store._upsert_lemma(  # pylint: disable=protected-access
        label="converge",
        sense_title="",
        llm_model=None,
        llm_params=None,
        now=now,
    )
    updated = _lemma_payload(store, lemma_id)
    assert updated["label"] == "Converge"
    assert updated["sense_title"] == "Sense Title"
    assert updated["llm_model"] == "gpt-x"
    assert updated["llm_params"] == '{"temperature": 0.2}'


def test_upsert_does_not_override_existing_sense_title():
    client = FakeFirestoreClient()
    store = FirestoreWordPackStore(client)  # type: ignore[arg-type]

    now = datetime.now(UTC).isoformat()
    lemma_id = store._upsert_lemma(  # pylint: disable=protected-access
        label="Accelerate",
        sense_title="初速を上げる",
        llm_model=None,
        llm_params=None,
        now=now,
    )

    store._upsert_lemma(  # pylint: disable=protected-access
        label="accelerate",
        sense_title="速度を増す",
        llm_model="gpt-5",
        llm_params='{"foo": 1}',
        now=now,
    )

    payload = _lemma_payload(store, lemma_id)
    assert payload["label"] == "Accelerate"
    assert payload["sense_title"] == "初速を上げる"
    assert payload["llm_model"] == "gpt-5"
    assert payload["llm_params"] == '{"foo": 1}'
