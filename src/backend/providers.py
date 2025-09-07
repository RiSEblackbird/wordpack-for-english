from typing import Any, Optional, List

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
    # Placeholder implementation.
    return None


class ChromaClientFactory:
    """Factory for creating a ChromaDB client and collections.

    RAG 用に `word_snippets` と `domain_terms` の 2 コレクションを扱うことを想定。
    実環境では永続ストアのパスやサーバーモードの URL を環境変数で指定する。
    """

    def __init__(self, persist_directory: Optional[str] = ".chroma") -> None:
        self.persist_directory = persist_directory

    def create_client(self) -> Any | None:
        if chromadb is None:  # pragma: no cover - tests may stub
            return None
        try:
            underlying = chromadb.PersistentClient(path=self.persist_directory)  # type: ignore[attr-defined]
        except Exception:
            # Fallback to in-memory client if persistent not available
            try:
                underlying = chromadb.Client()  # type: ignore[attr-defined]
            except Exception:
                return None
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
