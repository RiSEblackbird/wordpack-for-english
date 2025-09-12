import os
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
    import backend.config
    import backend.providers
    reload(backend.config)
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
    import backend.config
    import backend.providers
    reload(backend.config)
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
    import backend.config
    import backend.providers
    from backend.providers import get_llm_provider

    reload(backend.config)
    reload(backend.providers)
    llm1 = get_llm_provider()
    llm2 = get_llm_provider()
    assert llm1 is llm2


def test_chroma_client_fallback_when_module_missing(monkeypatch):
    # remove chromadb module to trigger in-memory fallback
    sys.modules.pop("chromadb", None)
    monkeypatch.setenv("STRICT_MODE", "false")
    from importlib import reload
    import backend.config
    import backend.providers
    reload(backend.config)
    reload(backend.providers)
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
    from importlib import reload
    import backend.config
    import backend.providers
    reload(backend.config)
    reload(backend.providers)
    from backend.providers import get_embedding_provider

    ef = get_embedding_provider()
    vecs = ef(["abc", "def"])  # type: ignore[operator]
    assert isinstance(vecs, list) and len(vecs) == 2


def test_openai_reasoning_param_fallback_on_unexpected_keyword(monkeypatch):
    """SDKが reasoning/text を未サポートで TypeError: unexpected keyword argument を返した場合、
    自動的に当該パラメータを外して再試行することを検証する。
    """
    # 環境を OpenAI + gpt-5-mini（reasoning/text を付ける対象）に設定
    monkeypatch.setenv("STRICT_MODE", "false")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-5-mini")
    # 'test-key' だと早期固定応答になるため、別キー名にして実際の分岐を通す
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-realistic-key")

    # モジュールをリロード
    from importlib import reload
    import backend.config
    import backend.providers
    reload(backend.config)
    reload(backend.providers)

    # Dummy OpenAI クライアントを注入（reasoning 付きでは TypeError を投げ、
    # reasoning を外すと JSON 文字列を返す）
    class _DummyMessage:
        def __init__(self, content: str) -> None:
            self.content = content

    class _DummyChoice:
        def __init__(self, content: str) -> None:
            self.message = _DummyMessage(content)

    class _DummyResp:
        def __init__(self, content: str) -> None:
            self.choices = [_DummyChoice(content)]

    class _DummyResponses:
        def create(self, **kwargs):  # type: ignore[no-untyped-def]
            # 初回: reasoning/text が含まれていれば SDK 未対応エラーを模倣
            if "reasoning" in kwargs or "text" in kwargs:
                raise TypeError("Responses.create() got an unexpected keyword argument 'reasoning'")
            # 再試行: reasoning/text を外してくれれば成功（Responses API 互換: output_text を返す）
            return _DummyResp('{"senses": [{"id": "s1", "gloss_ja": "ok"}], "examples": {"Dev": [], "CS": [], "LLM": [], "Business": [], "Common": []}}')

    class DummyOpenAI:
        def __init__(self, api_key: str) -> None:  # type: ignore[no-untyped-def]
            self.responses = _DummyResponses()

    backend.providers.OpenAI = DummyOpenAI  # type: ignore[assignment]

    # 実行：reasoning/text オプションを与えてプロバイダを取得
    from backend.providers import get_llm_provider
    llm = get_llm_provider(
        reasoning_override={"effort": "high"},
        text_override={"verbosity": "high"},
    )

    out = llm.complete("ping")
    assert isinstance(out, str) and "\"senses\"" in out