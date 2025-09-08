import os
import sys
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client_with_chroma(tmp_path_factory):
    # テスト専用の Chroma 永続ディレクトリ
    persist_dir = tmp_path_factory.mktemp("chroma")
    os.environ["CHROMA_PERSIST_DIR"] = str(persist_dir)
    os.environ["STRICT_MODE"] = "false"

    # 先にスタブが注入されている可能性をクリア
    for mod in ["chromadb", "langgraph", "langgraph.graph"]:
        if mod in sys.modules and getattr(sys.modules[mod], "__name__", None):
            sys.modules.pop(mod)

    # src を import パスに追加
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

    # 依存をインポートして最小シード投入
    from backend.providers import ChromaClientFactory
    from backend.indexing import seed_word_snippets, seed_domain_terms

    client = ChromaClientFactory(persist_directory=str(persist_dir)).create_client()
    assert client is not None, "chromadb が利用できません"
    seed_word_snippets(client)
    seed_domain_terms(client)

    # アプリをロード
    from backend.main import app
    return TestClient(app)


def test_word_pack_integration_rag(client_with_chroma):
    # 近傍のある語で問い合わせ
    resp = client_with_chroma.post("/api/word/pack", json={"lemma": "converge"})
    assert resp.status_code == 200
    j = resp.json()
    # citations が1件以上、confidence が medium 以上（実装では medium）
    assert isinstance(j.get("citations"), list)
    assert len(j.get("citations")) >= 1
    assert j.get("confidence") in ("medium", "high")


