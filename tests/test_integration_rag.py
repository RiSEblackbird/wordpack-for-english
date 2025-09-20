import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("STRICT_MODE", "false")


@pytest.fixture(scope="module")
def client_with_openai_llm():
    """OpenAI LLMを使用するテストクライアント"""
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["LLM_MODEL"] = "gpt-4o-mini"
    os.environ["STRICT_MODE"] = "false"
    
    # OpenAI APIキーが設定されていない場合はダミーキーを使用
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = "test-key"

    # src を import パスに追加
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend"))

    # 設定反映のため関連モジュールをリロード
    import importlib
    importlib.invalidate_caches()
    for name in list(sys.modules.keys()):
        if name == "backend" or name.startswith("backend."):
            sys.modules.pop(name)
    for m in ["backend.providers", "backend.main"]:
        if m in sys.modules:
            importlib.reload(sys.modules[m])

    # アプリをロード
    from backend.main import app
    return TestClient(app)


def test_word_pack_integration_openai_llm(client_with_openai_llm):
    """OpenAI LLMを使用した単語パック生成のテスト"""
    resp = client_with_openai_llm.post("/api/word/pack", json={"lemma": "converge"})
    assert resp.status_code == 200
    j = resp.json()
    
    # 基本的な構造の確認
    assert "lemma" in j
    assert j["lemma"] == "converge"
    assert "confidence" in j
    assert "citations" in j
    assert isinstance(j["citations"], list)
    
    # LLMが使用されている場合、confidenceはmedium以上になる
    assert j["confidence"] in ("medium", "high")
