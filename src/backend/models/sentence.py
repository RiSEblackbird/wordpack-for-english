from typing import List, Optional
from pydantic import BaseModel


class SentenceCheckRequest(BaseModel):
    """Request model for sentence checking.

    クライアントから文を受け取り、診断・修正案の生成を要求するための
    リクエストボディ。
    """

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
    """Detailed feedback about a sentence.

    文法・語法の指摘（issues）、スタイル別の書き換え案（revisions）、
    簡易演習（exercise）を含むフィードバック。
    """

    issues: List[Issue] = []
    revisions: List[Revision] = []
    exercise: Optional[MiniExercise] = None
