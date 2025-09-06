from pydantic import BaseModel


class SentenceCheckRequest(BaseModel):
    """Request model for sentence checking."""

    sentence: str


class SentenceCheckResponse(BaseModel):
    """Response model with feedback about a sentence."""

    feedback: str
    # TODO: add more detailed feedback fields
