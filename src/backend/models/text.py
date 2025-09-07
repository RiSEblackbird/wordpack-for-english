from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class TextAssistRequest(BaseModel):
    """Request model for reading assistance."""

    paragraph: str


class SyntaxInfo(BaseModel):
    subject: Optional[str] = None
    predicate: Optional[str] = None
    mods: List[str] = []


class TermInfo(BaseModel):
    lemma: str
    gloss_ja: Optional[str] = None
    ipa: Optional[str] = None
    collocation: Optional[str] = None


class AssistedSentence(BaseModel):
    raw: str
    syntax: SyntaxInfo
    terms: List[TermInfo] = []
    paraphrase: Optional[str] = None


class TextAssistResponse(BaseModel):
    """Response model for reading assistance."""

    sentences: List[AssistedSentence] = []
    summary: Optional[str] = None
    citations: List[Dict[str, Any]] = []
