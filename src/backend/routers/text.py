from fastapi import APIRouter

from ..flows.reading_assist import ReadingAssistFlow
from ..models.text import TextAssistRequest, TextAssistResponse

router = APIRouter()


@router.post("/assist", response_model=TextAssistResponse)
async def assist_text(req: TextAssistRequest) -> TextAssistResponse:
    """Provide reading assistance for a given paragraph using LangGraph flow.

    段落テキストを入力として、文分割・用語注・パラフレーズ等の
    リーディング支援情報を返す。MVP はダミー応答。
    """
    flow = ReadingAssistFlow()
    return flow.run(req.paragraph)
