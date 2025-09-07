from fastapi import APIRouter

from ..flows.feedback import FeedbackFlow

router = APIRouter()


@router.get("/today")
async def review_today() -> dict[str, str]:
    """Return today's review items.

    今日レビュー対象のアイテム一覧を返す。
    MVP では固定レスポンス。将来は SRS の間隔計算に基づく取得を実装。
    """
    return {"detail": "review retrieval pending"}


@router.post("/grade")
async def review_grade() -> dict[str, str]:
    """Grade a review item.

    復習結果（正誤や信頼度）を評価・記録する。
    MVP ではダミー実装。将来は ``FeedbackFlow`` と連携し自動採点を検討。
    """
    flow = FeedbackFlow()
    _ = flow  # placeholder
    return {"detail": "review grading pending"}
