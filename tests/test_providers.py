import os
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def add_src_to_path():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend"))
    os.environ.setdefault("STRICT_MODE", "false")
    import importlib
    importlib.invalidate_caches()
    for name in list(sys.modules.keys()):
        if name == "backend" or name.startswith("backend."):
            sys.modules.pop(name)
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
    monkeypatch.setenv("LLM_MODEL", "gpt-5.4-mini")
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


def test_openai_request_uses_reasoning_text_params(monkeypatch):
    """OpenAI 呼び出しで現行モデル用の reasoning/text/max_output_tokens だけを送る。"""
    monkeypatch.setenv("STRICT_MODE", "false")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-realistic-key")

    from importlib import reload
    import backend.config
    import backend.providers
    reload(backend.config)
    reload(backend.providers)

    calls: list[dict] = []

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
            calls.append(kwargs)
            return _DummyResp('{"senses": [{"id": "s1", "gloss_ja": "ok"}], "examples": {"Dev": [], "CS": [], "LLM": [], "Business": [], "Common": []}}')

    class DummyOpenAI:
        def __init__(self, api_key: str) -> None:  # type: ignore[no-untyped-def]
            self.responses = _DummyResponses()

    backend.providers.llm.OpenAI = DummyOpenAI  # type: ignore[attr-defined, assignment]

    from backend.providers import get_llm_provider
    llm = get_llm_provider(
        reasoning_override={"effort": "high"},
        text_override={"verbosity": "high"},
    )

    out = llm.complete("ping")
    assert isinstance(out, str) and "\"senses\"" in out
    assert calls
    first = calls[0]
    assert first["model"] == "gpt-5.4-mini"
    assert first["reasoning"] == {"effort": "high"}
    assert first["text"] == {"verbosity": "high"}
    assert first["max_output_tokens"] > 0
    assert "temperature" not in first
    assert "max_tokens" not in first
    assert "max_completion_tokens" not in first


def test_openai_request_uses_nano_model(monkeypatch):
    """gpt-5.4-nano でも同じ現行パラメータを送る。"""
    monkeypatch.setenv("STRICT_MODE", "false")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-5.4-nano")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-realistic-key")

    from importlib import reload
    import backend.config
    import backend.providers
    reload(backend.config)
    reload(backend.providers)

    calls: list[dict] = []

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
            calls.append(kwargs)
            return _DummyResp('{"senses": [{"id": "s1", "gloss_ja": "ok"}], "examples": {"Dev": [], "CS": [], "LLM": [], "Business": [], "Common": []}}')

    class DummyOpenAI:
        def __init__(self, api_key: str) -> None:  # type: ignore[no-untyped-def]
            self.responses = _DummyResponses()

    backend.providers.llm.OpenAI = DummyOpenAI  # type: ignore[attr-defined, assignment]

    from backend.providers import get_llm_provider
    llm = get_llm_provider(
        reasoning_override={"effort": "high"},
        text_override={"verbosity": "high"},
    )
    out = llm.complete("ping")
    assert isinstance(out, str) and "\"senses\"" in out
    assert calls[0]["model"] == "gpt-5.4-nano"
    assert calls[0]["reasoning"] == {"effort": "high"}
    assert calls[0]["text"] == {"verbosity": "high"}
    assert "temperature" not in calls[0]
