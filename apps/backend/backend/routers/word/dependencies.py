from __future__ import annotations

from importlib import import_module
from typing import Any, Awaitable, Callable

from fastapi import Request

from ...infrastructure.llm.wordpack_generator import run_wordpack_flow as _run_wordpack_flow
from ...auth import get_current_user
from ...config import settings
from ...id_factory import generate_word_pack_id as _generate_word_pack_id
from ...store import store as _default_store
from ...store.proxy import CurrentStoreProxy

store = CurrentStoreProxy(_default_store)
generate_word_pack_id = _generate_word_pack_id
run_wordpack_flow = _run_wordpack_flow


async def require_authenticated_user(request: Request) -> dict[str, str]:
    """ゲストを拒否するための認証依存関数（テスト時は無効化設定に合わせる）。"""

    # なぜ: DISABLE_SESSION_AUTH が有効な検証環境でも生成系 API を動かせるようにしつつ、
    #       本番では get_current_user でゲスト拒否とセッション検証を強制する。
    if settings.disable_session_auth:
        return {"mode": "test"}
    return await get_current_user(request)


def _word_router_package() -> Any | None:
    try:
        return import_module("backend.routers.word")
    except Exception:
        return None


def get_store() -> Any:
    package = _word_router_package()
    return getattr(package, "store", store)


def next_word_pack_id() -> str:
    package = _word_router_package()
    generator = getattr(package, "generate_word_pack_id", generate_word_pack_id)
    return str(generator())


def get_run_wordpack_flow() -> Callable[..., Awaitable[Any]]:
    package = _word_router_package()
    return getattr(package, "run_wordpack_flow", run_wordpack_flow)
