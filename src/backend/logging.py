import logging
import structlog


def configure_logging() -> None:
    """Configure structlog for application-wide logging."""
    logging.basicConfig(level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


logger = structlog.get_logger()
