from fastapi import APIRouter

from ..flows.feedback import FeedbackFlow

router = APIRouter()


@router.get("/today")
async def review_today() -> dict[str, str]:
    """Return today's review items.

    TODO: implement spaced-repetition retrieval.
    """
    return {"detail": "review retrieval pending"}


@router.post("/grade")
async def review_grade() -> dict[str, str]:
    """Grade a review item.

    TODO: integrate ``FeedbackFlow`` to evaluate answers.
    """
    flow = FeedbackFlow()
    _ = flow  # placeholder
    return {"detail": "review grading pending"}
