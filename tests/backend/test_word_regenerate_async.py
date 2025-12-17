import time
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "backend"))

from backend.main import app  # noqa: E402
from backend.models.word import (  # noqa: E402
    CollocationLists,
    Collocations,
    Examples,
    Pronunciation,
    WordPack,
)
from backend.routers import word as word_router  # noqa: E402


class _FakeStore:
    def __init__(self) -> None:
        self.data: dict[str, tuple[str, str, str | None, str | None]] = {}

    def get_word_pack(self, word_pack_id: str):
        return self.data.get(word_pack_id)

    def save_word_pack(self, word_pack_id: str, lemma: str, data_json: str):
        self.data[word_pack_id] = (lemma, data_json, None, None)


def _dummy_word_pack(lemma: str = "idempotency") -> WordPack:
    return WordPack(
        lemma=lemma,
        sense_title="dummy",
        pronunciation=Pronunciation(
            ipa_GA=None, ipa_RP=None, syllables=None, stress_index=None, linking_notes=[]
        ),
        senses=[],
        collocations=Collocations(
            general=CollocationLists(verb_object=[], adj_noun=[], prep_noun=[]),
            academic=CollocationLists(verb_object=[], adj_noun=[], prep_noun=[]),
        ),
        contrast=[],
        examples=Examples(Dev=[], CS=[], LLM=[], Business=[], Common=[]),
        etymology={"note": "-", "confidence": "low"},
        study_card="",
        citations=[],
        confidence="low",
    )


@pytest.fixture()
def fake_store() -> _FakeStore:
    store = _FakeStore()
    wp = _dummy_word_pack()
    store.save_word_pack("wp:demo", wp.lemma, wp.model_dump_json())
    return store


@pytest.fixture(autouse=True)
def patch_store_and_flow(monkeypatch: pytest.MonkeyPatch, fake_store: _FakeStore):
    async def _fake_run_flow(**kwargs):
        return _dummy_word_pack(), {"model": "stub", "params": None}

    monkeypatch.setattr(word_router, "store", fake_store)
    monkeypatch.setattr(word_router, "run_wordpack_flow", _fake_run_flow)
    # Clear job registry between tests
    monkeypatch.setattr(word_router, "_regenerate_jobs", {})
    yield


def test_regenerate_async_happy_path():
    client = TestClient(app)
    resp = client.post("/api/word/packs/wp:demo/regenerate/async", json={"regenerate_scope": "all"})
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    # poll status
    status = None
    result = None
    for _ in range(10):
        poll = client.get(f"/api/word/packs/wp:demo/regenerate/jobs/{job_id}")
        assert poll.status_code == 200
        body = poll.json()
        status = body["status"]
        result = body.get("result")
        if status == "succeeded":
            break
        time.sleep(0.01)
    assert status == "succeeded"
    assert result
    assert result["lemma"] == "idempotency"


def test_regenerate_async_job_not_found():
    client = TestClient(app)
    resp = client.get("/api/word/packs/wp:demo/regenerate/jobs/not-found")
    assert resp.status_code == 404

