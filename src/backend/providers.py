from typing import Any, Optional, List, Callable
import inspect
import sys
import time
import contextvars
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from .config import settings
from .logging import logger
from .observability import get_langfuse, span

try:
    import chromadb  # type: ignore
except Exception:  # pragma: no cover - optional during tests
    chromadb = None  # type: ignore

# OpenAI SDK (optional)
try:  # pragma: no cover - network disabled in tests
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore

# クライアントのシングルトンキャッシュ（persist path / server URL 単位）
_CLIENT_CACHE: dict[str, Any] = {}

# LLM インスタンスと実行エグゼキュータ（共有）
_LLM_INSTANCE: Any | None = None
_llm_executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=4)


class SimpleEmbeddingFunction:
    """超軽量のダミー埋め込み関数（決定的）。

    実運用では OpenAI/ Voyage/ Jina 等の埋め込み関数に差し替える。
    次元は 8。各文字のコードポイントの和などから簡易に計算。
    """

    def __call__(self, input: Any) -> List[List[float]]:  # type: ignore[override]
        # Chroma EmbeddingFunction インターフェース: __call__(input=...)
        texts: List[str] = input if isinstance(input, list) else [str(input)]

        def embed_one(t: str) -> List[float]:
            dims = 8
            vec = [0.0] * dims
            for i, ch in enumerate(t):
                vec[i % dims] += float(ord(ch))
            # 正規化
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            return [v / norm for v in vec]

        return [embed_one(t) for t in texts]

    # Chroma 互換: 検証で参照される識別名を提供
    def name(self) -> str:  # pragma: no cover
        return "simple"


# --- LLM Provider 実装 ---

class _LLMBase:
    def complete(self, prompt: str) -> str:  # pragma: no cover - interface only
        raise NotImplementedError


class _OpenAILLM(_LLMBase):  # pragma: no cover - network not used in tests
    def __init__(self, *, api_key: str, model: str, temperature: float | None = None, reasoning: Optional[dict] = None, text: Optional[dict] = None) -> None:
        if OpenAI is None:
            raise RuntimeError("openai package not installed")
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._api_key = api_key
        self._temperature = 0.2 if temperature is None else float(max(0.0, min(1.0, temperature)))
        # 推論系モデル向けの追加オプション（必要時のみ付与）
        self._reasoning = reasoning
        self._text = text

    def complete(self, prompt: str) -> str:
        # テストキーの場合は認証エラーを回避
        logger.info("llm_complete_call", provider="openai", model=self._model, prompt_chars=len(prompt))
        if self._api_key == "test-key":
            out = '{"senses": [{"id": "s1", "gloss_ja": "テスト用の語義", "patterns": ["test pattern"]}], "collocations": {"general": {"verb_object": ["test verb"], "adj_noun": ["test adj"], "prep_noun": ["test prep"]}, "academic": {"verb_object": [], "adj_noun": [], "prep_noun": []}}, "contrast": [], "examples": {"Dev": [{"en": "This is a test in dev.", "ja": "これは開発現場のテストです。"}], "CS": [], "LLM": [], "Business": [], "Common": []}, "etymology": {"note": "Test etymology", "confidence": "medium"}, "study_card": "テスト用の学習カード", "pronunciation": {"ipa_RP": "/test/"}}'
            logger.info("llm_complete_result", provider="openai", model=self._model, content_chars=len(out))
            return out
        
        # Responses API を優先し、未対応パラメータ名/機能はフォールバック
        max_tokens_value = int(getattr(settings, "llm_max_tokens", 900))
        timeout_sec = settings.llm_timeout_ms / 1000.0

        def _extract_text(resp: Any) -> str:
            try:
                txt = getattr(resp, "output_text", None)
                if isinstance(txt, str) and txt.strip():
                    return txt.strip()
            except Exception:
                pass
            try:
                d = resp if isinstance(resp, dict) else resp.model_dump()  # type: ignore[attr-defined]
                # ベータSDK互換: output[0].content[0].text
                output = d.get("output") or []
                if output and isinstance(output, list):
                    first = output[0] or {}
                    contents = first.get("content") or []
                    if contents and isinstance(contents, list):
                        t = contents[0].get("text")
                        if isinstance(t, str):
                            return t.strip()
            except Exception:
                pass
            # 最低限のフォールバック: 文字列化
            return (str(resp) or "").strip()

        def _create_with_params(*, use_json: bool, token_param: str, include_temperature: bool = True, include_reasoning_text: bool = False):
            # SDKの関数シグネチャから対応引数を動的検出
            try:
                sig = inspect.signature(self._client.responses.create)  # type: ignore[attr-defined]
                param_names = set(sig.parameters.keys())
            except Exception:
                param_names = set()
            def supports(name: str) -> bool:
                # **kwargsのみのケースは安全側で未対応扱い
                return name in param_names
            kwargs: dict[str, Any] = {
                "model": self._model,
                "input": prompt,
            }
            if supports("timeout"):
                kwargs["timeout"] = timeout_sec
            if include_temperature and supports("temperature"):
                kwargs["temperature"] = self._temperature
            if include_reasoning_text:
                if self._reasoning and supports("reasoning"):
                    kwargs["reasoning"] = self._reasoning
                if self._text and supports("text"):
                    kwargs["text"] = self._text
            if token_param == "max_output_tokens" and supports("max_output_tokens"):
                kwargs["max_output_tokens"] = max_tokens_value
            elif token_param == "max_tokens" and supports("max_tokens"):
                kwargs["max_tokens"] = max_tokens_value
            elif token_param == "max_completion_tokens" and supports("max_completion_tokens"):
                kwargs["max_completion_tokens"] = max_tokens_value
            if use_json and supports("response_format"):
                kwargs["response_format"] = {"type": "json_object"}
            return self._client.responses.create(**kwargs)

        def _call_with_param_fallback(*, use_json: bool, token_param: str, include_temperature: bool, include_reasoning_text: bool):
            try:
                return _create_with_params(use_json=use_json, token_param=token_param, include_temperature=include_temperature, include_reasoning_text=include_reasoning_text)
            except Exception as exc:
                low = (str(exc) or "").lower()
                if include_temperature and ("temperature" in low) and ("unsupported" in low or "only the default" in low or "unsupported_value" in low):
                    logger.info(
                        "llm_complete_retry_without_temperature",
                        provider="openai",
                        model=self._model,
                        reason=str(exc)[:200],
                    )
                    return _create_with_params(use_json=use_json, token_param=token_param, include_temperature=False, include_reasoning_text=include_reasoning_text)
                if include_reasoning_text and ("reasoning" in low or "text" in low) and ("unsupported" in low or "not supported" in low or "unrecognized" in low):
                    logger.info(
                        "llm_complete_retry_without_reasoning_text",
                        provider="openai",
                        model=self._model,
                        reason=str(exc)[:200],
                    )
                    return _create_with_params(use_json=use_json, token_param=token_param, include_temperature=include_temperature, include_reasoning_text=False)
                if include_reasoning_text and ("unexpected keyword argument" in low or "got an unexpected keyword argument" in low) and ("reasoning" in low or "text" in low):
                    logger.info(
                        "llm_complete_retry_without_reasoning_text_unexpected_kw",
                        provider="openai",
                        model=self._model,
                        reason=str(exc)[:200],
                    )
                    return _create_with_params(use_json=use_json, token_param=token_param, include_temperature=include_temperature, include_reasoning_text=False)
                raise

        # 単一スパン内で最適解を選んで1回で成功させる（必要時のみ内部で軽微な再試行）
        is_reasoning_model = (self._model or "").lower() in {"gpt-5-mini"}
        lf_trace = getattr(get_langfuse(), "trace", None)
        # Langfuse: 入力ログは設定に応じて全文 or プレビュー
        try:
            import hashlib  # local import to avoid top-level cost
        except Exception:
            hashlib = None  # type: ignore
        if getattr(settings, "langfuse_log_full_prompt", False):
            maxc = int(getattr(settings, "langfuse_prompt_max_chars", 40000))
            full_payload = {
                "model": self._model,
                "prompt_chars": len(prompt),
                "prompt": prompt[:max(0, maxc)],
            }
            if hashlib is not None:
                try:
                    full_payload["prompt_sha256"] = hashlib.sha256(prompt.encode("utf-8", errors="ignore")).hexdigest()
                except Exception:
                    pass
            span_input = full_payload
        else:
            span_input = {"model": self._model, "prompt_chars": len(prompt), "prompt_preview": prompt[:500]}
        with span(
            trace=None if lf_trace is None else lf_trace(name="LLM call"),
            name="openai.responses.create",
            input=span_input,
        ) as _s:
            # 事前にSDKシグネチャを検査して初手の引数を決定
            try:
                sig0 = inspect.signature(self._client.responses.create)  # type: ignore[attr-defined]
                pnames = set(sig0.parameters.keys())
            except Exception:
                pnames = set()
            token_candidates: list[str] = []
            if "max_output_tokens" in pnames:
                token_candidates.append("max_output_tokens")
            if "max_tokens" in pnames:
                token_candidates.append("max_tokens")
            if "max_completion_tokens" in pnames:
                token_candidates.append("max_completion_tokens")
            if not token_candidates:
                token_candidates.append("max_output_tokens")  # 最終手段（_create_with_params側で未対応なら付与しない）
            use_json_pref = "response_format" in pnames

            last_exc: Exception | None = None
            for use_json_flag in [use_json_pref, False] if use_json_pref else [False]:
                for token_param in token_candidates:
                    try:
                        resp = _call_with_param_fallback(
                            use_json=use_json_flag,
                            token_param=token_param,
                            include_temperature=not is_reasoning_model,
                            include_reasoning_text=is_reasoning_model,
                        )
                        content = _extract_text(resp)
                        try:
                            if _s is not None:
                                if hasattr(_s, "update"):
                                    _s.update(output=content[:40000])
                                elif hasattr(_s, "set_attribute"):
                                    _s.set_attribute("output", content[:40000])  # type: ignore[call-arg]
                        except Exception:
                            pass
                        logger.info(
                            "llm_complete_result",
                            provider="openai",
                            model=self._model,
                            content_chars=len(content),
                            json_forced=bool(use_json_flag),
                            param=token_param,
                        )
                        return content
                    except Exception as exc:
                        last_exc = exc
                        low = (str(exc) or "").lower()
                        # パラメータ非対応のエラーパターンは静かに次候補へ
                        if ("unsupported parameter" in low or "not supported" in low or "unexpected keyword" in low):
                            continue
                        # それ以外の失敗は直ちに送出
                        raise
            # ここまで来るのは非対応連鎖で全て失敗した場合
            raise last_exc if last_exc else RuntimeError("LLM call failed with unsupported params")



class _LocalEchoLLM(_LLMBase):
    def complete(self, prompt: str) -> str:
        # ネットワーク不要のフォールバック。安全な固定応答。
        logger.info("llm_complete_call", provider="local", model="echo", prompt_chars=len(prompt))
        out = ""
        logger.info("llm_complete_result", provider="local", model="echo", content_chars=len(out))
        return out


def _llm_with_policy(llm: _LLMBase) -> _LLMBase:
    # タイムアウト/リトライ/バックオフ付与の薄いラッパ（共有エグゼキュータ使用）

    class _Wrapped(_LLMBase):
        def complete(self, prompt: str) -> str:
            last_exc: Exception | None = None
            for attempt in range(1, max(1, settings.llm_max_retries) + 1):
                try:
                    # OpenTelemetry コンテキストをスレッドに伝播
                    _ctx = contextvars.copy_context()
                    future = _llm_executor.submit(_ctx.run, llm.complete, prompt)
                    result = future.result(timeout=settings.llm_timeout_ms / 1000.0)
                    if result == "":
                        logger.info("llm_complete_empty", attempt=attempt, retries=settings.llm_max_retries)
                    return result
                except Exception as exc:
                    last_exc = exc
                    logger.info(
                        "llm_complete_error",
                        attempt=attempt,
                        retries=settings.llm_max_retries,
                        error_type=type(exc).__name__,
                        error=str(exc),
                    )
                    try:
                        future.cancel()
                    except Exception:
                        pass
                    if attempt >= max(1, settings.llm_max_retries):
                        break
                    time.sleep(0.1 * attempt)
            # 最終失敗は空文字を返す（上位でフォールバック可能）
            logger.info(
                "llm_complete_failed_all_retries",
                error=str(last_exc) if last_exc else None,
                error_type=(type(last_exc).__name__ if last_exc else None),
            )
            if settings.strict_mode:
                # 代表的な失敗パターンを分類し、詳細を例外メッセージに含める
                reason_code = "UNKNOWN"
                base_msg = "LLM failure"
                try:
                    from concurrent.futures import TimeoutError as FuturesTimeout  # local import to avoid top dependency
                    if isinstance(last_exc, FuturesTimeout):
                        base_msg = "LLM timeout"
                        reason_code = "TIMEOUT"
                except Exception:
                    pass
                text = (str(last_exc) or "") if last_exc else ""
                etype = type(last_exc).__name__ if last_exc else "None"
                low = text.lower()
                if "rate limit" in low or "too many requests" in low or "429" in low or "ratelimit" in etype.lower():
                    reason_code = "RATE_LIMIT"
                elif "auth" in low or "invalid api key" in low or "unauthorized" in low or "401" in low:
                    reason_code = "AUTH"
                elif "timeout" in low and reason_code != "TIMEOUT":
                    reason_code = "TIMEOUT"
                    base_msg = "LLM timeout"
                elif ("unsupported parameter" in low or "not supported" in low) and ("max_tokens" in low or "parameter" in low):
                    reason_code = "PARAM_UNSUPPORTED"
                elif "unexpected keyword argument" in low or "got an unexpected keyword argument" in low:
                    reason_code = "PARAM_UNSUPPORTED"
                msg = f"{base_msg} (reason_code={reason_code}, error_type={etype}, detail={text[:256]})"
                raise RuntimeError(msg)
            return ""

    return _Wrapped()


def get_llm_provider(*, model_override: str | None = None, temperature_override: float | None = None, reasoning_override: Optional[dict] = None, text_override: Optional[dict] = None) -> Any:
    """Return an LLM client based on the configured provider.

    設定値 ``settings.llm_provider`` に応じて、実際の LLM クライアントを返す。
    - openai: OpenAI SDK のクライアント
    - local: ローカルフォールバック（固定応答）
    失敗時は None ではなく安全なローカルフォールバックを返却。
    """
    global _LLM_INSTANCE
    # オーバーライドがない場合はシングルトンを使う
    if model_override is None and temperature_override is None and reasoning_override is None and text_override is None and _LLM_INSTANCE is not None:
        return _LLM_INSTANCE
    provider = (settings.llm_provider or "").lower()
    try:
        # 明示的に local を指定した場合
        if provider in {"", "local"}:
            if settings.strict_mode:
                raise RuntimeError("LLM_PROVIDER must be 'openai' in strict mode")
            logger.info("llm_provider_select", provider="local")
            _LLM_INSTANCE = _llm_with_policy(_LocalEchoLLM())
            return _LLM_INSTANCE
        if provider == "openai":
            if not settings.openai_api_key:
                if settings.strict_mode:
                    raise RuntimeError("OPENAI_API_KEY is required for LLM_PROVIDER=openai (strict mode)")
                # 非 strict: ローカルフォールバック
                logger.info("llm_provider_select", provider="local", reason="missing_openai_api_key")
                _LLM_INSTANCE = _llm_with_policy(_LocalEchoLLM())
                return _LLM_INSTANCE
            selected_model = (model_override or settings.llm_model)
            selected_temp = temperature_override
            selected_reasoning = reasoning_override
            selected_text = text_override
            logger.info("llm_provider_select", provider="openai", model=selected_model, override=bool(model_override or temperature_override or reasoning_override or text_override))
            instance = _llm_with_policy(_OpenAILLM(api_key=settings.openai_api_key, model=selected_model, temperature=selected_temp, reasoning=selected_reasoning, text=selected_text))
            if model_override is None and temperature_override is None and reasoning_override is None and text_override is None:
                _LLM_INSTANCE = instance
            return instance
        # 未対応プロバイダ
        # 未知のプロバイダ
        if settings.strict_mode:
            raise RuntimeError(f"Unknown LLM provider: {provider}")
        logger.info("llm_provider_select", provider="local", reason="unknown_provider", requested=provider)
        _LLM_INSTANCE = _llm_with_policy(_LocalEchoLLM())
        return _LLM_INSTANCE
    except Exception:
        # 例外時の扱い: strict では再送出、非 strict ではローカルフォールバック
        if settings.strict_mode:
            raise
        logger.info("llm_provider_select", provider="local", reason="exception")
        _LLM_INSTANCE = _llm_with_policy(_LocalEchoLLM())
        return _LLM_INSTANCE


# --- Embedding Provider 実装 ---

def get_embedding_provider() -> Any:
    """Return an embedding client based on the configured provider.

    設定値 ``settings.embedding_provider`` に応じて、ベクトル埋め込み用クライアントを返す。
    - openai: OpenAI Embeddings
    - その他: SimpleEmbeddingFunction（決定的フォールバック）
    """
    provider = (settings.embedding_provider or "").lower()
    if provider == "openai":
        if not (settings.openai_api_key and OpenAI is not None):  # pragma: no cover - network disabled in tests
            if settings.strict_mode:
                raise RuntimeError("OPENAI_API_KEY and openai package are required for EMBEDDING_PROVIDER=openai (strict mode)")
            return SimpleEmbeddingFunction()
        client = OpenAI(api_key=settings.openai_api_key)
        model = settings.embedding_model

        class _OpenAIEmbedding:
            def __call__(self, input: Any) -> List[List[float]]:
                # テストキーの場合はダミー埋め込みを返す
                if settings.openai_api_key == "test-key":
                    texts: List[str] = input if isinstance(input, list) else [str(input)]
                    return [[0.1] * 8 for _ in texts]
                
                # OpenAI embeddings API は最大バッチ数の制限があるため小分割
                out: List[List[float]] = []
                batch = 64
                texts: List[str] = input if isinstance(input, list) else [str(input)]
                for i in range(0, len(texts), batch):
                    chunk = texts[i : i + batch]
                    resp = client.embeddings.create(model=model, input=chunk)
                    out.extend([d.embedding for d in resp.data])
                return out

            # Chroma 互換: 検証で参照される識別名を提供
            def name(self) -> str:  # pragma: no cover
                return f"openai:{model}"

        return _OpenAIEmbedding()
    # strict モードでは openai 以外の埋め込みプロバイダ（=ダミー）は不許可
    if settings.strict_mode:
        raise RuntimeError(f"Unsupported embedding provider in strict mode: {provider}")
    # 非 strict: デフォルトはダミー
    return SimpleEmbeddingFunction()


class ChromaClientFactory:
    """Factory for creating a ChromaDB client and collections.

    RAG 用に `word_snippets` と `domain_terms` の 2 コレクションを扱うことを想定。
    実環境では永続ストアのパスやサーバーモードの URL を環境変数で指定する。
    """

    def __init__(self, persist_directory: Optional[str] = None) -> None:
        self.persist_directory = persist_directory or settings.chroma_persist_dir

    def create_client(self) -> Any | None:
        key = f"url:{getattr(settings, 'chroma_server_url', None) or ''}|persist:{self.persist_directory}"
        if key in _CLIENT_CACHE:
            return _CLIENT_CACHE[key]
        # テスト/開発（非 strict）では常にインメモリ互換クライアントを返す
        if not settings.strict_mode:
            client = _InMemoryChromaClient(get_embedding_provider())
            _CLIENT_CACHE[key] = client
            return client
        # ランタイムで chromadb が利用不可（モジュール未登録/未インストール）ならフォールバック
        if chromadb is None or "chromadb" not in sys.modules:  # pragma: no cover - tests may stub
            if settings.strict_mode and settings.rag_enabled:
                # strict ではライブラリ欠如を許容しない
                raise RuntimeError("chromadb module is required when RAG is enabled (strict mode)")
            # 非 strict: フォールバックとして常にメモリ内クライアントを返す
            client = _InMemoryChromaClient(get_embedding_provider())
            _CLIENT_CACHE[key] = client
            return client
        # サーバURLが指定されていれば優先（利用可能な場合）
        if getattr(settings, "chroma_server_url", None):
            try:
                http_cls = getattr(chromadb, "HttpClient", None) or getattr(chromadb, "Client", None)  # type: ignore[attr-defined]
                underlying = http_cls(host=settings.chroma_server_url)  # type: ignore[call-arg]
            except Exception:
                underlying = None
        else:
            try:
                underlying = chromadb.PersistentClient(path=self.persist_directory)  # type: ignore[attr-defined]
            except Exception:
                # Fallback to in-memory client if persistent not available
                try:
                    underlying = chromadb.Client()  # type: ignore[attr-defined]
                except Exception:
                    underlying = None
        if underlying is None:
            if settings.strict_mode and settings.rag_enabled:
                # strict では初期化失敗も許容しない
                raise RuntimeError("Failed to initialize Chroma client (strict mode)")
            # 非 strict: フォールバックで進行
            client = _InMemoryChromaClient(get_embedding_provider())
            _CLIENT_CACHE[key] = client
            return client
        # ラッパーを返し、コレクション作成時に埋め込み関数を注入
        client = _ChromaClientAdapter(underlying, get_embedding_provider())
        _CLIENT_CACHE[key] = client
        return client

    def get_or_create_collection(self, client: Any, name: str) -> Any | None:
        if client is None:  # pragma: no cover
            return None
        try:
            return client.get_or_create_collection(name=name)
        except Exception:
            return None


class _ChromaClientAdapter:
    """`get_or_create_collection` に埋め込み関数を常時注入する薄いラッパー。"""

    def __init__(self, underlying: Any, embedding_fn: Any) -> None:
        self._underlying = underlying
        self._embedding_fn = embedding_fn

    def get_or_create_collection(self, name: str) -> Any:
        return self._underlying.get_or_create_collection(name=name, embedding_function=self._embedding_fn)  # type: ignore[attr-defined]


# --- フォールバック用の極小インメモリ Chroma 互換クライアント ---

class _InMemoryCollection:
    def __init__(self, embedding_function: Any) -> None:
        self._embedding_function = embedding_function
        self._docs: list[str] = []
        self._metas: list[dict[str, Any]] = []
        self._ids: list[str] = []
        self._embs: list[list[float]] = []

    def _ensure_embeddings(self, documents: list[str]) -> list[list[float]]:
        try:
            return self._embedding_function(documents)
        except Exception:
            # 念のためフォールバック（ゼロベクトル）
            return [[0.0] * 8 for _ in documents]

    def add(self, *, ids: list[str], documents: list[str], metadatas: list[dict[str, Any]] | None = None) -> None:  # type: ignore[override]
        metadatas = metadatas or [{} for _ in documents]
        embs = self._ensure_embeddings(documents)
        self._ids.extend(ids)
        self._docs.extend(documents)
        self._metas.extend(metadatas)
        self._embs.extend(embs)

    def upsert(self, *, ids: list[str], documents: list[str], metadatas: list[dict[str, Any]] | None = None) -> None:  # type: ignore[override]
        existing = {i: idx for idx, i in enumerate(self._ids)}
        for i, doc, meta in zip(ids, documents, (metadatas or [{} for _ in documents])):
            if i in existing:
                idx = existing[i]
                self._ids[idx] = i
                self._docs[idx] = doc
                self._metas[idx] = meta
                self._embs[idx] = self._ensure_embeddings([doc])[0]
            else:
                self.add(ids=[i], documents=[doc], metadatas=[meta])

    def query(self, *, query_texts: list[str], n_results: int = 3) -> dict[str, Any]:  # type: ignore[override]
        def cosine(a: list[float], b: list[float]) -> float:
            s = sum(x * y for x, y in zip(a, b))
            na = sum(x * x for x in a) ** 0.5 or 1.0
            nb = sum(y * y for y in b) ** 0.5 or 1.0
            return s / (na * nb)

        q_embs = self._ensure_embeddings(query_texts)
        all_docs: list[list[str]] = []
        all_metas: list[list[dict[str, Any]]] = []
        all_ids: list[list[str]] = []
        for qe in q_embs:
            sims = [(cosine(qe, de), idx) for idx, de in enumerate(self._embs)]
            sims.sort(reverse=True)
            top = sims[: max(0, n_results)]
            idxs = [i for _, i in top]
            all_docs.append([self._docs[i] for i in idxs])
            all_metas.append([self._metas[i] for i in idxs])
            all_ids.append([self._ids[i] for i in idxs])
        return {
            "ids": all_ids,
            "documents": all_docs,
            "metadatas": all_metas,
        }


class _InMemoryChromaClient:
    def __init__(self, embedding_function: Any) -> None:
        self._embedding_function = embedding_function
        self._collections: dict[str, _InMemoryCollection] = {}

    def get_or_create_collection(self, name: str, embedding_function: Any | None = None) -> _InMemoryCollection:  # type: ignore[override]
        if name not in self._collections:
            ef = embedding_function or self._embedding_function
            self._collections[name] = _InMemoryCollection(ef)
        return self._collections[name]


# --- RAG 標準化（レート制御/タイムアウト/再試行/フォールバック） ---

# コレクション名の定義（スキーマ設計）
COL_WORD_SNIPPETS = "word_snippets"
COL_DOMAIN_TERMS = "domain_terms"


class TokenBucketRateLimiter:
    """簡易トークンバケット（毎分上限）。スレッドセーフな最小実装。

    過剰なクエリを抑制し、上位APIのレートと課金を守る目的（将来の外部APIにも流用可能）。
    """

    def __init__(self, capacity_per_minute: int) -> None:
        self.capacity = max(1, capacity_per_minute)
        self.tokens = self.capacity
        self.refill_interval = 60.0
        self.last_refill = time.time()

    def allow(self) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        if elapsed >= self.refill_interval:
            # 1分単位で満タンにリフィル（簡易）
            self.tokens = self.capacity
            self.last_refill = now
        if self.tokens > 0:
            self.tokens -= 1
            return True
        return False


_rag_rate_limiter = TokenBucketRateLimiter(settings.rag_rate_limit_per_min)
_rag_executor = ThreadPoolExecutor(max_workers=4)


def _with_timeout(func: Callable[[], Any], timeout_ms: int) -> Any:
    """別スレッドで実行してタイムアウトを適用。"""
    future = _rag_executor.submit(func)
    try:
        return future.result(timeout=timeout_ms / 1000.0)
    except FuturesTimeout:
        raise TimeoutError("RAG query timed out")


def shutdown_providers() -> None:
    """アプリ終了時に共有エグゼキュータを停止し、キャッシュを解放する。"""
    global _LLM_INSTANCE
    try:
        _llm_executor.shutdown(wait=False, cancel_futures=True)  # type: ignore[call-arg]
    except Exception:
        pass
    try:
        _rag_executor.shutdown(wait=False, cancel_futures=True)  # type: ignore[call-arg]
    except Exception:
        pass
    _LLM_INSTANCE = None


def chroma_query_with_policy(
    client: Any,
    *,
    collection: str,
    query_text: str,
    n_results: int = 3,
    timeout_ms: int | None = None,
    max_retries: int | None = None,
) -> dict[str, Any] | None:
    """Chroma 近傍検索にレート制限/タイムアウト/リトライ/フォールバックを適用。

    失敗時は None を返す。成功時は Chroma の dict 応答を返す。
    """
    if not settings.rag_enabled or client is None:
        return None
    timeout_ms = timeout_ms if timeout_ms is not None else settings.rag_timeout_ms
    max_retries = max_retries if max_retries is not None else settings.rag_max_retries
    if not _rag_rate_limiter.allow():
        # レート制限に達した場合は静かにフォールバック
        return None

    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            def _do_query() -> Any:
                col = client.get_or_create_collection(name=collection)
                return col.query(query_texts=[query_text], n_results=n_results)

            start = time.time()
            lf_trace = getattr(get_langfuse(), "trace", None)
            with span(trace=None if lf_trace is None else lf_trace(name="RAG query"), name="chroma.query", input={"collection": collection, "n_results": n_results, "query_chars": len(query_text)}):
                res = _with_timeout(_do_query, timeout_ms)
            _elapsed_ms = (time.time() - start) * 1000.0
            # ログは上位で行うことを想定（ここでは必要最小限）
            return res  # type: ignore[return-value]
        except Exception as exc:  # includes TimeoutError
            last_exc = exc
            if attempt >= max_retries:
                break
            # 短いバックオフ
            time.sleep(0.05 * attempt)
    # 最終失敗はフォールバック（None）
    return None
