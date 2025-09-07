from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from .common import Citation, ConfidenceLevel


class SentenceCheckRequest(BaseModel):
    """Request model for sentence checking.

    クライアントから文を受け取り、診断・修正案の生成を要求するための
    リクエストボディ。
    """

    model_config = ConfigDict(json_schema_extra={
        "examples": [{"sentence": "I researches about AI."}]
    })

    sentence: str = Field(min_length=1, max_length=500, description="対象の英文（最大500字）")


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
    """Detailed feedback about a sentence.

    文法・語法の指摘（issues）、スタイル別の書き換え案（revisions）、
    簡易演習（exercise）を含むフィードバック。
    """

    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "issues": [{"what": "語法", "why": "動詞の一致", "fix": "research"}],
                "revisions": [{"style": "natural", "text": "I research AI."}],
                "exercise": {"q": "Fix the verb: I ____ about AI.", "a": "research"},
                "citations": [],
                "confidence": "low"
            }
        ]
    })

    issues: List[Issue] = Field(default_factory=list)
    revisions: List[Revision] = Field(default_factory=list)
    exercise: Optional[MiniExercise] = None
    citations: List[Citation] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.low
