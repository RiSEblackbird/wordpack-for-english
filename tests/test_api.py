import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    sys.modules.setdefault("langgraph", types.SimpleNamespace(Graph=object))
    sys.modules.setdefault("chromadb", types.SimpleNamespace())
    from backend.main import app
    return TestClient(app)


def test_health(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_word_pack(client):
    resp = client.post("/api/word/pack")
    assert resp.status_code == 200
    assert resp.json() == {"detail": "word pack generation pending"}


def test_word_lookup(client):
    resp = client.get("/api/word")
    assert resp.status_code == 200
    assert resp.json() == {"detail": "word lookup pending"}


def test_sentence_check(client):
    resp = client.post("/api/sentence/check", json={"sentence": "Hello"})
    assert resp.status_code == 200
    assert resp.json() == {"detail": "sentence checking pending"}


def test_text_assist(client):
    resp = client.post("/api/text/assist", json={"paragraph": "Some text"})
    assert resp.status_code == 200
    assert resp.json() == {"detail": "reading assistance pending"}


def test_review_today(client):
    resp = client.get("/api/review/today")
    assert resp.status_code == 200
    assert resp.json() == {"detail": "review retrieval pending"}


def test_review_grade(client):
    resp = client.post("/api/review/grade")
    assert resp.status_code == 200
    assert resp.json() == {"detail": "review grading pending"}
