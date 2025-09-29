from fastapi import APIRouter
from ..config import settings


router = APIRouter()


@router.get("/config")
def get_runtime_config() -> dict[str, object]:
    """Expose runtime config needed by the frontend.

    フロントエンドが同期すべき実行時設定を返す。現状は
    フロントのリクエスト・タイムアウト(ms)をサーバの env に
    揃えるために `llm_timeout_ms` をそのまま返す。
    """
    return {
        "request_timeout_ms": settings.llm_timeout_ms,
        "llm_model": settings.llm_model,
    }
