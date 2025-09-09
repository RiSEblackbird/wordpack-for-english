import sys
import types
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def add_src_to_path():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    yield


def test_get_llm_provider_without_keys_returns_safe_client(monkeypatch):
    from backend.providers import get_llm_provider

    # Force provider to local or unset keys
    monkeypatch.setenv("STRICT_MODE", "false")
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # Reload settings to pick env
    from importlib import reload
    import backend.providers
    reload(backend.providers)

    llm = get_llm_provider()
    assert llm is not None
    # complete should not raise and return str
    out = llm.complete("ping")
    assert isinstance(out, str)


def test_get_llm_provider_openai_with_key(monkeypatch):
    """OpenAI APIキーが設定されている場合のテスト"""
    from backend.providers import get_llm_provider

    # OpenAI provider with test key
    monkeypatch.setenv("STRICT_MODE", "false")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Reload settings to pick env
    from importlib import reload
    import backend.providers
    reload(backend.providers)

    llm = get_llm_provider()
    assert llm is not None
    # complete should not raise and return str
    out = llm.complete("ping")
    assert isinstance(out, str)


def test_get_llm_provider_is_singleton(monkeypatch):
    # LLM プロバイダはモジュール内でキャッシュされ、同一インスタンスが返る
    monkeypatch.setenv("STRICT_MODE", "false")
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from importlib import reload
    import backend.providers
    from backend.providers import get_llm_provider

    reload(backend.providers)
    llm1 = get_llm_provider()
    llm2 = get_llm_provider()
    assert llm1 is llm2


def test_chroma_client_fallback_when_module_missing(monkeypatch):
    # remove chromadb module to trigger in-memory fallback
    sys.modules.pop("chromadb", None)
    monkeypatch.setenv("STRICT_MODE", "false")
    from backend.providers import ChromaClientFactory

    client = ChromaClientFactory().create_client()
    assert client is not None
    col = client.get_or_create_collection("tmp")
    col.add(ids=["a"], documents=["hello"], metadatas=[{}])
    res = col.query(query_texts=["hello"], n_results=1)
    assert isinstance(res, dict)


def test_embedding_provider_default_is_callable(monkeypatch):
    # Ensure no OpenAI key -> fallback SimpleEmbeddingFunction
    monkeypatch.setenv("STRICT_MODE", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from backend.providers import get_embedding_provider

    ef = get_embedding_provider()
    vecs = ef(["abc", "def"])  # type: ignore[operator]
    assert isinstance(vecs, list) and len(vecs) == 2