from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from .word import ExampleCategory


class ArticleImportRequest(BaseModel):
    """文章インポート用リクエスト。

    入力テキストから重要語彙/述語を抽出し、記事（英題/英文化/日本語訳/解説）を生成。
    抽出語について既存の WordPack を関連付け、無ければ空の WordPack を新規作成する。
    """

    text: str = Field(min_length=1, description="インポート対象の文章（日本語/英語いずれも可）")
    # 任意のLLM指定（word endpoints と整合）
    model: Optional[str] = Field(default=None)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    reasoning: Optional[dict] = Field(default=None)
    text_opts: Optional[dict] = Field(default=None)

    model_config = ConfigDict(populate_by_name=True)


class ArticleWordPackLink(BaseModel):
    word_pack_id: str
    lemma: str
    status: str = Field(description="existing|created")
    is_empty: bool = Field(default=False, description="WordPackが空かどうか（UI用）")


class Article(BaseModel):
    title_en: str
    body_en: str
    body_ja: str
    notes_ja: Optional[str] = None
    # LLM 情報（任意）
    llm_model: Optional[str] = None
    llm_params: Optional[str] = None
    related_word_packs: List[ArticleWordPackLink] = Field(default_factory=list)


class ArticleDetailResponse(Article):
    id: str
    created_at: str
    updated_at: str


class ArticleListItem(BaseModel):
    id: str
    title_en: str
    created_at: str
    updated_at: str


class ArticleListResponse(BaseModel):
    items: List[ArticleListItem]
    total: int
    limit: int
    offset: int


