import sys
from pathlib import Path
import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from backend.main import app
    return TestClient(app)


def test_simple_load_smoke(client):
    # 軽負荷スモーク（10リクエスト程度）
    start = time.time()
    for _ in range(10):
        r1 = client.get("/healthz")
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


