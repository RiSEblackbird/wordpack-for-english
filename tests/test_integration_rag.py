import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client_with_openai_llm():
    """OpenAI LLMを使用するテストクライアント"""
    # RAGを無効化し、OpenAI LLMを使用する設定
    os.environ["RAG_ENABLED"] = "false"
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["LLM_MODEL"] = "gpt-4o-mini"
    os.environ["STRICT_MODE"] = "false"
    
    # OpenAI APIキーが設定されていない場合はダミーキーを使用
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = "test-key"

    # src を import パスに追加
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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


def test_reading_assist_integration_openai_llm(client_with_openai_llm):
    """OpenAI LLMを使用した読解支援のテスト"""
    resp = client_with_openai_llm.post("/api/text/assist", json={"paragraph": "The quick brown fox jumps over the lazy dog."})
    assert resp.status_code == 200
    j = resp.json()
    
    # 基本的な構造の確認
    assert "sentences" in j
    assert "confidence" in j
    assert isinstance(j["sentences"], list)
    assert len(j["sentences"]) > 0


def test_feedback_integration_openai_llm(client_with_openai_llm):
    """OpenAI LLMを使用したフィードバック生成のテスト"""
    resp = client_with_openai_llm.post("/api/sentence/check", json={"sentence": "I am go to school."})
    assert resp.status_code == 200
    j = resp.json()
    
    # 基本的な構造の確認
    assert "issues" in j
    assert "revisions" in j
    assert "exercise" in j
    assert "confidence" in j
    assert isinstance(j["issues"], list)
    assert isinstance(j["revisions"], list)


