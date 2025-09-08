from datetime import datetime
from pydantic import BaseModel
from pydantic import Field


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


class ReviewGradeByLemmaRequest(BaseModel):
    """レンマ直採点のリクエストモデル。

    - lemma: 学習語の見出し
    - grade: 0|1|2 の三段階
    """

    lemma: str = Field(min_length=1, max_length=64)
    grade: int = Field(ge=0, le=2)


class ReviewStatsResponse(BaseModel):
    """進捗の見える化 用の統計レスポンス。

    - due_now: 現在時点で出題すべき件数（残数）
    - reviewed_today: 今日レビュー済み件数
    - recent: 直近レビューした最大5件
    """

    due_now: int
    reviewed_today: int
    recent: list[ReviewCard] = []
