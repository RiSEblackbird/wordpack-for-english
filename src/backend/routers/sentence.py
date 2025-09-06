from fastapi import APIRouter

from ..flows.feedback import FeedbackFlow

router = APIRouter()


@router.post("/check")
async def check_sentence() -> dict[str, str]:
    """Check a sentence and return feedback.

    TODO: integrate ``FeedbackFlow`` for real analysis.
    """
    flow = FeedbackFlow()
    _ = flow  # placeholder
    return {"detail": "sentence checking pending"}
