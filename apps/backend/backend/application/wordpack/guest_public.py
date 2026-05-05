from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, Request

from ...logging import logger
from ...models.word import WordPackGuestPublicRequest, WordPackGuestPublicResponse


def update_guest_public_flag(
    *,
    request: Request,
    repository,
    word_pack_id: str,
    req: WordPackGuestPublicRequest,
) -> WordPackGuestPublicResponse:
    metadata = repository.get_word_pack_metadata(word_pack_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail="WordPack not found")

    now = datetime.now(UTC).isoformat()
    repository.update_word_pack_metadata(
        word_pack_id,
        updated_at=now,
        guest_public=req.guest_public,
    )

    logger.info(
        "wordpack_guest_public_updated",
        word_pack_id=word_pack_id,
        user_id=getattr(request.state, "user_id", None),
        guest_public=req.guest_public,
    )

    return WordPackGuestPublicResponse(
        word_pack_id=word_pack_id,
        guest_public=req.guest_public,
    )
