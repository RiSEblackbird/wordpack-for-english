from datetime import datetime
from pydantic import BaseModel


class ReviewCard(BaseModel):
    """A single review card to display on the frontend."""

    id: str
    front: str
    back: str


class ReviewTodayResponse(BaseModel):
    """Response model for today's review items.

    今日の復習対象（SRS で間隔が来たカード等）
    """

    items: list[ReviewCard]


class ReviewGradeRequest(BaseModel):
    """Request model for submitting a review grade.

    復習結果の採点（正誤・信頼度など）をサーバへ送るためのリクエスト。
    """

    item_id: str
    grade: int


class ReviewGradeResponse(BaseModel):
    ok: bool
    next_due: datetime
