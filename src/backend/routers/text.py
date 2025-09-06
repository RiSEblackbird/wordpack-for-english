from fastapi import APIRouter

from ..flows.reading_assist import ReadingAssistFlow

router = APIRouter()


@router.post("/assist")
async def assist_text() -> dict[str, str]:
    """Provide reading assistance for a given text.

    TODO: hook into ``ReadingAssistFlow`` for real assistance.
    """
    flow = ReadingAssistFlow()
    _ = flow  # placeholder
    return {"detail": "reading assistance pending"}
