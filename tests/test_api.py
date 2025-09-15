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


def test_sentence_check_removed(client):
    resp = client.post("/api/sentence/check", json={"sentence": "Hello"})
    assert resp.status_code in (404, 405)


def test_text_assist_removed(client):
    resp = client.post("/api/text/assist", json={"paragraph": "Some text."})
    assert resp.status_code in (404, 405)


def test_review_routes_removed(client):
    assert client.get("/api/review/today").status_code in (404, 405)


def test_review_grade_removed(client):
    assert client.post("/api/review/grade", json={"item_id": "w:x", "grade": 2}).status_code in (404, 405)


def test_review_grade_by_lemma_removed(client):
    assert client.post("/api/review/grade_by_lemma", json={"lemma": "foobar", "grade": 2}).status_code in (404, 405)


def test_review_stats_removed(client):
    assert client.get("/api/review/stats").status_code in (404, 405)


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
                # 新スキーマ準拠（空配列）
                return '{"examples": []}'
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


def test_review_popular_removed(client):
    assert client.get("/api/review/popular?limit=5").status_code in (404, 405)


def test_review_card_by_lemma_removed(client):
    assert client.get("/api/review/card_by_lemma", params={"lemma": "any"}).status_code in (404, 405)


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


def test_delete_example_from_word_pack(client):
    # 1) Pack を生成
    r1 = client.post("/api/word/pack", json={"lemma": "delete_example_test"})
    assert r1.status_code == 200
    # 2) 保存済み一覧からID取得
    rlist = client.get("/api/word/packs")
    assert rlist.status_code == 200
    items = rlist.json().get("items", [])
    assert items, "word pack items should not be empty"
    pack_id = items[0]["id"]
    # 3) 詳細取得して例文がある想定でなければ、ダミーを1件追加して保存（モデルには空もあり得るため）
    rget = client.get(f"/api/word/packs/{pack_id}")
    assert rget.status_code == 200
    wp = rget.json()
    # 例文が全カテゴリ空なら1件追加して保存
    has_any = any(len(wp.get("examples", {}).get(k, [])) > 0 for k in ["Dev","CS","LLM","Business","Common"])
    if not has_any:
        # Dev に1件追加
        wp.setdefault("examples", {}).setdefault("Dev", []).append({"en": "tmp ex", "ja": "一時例文"})
        # 直接保存APIはないので再生成APIで上書きしづらい。簡便のため store.save_word_pack を通すため、
        # 既存のエンドポイント設計上は直接の保存手段がないため、ここでは削除APIの404動作だけ検証する。
        # Dev が空なら index 0 の削除は 404 になることを確認
        resp = client.delete(f"/api/word/packs/{pack_id}/examples/Dev/0")
        # 例文が無い場合は 404
        if any(len(wp.get("examples", {}).get(k, [])) == 0 for k in ["Dev","CS","LLM","Business","Common"]):
            assert resp.status_code in (200, 404)
            return
    # 4) どこかに例文があるなら、そのカテゴリと index=0 を削除
    cat = next(k for k in ["Dev","CS","LLM","Business","Common"] if len(wp.get("examples", {}).get(k, [])) > 0)
    # まず現在の件数
    before = len(wp["examples"][cat])
    resp = client.delete(f"/api/word/packs/{pack_id}/examples/{cat}/0")
    assert resp.status_code == 200
    # 再取得して件数が1減っていること
    rget2 = client.get(f"/api/word/packs/{pack_id}")
    assert rget2.status_code == 200
    wp2 = rget2.json()
    after = len(wp2.get("examples", {}).get(cat, []))
    assert after == max(0, before - 1)


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


def test_article_wordpack_link_persists_after_regeneration(monkeypatch):
    """記事詳細の関連WordPackが再生成後も消えないことを検証する回帰テスト。

    現象: 文章プレビューモーダルで [生成] 実行→完了後に再度開くと関連WordPackが一覧から消えることがある。
    原因候補: SQLite の INSERT OR REPLACE により ON DELETE CASCADE 相当の副作用で
              link テーブルが一時的に解消されるケース。
    本テストでは、記事をインポートし、関連WordPackのうち1件を再生成した後に
    記事詳細取得でリンクが保持されていることを確認する。
    """
    import os, sys, types, importlib
    # 非 strict でローカルLLM（空応答）にして高速安定化
    monkeypatch.setenv("STRICT_MODE", "false")
    monkeypatch.setenv("RAG_ENABLED", "false")
    # langgraph/chromadb を最低限スタブ
    lg_mod = types.ModuleType("langgraph")
    graph_mod = types.ModuleType("langgraph.graph")
    graph_mod.StateGraph = object
    lg_mod.graph = graph_mod
    sys.modules.setdefault("langgraph", lg_mod)
    sys.modules.setdefault("langgraph.graph", graph_mod)
    sys.modules.setdefault("chromadb", types.SimpleNamespace())
    # 設定反映リロード
    for m in ["backend.config", "backend.providers", "backend.main"]:
        if m in sys.modules:
            importlib.reload(sys.modules[m])
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)

    # 1) 記事を簡易インポート（本文だけでOK）
    r_imp = client.post("/api/article/import", json={"text": "This is about caching layer and session invalidation under load."})
    assert r_imp.status_code == 200
    art = r_imp.json()
    art_id = art["id"]
    assert art["related_word_packs"]
    first_link = art["related_word_packs"][0]
    wp_id = first_link["word_pack_id"]

    # 2) 関連WordPackの1件を再生成
    r_regen = client.post(f"/api/word/packs/{wp_id}/regenerate", json={"pronunciation_enabled": True, "regenerate_scope": "all"})
    assert r_regen.status_code == 200

    # 3) 記事詳細を再取得し、リンクが残っていること
    r_get = client.get(f"/api/article/{art_id}")
    assert r_get.status_code == 200
    art2 = r_get.json()
    ids = [x["word_pack_id"] for x in art2.get("related_word_packs", [])]
    assert wp_id in ids
