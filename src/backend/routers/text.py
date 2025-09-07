from fastapi import APIRouter

from ..flows.reading_assist import ReadingAssistFlow
from ..providers import ChromaClientFactory
from ..config import settings
from ..models.text import TextAssistRequest, TextAssistResponse

router = APIRouter(tags=["text"])


@router.post("/assist", response_model=TextAssistResponse, response_model_exclude_none=True, summary="段落のアシスト（ダミー）")
async def assist_text(req: TextAssistRequest) -> TextAssistResponse:
    """Provide reading assistance for a given paragraph using LangGraph flow.

    段落テキストを入力として、文分割・用語注・パラフレーズ等の
    リーディング支援情報を返す。MVP はダミー応答。
    """
    chroma_client = ChromaClientFactory().create_client() if settings.rag_enabled else None
    flow = ReadingAssistFlow(chroma_client=chroma_client)
    return flow.run(req.paragraph)
