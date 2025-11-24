"""Logging utilities and sanitisation helpers.

構造化ログの初期化と、機密情報を含むイベントを安全にマスクする
ヘルパーをまとめて提供する。Cloud Run などの実行環境では、誤って
API キーが出力されるとログ閲覧者にシークレットが露出するため、
ここで一元的にフィルタリングする。
"""

from typing import Any

import logging
import structlog
from structlog import contextvars as structlog_contextvars
from .config import settings


_SENSITIVE_KEYWORDS = ("api_key", "token", "secret", "authorization", "password", "key")
_MASK_PLACEHOLDER = "***"
_TRACE_CONTEXT_KEYS = ("trace", "spanId", "trace_sampled")


def _mask_secret_value(raw: object) -> str:
    """Return a masked representation of a secret-like value.

    なぜ: フル値をログへ出力すると即座に漏洩する。短い値は `***` に、
    一定長以上は先頭4文字+末尾4文字だけを残し中間を隠す。
    """

    if raw is None:
        return _MASK_PLACEHOLDER
    text = str(raw).strip()
    if not text:
        return _MASK_PLACEHOLDER
    if len(text) <= 8:
        return _MASK_PLACEHOLDER
    return f"{text[:4]}…{text[-4:]}"


def _is_sensitive_key(key: str) -> bool:
    """Check whether a log key name should be masked.

    API キーやトークンを示すキー名（`api_key`/`token` など）が含まれる場合に
    True を返し、値をマスク対象として扱う。
    """

    lowered = key.lower()
    return any(keyword in lowered for keyword in _SENSITIVE_KEYWORDS)


def _mask_known_literals(value: str, known_secrets: tuple[str, ...]) -> str:
    """Replace known secret literals within the given string.

    Cloud Run の環境変数として渡された API キーがメッセージ本文に混入した
    場合でも、既知の値を検出して置換することで漏洩を防ぐ。
    """

    masked = value
    for secret in known_secrets:
        if not secret:
            continue
        masked = masked.replace(secret, _mask_secret_value(secret))
    return masked


def _sanitize_event_dict(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Sanitize sensitive fields before rendering a log event.

    キー名に `api_key`/`token` 等が含まれる場合は値をマスクし、文字列内に
    既知のシークレットリテラルが紛れ込んでいれば置換する。ネストした dict
    も同様に再帰的に処理する。
    """

    known_secrets: tuple[str, ...] = tuple(
        secret
        for secret in (settings.openai_api_key, settings.voyage_api_key)
        if secret
    )

    def _sanitize_value(value: Any, key_hint: str | None = None) -> Any:
        if isinstance(value, dict):
            return {k: _sanitize_value(v, k) for k, v in value.items()}
        if isinstance(value, str):
            cleaned = _mask_known_literals(value, known_secrets)
            if key_hint and _is_sensitive_key(key_hint):
                return _mask_secret_value(cleaned)
            return cleaned
        if key_hint and _is_sensitive_key(key_hint):
            return _mask_secret_value(value)
        return value

    for key, value in list(event_dict.items()):
        event_dict[key] = _sanitize_value(value, str(key))
    return event_dict


def _merge_trace_context(
    _logger: structlog.types.WrappedLogger,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Merge Cloud Trace contextvars into the log payload if available.

    なぜ: Cloud Run が出力するリクエストログとアプリケーションログを突合するため、
    `trace`/`spanId`/`trace_sampled` を全ログへ自動付与する。ContextVar に保存済みの
    値のみを取り出すことで、他のスレッド/リクエストに漏洩しないようにしている。
    """

    context = structlog_contextvars.get_contextvars()
    for key in _TRACE_CONTEXT_KEYS:
        if key in context and key not in event_dict:
            event_dict[key] = context[key]
    return event_dict


def configure_logging() -> None:
    """Configure structlog for application-wide logging.

    アプリ全体のロギング設定を行う。標準 logging を INFO レベルで初期化し、
    structlog で ISO タイムスタンプと JSON 形式の出力を有効化する。
    運用環境では集約・可観測性ツールに連携しやすい形で出力される。
    """
    # stdlib 側の出力に余計なプレフィックス（"INFO:logger:" など）を付けない
    # ため、フォーマットはメッセージのみ(%(message)s)に固定する。
    # force=True で既存ハンドラ（uvicorn 等）を上書きして一貫化。
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[logging.StreamHandler()],
        force=True,
    )
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog_contextvars.merge_contextvars,
            _merge_trace_context,
            _sanitize_event_dict,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    # Optional: Sentry integration (enabled if DSN is provided)
    try:
        if settings.sentry_dsn:
            import sentry_sdk  # type: ignore
            from sentry_sdk.integrations.logging import LoggingIntegration  # type: ignore

            sentry_logging = LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            )
            sentry_sdk.init(dsn=settings.sentry_dsn, integrations=[sentry_logging])
    except Exception:
        # Sentryが未インストール/初期化失敗でもアプリは継続
        pass


logger = structlog.get_logger()
