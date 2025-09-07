import logging
import structlog


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
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


logger = structlog.get_logger()
