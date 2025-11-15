from typing import Annotated

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources.types import NoDecode


DEFAULT_DB_PATH = ".data/wordpack.sqlite3"
_MIN_SESSION_SECRET_KEY_LENGTH = 32
_PLACEHOLDER_SESSION_SECRETS = frozenset({
    "change-me",
    "changeme",
    "change-me-to-random-value",
    "please-change-me",
})


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
        description="Per-user API requests per minute / 認証セッション単位の毎分上限",
    )
    # --- Security headers ---
    security_hsts_max_age_seconds: int = Field(
        default=63072000,
        description=(
            "Strict-Transport-Security max-age directive in seconds / "
            "Strict-Transport-Security の max-age（秒）"
        ),
    )
    security_hsts_include_subdomains: bool = Field(
        default=True,
        description=(
            "Whether to append includeSubDomains to Strict-Transport-Security / "
            "Strict-Transport-Security に includeSubDomains を付与するか"
        ),
    )
    security_hsts_preload: bool = Field(
        default=False,
        description=(
            "Whether to append preload to Strict-Transport-Security / "
            "Strict-Transport-Security に preload を付与するか"
        ),
    )
    security_csp_default_src: Annotated[tuple[str, ...], NoDecode] = Field(
        default=("'self'",),
        description=(
            "Content-Security-Policy default-src sources (comma separated) / "
            "Content-Security-Policy の default-src で許可するソース"
        ),
        validation_alias=AliasChoices(
            "security_csp_default_src",
            "security_csp_origins",
        ),
    )
    security_csp_connect_src: Annotated[tuple[str, ...], NoDecode] = Field(
        default=(),
        description=(
            "Content-Security-Policy connect-src sources (comma separated). "
            "Empty tuple falls back to default-src / "
            "Content-Security-Policy の connect-src で許可するソース（空の場合は default-src を利用）"
        ),
        validation_alias=AliasChoices(
            "security_csp_connect_src",
            "security_csp_connect_origins",
        ),
    )
    sentry_dsn: str | None = Field(
        default=None, description="Sentry DSN (enable if set)"
    )
    # なぜ: CORS の許可オリジンを設定ファイルから明示することで、誤ったドメインを
    # 許可しないまま本番リリースしてしまうリスクを避ける。未設定の場合は既存の
    # ワイルドカード挙動（認証クッキー非許可）にフォールバックする。
    allowed_cors_origins: Annotated[tuple[str, ...], NoDecode] = Field(
        default=(),
        description=(
            "Comma separated CORS origins / CORS で許可するオリジンのカンマ区切り一覧"
        ),
        validation_alias=AliasChoices("allowed_cors_origins", "cors_allowed_origins"),
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

    trusted_proxy_ips: Annotated[tuple[str, ...], NoDecode] = Field(
        default=("127.0.0.1",),
        description=(
            "Trusted proxy IPs/CIDR ranges for ProxyHeadersMiddleware / "
            "ProxyHeadersMiddleware に渡す信頼済みプロキシの IP または CIDR"
        ),
        validation_alias=AliasChoices(
            "trusted_proxy_ips",
            "forwarded_allow_ips",
        ),
    )
    allowed_hosts: Annotated[tuple[str, ...], NoDecode] = Field(
        default=("*",),
        description=(
            "Allowed hosts for TrustedHostMiddleware / TrustedHostMiddleware で許可するホスト名"
        ),
        validation_alias=AliasChoices(
            "allowed_hosts",
            "trusted_hosts",
        ),
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


    @field_validator("session_secret_key", mode="after")
    @classmethod
    def _validate_session_secret(
        cls, value: str
    ) -> str:
        """Ensure session secret keys are safely randomised before accepting them.

        なぜ: セッション署名鍵が既知のプレースホルダーや短い文字列のまま起動すると
        総当たり攻撃で利用者のセッションが奪取される恐れがあるため、環境変数の
        読み込み段階で検証し、危険な値は即座に拒否する。
        """

        secret = (value or "").strip()
        if not secret:
            raise ValueError(
                "SESSION_SECRET_KEY must be a non-empty random string",
            )

        if secret.casefold() in _PLACEHOLDER_SESSION_SECRETS:
            raise ValueError(
                "SESSION_SECRET_KEY must not use placeholder values like 'change-me'",
            )

        if len(secret) < _MIN_SESSION_SECRET_KEY_LENGTH:
            raise ValueError(
                "SESSION_SECRET_KEY must be at least 32 characters long",
            )

        return secret

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

    @field_validator("allowed_cors_origins", mode="before")
    @classmethod
    def _normalise_allowed_cors_origins(
        cls, raw_origins: object
    ) -> tuple[str, ...] | object:  # pragma: no cover - pydantic handles typing
        """Convert environment input into a deduplicated tuple of origins.

        なぜ: CORS 設定を `.env` で管理するときに空白や重複が混ざりやすいため、
        FastAPI へ渡す前にトリムと重複排除を行って安全な配列へ正規化する。
        """

        if raw_origins is None:
            candidates: list[str] = []
        elif isinstance(raw_origins, str):
            candidates = raw_origins.split(",")
        else:
            try:
                candidates = list(raw_origins)
            except TypeError:
                return raw_origins

        normalised: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            trimmed = candidate.strip()
            if not trimmed or trimmed in seen:
                continue
            seen.add(trimmed)
            normalised.append(trimmed)

        return tuple(normalised)

    @field_validator("trusted_proxy_ips", mode="before")
    @classmethod
    def _normalise_trusted_proxy_ips(
        cls, raw_ips: object
    ) -> tuple[str, ...] | object:  # pragma: no cover - pydantic handles typing
        """Normalise trusted proxy definitions into a trimmed, deduplicated tuple.

        なぜ: Cloud Run やロードバランサの IP 範囲を `.env` で管理するとき、
        空白や重複・誤入力が混ざると本来信頼すべきヘッダが拒否され、
        アクセス元 IP の解析やレート制限の判定が正しく行われなくなる。
        入力段階で正規化し、ProxyHeadersMiddleware へ安全に渡す。
        """

        if raw_ips is None:
            candidates: list[str] = []
        elif isinstance(raw_ips, str):
            candidates = raw_ips.split(",")
        else:
            try:
                candidates = list(raw_ips)
            except TypeError:
                return raw_ips

        normalised: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            trimmed = candidate.strip()
            if not trimmed or trimmed in seen:
                continue
            seen.add(trimmed)
            normalised.append(trimmed)

        return tuple(normalised)

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def _normalise_allowed_hosts(
        cls, raw_hosts: object
    ) -> tuple[str, ...] | object:  # pragma: no cover - pydantic handles typing
        """Normalise allowed hostnames/patterns before TrustedHostMiddleware consumes them.

        なぜ: TrustedHostMiddleware の許可リストに空白や重複を残すと、
        想定外のホストヘッダを許可したり、必要なドメインを拒否する恐れがある。
        あらかじめトリムと重複排除を行い、安全なホスト配列を構成する。
        """

        if raw_hosts is None:
            candidates: list[str] = []
        elif isinstance(raw_hosts, str):
            candidates = raw_hosts.split(",")
        else:
            try:
                candidates = list(raw_hosts)
            except TypeError:
                return raw_hosts

        normalised: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            trimmed = candidate.strip()
            if not trimmed or trimmed in seen:
                continue
            seen.add(trimmed)
            normalised.append(trimmed)

        return tuple(normalised)

    @field_validator(
        "security_csp_default_src",
        "security_csp_connect_src",
        mode="before",
    )
    @classmethod
    def _normalise_csp_sources(
        cls, raw_sources: object
    ) -> tuple[str, ...] | object:  # pragma: no cover - pydantic handles typing
        """Normalise CSP directive source values to trimmed, deduplicated tuples.

        なぜ: CSP の許可リストは空白や重複が混ざりやすく、誤ったスペースや
        末尾のスラッシュ差異があるとセキュリティヘッダが意図通りに作用しない。
        事前にトリムと重複排除を行い、設定ミスに起因する許可漏れ/過剰許可を
        防止する。
        """

        if raw_sources is None:
            candidates: list[str] = []
        elif isinstance(raw_sources, str):
            candidates = raw_sources.split(",")
        else:
            try:
                candidates = list(raw_sources)
            except TypeError:
                return raw_sources

        normalised: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            trimmed = candidate.strip()
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
