from typing import Any, Optional, List, Callable
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from .config import settings

try:
    import chromadb  # type: ignore
except Exception:  # pragma: no cover - optional during tests
    chromadb = None  # type: ignore


class SimpleEmbeddingFunction:
    """超軽量のダミー埋め込み関数（決定的）。

    実運用では OpenAI/ Voyage/ Jina 等の埋め込み関数に差し替える。
    次元は 8。各文字のコードポイントの和などから簡易に計算。
    """

    def __call__(self, texts: List[str]) -> List[List[float]]:  # type: ignore[override]
        def embed_one(t: str) -> List[float]:
            dims = 8
            vec = [0.0] * dims
            for i, ch in enumerate(t):
                vec[i % dims] += float(ord(ch))
            # 正規化
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            return [v / norm for v in vec]

        return [embed_one(t) for t in texts]


def get_llm_provider() -> Any:
    """Return an LLM client based on the configured provider.

    設定値 ``settings.llm_provider`` に応じて、実際の LLM クライアント
    （例: OpenAI, Azure OpenAI, Anthropic など）を返す想定のファクトリ関数。
    現時点ではプレースホルダとして ``None`` を返す。
    実装時の例:
    - openai: OpenAI SDK のクライアントを初期化して返却
    - azure-openai: 接続先エンドポイント/デプロイ名を指定
    - local: ローカル推論サーバへのクライアント
    """
    # Placeholder implementation.
    return None


def get_embedding_provider() -> Any:
    """Return an embedding client based on the configured provider.

    設定値 ``settings.embedding_provider`` に応じて、ベクトル埋め込み用の
    クライアントを返すファクトリ関数。検索/RAG 用に使用される想定。
    現時点ではプレースホルダとして ``None`` を返す。
    実装時の例:
    - openai: text-embedding-3 系のエンドポイント
    - voyage, jina, nvidia などの各種埋め込みモデル
    - 自前ベクトル化 API
    """
    # 現状はダミーの決定的埋め込みを返す（運用導入時に差し替え）
    return SimpleEmbeddingFunction()


class ChromaClientFactory:
    """Factory for creating a ChromaDB client and collections.

    RAG 用に `word_snippets` と `domain_terms` の 2 コレクションを扱うことを想定。
    実環境では永続ストアのパスやサーバーモードの URL を環境変数で指定する。
    """

    def __init__(self, persist_directory: Optional[str] = None) -> None:
        self.persist_directory = persist_directory or settings.chroma_persist_dir

    def create_client(self) -> Any | None:
        if chromadb is None:  # pragma: no cover - tests may stub
            # フォールバック：インメモリ互換クライアント
            return _InMemoryChromaClient(SimpleEmbeddingFunction())
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
            # フォールバック：インメモリ互換クライアント
            return _InMemoryChromaClient(SimpleEmbeddingFunction())
        # ラッパーを返し、コレクション作成時に埋め込み関数を注入
        return _ChromaClientAdapter(underlying, SimpleEmbeddingFunction())

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
_executor = ThreadPoolExecutor(max_workers=4)


def _with_timeout(func: Callable[[], Any], timeout_ms: int) -> Any:
    """別スレッドで実行してタイムアウトを適用。"""
    future = _executor.submit(func)
    try:
        return future.result(timeout=timeout_ms / 1000.0)
    except FuturesTimeout:
        raise TimeoutError("RAG query timed out")


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
