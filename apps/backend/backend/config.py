from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_DB_PATH = ".data/wordpack.sqlite3"


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
        default=60000,
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

    # （削除済み）

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

    # （Chroma 設定は削除）

    # --- API Keys ---
    openai_api_key: str | None = Field(default=None, description="OpenAI API Key")
    voyage_api_key: str | None = Field(default=None, description="Voyage API Key")

    # --- データ永続化設定 ---
    wordpack_db_path: str = Field(
        default=DEFAULT_DB_PATH,
        description="Path to SQLite database for WordPack persistence / WordPack用SQLite DBパス",
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
    sentry_dsn: str | None = Field(
        default=None, description="Sentry DSN (enable if set)"
    )
    # Langfuse 観測基盤
    langfuse_enabled: bool = Field(
        default=False,
        description="Enable Langfuse tracing/observability / Langfuse の有効化",
    )
    langfuse_public_key: str | None = Field(
        default=None, description="Langfuse public key"
    )
    langfuse_secret_key: str | None = Field(
        default=None, description="Langfuse secret key"
    )
    langfuse_host: str | None = Field(
        default=None, description="Langfuse host (e.g. https://cloud.langfuse.com)"
    )
    langfuse_release: str | None = Field(
        default=None, description="Release/version tag for tracing"
    )
    # Langfuse 除外パス（完全一致 or 接頭一致のワイルドカード*対応）
    langfuse_exclude_paths: list[str] = Field(
        default=["/healthz", "/health", "/metrics*"],
        description="Exclude paths from Langfuse tracing (exact or prefix*)",
    )
    # Langfuse 入力ログの詳細度（LLM プロンプトの全文送信を制御）
    langfuse_log_full_prompt: bool = Field(
        default=False,
        description="Send full LLM prompt to Langfuse in span input (disabled by default)",
    )
    langfuse_prompt_max_chars: int = Field(
        default=40000,
        description="Max characters to record for prompt/input to Langfuse",
    )

    # --- Strict mode ---
    strict_mode: bool = Field(
        default=True,
        description="Fail fast on missing/invalid configuration (disable only for tests)",
    )

    user_role: Literal["admin", "viewer"] = Field(
        default="admin",
        description="Current user role / 現在のユーザーロール (admin|viewer)",
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
