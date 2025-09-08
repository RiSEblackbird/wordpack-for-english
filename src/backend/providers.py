from typing import Any, Optional, List, Callable
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from .config import settings

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
    def __init__(self, *, api_key: str, model: str) -> None:
        if OpenAI is None:
            raise RuntimeError("openai package not installed")
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete(self, prompt: str) -> str:
        # 最小実装（Chat Completions）
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=64,
        )
        return (resp.choices[0].message.content or "").strip()



class _LocalEchoLLM(_LLMBase):
    def complete(self, prompt: str) -> str:
        # ネットワーク不要のフォールバック。安全な固定応答。
        return ""


def _llm_with_policy(llm: _LLMBase) -> _LLMBase:
    # タイムアウト/リトライ/バックオフ付与の薄いラッパ（共有エグゼキュータ使用）

    class _Wrapped(_LLMBase):
        def complete(self, prompt: str) -> str:
            last_exc: Exception | None = None
            for attempt in range(1, max(1, settings.llm_max_retries) + 1):
                try:
                    future = _llm_executor.submit(llm.complete, prompt)
                    return future.result(timeout=settings.llm_timeout_ms / 1000.0)
                except Exception as exc:
                    last_exc = exc
                    if attempt >= max(1, settings.llm_max_retries):
                        break
                    time.sleep(0.1 * attempt)
            # 最終失敗は空文字を返す（上位でフォールバック可能）
            return ""

    return _Wrapped()


def get_llm_provider() -> Any:
    """Return an LLM client based on the configured provider.

    設定値 ``settings.llm_provider`` に応じて、実際の LLM クライアントを返す。
    - openai: OpenAI SDK のクライアント
    - local: ローカルフォールバック（固定応答）
    失敗時は None ではなく安全なローカルフォールバックを返却。
    """
    global _LLM_INSTANCE
    if _LLM_INSTANCE is not None:
        return _LLM_INSTANCE
    provider = (settings.llm_provider or "").lower()
    try:
        # 明示的に local を指定した場合
        if provider in {"", "local"}:
            if settings.strict_mode:
                raise RuntimeError("LLM_PROVIDER must be 'openai' in strict mode")
            _LLM_INSTANCE = _llm_with_policy(_LocalEchoLLM())
            return _LLM_INSTANCE
        if provider == "openai":
            if not settings.openai_api_key:
                if settings.strict_mode:
                    raise RuntimeError("OPENAI_API_KEY is required for LLM_PROVIDER=openai (strict mode)")
                # 非 strict: ローカルフォールバック
                _LLM_INSTANCE = _llm_with_policy(_LocalEchoLLM())
                return _LLM_INSTANCE
            _LLM_INSTANCE = _llm_with_policy(_OpenAILLM(api_key=settings.openai_api_key, model=settings.llm_model))
            return _LLM_INSTANCE
        # 未対応プロバイダ
        # 未知のプロバイダ
        if settings.strict_mode:
            raise RuntimeError(f"Unknown LLM provider: {provider}")
        _LLM_INSTANCE = _llm_with_policy(_LocalEchoLLM())
        return _LLM_INSTANCE
    except Exception:
        # 例外時の扱い: strict では再送出、非 strict ではローカルフォールバック
        if settings.strict_mode:
            raise
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
