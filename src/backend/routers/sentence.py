from fastapi import APIRouter

from ..flows.feedback import FeedbackFlow
from ..models.sentence import SentenceCheckRequest, SentenceCheckResponse

router = APIRouter()


@router.post("/check", response_model=SentenceCheckResponse)
async def check_sentence(req: SentenceCheckRequest) -> SentenceCheckResponse:
    """Check a sentence and return feedback using LangGraph flow."""
    flow = FeedbackFlow()
    return flow.run(req.sentence)
