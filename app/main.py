import time
import structlog
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.timeout import TimeoutMiddleware

from .config import settings
from .logging_config import setup_logging

setup_logging()
logger = structlog.get_logger()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TimeoutMiddleware, timeout=10)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
    finally:
        latency_ms = (time.time() - start) * 1000
        tokens = response.headers.get("x-token-count", "0")
        logger.info(
            "request_complete", path=request.url.path, latency_ms=latency_ms, tokens=tokens
        )
    return response


@app.get("/api/example")
async def example_endpoint():
    return {"message": "example"}


# Serve static files for minimal UI
app.mount("/", StaticFiles(directory="static", html=True), name="static")
