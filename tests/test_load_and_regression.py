import sys
from pathlib import Path
import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    import os
    os.environ["STRICT_MODE"] = "false"
    from backend.main import app
    return TestClient(app)


def test_simple_load_smoke(client):
    # 軽負荷スモーク（10リクエスト程度）
    start = time.time()
    for _ in range(10):
        r1 = client.get("/healthz")
        # Request ID が付与されている（運用: トレース用）
        assert r1.headers.get("X-Request-ID")
        assert r1.status_code == 200
        r2 = client.post("/api/sentence/check", json={"sentence": "Hello"})
        assert r2.status_code == 200
    elapsed = time.time() - start
    # 10リクエストが5秒以内で応答（ゆるい門）
    assert elapsed < 5.0


def test_prompt_regression_pack_schema(client):
    # プロンプト/生成の回帰: スキーマの必須キーが壊れていないこと
    r = client.post("/api/word/pack", json={"lemma": "regression"})
    assert r.status_code == 200
    j = r.json()
    for key in ["lemma", "senses", "examples", "citations", "confidence"]:
        assert key in j

def test_progress_and_grade_lemma_regression(client):
    # 進捗APIが最低限のキーを返し、整数/配列型であること
    r1 = client.get("/api/review/stats")
    assert r1.status_code == 200
    s = r1.json()
    assert isinstance(s.get("due_now"), int)
    assert isinstance(s.get("reviewed_today"), int)
    assert isinstance(s.get("recent"), list)

    # レンマ採点APIの回帰: 正常応答
    r2 = client.post("/api/review/grade_by_lemma", json={"lemma": "regress", "grade": 1})
    assert r2.status_code == 200
    j2 = r2.json()
    assert j2.get("ok") is True and "next_due" in j2


def test_sla_with_and_without_rag(client):
    """RAG有効/無効の両モードで、基本SLA(少数リクエストで5秒以内)を満たす。"""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    # RAG 有効
    import backend.config as cfg
    cfg.settings.rag_enabled = True
    start = time.time()
    for _ in range(5):
        assert client.post("/api/word/pack", json={"lemma": "sla"}).status_code == 200
    elapsed_on = time.time() - start
    assert elapsed_on < 5.0

    # RAG 無効
    cfg.settings.rag_enabled = False
    start = time.time()
    for _ in range(5):
        assert client.post("/api/word/pack", json={"lemma": "sla"}).status_code == 200
    elapsed_off = time.time() - start
    assert elapsed_off < 5.0


