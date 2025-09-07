import time
from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.timeout import TimeoutMiddleware

from .config import settings  # noqa: F401 - imported for side effects or future use
from .logging import configure_logging, logger
from .routers import health, review, sentence, text, word
from .metrics import registry

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

# タイムアウト（運用の初期値: 10秒）
app.add_middleware(TimeoutMiddleware, timeout=10)


@app.middleware("http")
async def access_log_and_metrics(request: Request, call_next):
    start = time.time()
    path = request.url.path
    is_error = False
    is_timeout = False
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        is_error = True
        raise exc
    finally:
        latency_ms = (time.time() - start) * 1000
        registry.record(path, latency_ms, is_error=is_error, is_timeout=is_timeout)
        logger.info("request_complete", path=path, latency_ms=latency_ms)

app.include_router(word.router, prefix="/api/word")  # 語彙関連エンドポイント
app.include_router(sentence.router, prefix="/api/sentence")  # 例文チェック関連
app.include_router(text.router, prefix="/api/text")  # リーディング支援関連
app.include_router(review.router, prefix="/api/review")  # 復習（SRS）関連
app.include_router(health.router)  # ヘルスチェック
