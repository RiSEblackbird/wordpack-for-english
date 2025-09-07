from fastapi import APIRouter

from ..flows.reading_assist import ReadingAssistFlow
from ..models.text import TextAssistRequest, TextAssistResponse

router = APIRouter()


@router.post("/assist", response_model=TextAssistResponse)
async def assist_text(req: TextAssistRequest) -> TextAssistResponse:
    """Provide reading assistance for a given paragraph using LangGraph flow."""
    flow = ReadingAssistFlow()
    return flow.run(req.paragraph)
