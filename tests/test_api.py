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
    # 設定変更後に関連モジュールをリロードして反映
    import importlib
    for m in ["backend.config", "backend.providers", "backend.main"]:
        if m in sys.modules:
            importlib.reload(sys.modules[m])
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
    import os, sys, importlib, types
    # 退避
    prev_strict = os.environ.get("STRICT_MODE")
    prev_rag = os.environ.get("RAG_ENABLED")
    prev_openai = os.environ.get("OPENAI_API_KEY")
    try:
        monkeypatch.setenv("STRICT_MODE", "true")
        monkeypatch.setenv("RAG_ENABLED", "true")
        sys.modules.pop("chromadb", None)
        # backend.config / backend.providers / backend.main をリロードして settings を反映
        for m in ["backend.config", "backend.providers", "backend.main"]:
            if m in sys.modules:
                importlib.reload(sys.modules[m])
        # LLM を完全モック化してキー不要にする
        import backend.providers as providers_mod
        class _StubLLM:
            def complete(self, prompt: str) -> str:
                # 最小のJSON（examplesの空辞書）を返し、LLM依存を回避
                return '{"examples": {"Dev": [], "CS": [], "LLM": [], "Tech": [], "Common": []}}'
        providers_mod._LLM_INSTANCE = _StubLLM()
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        r = client.post("/api/word/pack", json={"lemma": "nohit"})
        assert r.status_code == 424
        body = r.json()
        assert "detail" in body
    finally:
        # 元の環境に戻す（テスト汚染回避）
        if prev_strict is None:
            os.environ.pop("STRICT_MODE", None)
        else:
            os.environ["STRICT_MODE"] = prev_strict
        if prev_rag is None:
            os.environ.pop("RAG_ENABLED", None)
        else:
            os.environ["RAG_ENABLED"] = prev_rag
        if prev_openai is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = prev_openai or ""
        # chromadb を最低限のスタブに戻す
        sys.modules.setdefault("chromadb", types.SimpleNamespace())
        # 関連モジュールを非厳格に戻した環境で再ロード
        for m in ["backend.config", "backend.providers", "backend.main"]:
            if m in sys.modules:
                importlib.reload(sys.modules[m])


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


def test_word_pack_persistence(client):
    """WordPack永続化機能のテスト"""
    # 1. 新しいWordPackを生成（自動保存される）
    resp = client.post("/api/word/pack", json={"lemma": "persistence_test"})
    assert resp.status_code == 200
    word_pack = resp.json()
    assert word_pack["lemma"] == "persistence_test"
    
    # 2. 保存済みWordPack一覧を取得
    resp = client.get("/api/word/packs")
    assert resp.status_code == 200
    packs_list = resp.json()
    assert "items" in packs_list
    assert "total" in packs_list
    assert "limit" in packs_list
    assert "offset" in packs_list
    assert len(packs_list["items"]) > 0
    
    # 最初のWordPackのIDを取得
    first_pack = packs_list["items"][0]
    pack_id = first_pack["id"]
    assert "id" in first_pack
    assert "lemma" in first_pack
    assert "created_at" in first_pack
    assert "updated_at" in first_pack
    
    # 3. 特定のWordPackを取得
    resp = client.get(f"/api/word/packs/{pack_id}")
    assert resp.status_code == 200
    retrieved_pack = resp.json()
    assert retrieved_pack["lemma"] == first_pack["lemma"]
    assert "senses" in retrieved_pack
    assert "citations" in retrieved_pack
    assert "confidence" in retrieved_pack
    
    # 4. WordPackを再生成
    resp = client.post(f"/api/word/packs/{pack_id}/regenerate", json={
        "pronunciation_enabled": True,
        "regenerate_scope": "all"
    })
    assert resp.status_code == 200
    regenerated_pack = resp.json()
    assert regenerated_pack["lemma"] == first_pack["lemma"]
    
    # 5. 存在しないWordPackの取得
    resp = client.get("/api/word/packs/nonexistent_id")
    assert resp.status_code == 404
    
    # 6. WordPackを削除
    resp = client.delete(f"/api/word/packs/{pack_id}")
    assert resp.status_code == 200
    delete_result = resp.json()
    assert "message" in delete_result
    
    # 7. 削除後の確認
    resp = client.get(f"/api/word/packs/{pack_id}")
    assert resp.status_code == 404
    
    # 8. 存在しないWordPackの削除
    resp = client.delete("/api/word/packs/nonexistent_id")
    assert resp.status_code == 404


def test_word_pack_list_pagination(client):
    """WordPack一覧のページネーション機能のテスト"""
    # 複数のWordPackを生成
    for i in range(3):
        resp = client.post("/api/word/pack", json={"lemma": f"pagination_test_{i}"})
        assert resp.status_code == 200
    
    # ページネーションパラメータをテスト
    resp = client.get("/api/word/packs?limit=2&offset=0")
    assert resp.status_code == 200
    result = resp.json()
    assert len(result["items"]) <= 2
    assert result["limit"] == 2
    assert result["offset"] == 0
    
    # 無効なパラメータのテスト
    resp = client.get("/api/word/packs?limit=0")
    assert resp.status_code == 422  # validation error
    
    resp = client.get("/api/word/packs?offset=-1")
    assert resp.status_code == 422  # validation error


def test_word_pack_strict_empty_llm(monkeypatch):
    """STRICT_MODE で LLM が空文字を返した場合、5xx となることを確認。

    ルータは内部で例外をリレーズするため、FastAPI の既定ハンドラで 500 になる。
    （RAG 依存不足時の 424 は別テストで担保済み）
    """
    import os, sys
    import importlib
    # Strict を有効化して設定を再ロード
    monkeypatch.setenv("STRICT_MODE", "true")
    # 既存LLMインスタンスをクリア
    try:
        import backend.providers as providers
        providers._LLM_INSTANCE = None
    except Exception:
        pass
    for m in ["backend.config", "backend.providers", "backend.main"]:
        if m in sys.modules:
            importlib.reload(sys.modules[m])
    from backend import main as backend_main
    from fastapi.testclient import TestClient
    # LLM を空応答に固定
    import backend.providers as providers_mod

    class _StubLLM:
        def complete(self, prompt: str) -> str:
            return ""

    providers_mod._LLM_INSTANCE = _StubLLM()

    client = TestClient(backend_main.app)
    r = client.post("/api/word/pack", json={"lemma": "no_data"})
    assert 500 <= r.status_code < 600
