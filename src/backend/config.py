from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    環境変数から読み込まれるアプリ設定クラス。
    - environment: 実行環境（development/staging/production など）
    - llm_provider: 利用する LLM プロバイダ
    - embedding_provider: 利用するベクトル埋め込みプロバイダ
    """

    environment: str = Field(
        default="development",
        description="Runtime environment / 実行環境",
    )
    llm_provider: str = Field(
        default="openai",
        description="LLM service provider / 利用するLLMプロバイダ",
    )
    embedding_provider: str = Field(
        default="openai",
        description="Embedding service provider / 利用する埋め込みプロバイダ",
    )

    # --- RAG 制御（導入のみ・フラグで無効化可） ---
    rag_enabled: bool = Field(
        default=True,
        description="Enable RAG pipeline / RAG 機能の有効化スイッチ",
    )
    rag_timeout_ms: int = Field(
        default=1500,
        description="Per-attempt timeout for vector queries (ms) / 近傍クエリの試行毎タイムアウト(ms)",
    )
    rag_max_retries: int = Field(
        default=2,
        description="Max retries for vector queries / 近傍クエリの最大リトライ回数",
    )
    rag_rate_limit_per_min: int = Field(
        default=120,
        description="Rate limit for RAG queries per minute / RAGクエリの毎分上限",
    )

    # --- Chroma 設定（永続ディレクトリ or 将来のリモート URL） ---
    chroma_persist_dir: str = Field(
        default=".chroma",
        description="Chroma persistent storage directory / Chroma 永続ディレクトリ",
    )
    chroma_server_url: str | None = Field(
        default=None,
        description="Optional Chroma server URL / 任意の Chroma サーバURL（未指定ならローカル）",
    )

    # --- API Keys（運用時に設定。未設定ならダミー動作） ---
    openai_api_key: str | None = Field(default=None, description="OpenAI API Key")
    azure_openai_api_key: str | None = Field(default=None, description="Azure OpenAI API Key")
    voyage_api_key: str | None = Field(default=None, description="Voyage API Key")

    class Config:
        env_file = ".env"


settings = Settings()
