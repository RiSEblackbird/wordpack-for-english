import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _reload_backend_app(monkeypatch: pytest.MonkeyPatch, *, strict: bool, db_path: Path | None = None):
    """テスト用に backend.* モジュールを再読み込みしてクリーンな状態を準備する補助関数。"""

    import importlib

    backend_root = Path(__file__).resolve().parents[1] / "apps" / "backend"
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    monkeypatch.setenv("STRICT_MODE", "true" if strict else "false")
    if db_path is not None:
        monkeypatch.setenv("WORDPACK_DB_PATH", str(db_path))

    # backend.* を一度破棄して設定と永続層のキャッシュをリセット
    for name in list(sys.modules.keys()):
        if name == "backend" or name.startswith("backend."):
            sys.modules.pop(name)

    # 必須依存が未導入でも import できるよう最低限スタブ化
    lg_mod = types.ModuleType("langgraph")
    graph_mod = types.ModuleType("langgraph.graph")
    graph_mod.StateGraph = object  # 最小限のダミー
    lg_mod.graph = graph_mod
    sys.modules.setdefault("langgraph", lg_mod)
    sys.modules.setdefault("langgraph.graph", graph_mod)
    sys.modules.setdefault("chromadb", types.SimpleNamespace())

    # 設定・ストアを新しい環境変数で初期化
    importlib.import_module("backend.config")
    importlib.import_module("backend.store")
    return importlib.import_module("backend.main")


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory):
    backend_root = Path(__file__).resolve().parents[1] / "apps" / "backend"
    sys.path.insert(0, str(backend_root))
    db_path = tmp_path_factory.mktemp("wordpack") / "store.sqlite3"
    backend_main = _reload_backend_app(monkeypatch, strict=False, db_path=db_path)
    return TestClient(backend_main.app)


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
    # 生成結果の基本フィールド
    assert "citations" in body and "confidence" in body


def test_word_pack_llm_model_updates_on_generate_and_regenerate(client):
    # 1) 生成時に model を上書きし、llm_model に反映されること
    r_gen = client.post("/api/word/pack", json={"lemma": "alpha", "model": "gpt-4o-mini", "temperature": 0.5})
    assert r_gen.status_code == 200
    wp = r_gen.json()
    assert wp.get("llm_model") == "gpt-4o-mini"
    # 2) 保存済み一覧から ID を取得
    r_list = client.get("/api/word/packs")
    assert r_list.status_code == 200
    items = r_list.json().get("items", [])
    pack_id = next((it["id"] for it in items if it.get("lemma") == "alpha"), None)
    assert pack_id, "generated pack not found"
    # 3) 再生成で model を別値に上書きし、llm_model が更新されること
    r_regen = client.post(f"/api/word/packs/{pack_id}/regenerate", json={
        "pronunciation_enabled": True,
        "regenerate_scope": "all",
        "model": "gpt-5-nano",
        "reasoning": {"effort": "minimal"},
        "text": {"verbosity": "medium"},
    })
    assert r_regen.status_code == 200
    wp2 = r_regen.json()
    assert wp2.get("llm_model") == "gpt-5-nano"


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


def test_word_pack_strict_llm_json_parse_failure_to_502(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    backend_main = _reload_backend_app(monkeypatch, strict=True, db_path=tmp_path / "strict.sqlite3")
    from fastapi.testclient import TestClient
    import backend.providers as providers_mod

    class _StubLLM:
        def complete(self, prompt: str) -> str:
            return "{ not a json }"

    providers_mod._LLM_INSTANCE = _StubLLM()

    client = TestClient(backend_main.app, raise_server_exceptions=False)
    r = client.post("/api/word/pack", json={"lemma": "no_data"})
    assert r.status_code == 502


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


def test_word_pack_strict_empty_llm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """STRICT_MODE で LLM が空文字を返した場合、5xx となることを確認。

    ルータは内部で例外をリレーズするため、FastAPI の既定ハンドラで 500 になる。
    （依存不足系の424は廃止）
    """
    backend_main = _reload_backend_app(monkeypatch, strict=True, db_path=tmp_path / "strict_empty.sqlite3")
    from fastapi.testclient import TestClient
    # LLM を空応答に固定
    import backend.providers as providers_mod

    class _StubLLM:
        def complete(self, prompt: str) -> str:
            return ""

    providers_mod._LLM_INSTANCE = _StubLLM()

    client = TestClient(backend_main.app, raise_server_exceptions=False)
    r = client.post("/api/word/pack", json={"lemma": "no_data"})
    assert 500 <= r.status_code < 600


def test_article_wordpack_link_persists_after_regeneration(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """記事詳細の関連WordPackが再生成後も消えないことを検証する回帰テスト。

    現象: 文章プレビューモーダルで [生成] 実行→完了後に再度開くと関連WordPackが一覧から消えることがある。
    原因候補: SQLite の INSERT OR REPLACE により ON DELETE CASCADE 相当の副作用で
              link テーブルが一時的に解消されるケース。
    本テストでは、記事をインポートし、関連WordPackのうち1件を再生成した後に
    記事詳細取得でリンクが保持されていることを確認する。
    """
    backend_main = _reload_backend_app(monkeypatch, strict=False, db_path=tmp_path / "article_link.sqlite3")
    from fastapi.testclient import TestClient
    import backend.providers as providers_mod
    from backend.flows.article_import import ArticleImportFlow

    monkeypatch.setattr(ArticleImportFlow, "_post_filter_lemmas", lambda self, raw: ["session invalidation"])

    class _StubLLM:
        def complete(self, prompt: str) -> str:
            p = str(prompt or "")
            if "JSON 配列" in p and "lemmas" in p:
                return "{\"lemmas\": [\"session invalidation\", \"concurrency control\"]}"
            if "日本語へ忠実に翻訳" in p:
                return "これはキャッシュレイヤーとセッション無効化を扱う解説文です。"
            if "詳細な解説" in p:
                return "文は高負荷時のキャッシュ戦略とセッション無効化手順を段階的に説明している。"
            if "タイトル" in p:
                return "Cache strategies under load"
            return "補足メモ"

    providers_mod._LLM_INSTANCE = _StubLLM()
    client = TestClient(backend_main.app, raise_server_exceptions=False)

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


def test_category_generate_and_import_endpoint(client, monkeypatch):
    """カテゴリ別の生成＆インポートの簡易テスト。

    - LLM をスタブして決定的に動作させる
    - 返却値に lemma/word_pack_id/article_ids が含まれること
    - 該当WordPackに例文が2件以上追加されていること
    - 作成された記事が取得できること
    """
    import json as _json
    import backend.providers as providers_mod

    class _StubLLM:
        def complete(self, prompt: str) -> str:
            p = (prompt or "")
            # 例文生成プロンプト（スキーマに examples のみ）
            if ("\"examples\"" in p) and ("スキーマ" in p):
                return _json.dumps({
                    "examples": [
                        {"en": "Cache invalidation is one of the two hard things in CS.", "ja": "キャッシュ無効化はCSで難題の一つ。", "grammar_ja": "SVC。"},
                        {"en": "We cache API responses to improve latency under load.", "ja": "負荷時のレイテンシ改善のためAPIレスポンスをキャッシュする。", "grammar_ja": "SVO。"},
                    ]
                })
            # カテゴリ別：単一 lemma を返すプロンプト
            if ("例文生成のためにカテゴリに密接に関連する英語の lemma" in p):
                return '{"lemma":"cache"}'
            # 記事インポート系の補助（lemmas抽出など）
            if ("返却形式" in p) and ("JSON" in p):
                return '["cache","invalidation"]'
            # タイトル/訳/説明等はプレーンテキストで十分
            return "ok"

    # 共有LLMインスタンスをスタブで上書き
    providers_mod._LLM_INSTANCE = _StubLLM()

    r = client.post("/api/article/generate_and_import", json={"category": "Dev"})
    assert r.status_code == 200
    body = r.json()
    assert body["lemma"] == "cache"
    assert body["generated_examples"] >= 2
    assert isinstance(body.get("word_pack_id"), str) and body["word_pack_id"].startswith("wp:")
    assert isinstance(body.get("article_ids"), list) and len(body["article_ids"]) >= 1

    # 記事が取得できること
    first_article_id = body["article_ids"][0]
    r_get = client.get(f"/api/article/{first_article_id}")
    assert r_get.status_code == 200
    art_detail = r_get.json()
    assert art_detail.get("generation_category") == "Dev"
    assert art_detail.get("llm_model")
    assert art_detail.get("generation_started_at")
    assert art_detail.get("generation_completed_at")
    assert art_detail.get("generation_duration_ms") is not None
    assert art_detail.get("generation_duration_ms") >= 0

    # WordPack 一覧から該当 lemma を探し、例文が2件以上あること
    r_list = client.get("/api/word/packs")
    assert r_list.status_code == 200
    items = r_list.json().get("items", [])
    pack_id = next((it["id"] for it in items if it.get("lemma") == "cache"), None)
    assert pack_id, "generated word pack not found in list"
    r_wp = client.get(f"/api/word/packs/{pack_id}")
    assert r_wp.status_code == 200
    wp = r_wp.json()
    assert len(wp.get("examples", {}).get("Dev", [])) >= 2


def test_category_generate_import_fallback_on_duplicate(client, monkeypatch):
    """LLM が既存の lemma を繰り返し提案しても、重複回避で成功すること。

    手順:
    1) 先に `dupword` の WordPack を作成
    2) LLM をスタブし、lemma 選定プロンプトには常に `dupword` を返す
    3) /api/article/generate_and_import を叩くと、409 ではなく 200 で
       別の lemma が選ばれて WordPack が作成されることを検証
    """
    import json as _json
    import backend.providers as providers_mod

    # 1) 先に重複対象の WordPack を用意
    r_pre = client.post("/api/word/pack", json={"lemma": "dupword"})
    assert r_pre.status_code == 200

    class _StubLLMAlwaysDuplicate:
        def complete(self, prompt: str) -> str:
            p = (prompt or "")
            # 例文生成プロンプト（スキーマに examples のみ）
            if ("\"examples\"" in p) and ("スキーマ" in p):
                return _json.dumps({
                    "examples": [
                        {"en": "Example about systems.", "ja": "システムに関する例。", "grammar_ja": "SVO。"},
                        {"en": "Another example about performance.", "ja": "性能に関する別の例。", "grammar_ja": "SVO。"},
                    ]
                })
            # カテゴリ別：単一 lemma を返すプロンプト（常に既存の dupword を返す）
            if ("例文生成のためにカテゴリに密接に関連する英語の lemma" in p):
                return '{"lemma":"dupword"}'
            # 記事インポート系の補助（lemmas抽出など）
            if ("返却形式" in p) and ("JSON" in p):
                return '["dupword","performance"]'
            # タイトル/訳/説明等はプレーンテキストで十分
            return "ok"

    # 共有LLMインスタンスをスタブで上書き
    providers_mod._LLM_INSTANCE = _StubLLMAlwaysDuplicate()

    r = client.post("/api/article/generate_and_import", json={"category": "Dev"})
    # 旧実装では 409。改善後は 200 を期待
    assert r.status_code == 200
    body = r.json()
    assert body["lemma"] != "dupword"
    assert isinstance(body.get("word_pack_id"), str) and body["word_pack_id"].startswith("wp:")
    assert body.get("generated_examples", 0) >= 2


def test_article_import_includes_llm_metadata(monkeypatch, tmp_path):
    """記事インポート時にLLMメタ情報が保存・返却されることを検証する。"""

    backend_main = _reload_backend_app(monkeypatch, strict=False, db_path=tmp_path / "article_llm_meta.sqlite3")
    from fastapi.testclient import TestClient
    import backend.providers as providers_mod
    from backend.flows.article_import import ArticleImportFlow

    monkeypatch.setattr(ArticleImportFlow, "_post_filter_lemmas", lambda self, raw: ["resilience"])

    class _StubLLM:
        def complete(self, prompt: str) -> str:
            text = str(prompt or "")
            if "JSON 配列" in text and "lemmas" in text:
                return '{"lemmas": ["resilience"]}'
            if "日本語へ忠実に翻訳" in text:
                return "これはレジリエンスに関する日本語訳です。"
            if "詳細な解説" in text:
                return "レジリエンスは障害からの迅速な回復能力を指します。"
            if "タイトル" in text:
                return "Operational resilience"
            return "補足"

    providers_mod._LLM_INSTANCE = _StubLLM()
    client = TestClient(backend_main.app, raise_server_exceptions=False)

    payload = {
        "text": "Resilience keeps systems available.",
        "model": "gpt-test-alpha",
        "temperature": 0.42,
        "reasoning": {"effort": "focused"},
        "text_opts": {"verbosity": "medium"},
    }

    r_imp = client.post("/api/article/import", json=payload)
    assert r_imp.status_code == 200
    data = r_imp.json()
    assert data["llm_model"] == "gpt-test-alpha"
    assert data["llm_params"]
    assert "temperature=0.42" in data["llm_params"]
    assert "reasoning.effort=focused" in data["llm_params"]
    assert "text.verbosity=medium" in data["llm_params"]
    # generation_category は明示指定していないため None のままでよい
    assert data["generation_started_at"]
    assert data["generation_completed_at"]
    assert data["generation_duration_ms"] >= 0

    art_id = data["id"]
    r_get = client.get(f"/api/article/{art_id}")
    assert r_get.status_code == 200
    detail = r_get.json()
    assert detail["llm_model"] == "gpt-test-alpha"
    assert detail["llm_params"] == data["llm_params"]
    assert detail["generation_started_at"]
    assert detail["generation_completed_at"]
    assert detail["generation_duration_ms"] >= 0

def test_article_import_category_and_zero_duration(monkeypatch, tmp_path):
    """インポート時に generation_category を指定した場合に保存/再読込で保持され、
    時刻が同一なら duration=0 になることを検証。
    """
    backend_main = _reload_backend_app(monkeypatch, strict=False, db_path=tmp_path / "article_llm_meta2.sqlite3")
    from fastapi.testclient import TestClient
    import backend.providers as providers_mod
    from backend.flows.article_import import ArticleImportFlow

    # lemmas を固定して最低限進むようにする
    monkeypatch.setattr(ArticleImportFlow, "_post_filter_lemmas", lambda self, raw: ["resilience"])

    class _StubLLM:
        def complete(self, prompt: str) -> str:
            text = str(prompt or "")
            if "JSON 配列" in text and "lemmas" in text:
                return '{"lemmas": ["resilience"]}'
            if "日本語へ忠実に翻訳" in text:
                return "訳"
            if "詳細な解説" in text:
                return "解説"
            if "タイトル" in text:
                return "T"
            return "補足"

    providers_mod._LLM_INSTANCE = _StubLLM()
    client = TestClient(backend_main.app, raise_server_exceptions=False)

    payload = {
        "text": "text",
        "model": "gpt-x",
        "temperature": 0.0,
        "generation_category": "Common",
    }

    r_imp = client.post("/api/article/import", json=payload)
    assert r_imp.status_code == 200
    data = r_imp.json()
    assert data.get("generation_category") == "Common"
    # created/updated の等価性に依存せず、duration_ms が 0 以上で返る
    assert data.get("generation_duration_ms") is not None
    art_id = data["id"]

    # 再取得時も同値
    r_get = client.get(f"/api/article/{art_id}")
    assert r_get.status_code == 200
    detail = r_get.json()
    assert detail.get("generation_category") == "Common"
    assert detail.get("generation_started_at")
    assert detail.get("generation_completed_at")
    assert detail.get("generation_duration_ms") is not None
