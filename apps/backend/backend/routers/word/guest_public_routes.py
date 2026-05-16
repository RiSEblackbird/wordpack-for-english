from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ...application.wordpack.guest_public import update_guest_public_flag
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

    return update_guest_public_flag(
        request=request,
        repository=get_store(),
        word_pack_id=word_pack_id,
        req=req,
    )
