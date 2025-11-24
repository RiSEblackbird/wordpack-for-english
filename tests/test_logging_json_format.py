import io
import json
import os
import sys
import types
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1] / "apps" / "backend"
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("DISABLE_SESSION_AUTH", "true")


@contextmanager
def _use_fake_settings() -> object:
    """Install a lightweight Settings stub during a test and restore afterwards.

    なぜ: 本番用設定は外部依存や厳格モードを要求するため、ログ検証では
    最小限の属性のみを持つスタブを使って副作用を抑える。テスト終了後は
    モジュールを元に戻し、他テストへの影響を遮断する。
    """

    original_config = sys.modules.get("backend.config")
    fake_config = types.ModuleType("backend.config")

    class _Settings:
        sentry_dsn = None
        auto_seed_on_startup = False
        rate_limit_per_min_ip = 120
        rate_limit_per_min_user = 120
        llm_timeout_ms = 1000
        disable_session_auth = True
        environment = "development"
        session_cookie_name = "wp_session"
        session_cookie_secure = False
        session_max_age_seconds = 60 * 60 * 24 * 14
        security_hsts_max_age_seconds = 63072000
        security_hsts_include_subdomains = True
        security_hsts_preload = False
        security_csp_default_src = ("'self'",)
        security_csp_connect_src = ()
        langfuse_enabled = False
        langfuse_exclude_paths = []
        allowed_cors_origins = ()
        allowed_hosts = ()
        allowed_hosts_raw = ""
        strict_mode = False
        wordpack_db_path = ":memory:"
        openai_api_key = None
        voyage_api_key = None
        trusted_proxy_ips = ()
        gcp_project_id: str | None = None

    fake_config.settings = _Settings()
    sys.modules["backend.config"] = fake_config
    for module in ("backend.logging", "backend.main"):
        if module in sys.modules:
            del sys.modules[module]
    try:
        yield fake_config.settings
    finally:
        if original_config is not None:
            sys.modules["backend.config"] = original_config
        else:
            sys.modules.pop("backend.config", None)
        for module in ("backend.logging", "backend.main"):
            sys.modules.pop(module, None)


def _extract_request_complete_lines(buffer_text: str) -> list[str]:
    """Return request_complete log lines from mixed stdout/stderr text."""

    lines = [ln for ln in buffer_text.splitlines() if ln.strip()]
    return [ln for ln in lines if '"event": "request_complete"' in ln]


_TRACE_ID_SAMPLE = "105445aa7843bc8bf206b120001000ab"
_SPAN_ID_SAMPLE = "123"
_TRACE_HEADER = f"{_TRACE_ID_SAMPLE}/{_SPAN_ID_SAMPLE};o=1"


def test_structlog_outputs_pure_json_without_stdlib_prefix():
    # Arrange
    # Capture both stdout/stderr because logging may use stderr by default
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    message_text = None

    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        with _use_fake_settings():
            from backend.logging import configure_logging, logger

            configure_logging()
            logger.info(
                "request_complete",
                path="/healthz",
                method="GET",
                latency_ms=1.23,
                request_id="test-request-id",
            )

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
    assert data.get("request_id") == "test-request-id"


def test_request_complete_log_contains_request_id() -> None:
    # Arrange
    buf_out = io.StringIO()
    buf_err = io.StringIO()

    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        with _use_fake_settings():
            from backend.logging import configure_logging

            configure_logging()

            from fastapi.testclient import TestClient

            from backend.main import app

            with TestClient(app) as client:
                response = client.get("/healthz")

            assert response.status_code == 200

    raw = buf_err.getvalue().strip() or buf_out.getvalue().strip()
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    request_lines = [ln for ln in lines if '"event": "request_complete"' in ln]

    assert request_lines, "request_complete log line not found"

    data = json.loads(request_lines[-1])
    assert data.get("request_id"), data


def test_request_complete_log_contains_status_code() -> None:
    """成功レスポンスのステータスコードをログへ含めることを検証する。"""

    buf_out = io.StringIO()
    buf_err = io.StringIO()

    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        with _use_fake_settings():
            from backend.logging import configure_logging

            configure_logging()

            from fastapi.testclient import TestClient

            from backend.main import app

            with TestClient(app) as client:
                response = client.get("/healthz")

            assert response.status_code == 200

    raw = buf_err.getvalue().strip() or buf_out.getvalue().strip()
    request_lines = _extract_request_complete_lines(raw)

    assert request_lines, "request_complete log line not found"

    data = json.loads(request_lines[-1])
    assert data.get("status_code") == 200


def test_sensitive_values_are_masked_in_logs() -> None:
    # Arrange
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    secret = "sk-proj-1234567890"

    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        with _use_fake_settings() as fake_settings:
            fake_settings.openai_api_key = secret

            from backend.logging import configure_logging, logger

            configure_logging()
            logger.info(
                "config_dump",
                openai_api_key=secret,
                nested={"api_key": secret, "note": f"using {secret} now"},
            )

    raw = buf_err.getvalue().strip() or buf_out.getvalue().strip()
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    message_text = lines[-1] if lines else ""

    assert message_text, "log output missing"
    assert secret not in message_text

    data = json.loads(message_text)
    assert data.get("openai_api_key") != secret
    assert data.get("nested", {}).get("api_key") != secret
    masked_note = data.get("nested", {}).get("note", "")
    assert secret not in masked_note


def test_access_log_includes_trace_fields_from_header() -> None:
    # Arrange
    buf_out = io.StringIO()
    buf_err = io.StringIO()

    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        with _use_fake_settings() as fake_settings:
            fake_settings.gcp_project_id = "demo-project"

            from backend.logging import configure_logging

            configure_logging()

            from fastapi.testclient import TestClient

            from backend.main import app

            with TestClient(app) as client:
                response = client.get(
                    "/healthz", headers={"X-Cloud-Trace-Context": _TRACE_HEADER}
                )

            assert response.status_code == 200

    raw = buf_err.getvalue().strip() or buf_out.getvalue().strip()
    request_lines = _extract_request_complete_lines(raw)

    assert request_lines, "request_complete log line not found"

    data = json.loads(request_lines[-1])
    assert (
        data.get("trace")
        == f"projects/demo-project/traces/{_TRACE_ID_SAMPLE}"
    )
    assert data.get("spanId") == _SPAN_ID_SAMPLE
    assert data.get("trace_sampled") is True


def test_trace_fields_omitted_without_project_id() -> None:
    # Arrange
    buf_out = io.StringIO()
    buf_err = io.StringIO()

    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        with _use_fake_settings() as fake_settings:
            fake_settings.gcp_project_id = None

            from backend.logging import configure_logging

            configure_logging()

            from fastapi.testclient import TestClient

            from backend.main import app

            with TestClient(app) as client:
                response = client.get(
                    "/healthz", headers={"X-Cloud-Trace-Context": _TRACE_HEADER}
                )

            assert response.status_code == 200

    raw = buf_err.getvalue().strip() or buf_out.getvalue().strip()
    request_lines = _extract_request_complete_lines(raw)

    assert request_lines, "request_complete log line not found"

    data = json.loads(request_lines[-1])
    assert "trace" not in data
    assert "spanId" not in data
    assert "trace_sampled" not in data


def test_request_log_records_error_context() -> None:
    """失敗リクエストでも構造化ログへエラー要約を残す。"""

    buf_out = io.StringIO()
    buf_err = io.StringIO()

    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        with _use_fake_settings():
            from backend.logging import configure_logging

            configure_logging()

            from fastapi.testclient import TestClient

            from backend.main import app

            @app.get("/boom")
            async def boom() -> None:  # pragma: no cover - 呼び出し側で検証
                raise RuntimeError("intentional failure")

            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/boom")

            assert response.status_code == 500

    raw = buf_err.getvalue().strip() or buf_out.getvalue().strip()
    request_lines = _extract_request_complete_lines(raw)

    assert request_lines, "request_complete log line not found"

    data = json.loads(request_lines[-1])
    assert data.get("status_code") == 500
    assert data.get("error_type") == "RuntimeError"
    assert "intentional failure" in data.get("error_message", "")


