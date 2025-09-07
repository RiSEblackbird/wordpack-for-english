from typing import List, Optional
from pydantic import BaseModel


class SentenceCheckRequest(BaseModel):
    """Request model for sentence checking."""

    sentence: str


class Issue(BaseModel):
    what: str
    why: str
    fix: str


class Revision(BaseModel):
    style: str  # natural / formal / academic
    text: str


class MiniExercise(BaseModel):
    q: str
    a: str


class SentenceCheckResponse(BaseModel):
    """Detailed feedback about a sentence."""

    issues: List[Issue] = []
    revisions: List[Revision] = []
    exercise: Optional[MiniExercise] = None
