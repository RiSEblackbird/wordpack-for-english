from pydantic import BaseModel


class TextAssistRequest(BaseModel):
    """Request model for reading assistance."""

    text: str


class TextAssistResponse(BaseModel):
    """Response model for reading assistance."""

    summary: str | None = None
    # TODO: include vocabulary highlights, comprehension questions, etc.
