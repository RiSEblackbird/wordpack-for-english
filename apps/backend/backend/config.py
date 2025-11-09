from pydantic import Field, field_validator, model_validator
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
    google_client_id: str = Field(
        default="",
        description="Google OAuth client ID / Googleサインイン用クライアントID",
    )
    google_allowed_hd: str | None = Field(
        default=None,
        description="Optional allowed Google Workspace domain / 許可するGoogle Workspaceドメイン",
    )
    google_clock_skew_seconds: int = Field(
        default=60,
        description=(
            "Allowed clock skew when verifying Google ID tokens (seconds) / "
            "Google ID トークン検証時に許容する時計ずれ（秒）"
        ),
    )
    admin_email_allowlist: tuple[str, ...] = Field(
        default=(),
        description=(
            "Email addresses allowed to sign in when restrict mode is enabled / "
            "ログインを許可するメールアドレス一覧（制限有効時に使用）"
        ),
    )
    session_secret_key: str = Field(
        default="",
        description="Secret key for signing session cookies / セッションクッキー署名用シークレット",
    )
    session_cookie_name: str = Field(
        default="wp_session",
        description="Session cookie name / セッションクッキー名",
    )
    session_cookie_secure: bool = Field(
        default=False,
        description="Whether to mark session cookie as Secure / セッションクッキーにSecure属性を付与するか",
    )
    session_max_age_seconds: int = Field(
        default=60 * 60 * 24 * 14,
        description="Session lifetime in seconds / セッションの寿命（秒）",
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

    disable_session_auth: bool = Field(
        default=False,
        description=(
            "Disable session cookie authentication (development/testing only) / "
            "セッションクッキー認証を無効化する（開発・テスト用途のみ）"
        ),
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


    @field_validator("admin_email_allowlist", mode="before")
    @classmethod
    def _normalise_admin_allowlist(
        cls, raw_allowlist: object
    ) -> tuple[str, ...] | object:  # pragma: no cover - pydantic handles typing
        """Normalise allowlist values before model parsing.

        文字列/シーケンスのいずれでも受け取り、重複排除・小文字化したタプルへ変換する。
        """

        if raw_allowlist is None:
            candidates: list[str] = []
        elif isinstance(raw_allowlist, str):
            candidates = raw_allowlist.split(",")
        else:
            try:
                candidates = list(raw_allowlist)
            except TypeError:
                return raw_allowlist

        normalised: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            trimmed = candidate.strip().lower()
            if not trimmed or trimmed in seen:
                continue
            seen.add(trimmed)
            normalised.append(trimmed)

        return tuple(normalised)

    @model_validator(mode="after")
    def _apply_environment_sensitive_defaults(self) -> "Settings":
        """Harmonise environment defaults without overriding explicit choices.

        なぜ: ローカル開発環境（HTTPアクセスが多い）で Secure 属性が有効だと
        document.cookie からセッション Cookie を参照できずログイン検証が失敗する。
        ENVIRONMENT=production のときだけ Secure を既定で有効化し、環境変数や
        テストから明示的に設定された値は上書きしない。
        """

        environment_name = (self.environment or "").lower()
        is_secure_explicitly_configured = "session_cookie_secure" in self.model_fields_set
        if environment_name == "production" and not is_secure_explicitly_configured:
            self.session_cookie_secure = True

        return self


settings = Settings()
