import logging
import structlog


def setup_logging() -> None:
    """Configure structlog for JSON output with latency and token metrics."""
    logging.basicConfig(level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
    )
