import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    # langgraph を本物のモジュールとしてスタブ（パッケージ/サブモジュール両方）
    lg_mod = types.ModuleType("langgraph")
    graph_mod = types.ModuleType("langgraph.graph")
    graph_mod.StateGraph = object  # 最小スタブ
    lg_mod.graph = graph_mod
    sys.modules.setdefault("langgraph", lg_mod)
    sys.modules.setdefault("langgraph.graph", graph_mod)
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
    # RAG導入後のフィールド
    assert "citations" in body and "confidence" in body


def test_word_lookup(client):
    resp = client.get("/api/word")
    assert resp.status_code == 200
    assert resp.json() == {"definition": None, "examples": []}


def test_sentence_check(client):
    resp = client.post("/api/sentence/check", json={"sentence": "Hello"})
    assert resp.status_code == 200
    j = resp.json()
    assert "issues" in j and isinstance(j["issues"], list)
    assert "citations" in j and "confidence" in j


def test_text_assist(client):
    resp = client.post("/api/text/assist", json={"paragraph": "Some text."})
    assert resp.status_code == 200
    j = resp.json()
    assert "sentences" in j and isinstance(j["sentences"], list)
    assert "citations" in j and "confidence" in j


def test_review_today(client):
    resp = client.get("/api/review/today")
    assert resp.status_code == 200
    j = resp.json()
    assert "items" in j and isinstance(j["items"], list)
    # when seeded, at least 1 item should be due
    if j["items"]:
        first = j["items"][0]
        assert set(["id", "front", "back"]).issubset(first.keys())


def test_review_grade(client):
    # get one card
    today = client.get("/api/review/today").json()
    if not today["items"]:
        return
    item_id = today["items"][0]["id"]
    resp = client.post("/api/review/grade", json={"item_id": item_id, "grade": 2})
    assert resp.status_code == 200
    j = resp.json()
    assert j.get("ok") is True and "next_due" in j


def test_review_grade_by_lemma(client):
    resp = client.post("/api/review/grade_by_lemma", json={"lemma": "foobar", "grade": 2})
    assert resp.status_code == 200
    j = resp.json()
    assert j.get("ok") is True and "next_due" in j

    # invalid grade should be rejected by validation
    resp2 = client.post("/api/review/grade_by_lemma", json={"lemma": "foobar", "grade": 3})
    assert resp2.status_code == 422


def test_review_stats(client):
    # 基本的に 200 が返り、必須キーがあること
    resp = client.get("/api/review/stats")
    assert resp.status_code == 200
    j = resp.json()
    assert set(["due_now", "reviewed_today", "recent"]).issubset(j.keys())
    assert isinstance(j["due_now"], int)
    assert isinstance(j["reviewed_today"], int)
    assert isinstance(j["recent"], list)


def test_review_popular(client):
    resp = client.get("/api/review/popular?limit=5")
    assert resp.status_code == 200
    arr = resp.json()
    assert isinstance(arr, list)
    if arr:
        first = arr[0]
        assert set(["id", "front", "back"]).issubset(first.keys())
