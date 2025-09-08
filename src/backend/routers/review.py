from fastapi import APIRouter, HTTPException

from ..flows.feedback import FeedbackFlow
from ..srs import store
from ..models.review import (
    ReviewTodayResponse,
    ReviewGradeRequest,
    ReviewGradeResponse,
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
