import time
import asyncio
from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
try:
    from starlette.middleware.timeout import TimeoutMiddleware  # type: ignore
except Exception:  # Starlette が古い場合などに備えたフォールバック
    TimeoutMiddleware = None  # type: ignore[assignment]

try:
    from starlette.exceptions import TimeoutException  # type: ignore
except Exception:
    TimeoutException = None  # type: ignore[assignment]

from .config import settings  # noqa: F401 - imported for side effects or future use
from .logging import configure_logging, logger
from .routers import health, review, sentence, text, word
from .metrics import registry
from .config import settings
from .middleware import RequestIDMiddleware, RateLimitMiddleware
from .providers import shutdown_providers, ChromaClientFactory
from .indexing import seed_word_snippets, seed_domain_terms, seed_from_jsonl
from pathlib import Path

configure_logging()
app = FastAPI(title="WordPack API", version="0.3.0")

# CORS（必要に応じて環境変数に移行可能）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# タイムアウト（運用の初期値: 10秒）: Starlette が未対応ならスキップ
if TimeoutMiddleware is not None:
    app.add_middleware(TimeoutMiddleware, timeout=10)

# リクエストID付与（全リクエスト）
app.add_middleware(RequestIDMiddleware)

# レート制限（IP/ユーザ, 429応答）。必要に応じて環境変数で閾値を調整
app.add_middleware(
    RateLimitMiddleware,
    ip_capacity_per_minute=settings.rate_limit_per_min_ip,
    user_capacity_per_minute=settings.rate_limit_per_min_user,
)


@app.middleware("http")
async def access_log_and_metrics(request: Request, call_next):
    start = time.time()
    path = request.url.path
    method = request.method
    request_id = getattr(request.state, "request_id", None)
    client_ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "-")
    is_error = False
    is_timeout = False
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        is_error = True
        if (TimeoutException is not None and isinstance(exc, TimeoutException)) or isinstance(exc, asyncio.TimeoutError):
            is_timeout = True
        raise exc
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

app.include_router(word.router, prefix="/api/word")  # 語彙関連エンドポイント
app.include_router(sentence.router, prefix="/api/sentence")  # 例文チェック関連
app.include_router(text.router, prefix="/api/text")  # リーディング支援関連
app.include_router(review.router, prefix="/api/review")  # 復習（SRS）関連
app.include_router(health.router)  # ヘルスチェック


@app.on_event("shutdown")
async def _on_shutdown() -> None:
    # 共有スレッドプールなどのリソースを解放
    shutdown_providers()


@app.on_event("startup")
async def _on_startup_seed() -> None:
    # 起動時自動シード（任意）: STRICT_MODE=true でも、明示フラグがtrueなら最小シードを投入
    try:
        if settings.auto_seed_on_startup and settings.rag_enabled:
            client = ChromaClientFactory().create_client()
            if client is None:
                return
            wj = Path(settings.auto_seed_word_jsonl) if settings.auto_seed_word_jsonl else None
            tj = Path(settings.auto_seed_terms_jsonl) if settings.auto_seed_terms_jsonl else None
            if (wj and wj.exists()) or (tj and tj.exists()):
                seed_from_jsonl(client, word_snippets_path=wj, domain_terms_path=tj)
                logger.info("auto_seed", mode="jsonl", word_jsonl=str(wj) if wj else None, terms_jsonl=str(tj) if tj else None)
            else:
                seed_word_snippets(client)
                seed_domain_terms(client)
                logger.info("auto_seed", mode="minimal")
    except Exception as exc:
        # strict モードでも起動継続。RAG は依存未満で424が返るため、API全体の起動は止めない
        logger.warning("auto_seed_failed", error=repr(exc))
