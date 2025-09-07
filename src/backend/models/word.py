from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict

from .common import Citation, ConfidenceLevel


class RegenerateScope(str, Enum):
    all = "all"
    examples = "examples"
    collocations = "collocations"


class WordPackRequest(BaseModel):
    """Request model for generating a word pack (MVP).

    学習対象の語（lemma）と必要に応じて品詞などの条件を指定する。
    """

    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {"lemma": "converge", "pronunciation_enabled": True, "regenerate_scope": "all"},
            {"lemma": "converge", "pronunciation_enabled": False, "regenerate_scope": "examples"},
            {"lemma": "converge", "regenerate_scope": "collocations"}
        ],
        "x-schema-version": "0.3.0"
    })

    lemma: str = Field(min_length=1, max_length=64, description="見出し語（1..64文字）")
    pos: Optional[str] = None
    pronunciation_enabled: bool = True
    regenerate_scope: RegenerateScope = Field(
        default=RegenerateScope.all,
        description=(
            "再生成スコープ。MVPでは全体生成の上で、examples=例文セクション強化、"
            "collocations=共起セクションのみダミー加筆。"
        ),
    )


class Sense(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {"id": "s1", "gloss_ja": "意味（暫定）", "patterns": []}
        ]
    })

    id: str
    gloss_ja: str
    patterns: List[str] = Field(default_factory=list)
    register: Optional[str] = None


class CollocationLists(BaseModel):
    verb_object: List[str] = Field(default_factory=list)
    adj_noun: List[str] = Field(default_factory=list)
    prep_noun: List[str] = Field(default_factory=list)


class Collocations(BaseModel):
    general: CollocationLists = Field(default_factory=CollocationLists)
    academic: CollocationLists = Field(default_factory=CollocationLists)


class ContrastItem(BaseModel):
    with_: str = Field(alias="with")
    diff_ja: str

    class Config:
        allow_population_by_field_name = True


class Examples(BaseModel):
    A1: List[str] = Field(default_factory=list)
    B1: List[str] = Field(default_factory=list)
    C1: List[str] = Field(default_factory=list)
    tech: List[str] = Field(default_factory=list)


class Etymology(BaseModel):
    note: str
    confidence: ConfidenceLevel = ConfidenceLevel.low


class Pronunciation(BaseModel):
    ipa_GA: Optional[str] = None
    ipa_RP: Optional[str] = None
    syllables: Optional[int] = None
    stress_index: Optional[int] = None
    linking_notes: List[str] = Field(default_factory=list)


class WordPack(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "lemma": "converge",
                "pronunciation": {"ipa_GA": "/kənvɝdʒ/", "syllables": 2, "stress_index": 1, "linking_notes": []},
                "senses": [{"id": "s1", "gloss_ja": "意味（暫定）", "patterns": []}],
                "collocations": {"general": {"verb_object": [], "adj_noun": [], "prep_noun": []}, "academic": {"verb_object": [], "adj_noun": [], "prep_noun": []}},
                "contrast": [],
                "examples": {"A1": ["converge example."], "B1": [], "C1": [], "tech": []},
                "etymology": {"note": "TBD", "confidence": "low"},
                "study_card": "この語の要点（暫定）。",
                "citations": [],
                "confidence": "low"
            }
        ],
        "x-schema-version": "0.3.0"
    })

    lemma: str
    pronunciation: Pronunciation
    senses: List[Sense] = Field(default_factory=list)
    collocations: Collocations = Field(default_factory=Collocations)
    contrast: List[ContrastItem] = Field(default_factory=list)
    examples: Examples = Field(default_factory=Examples)
    etymology: Etymology
    study_card: str
    citations: List[Citation] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.low


"""
GET /api/word プレースホルダは PR2 で廃止。
必要になれば専用エンドポイント設計の上で別モデルを追加する。
"""
