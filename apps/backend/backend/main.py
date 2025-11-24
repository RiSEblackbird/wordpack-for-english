from __future__ import annotations

import asyncio
import inspect
import string
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp
from structlog import contextvars as structlog_contextvars
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

try:  # FastAPI/Starlette のバージョンにより存在しない場合がある
    from starlette.middleware.timeout import TimeoutMiddleware  # type: ignore
except Exception:  # pragma: no cover - 互換目的のフォールバック
    TimeoutMiddleware = None  # type: ignore[assignment]

try:
    from starlette.exceptions import TimeoutException  # type: ignore
except Exception:  # pragma: no cover - 互換目的のフォールバック
    TimeoutException = None  # type: ignore[assignment]

from .auth import get_current_user
from .config import settings
from .indexing import seed_domain_terms, seed_from_jsonl, seed_word_snippets
from .logging import configure_logging, logger
from .metrics import registry
from .middleware import RateLimitMiddleware, RequestIDMiddleware, SecurityHeadersMiddleware
from .middleware.host import ForwardedHostTrustedHostMiddleware
from .observability import request_trace
from .providers import ChromaClientFactory, shutdown_providers
from .routers import article as article_router
from .routers import auth as auth_router
from .routers import config as cfg
from .routers import debug, diagnostics, health, tts, word


_PROXY_MIDDLEWARE_PARAM = (
    "forwarded_allow_ips"
    if "forwarded_allow_ips"
    in inspect.signature(ProxyHeadersMiddleware.__init__).parameters
    else "trusted_hosts"
)


def _parse_cloud_trace_header(raw_header: str | None) -> dict[str, object]:
    """Parse `X-Cloud-Trace-Context` and shape it for Cloud Logging.

    なぜ: Cloud Run のリクエストログとアプリケーションログを関連付けるためには、
    `trace`/`spanId`/`trace_sampled` をログに含める必要がある。本関数でヘッダーを
    安全に解析し、形式に沿ったフィールドを返す。
    """

    if not raw_header or not settings.gcp_project_id:
        return {}

    trace_span_part, _, option_part = raw_header.partition(";")
    trace_id, separator, span_part = trace_span_part.partition("/")
    if not separator or not trace_id:
        return {}

    trace_id = trace_id.strip()
    if len(trace_id) != 32 or any(ch not in string.hexdigits for ch in trace_id):
        return {}

    span_id: str | None = None
    cleaned_span = span_part.strip()
    if cleaned_span:
        try:
            # Cloud Trace の spanId は 64bit 整数。桁あふれや文字列混入を避ける。
            span_int = int(cleaned_span, 10)
            if 0 <= span_int < 2**64:
                span_id = str(span_int)
        except ValueError:
            span_id = None

    trace_sampled = False
    if option_part:
        for opt in option_part.split(";"):
            key, _, value = opt.partition("=")
            if key.strip() == "o":
                trace_sampled = value.strip() == "1"

    trace_field = f"projects/{settings.gcp_project_id}/traces/{trace_id}"
    trace_context: dict[str, object] = {"trace": trace_field, "trace_sampled": trace_sampled}
    if span_id is not None:
        trace_context["spanId"] = span_id
    return trace_context

class AccessLogAndMetricsMiddleware(BaseHTTPMiddleware):
    """Emit structured request logs and capture latency/metrics for each call.

    なぜ: 監視対象のリクエストすべてに `request_id` を付与し、
    構造化ログとメトリクスへ遅延・エラー有無を記録することで、運用時の
    トラブルシュートを即座に行えるようにする。
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:  # type: ignore[override]
        start = time.time()
        path = request.url.path
        method = request.method
        request_id = getattr(request.state, "request_id", None)
        if not request_id:
            request_id = uuid4().hex
            request.state.request_id = request_id
        trace_log_fields = _parse_cloud_trace_header(
            request.headers.get("x-cloud-trace-context")
        )
        if trace_log_fields:
            # なぜ: Cloud Run リクエストログとアプリログを突合できるように、
            # トレース関連フィールドを ContextVar として紐付ける。
            structlog_contextvars.bind_contextvars(**trace_log_fields)
        client_ip = request.client.host if request.client else "unknown"
        ua = request.headers.get("user-agent", "-")
        is_error = False
        is_timeout = False
        status_code: int | None = None
        error_type: str | None = None
        error_message: str | None = None
        input_payload: dict[str, Any] = {
            "path": path,
            "method": method,
            "query": dict(request.query_params) if request.query_params else {},
        }
        with request_trace(
            name=f"HTTP {method} {path}",
            user_id=request.headers.get("x-user-id"),
            metadata={
                "request_id": request_id,
                "client_ip": client_ip,
                "user_agent": ua,
                "path": path,
            },
            path=path,
        ) as ctx:
            trace_obj = ctx.get("trace") if isinstance(ctx, dict) else None  # type: ignore[assignment]
            try:
                if trace_obj is not None and hasattr(trace_obj, "set_attribute"):
                    trace_obj.set_attribute("input", str(input_payload)[:40000])  # type: ignore[call-arg]
                elif trace_obj is not None and hasattr(trace_obj, "update"):
                    trace_obj.update(input=input_payload)
            except Exception:  # pragma: no cover - 追跡失敗時も処理継続
                pass
            try:
                response = await call_next(request)
                status_code = getattr(response, "status_code", None)
                try:
                    output_payload = {
                        "status": status_code,
                        "content_type": response.headers.get("content-type"),
                        "content_length": response.headers.get("content-length"),
                    }
                    if trace_obj is not None and hasattr(trace_obj, "set_attribute"):
                        trace_obj.set_attribute("output", str(output_payload)[:40000])  # type: ignore[call-arg]
                    elif trace_obj is not None and hasattr(trace_obj, "update"):
                        trace_obj.update(output=output_payload)
                except Exception:  # pragma: no cover - 出力メタ記録失敗時
                    pass
                return response
            except Exception as exc:
                is_error = True
                status_code = getattr(exc, "status_code", 500) if hasattr(exc, "status_code") else 500
                error_type = exc.__class__.__name__
                raw_error_message = str(exc)
                # なぜ: Cloud Run 上で失敗リクエストを特定しやすくするため、
                # 例外型と簡潔なメッセージを残しつつログ膨張を防ぐ。
                error_message = (
                    raw_error_message
                    if len(raw_error_message) <= 200
                    else f"{raw_error_message[:197]}..."
                )
                if (
                    TimeoutException is not None and isinstance(exc, TimeoutException)
                ) or isinstance(exc, asyncio.TimeoutError):
                    is_timeout = True
                raise
            finally:
                request_id = getattr(request.state, "request_id", request_id)
                latency_ms = (time.time() - start) * 1000
                registry.record(path, latency_ms, is_error=is_error, is_timeout=is_timeout)
                # Cloud Logging 上で失敗リクエストを確実に拾えるよう、エラー時は
                # severity=ERROR になる logger.error を使い分ける。
                log_method = logger.error if is_error else logger.info
                log_method(
                    "request_complete",
                    path=path,
                    method=method,
                    latency_ms=latency_ms,
                    is_error=is_error,
                    is_timeout=is_timeout,
                    status_code=status_code,
                    error_type=error_type,
                    error_message=error_message,
                    request_id=request_id,
                    client_ip=client_ip,
                    user_agent=ua,
                    **trace_log_fields,
                )
                if trace_log_fields:
                    structlog_contextvars.unbind_contextvars(*trace_log_fields.keys())


async def _on_shutdown() -> None:
    """Ensure providers (Chroma, LLM clients) are gracefully terminated."""
    shutdown_providers()


async def _on_startup_seed() -> None:
    """Optionally seed Chroma collections at application startup."""
    try:
        if not settings.auto_seed_on_startup:
            return
        client = ChromaClientFactory().create_client()
        if client is None:
            return
        wj = (
            Path(settings.auto_seed_word_jsonl)
            if settings.auto_seed_word_jsonl
            else None
        )
        tj = (
            Path(settings.auto_seed_terms_jsonl)
            if settings.auto_seed_terms_jsonl
            else None
        )
        if (wj and wj.exists()) or (tj and tj.exists()):
            seed_from_jsonl(client, word_snippets_path=wj, domain_terms_path=tj)
            logger.info(
                "auto_seed",
                mode="jsonl",
                word_jsonl=str(wj) if wj else None,
                terms_jsonl=str(tj) if tj else None,
            )
        else:
            seed_word_snippets(client)
            seed_domain_terms(client)
            logger.info("auto_seed", mode="minimal")
    except Exception as exc:  # pragma: no cover - 起動時エラーは継続
        logger.warning("auto_seed_failed", error=repr(exc))


def _maybe_add_timeout_middleware(app: FastAPI) -> None:
    """Attach Starlette's timeout middleware when the dependency is available."""
    if TimeoutMiddleware is None:
        return
    http_timeout_sec = max(1, int((settings.llm_timeout_ms + 5000) / 1000))
    app.add_middleware(TimeoutMiddleware, timeout=http_timeout_sec)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    configure_logging()
    logger.info(
        "ALLOWED_HOSTS init raw=%r parsed=%r",
        settings.allowed_hosts_raw,
        settings.allowed_hosts,
    )
    app = FastAPI(title="WordPack API", version="0.3.1")

    configured_proxies = [value for value in settings.trusted_proxy_ips if value]
    if not configured_proxies:
        configured_proxies = ["127.0.0.1"]
    proxy_argument: str
    if len(configured_proxies) == 1:
        proxy_argument = configured_proxies[0]
    else:
        proxy_argument = ",".join(configured_proxies)
    configured_hosts = list(settings.allowed_hosts)
    if not configured_hosts:
        configured_hosts = ["*"]
    configured_origins = list(settings.allowed_cors_origins)
    allow_credentials = bool(configured_origins)
    if not configured_origins:
        configured_origins = ["*"]

    # なぜ: ワイルドカード許可時に資格情報を無効化することで、本番でのクッキー漏洩を
    # 防ぎ、設定で明示された場合のみクレデンシャル付き CORS を許可する。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=configured_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _maybe_add_timeout_middleware(app)
    app.add_middleware(RequestIDMiddleware)
    # Middleware stack (inner → outer):
    #   RequestID → AccessLog → RateLimit → ForwardedHostTrustedHost → SecurityHeaders → ProxyHeaders
    #   （Timeout →）CORSMiddleware がさらに内側に位置する。
    # Starlette では後から追加したミドルウェアが外側で実行される。RequestID で
    # `request_id` を採番し、AccessLog 側で構造化ログとメトリクスを記録する。レート
    # 制限は署名付きセッションクッキーを検証して 429 を返すため外側に配置する。
    # ForwardedHostTrustedHostMiddleware で信頼済みプロキシからの X-Forwarded-Host を
    # 照合し、Host 偽装をアプリケーション処理より前に拒否する。SecurityHeaders を
    # その外側に配置することで RateLimit や FastAPI の自動レスポンスにも HSTS/CSP を
    # 付与する。最外周の ProxyHeaders で信頼済みプロキシが付与する X-Forwarded-For/
    # X-Forwarded-Proto を読み替え、AccessLog や RateLimit が実際のクライアント IP を
    # 参照できるようにしている。
    app.add_middleware(AccessLogAndMetricsMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        ip_capacity_per_minute=settings.rate_limit_per_min_ip,
        user_capacity_per_minute=settings.rate_limit_per_min_user,
    )
    app.add_middleware(
        ForwardedHostTrustedHostMiddleware,
        allowed_hosts=configured_hosts,
        trusted_proxy_ips=configured_proxies,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        ProxyHeadersMiddleware,
        **{_PROXY_MIDDLEWARE_PARAM: proxy_argument},
    )

    if settings.disable_session_auth:
        logger.warning(
            "session_auth_disabled",
            reason="config_flag",
        )
        protected_dependency: list[Any] = []
    else:
        protected_dependency = [Depends(get_current_user)]
    app.include_router(auth_router.router)
    app.include_router(word.router, prefix="/api/word", dependencies=protected_dependency)
    app.include_router(
        article_router.router,
        prefix="/api/article",
        dependencies=protected_dependency,
    )
    app.include_router(debug.router)
    app.include_router(diagnostics.router)
    app.include_router(health.router)
    app.include_router(cfg.router, prefix="/api")
    app.include_router(tts.router, dependencies=protected_dependency)

    app.add_event_handler("shutdown", _on_shutdown)
    app.add_event_handler("startup", _on_startup_seed)

    return app


app = create_app()
