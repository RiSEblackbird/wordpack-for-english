from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .word import ExampleCategory


# インポート文章の文字数上限を統一管理する定数。
# バックエンド/フロントエンド双方のバリデーション要件を同期するため、
# 関連モジュールから再利用できるようモデルモジュールに配置する。
ARTICLE_IMPORT_TEXT_MAX_LENGTH: int = 4000


class ArticleImportRequest(BaseModel):
    """文章インポート用リクエスト。

    入力テキストから重要語彙/述語を抽出し、記事（英題/英文化/日本語訳/解説）を生成。
    抽出語について既存の WordPack を関連付け、無ければ空の WordPack を新規作成する。
    """

    text: str = Field(
        min_length=1,
        max_length=ARTICLE_IMPORT_TEXT_MAX_LENGTH,
        description="インポート対象の文章（日本語/英語いずれも可）",
    )
    # 任意のLLM指定（word endpoints と整合）
    model: str | None = Field(default=None)
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    reasoning: dict | None = Field(default=None)
    text_opts: dict | None = Field(default=None)
    generation_category: ExampleCategory | None = Field(
        default=None,
        description="文章生成時に使用した例文カテゴリ（任意）",
    )

    model_config = ConfigDict(populate_by_name=True)


class ArticleWordPackLink(BaseModel):
    """Linking metadata between an article and a WordPack."""

    word_pack_id: str
    lemma: str
    status: str = Field(description="existing|created")
    is_empty: bool = Field(default=False, description="WordPackが空かどうか（UI用）")


class Article(BaseModel):
    """Article domain model returned by the backend APIs."""

    title_en: str
    body_en: str
    body_ja: str
    notes_ja: str | None = None
    # LLM 情報（任意）
    llm_model: str | None = None
    llm_params: str | None = None
    generation_category: ExampleCategory | None = None
    related_word_packs: list[ArticleWordPackLink] = Field(default_factory=list)
    generation_started_at: str | None = None
    generation_completed_at: str | None = None
    generation_duration_ms: int | None = None


class ArticleDetailResponse(Article):
    """Full article payload including identifiers and timestamps."""

    id: str
    created_at: str
    updated_at: str


class ArticleListItem(BaseModel):
    """Lightweight representation for article list endpoints."""

    id: str
    title_en: str
    created_at: str
    updated_at: str


class ArticleListResponse(BaseModel):
    items: list[ArticleListItem]
    total: int
    limit: int
    offset: int
