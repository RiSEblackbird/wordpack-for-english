from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def health_check() -> dict[str, str]:
    """Simple health check endpoint.

    ライブネス/レディネス確認用の簡易エンドポイント。
    監視ツールやコンテナオーケストレータからの疎通確認に使用。
    """
    return {"status": "ok"}
