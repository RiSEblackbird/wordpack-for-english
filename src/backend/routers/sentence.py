from fastapi import APIRouter

from ..flows.feedback import FeedbackFlow
from ..models.sentence import SentenceCheckRequest, SentenceCheckResponse

router = APIRouter()


@router.post("/check", response_model=SentenceCheckResponse)
async def check_sentence(req: SentenceCheckRequest) -> SentenceCheckResponse:
    """Check a sentence and return feedback using LangGraph flow.

    文の診断（issues/revisions/exercise）を返すエンドポイント。
    MVP ではダミーだが、将来的に LLM による詳細診断に置換予定。
    """
    flow = FeedbackFlow()
    return flow.run(req.sentence)
