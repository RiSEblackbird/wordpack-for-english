from __future__ import annotations

from fastapi import APIRouter

from .dependencies import get_store
from .schemas import LemmaLookupResponse

router = APIRouter()


@router.get(
    "/lemma/{lemma}",
    response_model=LemmaLookupResponse,
    summary="lemma から WordPack を検索（case-insensitive）",
)
async def lookup_by_lemma(lemma: str) -> LemmaLookupResponse:
    """DB内の WordPack を lemma=完全一致（大文字小文字無視）で検索し返す。"""

    result = get_store().find_word_pack_by_lemma_ci(lemma)
    if result is None:
        return LemmaLookupResponse(found=False)
    wp_id, saved_lemma, sense_title = result
    return LemmaLookupResponse(
        found=True, id=wp_id, lemma=saved_lemma, sense_title=sense_title
    )
