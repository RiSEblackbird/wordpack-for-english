from pydantic import BaseModel


class ReviewTodayResponse(BaseModel):
    """Response model for today's review items.

    今日の復習対象（SRS で間隔が来たカード等）を返すためのレスポンス。
    MVP では文字列 ID のみだが、将来はメタ情報を含める可能性あり。
    """

    items: list[str]


class ReviewGradeRequest(BaseModel):
    """Request model for submitting a review grade.

    復習結果の採点（正誤・信頼度など）をサーバへ送るためのリクエスト。
    """

    item_id: str
    grade: int
