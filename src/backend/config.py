from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    llm_model: str = Field(
        default="gpt-4o-mini",
        description="LLM model name / 利用するLLMモデル名",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name / 埋め込みモデル名",
    )

    # --- LLM 呼出しのタイムアウト/リトライ ---
    llm_timeout_ms: int = Field(
        default=20000,
        description="Per-attempt timeout for LLM calls (ms) / LLM呼出しの試行毎タイムアウト(ms)",
    )
    llm_max_retries: int = Field(
        default=1,
        description="Max retries for LLM calls / LLM呼出しの最大リトライ回数",
    )
    llm_max_tokens: int = Field(
        default=900,
        description="Max tokens for LLM completion output / LLM出力の最大トークン数",
    )

    # --- RAG 制御（導入のみ・フラグで無効化可） ---
    rag_enabled: bool = Field(
        default=False,
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

    # --- Auto seed on startup (optional) ---
    auto_seed_on_startup: bool = Field(
        default=False,
        description="Automatically seed Chroma collections on API startup / 起動時に自動シード",
    )
    auto_seed_word_jsonl: str | None = Field(
        default=None,
        description="Optional JSONL path for word_snippets to seed on startup / 起動時シード用のword_snippets JSONL",
    )
    auto_seed_terms_jsonl: str | None = Field(
        default=None,
        description="Optional JSONL path for domain_terms to seed on startup / 起動時シード用のdomain_terms JSONL",
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

    # --- API Keys ---
    openai_api_key: str | None = Field(default=None, description="OpenAI API Key")
    voyage_api_key: str | None = Field(default=None, description="Voyage API Key")

    # --- SRS（復習）の永続化設定 ---
    srs_db_path: str = Field(
        default=".data/srs.sqlite3",
        description="Path to SRS SQLite database / SRS用SQLite DBパス",
    )
    srs_max_today: int = Field(
        default=5,
        description="Max items to return for today's review / 本日の最大出題数",
    )

    # --- Operations/Observability (PR4) ---
    rate_limit_per_min_ip: int = Field(
        default=240,
        description="Per-IP API requests per minute / IP単位の毎分上限",
    )
    rate_limit_per_min_user: int = Field(
        default=240,
        description="Per-user API requests per minute / ユーザ単位の毎分上限（X-User-Id）",
    )
    sentry_dsn: str | None = Field(default=None, description="Sentry DSN (enable if set)")

    # --- Strict mode ---
    strict_mode: bool = Field(
        default=True,
        description="Fail fast on missing/invalid configuration (disable only for tests)",
    )

    # Pydantic v2 settings config
    # - env_file: .env を読み込む
    # - extra: .env に存在する未使用キー（例: api_key/allowed_origins など）を無視
    # - case_sensitive: 環境変数キーの大小文字を区別しない
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
