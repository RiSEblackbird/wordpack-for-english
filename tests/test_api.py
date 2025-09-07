import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    # langgraph の最小スタブ（StateGraph の参照を許す）
    lg = types.SimpleNamespace(graph=types.SimpleNamespace(StateGraph=object))
    sys.modules.setdefault("langgraph", lg)
    sys.modules.setdefault("chromadb", types.SimpleNamespace())
    from backend.main import app
    return TestClient(app)


def test_health(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_word_pack(client):
    resp = client.post("/api/word/pack", json={"lemma": "converge"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["lemma"] == "converge"
    assert "senses" in body


def test_word_lookup(client):
    resp = client.get("/api/word")
    assert resp.status_code == 200
    assert resp.json() == {"definition": None, "examples": []}


def test_sentence_check(client):
    resp = client.post("/api/sentence/check", json={"sentence": "Hello"})
    assert resp.status_code == 200
    j = resp.json()
    assert "issues" in j and isinstance(j["issues"], list)


def test_text_assist(client):
    resp = client.post("/api/text/assist", json={"paragraph": "Some text."})
    assert resp.status_code == 200
    j = resp.json()
    assert "sentences" in j and isinstance(j["sentences"], list)


def test_review_today(client):
    resp = client.get("/api/review/today")
    assert resp.status_code == 200
    assert resp.json() == {"detail": "review retrieval pending"}


def test_review_grade(client):
    resp = client.post("/api/review/grade")
    assert resp.status_code == 200
    assert resp.json() == {"detail": "review grading pending"}
