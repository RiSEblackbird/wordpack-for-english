from typing import Any

from .config import settings


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
