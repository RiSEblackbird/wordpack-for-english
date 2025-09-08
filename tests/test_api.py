import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    # tests: strict を無効化（ダミー・フォールバック許可）
    import os
    os.environ["STRICT_MODE"] = "false"
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

    # invalid lemma should be rejected by validation
    resp3 = client.post("/api/review/grade_by_lemma", json={"lemma": "", "grade": 1})
    assert resp3.status_code == 422


def test_review_stats(client):
    # 基本的に 200 が返り、必須キーがあること
    resp = client.get("/api/review/stats")
    assert resp.status_code == 200
    j = resp.json()
    assert set(["due_now", "reviewed_today", "recent"]).issubset(j.keys())
    assert isinstance(j["due_now"], int)
    assert isinstance(j["reviewed_today"], int)
    assert isinstance(j["recent"], list)


def test_word_pack_returns_424_when_rag_strict_and_no_citations(monkeypatch):
    # strict + RAG を有効化し、chromadb を外して依存未満を再現
    import os, sys
    monkeypatch.setenv("STRICT_MODE", "true")
    monkeypatch.setenv("RAG_ENABLED", "true")
    sys.modules.pop("chromadb", None)
    # backend.config をリロードして settings を反映
    sys.modules.pop("backend.config", None)
    sys.modules.pop("backend.providers", None)
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    r = client.post("/api/word/pack", json={"lemma": "nohit"})
    assert r.status_code == 424
    body = r.json()
    assert "detail" in body


def test_review_popular(client):
    resp = client.get("/api/review/popular?limit=5")
    assert resp.status_code == 200
    arr = resp.json()
    assert isinstance(arr, list)
    if arr:
        first = arr[0]
        assert set(["id", "front", "back"]).issubset(first.keys())


def test_review_card_by_lemma(client):
    # 未存在 → 404
    r404 = client.get("/api/review/card_by_lemma", params={"lemma": "___neverexists___"})
    assert r404.status_code == 404

    # grade_by_lemma で作成 → 取得できる
    lemma = "foobar2"
    r1 = client.post("/api/review/grade_by_lemma", json={"lemma": lemma, "grade": 2})
    assert r1.status_code == 200
    r2 = client.get("/api/review/card_by_lemma", params={"lemma": lemma})
    assert r2.status_code == 200
    j = r2.json()
    assert set(["repetitions", "interval_days", "due_at"]).issubset(j.keys())
