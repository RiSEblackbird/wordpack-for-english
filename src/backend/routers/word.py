from fastapi import APIRouter

from ..flows.word_pack import WordPackFlow
from ..models.word import WordPackRequest, WordPack, WordLookupResponse

router = APIRouter()


@router.post("/pack", response_model=WordPack)
async def generate_word_pack(req: WordPackRequest) -> WordPack:
    """Generate a new word pack using LangGraph flow."""
    flow = WordPackFlow()
    return flow.run(req.lemma)


@router.get("", response_model=WordLookupResponse)
async def get_word() -> WordLookupResponse:
    """Retrieve information about a word (placeholder)."""
    return WordLookupResponse(definition=None, examples=[])
