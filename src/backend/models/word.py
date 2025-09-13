from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict

from .common import Citation, ConfidenceLevel


class RegenerateScope(str, Enum):
    all = "all"
    examples = "examples"
    collocations = "collocations"


class WordPackCreateRequest(BaseModel):
    """Request model for creating an empty WordPack entry without generation.

    生成を行わず、空の各情報を持つ WordPack を保存するための最小入力。
    """

    lemma: str = Field(min_length=1, max_length=64, description="見出し語（1..64文字）")


class WordPackRequest(BaseModel):
    """Request model for generating a word pack (MVP).

    学習対象の語（lemma）と必要に応じて品詞などの条件を指定する。
    """

    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {"lemma": "converge", "pronunciation_enabled": True, "regenerate_scope": "all", "model": "gpt-4o-mini", "temperature": 0.6},
            {"lemma": "converge", "pronunciation_enabled": False, "regenerate_scope": "examples", "model": "gpt-4o-mini", "temperature": 0.6},
            {"lemma": "converge", "regenerate_scope": "collocations", "model": "gpt-4o-mini", "temperature": 0.6}
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
    # オプショナルな生成パラメータ（未指定ならバックエンド設定を使用）
    model: Optional[str] = Field(default=None, description="LLMモデル名の上書き（未指定なら既定 settings.llm_model）")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="生成の温度。未指定時は実装既定値を使用")
    # gpt-5-mini 等の推論系モデル向けパラメータ
    reasoning: Optional[dict] = Field(default=None, description="reasoning オプション（例: {effort: minimal|low|medium|high}）")
    text: Optional[dict] = Field(default=None, description="text オプション（例: {verbosity: low|medium|high}）")


class Sense(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {
                "id": "s1",
                "gloss_ja": "意味（暫定）",
                "definition_ja": "核となる定義を1〜2文で端的に示す。",
                "nuances_ja": "フォーマル/口語/専門寄り等の含意や使い分け。",
                "patterns": ["converge on N"],
                "synonyms": ["gather", "meet"],
                "antonyms": ["diverge"],
                "register": "formal",
                "notes_ja": "可算/不可算や自他/再帰などの注意点。"
            }
        ]
    })

    id: str
    gloss_ja: str
    # よりボリューミーな語義のための追加フィールド（すべて任意）
    definition_ja: Optional[str] = None
    nuances_ja: Optional[str] = None
    patterns: List[str] = Field(default_factory=list)
    synonyms: List[str] = Field(default_factory=list)
    antonyms: List[str] = Field(default_factory=list)
    register: Optional[str] = None
    notes_ja: Optional[str] = None


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

    model_config = ConfigDict(populate_by_name=True)


class Examples(BaseModel):
    class ExampleItem(BaseModel):
        en: str
        ja: str
        grammar_ja: Optional[str] = None

    Dev: List[ExampleItem] = Field(default_factory=list)
    CS: List[ExampleItem] = Field(default_factory=list)
    LLM: List[ExampleItem] = Field(default_factory=list)
    Business: List[ExampleItem] = Field(default_factory=list)
    Common: List[ExampleItem] = Field(default_factory=list)


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
                "examples": {"Dev": [{"en": "converge example in app dev.", "ja": "アプリ開発の現場での converge の例", "grammar_ja": "第3文型。"}], "CS": [], "LLM": [], "Business": [], "Common": []},
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


class WordPackListItem(BaseModel):
    """WordPack一覧表示用の軽量モデル"""
    id: str
    lemma: str
    created_at: str
    updated_at: str


class WordPackListResponse(BaseModel):
    """WordPack一覧レスポンス"""
    items: List[WordPackListItem]
    total: int
    limit: int
    offset: int


class WordPackRegenerateRequest(BaseModel):
    """WordPack再生成リクエスト"""
    pronunciation_enabled: bool = True
    regenerate_scope: RegenerateScope = Field(default=RegenerateScope.all)
    model: Optional[str] = Field(default=None, description="LLMモデル名の上書き（未指定なら既定 settings.llm_model）")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    reasoning: Optional[dict] = Field(default=None)
    text: Optional[dict] = Field(default=None)
