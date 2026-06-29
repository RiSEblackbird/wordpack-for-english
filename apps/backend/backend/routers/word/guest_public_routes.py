from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ...application.common.errors import NotFoundError
from ...application.wordpack.guest_public import (
    UpdateWordPackGuestPublicCommand,
    update_guest_public_flag,
)
from ...infrastructure.runtime import SystemClock
from ...logging import logger
from ...models.word import WordPackGuestPublicRequest, WordPackGuestPublicResponse
from .dependencies import get_store, require_authenticated_user

router = APIRouter()


@router.post(
    "/packs/{word_pack_id}/guest-public",
    response_model=WordPackGuestPublicResponse,
    summary="WordPackのゲスト公開フラグを更新",
)
async def update_word_pack_guest_public(
    request: Request,
    word_pack_id: str,
    req: WordPackGuestPublicRequest,
    _user: dict[str, str] = Depends(require_authenticated_user),
) -> WordPackGuestPublicResponse:
    """WordPack単位のゲスト公開フラグを更新する。"""

    command = UpdateWordPackGuestPublicCommand(
        word_pack_id=word_pack_id,
        guest_public=req.guest_public,
        updated_at=SystemClock().now_iso(),
    )
    try:
        result = update_guest_public_flag(repository=get_store(), command=command)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    logger.info(
        "wordpack_guest_public_updated",
        word_pack_id=word_pack_id,
        user_id=getattr(request.state, "user_id", None),
        guest_public=req.guest_public,
    )
    return WordPackGuestPublicResponse(
        word_pack_id=result.word_pack_id,
        guest_public=result.guest_public,
    )
