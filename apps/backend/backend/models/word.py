from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "lemma": "converge",
                    "pronunciation_enabled": True,
                    "regenerate_scope": "all",
                    "model": "gpt-4o-mini",
                    "temperature": 0.6,
                },
                {
                    "lemma": "converge",
                    "pronunciation_enabled": False,
                    "regenerate_scope": "examples",
                    "model": "gpt-4o-mini",
                    "temperature": 0.6,
                },
                {
                    "lemma": "converge",
                    "regenerate_scope": "collocations",
                    "model": "gpt-4o-mini",
                    "temperature": 0.6,
                },
            ],
            "x-schema-version": "0.3.0",
        }
    )

    lemma: str = Field(min_length=1, max_length=64, description="見出し語（1..64文字）")
    pos: str | None = None
    pronunciation_enabled: bool = True
    regenerate_scope: RegenerateScope = Field(
        default=RegenerateScope.all,
        description=(
            "再生成スコープ。MVPでは全体生成の上で、examples=例文セクション強化、"
            "collocations=共起セクションのみダミー加筆。"
        ),
    )
    # オプショナルな生成パラメータ（未指定ならバックエンド設定を使用）
    model: str | None = Field(
        default=None,
        description="LLMモデル名の上書き（未指定なら既定 settings.llm_model）",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="生成の温度。未指定時は実装既定値を使用",
    )
    # gpt-5-mini 等の推論系モデル向けパラメータ
    reasoning: dict | None = Field(
        default=None,
        description="reasoning オプション（例: {effort: minimal|low|medium|high}）",
    )
    text: dict | None = Field(
        default=None, description="text オプション（例: {verbosity: low|medium|high}）"
    )


class Sense(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
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
                    "notes_ja": "可算/不可算や自他/再帰などの注意点。",
                }
            ]
        },
    )

    id: str
    gloss_ja: str
    # よりボリューミーな語義のための追加フィールド（すべて任意）
    definition_ja: str | None = None
    nuances_ja: str | None = None
    # 名詞（特に専門用語）のときに概念解説を充実させる任意フィールド
    # term_overview_ja: 用語の概要（3〜5文程度）
    # term_core_ja: 用語の本質/本質的ポイント（1〜2文）
    term_overview_ja: str | None = None
    term_core_ja: str | None = None
    patterns: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    antonyms: list[str] = Field(default_factory=list)
    # BaseModel の属性名と衝突するため、フィールド名を register_ に変更し、API 互換のためエイリアスを維持
    register_: str | None = Field(default=None, alias="register")
    notes_ja: str | None = None


class CollocationLists(BaseModel):
    verb_object: list[str] = Field(default_factory=list)
    adj_noun: list[str] = Field(default_factory=list)
    prep_noun: list[str] = Field(default_factory=list)


class Collocations(BaseModel):
    general: CollocationLists = Field(default_factory=CollocationLists)
    academic: CollocationLists = Field(default_factory=CollocationLists)


class ContrastItem(BaseModel):
    with_: str = Field(alias="with")
    diff_ja: str

    model_config = ConfigDict(populate_by_name=True)


class ExampleCategory(str, Enum):
    Dev = "Dev"
    CS = "CS"
    LLM = "LLM"
    Business = "Business"
    Common = "Common"


class Examples(BaseModel):
    class ExampleItem(BaseModel):
        en: str
        ja: str
        grammar_ja: str | None = None
        # 追加メタ: カテゴリと生成に使用した LLM 情報
        category: ExampleCategory | None = Field(
            default=None, description="例文カテゴリ（後方互換のため任意）"
        )
        llm_model: str | None = Field(
            default=None, description="例文生成に使用したLLMモデル名（任意）"
        )
        llm_params: str | None = Field(
            default=None, description="LLMパラメータ情報を連結した文字列（任意）"
        )
        checked_only_count: int = Field(
            default=0,
            ge=0,
            description="この例文を確認しただけの回数（非負整数）",
        )
        learned_count: int = Field(
            default=0,
            ge=0,
            description="この例文を学習完了と記録した回数（非負整数）",
        )

    Dev: list[ExampleItem] = Field(default_factory=list)
    CS: list[ExampleItem] = Field(default_factory=list)
    LLM: list[ExampleItem] = Field(default_factory=list)
    Business: list[ExampleItem] = Field(default_factory=list)
    Common: list[ExampleItem] = Field(default_factory=list)


class Etymology(BaseModel):
    note: str
    confidence: ConfidenceLevel = ConfidenceLevel.low


# --- Example listing API models ---
class ExampleListItem(BaseModel):
    id: int
    word_pack_id: str
    lemma: str
    category: ExampleCategory
    en: str
    ja: str
    grammar_ja: str | None = None
    created_at: str
    word_pack_updated_at: str | None = None
    checked_only_count: int = Field(
        default=0,
        ge=0,
        description="例文を確認しただけの回数（非負整数）",
    )
    learned_count: int = Field(
        default=0,
        ge=0,
        description="例文を学習済みと記録した回数（非負整数）",
    )


class ExampleListResponse(BaseModel):
    items: list[ExampleListItem]
    total: int
    limit: int
    offset: int


class ExamplesBulkDeleteRequest(BaseModel):
    ids: list[int] = Field(
        default_factory=list,
        description="削除対象の例文ID一覧",
        min_length=1,
        max_length=200,
    )


class ExamplesBulkDeleteResponse(BaseModel):
    deleted: int = Field(description="削除に成功した件数")
    not_found: list[int] = Field(
        default_factory=list, description="削除できなかったID一覧（未存在など）"
    )


class Pronunciation(BaseModel):
    ipa_GA: str | None = None
    ipa_RP: str | None = None
    syllables: int | None = None
    stress_index: int | None = None
    linking_notes: list[str] = Field(default_factory=list)


class WordPack(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "lemma": "converge",
                    "sense_title": "収束ポイント",
                    "pronunciation": {
                        "ipa_GA": "/kənvɝdʒ/",
                        "syllables": 2,
                        "stress_index": 1,
                        "linking_notes": [],
                    },
                    "senses": [
                        {"id": "s1", "gloss_ja": "意味（暫定）", "patterns": []}
                    ],
                    "collocations": {
                        "general": {"verb_object": [], "adj_noun": [], "prep_noun": []},
                        "academic": {
                            "verb_object": [],
                            "adj_noun": [],
                            "prep_noun": [],
                        },
                    },
                    "contrast": [],
                    "examples": {
                        "Dev": [
                            {
                                "en": "converge example in app dev.",
                                "ja": "アプリ開発の現場での converge の例",
                                "grammar_ja": "第3文型。",
                            }
                        ],
                        "CS": [],
                        "LLM": [],
                        "Business": [],
                        "Common": [],
                    },
                    "etymology": {"note": "TBD", "confidence": "low"},
                    "study_card": "この語の要点（暫定）。",
                    "citations": [],
                    "confidence": "low",
                }
            ],
            "x-schema-version": "0.3.1",
        }
    )

    lemma: str
    sense_title: str = Field(
        default="",
        description="語義一覧などで表示する短い語義タイトル（10文字程度を想定）",
    )
    pronunciation: Pronunciation
    senses: list[Sense] = Field(default_factory=list)
    collocations: Collocations = Field(default_factory=Collocations)
    contrast: list[ContrastItem] = Field(default_factory=list)
    examples: Examples = Field(default_factory=Examples)
    etymology: Etymology
    study_card: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.low
    # 生成に使用したAIのメタ（任意）
    llm_model: str | None = Field(default=None)
    llm_params: str | None = Field(default=None)
    checked_only_count: int = Field(
        default=0,
        ge=0,
        description="WordPack全体を確認しただけの回数（非負整数）",
    )
    learned_count: int = Field(
        default=0,
        ge=0,
        description="WordPack全体を学習した回数（非負整数）",
    )


class WordPackListItem(BaseModel):
    """WordPack一覧表示用の軽量モデル"""

    id: str
    lemma: str
    sense_title: str = Field(default="", description="一覧表示用の語義タイトル")
    created_at: str
    updated_at: str
    is_empty: bool = Field(
        default=False, description="内容が空のWordPackかどうか（UI用）"
    )
    examples_count: dict | None = Field(
        default=None, description="カテゴリごとの例文数（UI用）"
    )
    checked_only_count: int = Field(
        default=0,
        ge=0,
        description="WordPack全体を確認しただけの回数（非負整数）",
    )
    learned_count: int = Field(
        default=0,
        ge=0,
        description="WordPack全体を学習した回数（非負整数）",
    )


class WordPackListResponse(BaseModel):
    """WordPack一覧レスポンス"""

    items: list[WordPackListItem]
    total: int
    limit: int
    offset: int


class StudyProgressRequest(BaseModel):
    kind: Literal["checked", "learned"] = Field(
        description="学習記録の種類: checked=確認のみ / learned=学習完了",
    )


class WordPackStudyProgressResponse(BaseModel):
    checked_only_count: int = Field(
        description="更新後の確認のみカウント",
        ge=0,
    )
    learned_count: int = Field(
        description="更新後の学習済みカウント",
        ge=0,
    )


class ExampleStudyProgressResponse(BaseModel):
    id: int = Field(description="対象の例文ID")
    word_pack_id: str = Field(description="例文が属するWordPack ID")
    checked_only_count: int = Field(
        description="更新後の確認のみカウント",
        ge=0,
    )
    learned_count: int = Field(
        description="更新後の学習済みカウント",
        ge=0,
    )


class WordPackRegenerateRequest(BaseModel):
    """WordPack再生成リクエスト"""

    pronunciation_enabled: bool = True
    regenerate_scope: RegenerateScope = Field(default=RegenerateScope.all)
    model: str | None = Field(
        default=None,
        description="LLMモデル名の上書き（未指定なら既定 settings.llm_model）",
    )
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    reasoning: dict | None = Field(default=None)
    text: dict | None = Field(default=None)
