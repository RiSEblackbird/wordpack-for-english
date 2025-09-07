from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class TextAssistRequest(BaseModel):
    """Request model for reading assistance.

    段落テキストを受け取り、文分割・用語注・パラフレーズ等の
    リーディング支援を要求するためのリクエスト。
    """

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
    """Response model for reading assistance.

    文ごとの支援情報（構文・用語・言い換え等）や、文章全体の要約、
    参考文献・出典の引用を含める想定。
    """

    sentences: List[AssistedSentence] = []
    summary: Optional[str] = None
    citations: List[Dict[str, Any]] = []
    confidence: str = "low"
