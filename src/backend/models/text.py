from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from .common import Citation, ConfidenceLevel


class TextAssistRequest(BaseModel):
    """Request model for reading assistance.

    段落テキストを受け取り、文分割・用語注・パラフレーズ等の
    リーディング支援を要求するためのリクエスト。
    """

    model_config = ConfigDict(json_schema_extra={
        "examples": [{"paragraph": "Our algorithm converges under mild assumptions."}]
    })

    paragraph: str = Field(min_length=1, max_length=2000, description="対象の段落（最大2000字）")


class SyntaxInfo(BaseModel):
    subject: Optional[str] = None
    predicate: Optional[str] = None
    mods: List[str] = Field(default_factory=list)


class TermInfo(BaseModel):
    lemma: str
    gloss_ja: Optional[str] = None
    ipa: Optional[str] = None
    collocation: Optional[str] = None


class AssistedSentence(BaseModel):
    raw: str
    syntax: SyntaxInfo
    terms: List[TermInfo] = Field(default_factory=list)
    paraphrase: Optional[str] = None


class TextAssistResponse(BaseModel):
    """Response model for reading assistance.

    文ごとの支援情報（構文・用語・言い換え等）や、文章全体の要約、
    参考文献・出典の引用を含める想定。
    """

    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "sentences": [
                    {
                        "raw": "Our algorithm converges under mild assumptions",
                        "syntax": {"subject": null, "predicate": null, "mods": []},
                        "terms": [{"lemma": "Our", "gloss_ja": null, "ipa": null}]
                    }
                ],
                "summary": null,
                "citations": [],
                "confidence": "low"
            }
        ]
    })

    sentences: List[AssistedSentence] = Field(default_factory=list)
    summary: Optional[str] = None
    citations: List[Citation] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.low
