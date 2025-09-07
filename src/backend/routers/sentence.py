from fastapi import APIRouter

from ..flows.feedback import FeedbackFlow
from ..providers import ChromaClientFactory, get_llm_provider
from ..config import settings
from ..models.sentence import SentenceCheckRequest, SentenceCheckResponse

router = APIRouter(tags=["sentence"])


@router.post("/check", response_model=SentenceCheckResponse, response_model_exclude_none=True, summary="英文の診断（ダミー）")
async def check_sentence(req: SentenceCheckRequest) -> SentenceCheckResponse:
    """Check a sentence and return feedback using LangGraph flow.

    文の診断（issues/revisions/exercise）を返すエンドポイント。
    MVP ではダミーだが、将来的に LLM による詳細診断に置換予定。
    """
    # 文章単文チェックでも将来的に出典提示を可能に
    chroma_client = ChromaClientFactory().create_client() if settings.rag_enabled else None
    llm = get_llm_provider()
    flow = FeedbackFlow(llm=llm, chroma_client=chroma_client)
    return flow.run(req.sentence)
