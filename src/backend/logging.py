import logging
import structlog
from .config import settings


def configure_logging() -> None:
    """Configure structlog for application-wide logging.

    アプリ全体のロギング設定を行う。標準 logging を INFO レベルで初期化し、
    structlog で ISO タイムスタンプと JSON 形式の出力を有効化する。
    運用環境では集約・可観測性ツールに連携しやすい形で出力される。
    """
    logging.basicConfig(level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
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
