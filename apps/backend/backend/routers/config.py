from fastapi import APIRouter, Depends

from ..config import settings
from ..permissions import UserRole, ensure_authenticated, resolve_user_role


router = APIRouter()


@router.get("/config")
def get_runtime_config(
    _: str = Depends(ensure_authenticated),
    user_role: UserRole = Depends(resolve_user_role),
) -> dict[str, object]:
    """Expose runtime config needed by the frontend.

    フロントエンドが同期すべき実行時設定を返す。現状は
    フロントのリクエスト・タイムアウト(ms)をサーバの env に
    揃えるために `llm_timeout_ms` をそのまま返す。
    """
    return {
        "request_timeout_ms": settings.llm_timeout_ms,
        "llm_model": settings.llm_model,
        "user_role": user_role,
    }
