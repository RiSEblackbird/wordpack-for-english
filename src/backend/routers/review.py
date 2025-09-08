from fastapi import APIRouter, HTTPException

from ..flows.feedback import FeedbackFlow
from ..flows.word_pack import WordPackFlow
from ..providers import ChromaClientFactory, get_llm_provider
from ..config import settings
from ..srs import store
from ..models.review import (
    ReviewTodayResponse,
    ReviewGradeRequest,
    ReviewGradeResponse,
    ReviewGradeByLemmaRequest,
    ReviewCard,
)

router = APIRouter(tags=["review"])


@router.get("/today", response_model=ReviewTodayResponse, response_model_exclude_none=True, summary="本日の復習カードを取得")
async def review_today() -> ReviewTodayResponse:
    """Return today's review items (up to 5)."""
    items = store.get_today(limit=5)
    cards = [ReviewCard(id=it.id, front=it.front, back=it.back) for it in items]
    return ReviewTodayResponse(items=cards)


@router.post("/grade", response_model=ReviewGradeResponse, response_model_exclude_none=True, summary="採点して次回出題時刻を更新")
async def review_grade(req: ReviewGradeRequest) -> ReviewGradeResponse:
    """Grade a review item using simplified SM-2 and return next due time."""
    updated = store.grade(item_id=req.item_id, grade=req.grade)
    if updated is None:
        raise HTTPException(status_code=404, detail="item not found")
    return ReviewGradeResponse(ok=True, next_due=updated.due_at)


@router.post("/grade_by_lemma", response_model=ReviewGradeResponse, response_model_exclude_none=True, summary="レンマ直採点（カード自動作成対応）")
async def review_grade_by_lemma(req: ReviewGradeByLemmaRequest) -> ReviewGradeResponse:
    """Grade by lemma. Create a card if it does not exist using study_card as back.

    - id 形式: "w:<lemma>"
    - front: lemma
    - back: WordPack.study_card
    """
    card_id = f"w:{req.lemma}"
    # 既存カードがなければ WordPack を用いて back を用意し作成
    chroma_client = ChromaClientFactory().create_client() if settings.rag_enabled else None
    llm = get_llm_provider()
    flow = WordPackFlow(chroma_client=chroma_client, llm=llm)
    pack = flow.run(req.lemma, pronunciation_enabled=False)
    back = pack.study_card or ""
    store.ensure_card(item_id=card_id, front=req.lemma, back=back)

    updated = store.grade(item_id=card_id, grade=req.grade)
    if updated is None:
        raise HTTPException(status_code=500, detail="failed to grade newly created card")
    return ReviewGradeResponse(ok=True, next_due=updated.due_at)
