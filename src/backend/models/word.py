from pydantic import BaseModel


class WordPackRequest(BaseModel):
    """Request model for generating a word pack."""

    topic: str  # TODO: refine fields


class WordPackResponse(BaseModel):
    """Response model containing the generated word pack."""

    words: list[str]


class WordLookupResponse(BaseModel):
    """Response model for word lookup."""

    definition: str | None = None
    examples: list[str] = []
