from fastapi import APIRouter

from ..flows.word_pack import WordPackFlow

router = APIRouter()


@router.post("/pack")
async def generate_word_pack() -> dict[str, str]:
    """Generate a new word pack.

    TODO: use ``WordPackFlow`` to create real packs.
    """
    flow = WordPackFlow()
    _ = flow  # placeholder to avoid unused variable
    return {"detail": "word pack generation pending"}


@router.get("")
async def get_word() -> dict[str, str]:
    """Retrieve information about a word.

    TODO: implement word lookup logic.
    """
    return {"detail": "word lookup pending"}
