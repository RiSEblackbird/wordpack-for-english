import io
import json
import sys
import types
from contextlib import redirect_stderr, redirect_stdout


def test_structlog_outputs_pure_json_without_stdlib_prefix():
    # Arrange
    # Capture both stdout/stderr because logging may use stderr by default
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    message_text = None

    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        # Stub settings to avoid importing external deps in config
        fake_config = types.ModuleType("apps.backend.backend.config")
        class _S:
            sentry_dsn = None
        fake_config.settings = _S()
        sys.modules["apps.backend.backend.config"] = fake_config

        from apps.backend.backend.logging import configure_logging, logger
        configure_logging()
        logger.info("request_complete", path="/healthz", method="GET", latency_ms=1.23)

    # Prefer stderr content (default for logging), fallback to stdout
    raw = buf_err.getvalue().strip() or buf_out.getvalue().strip()
    # Pick the last non-empty line (avoid noise from other handlers)
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    message_text = lines[-1] if lines else ""

    assert message_text, "no log output captured"
    # Should not contain stdlib prefix like 'INFO:...:'
    assert not message_text.startswith("INFO:"), message_text
    assert not message_text.startswith("WARNING:"), message_text

    # Should be valid JSON and contain our structured fields
    data = json.loads(message_text)
    assert data.get("event") == "request_complete"
    assert data.get("level") in {"info", "INFO"}
    assert data.get("path") == "/healthz"
    assert data.get("method") == "GET"
    assert "latency_ms" in data


