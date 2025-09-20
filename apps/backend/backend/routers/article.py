from __future__ import annotations

import json
import uuid
from typing import Any, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..config import settings
from ..logging import logger
from ..providers import get_llm_provider
from ..store import store
from ..models.word import WordPack
from ..models.article import (
    ArticleImportRequest,
    ArticleDetailResponse,
    ArticleListItem,
    ArticleListResponse,
    ArticleWordPackLink,
)
from ..observability import request_trace, span
from ..flows.article_import import ArticleImportFlow
from ..models.word import ExampleCategory
from pydantic import BaseModel, Field
from ..flows.category_generate_import import CategoryGenerateAndImportFlow
import anyio
from functools import partial


router = APIRouter(tags=["article"])


def _prompt_for_article_import(text: str) -> str:
    """原文保持・機能語除外の厳格プロンプト。"""
    return (
        """以下の英語テキストが与えられる。出力は次のキーだけを含む JSON に限定し、その他の情報は一切出力しない。
- title_en: 10語以内の非常に短い英語タイトル。
- body_ja: 入力テキストを忠実に訳した日本語（要約や言い換えは禁止）。
- notes_ja: 用法や文脈に焦点を当てた日本語の短い解説（1〜3文）。
- lemmas: 学習価値のある lemma/フレーズのみ（重複禁止）。厳格フィルタ: 機能語（冠詞・助動詞・be 動詞・単純な代名詞・基本的な前置詞/接続詞）や、'I','am','a','the','be','is','are','to','of','and','in','on','for','with','at','by','from','as' などの些末語を除外する。
  学術/専門的な語彙や複数語表現（句動詞・イディオム・コロケーション）を含める。
  目安は 5〜30 件。
重要: 入力テキストを言い換えたり書き換えたりしない。
返却形式: {"title_en", "body_ja", "notes_ja", "lemmas"} のキーだけを含む JSON。
入力テキスト:
""" + text
    )


# 英語の機能語など最低限の除外語（小文字）
_STOP_LEMMAS: set[str] = {
    "a","an","the","i","you","he","she","it","we","they","me","him","her","us","them",
    "my","your","his","her","its","our","their","mine","yours","hers","ours","theirs",
    "am","is","are","was","were","be","been","being","do","does","did","done","doing",
    "have","has","had","having","will","would","shall","should","can","could","may","might","must",
    "to","of","in","on","for","at","by","with","about","as","into","like","through","after","over","between","out","against","during","without","before","under","around","among",
    "and","or","but","if","because","so","than","too","very","not","no","nor","also","then","there","here",
}


def _post_filter_lemmas(raw: list[str]) -> list[str]:
    """LLM抽出結果に対しルールベースで簡易フィルタを適用。"""
    uniq: list[str] = []
    seen: set[str] = set()
    for t in raw:
        s = (t or "").strip()
        if not s:
            continue
        # 句はそのまま（空白を含むものは優先的に残す）
        if " " in s:
            key = s.lower()
            if key not in seen:
                uniq.append(s)
                seen.add(key)
            continue
        # 単語: 英字/ハイフン/アポストロフィのみ許容
        token = s.strip()
        if not all(ch.isalpha() or ch in {'-', '\''} for ch in token):
            continue
        low = token.lower()
        if low in _STOP_LEMMAS:
            continue
        # 極端に短い（2文字以下）は除外（大文字略語2-4文字は許容: AI, ML, NLPなど）
        if len(token) <= 2 and not (token.isupper() and 2 <= len(token) <= 4):
            continue
        key = low
        if key not in seen:
            norm = token if token.isupper() else low
            uniq.append(norm)
            seen.add(key)
    return uniq


@router.post("/import", response_model=ArticleDetailResponse, response_model_exclude_none=True)
async def import_article(req: ArticleImportRequest) -> ArticleDetailResponse:
    flow = ArticleImportFlow()
    # ルータ層は薄く、Langfuse の親スパンを貼ってフローを呼び出す
    from ..observability import request_trace
    with request_trace(name="ArticleImportFlow", metadata={"endpoint": "/api/article/import"}) as ctx:
        tr = ctx.get("trace") if isinstance(ctx, dict) else None  # type: ignore[assignment]
        with span(trace=tr, name="article.flow.run", input={"text_chars": len(req.text or "")}) as _:
            return flow.run(req)


@router.get("/", response_model=ArticleListResponse)
async def list_articles(limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> ArticleListResponse:
    items_raw = store.list_articles(limit=limit, offset=offset)
    items = [ArticleListItem(id=i[0], title_en=i[1], created_at=i[2], updated_at=i[3]) for i in items_raw]
    total = len(store.list_articles(limit=10000, offset=0))
    return ArticleListResponse(items=items, total=total, limit=limit, offset=offset)


# Trailing-slashless alias to avoid 307 redirects in some environments
@router.get("", response_model=ArticleListResponse, include_in_schema=False)
async def list_articles_no_slash(limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> ArticleListResponse:
    return await list_articles(limit=limit, offset=offset)


@router.get("/{article_id}", response_model=ArticleDetailResponse, response_model_exclude_none=True)
async def get_article(article_id: str) -> ArticleDetailResponse:
    result = store.get_article(article_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Article not found")
    title_en, body_en, body_ja, notes_ja, llm_model, llm_params, created_at, updated_at, links = result
    link_models: list[ArticleWordPackLink] = []
    for (wp_id, lemma, status) in links:
        is_empty = True
        try:
            got = store.get_word_pack(wp_id)
            if got is not None:
                _, data_json, _, _ = got
                d = json.loads(data_json)
                senses_empty = not d.get("senses")
                ex = d.get("examples") or {}
                examples_empty = all(not (ex.get(k) or []) for k in ["Dev","CS","LLM","Business","Common"])
                study_empty = not bool((d.get("study_card") or "").strip())
                is_empty = bool(senses_empty and examples_empty and study_empty)
        except Exception:
            is_empty = True
        link_models.append(ArticleWordPackLink(word_pack_id=wp_id, lemma=lemma, status=status, is_empty=is_empty))
    return ArticleDetailResponse(
        id=article_id,
        title_en=title_en,
        body_en=body_en,
        body_ja=body_ja,
        notes_ja=notes_ja,
        llm_model=llm_model,
        llm_params=llm_params,
        related_word_packs=link_models,
        created_at=created_at,
        updated_at=updated_at,
    )


@router.delete("/{article_id}")
async def delete_article(article_id: str) -> dict[str, str]:
    ok = store.delete_article(article_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"message": "Article deleted"}


class CategoryGenerateImportRequest(BaseModel):
    category: ExampleCategory = Field(description="例文カテゴリ")
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    reasoning: dict | None = None
    text: dict | None = None


@router.post("/generate_and_import")
async def generate_and_import_examples(req: CategoryGenerateImportRequest) -> dict[str, object]:
    """選択カテゴリに関連する語を1つ生成し、空のWordPackを作成、
    当該カテゴリの例文を2件生成して保存し、それぞれを文章インポートに渡して記事化する。
    """
    flow = CategoryGenerateAndImportFlow(
        model=getattr(req, "model", None),
        temperature=getattr(req, "temperature", None),
        reasoning=getattr(req, "reasoning", None),
        text=getattr(req, "text", None),
    )
    with request_trace(name="CategoryGenerateAndImportFlow", metadata={"endpoint": "/api/article/generate_and_import"}) as ctx:
        tr = ctx.get("trace") if isinstance(ctx, dict) else None  # type: ignore[assignment]
        with span(trace=tr, name="article.category_generate_and_import", input={"category": req.category.value}):
            # フローは同期実装のため、イベントループをブロックしないようスレッドにオフロード
            result = await anyio.to_thread.run_sync(partial(flow.run, req.category))
            return result


