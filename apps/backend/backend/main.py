from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

from fastapi import Depends, FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response

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
from .middleware import RateLimitMiddleware, RequestIDMiddleware
from .observability import request_trace
from .providers import ChromaClientFactory, shutdown_providers
from .routers import article as article_router
from .routers import auth as auth_router
from .routers import config as cfg
from .routers import diagnostics, health, tts, word


async def access_log_and_metrics(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Measure request latency and emit access logs/metrics.

    FastAPI の HTTP ミドルウェアとして、処理開始〜終了の遅延を計測し、
    リクエストIDやUAなどのメタ情報と共に構造化ログとメトリクスへ記録する。
    Langfuse トレースが有効な場合は入出力も添付する。
    """
    start = time.time()
    path = request.url.path
    method = request.method
    request_id = getattr(request.state, "request_id", None)
    client_ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "-")
    is_error = False
    is_timeout = False
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
            try:
                output_payload = {
                    "status": getattr(response, "status_code", None),
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
            if (
                TimeoutException is not None and isinstance(exc, TimeoutException)
            ) or isinstance(exc, asyncio.TimeoutError):
                is_timeout = True
            raise
        finally:
            latency_ms = (time.time() - start) * 1000
            registry.record(path, latency_ms, is_error=is_error, is_timeout=is_timeout)
            logger.info(
                "request_complete",
                path=path,
                method=method,
                latency_ms=latency_ms,
                is_error=is_error,
                is_timeout=is_timeout,
                request_id=request_id,
                client_ip=client_ip,
                user_agent=ua,
            )


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
    app = FastAPI(title="WordPack API", version="0.3.1")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _maybe_add_timeout_middleware(app)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        ip_capacity_per_minute=settings.rate_limit_per_min_ip,
        user_capacity_per_minute=settings.rate_limit_per_min_user,
    )

    app.middleware("http")(access_log_and_metrics)

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
    app.include_router(diagnostics.router)
    app.include_router(health.router)
    app.include_router(cfg.router, prefix="/api")
    app.include_router(tts.router, dependencies=protected_dependency)

    app.add_event_handler("shutdown", _on_shutdown)
    app.add_event_handler("startup", _on_startup_seed)

    return app


app = create_app()
