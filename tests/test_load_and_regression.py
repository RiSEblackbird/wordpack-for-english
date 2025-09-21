import os
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("STRICT_MODE", "false")


@pytest.fixture(scope="module")
def client():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend"))
    os.environ["STRICT_MODE"] = "false"
    import importlib
    importlib.invalidate_caches()
    for name in list(sys.modules.keys()):
        if name == "backend" or name.startswith("backend."):
            sys.modules.pop(name)
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

def test_review_endpoints_removed(client):
    # 復習系の互換APIは提供されない（404/405）
    assert client.get("/api/review/stats").status_code in (404, 405)
    assert client.post("/api/review/grade_by_lemma", json={"lemma": "regress", "grade": 1}).status_code in (404, 405)


def test_sla_word_pack_smoke(client):
    """基本SLA(少数リクエストで5秒以内)を満たす。"""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend"))
    start = time.time()
    for _ in range(10):
        assert client.post("/api/word/pack", json={"lemma": "sla"}).status_code == 200
    elapsed = time.time() - start
    assert elapsed < 5.0


