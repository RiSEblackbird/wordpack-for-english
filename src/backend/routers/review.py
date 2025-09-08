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
    ReviewStatsResponse,
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


@router.get("/stats", response_model=ReviewStatsResponse, response_model_exclude_none=True, summary="進捗統計（今日の提案数/残数、直近レビュー）")
async def review_stats() -> ReviewStatsResponse:
    """Return progress stats for the session experience.

    - due_now: due <= now のカード件数
    - reviewed_today: 当日レビュー済み数
    - recent: 直近レビュー（最大5件）
    """
    due_now, reviewed_today = store.get_stats()
    recent_items = store.get_recent_reviewed(limit=5)
    recent_cards = [ReviewCard(id=it.id, front=it.front, back=it.back) for it in recent_items]
    return ReviewStatsResponse(due_now=due_now, reviewed_today=reviewed_today, recent=recent_cards)


@router.get("/popular", summary="よく見る順（人気）カード一覧（最大10件）")
async def review_popular(limit: int = 10) -> list[ReviewCard]:
    """Return popular cards ordered by number of reviews (desc)."""
    items = store.get_popular(limit=limit)
    return [ReviewCard(id=it.id, front=it.front, back=it.back) for it in items]
