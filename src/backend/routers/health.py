from fastapi import APIRouter
from fastapi.responses import JSONResponse
from ..metrics import registry

router = APIRouter()


@router.get("/healthz")
def health_check() -> dict[str, str]:
    """Simple health check endpoint.

    ライブネス/レディネス確認用の簡易エンドポイント。
    監視ツールやコンテナオーケストレータからの疎通確認に使用。
    """
    return {"status": "ok"}


@router.get("/metrics")
def metrics() -> JSONResponse:
    """Return in-memory metrics snapshot.

    p95/エラー/タイムアウト/件数をパス別に返す簡易メトリクス。
    """
    return JSONResponse(content={"paths": registry.snapshot()})
