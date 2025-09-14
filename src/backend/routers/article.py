from __future__ import annotations

import json
import uuid
from typing import Any, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..config import settings
from ..logging import logger
from ..providers import get_llm_provider
from ..srs import store
from ..models.word import WordPack
from ..models.article import (
    ArticleImportRequest,
    ArticleDetailResponse,
    ArticleListItem,
    ArticleListResponse,
    ArticleWordPackLink,
)


router = APIRouter(tags=["article"])


def _prompt_for_article_import(text: str) -> str:
    """原文保持・機能語除外の厳格プロンプト。"""
    return (
        """You will receive an English text. Return JSON only with these keys and nothing else.
- title_en: A very short English title (<= 10 words).
- body_ja: Faithful Japanese translation of the input text (do not summarize or paraphrase).
- notes_ja: Short Japanese commentary (1-3 sentences), focusing on usage notes or context.
- lemmas: Learning-worthy lemmas/phrases only (unique). STRICT FILTER: exclude function words
  (articles, auxiliaries, copulas, simple pronouns, basic prepositions/conjunctions) and trivial tokens
  like 'I', 'am', 'a', 'the', 'be', 'is', 'are', 'to', 'of', 'and', 'in', 'on', 'for', 'with', 'at', 'by', 'from', 'as'.
  Include academic/professional terms and multi-word expressions (phrasal verbs, idioms, collocations).
  Aim for ~5-30 items.
IMPORTANT: Do NOT paraphrase or rewrite the input.
Return JSON with keys: {"title_en", "body_ja", "notes_ja", "lemmas"}.
Input text:
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
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    llm = get_llm_provider(
        model_override=getattr(req, "model", None),
        temperature_override=getattr(req, "temperature", None),
        reasoning_override=getattr(req, "reasoning", None),
        text_override=getattr(req, "text_opts", None),
    )
    original_text = req.text.strip()
    prompt = _prompt_for_article_import(original_text)
    out = llm.complete(prompt)
    if not out:
        raise HTTPException(status_code=502, detail="LLM returned empty content")

    # JSON parse
    try:
        data = json.loads(out)
    except Exception as exc:
        logger.info("article_import_json_parse_failed", error=str(exc))
        if settings.strict_mode:
            raise HTTPException(status_code=502, detail="LLM JSON parse failed (strict mode)")
        # 非 strict: 失敗時は最小構造で継続
        data = {"lemmas": []}

    lemmas: List[str] = []
    try:
        raw_list = [str(x) for x in (data.get("lemmas") or [])]
        lemmas = _post_filter_lemmas(raw_list)
    except Exception:
        lemmas = []

    title_en = str(data.get("title_en") or "Untitled").strip() or "Untitled"
    # 英語原文は入力そのものを保持
    body_en = original_text
    body_ja = str(data.get("body_ja") or "").strip()
    notes_ja = str(data.get("notes_ja") or "").strip() or None

    # WordPack 存在確認/作成
    links: list[ArticleWordPackLink] = []
    for lemma in lemmas:
        wp_id = store.find_word_pack_id_by_lemma(lemma)
        status = "existing"
        if wp_id is None:
            # 空のWordPackを作成
            empty_word_pack = WordPack(
                lemma=lemma,
                pronunciation={"ipa_GA": None, "ipa_RP": None, "syllables": None, "stress_index": None, "linking_notes": []},
                senses=[],
                collocations={"general": {"verb_object": [], "adj_noun": [], "prep_noun": []}, "academic": {"verb_object": [], "adj_noun": [], "prep_noun": []}},
                contrast=[],
                examples={"Dev": [], "CS": [], "LLM": [], "Business": [], "Common": []},
                etymology={"note": "-", "confidence": "low"},
                study_card="",
                citations=[],
                confidence="low",
            )
            wp_id = f"wp:{lemma}:{uuid.uuid4().hex[:8]}"
            store.save_word_pack(wp_id, lemma, empty_word_pack.model_dump_json())
            status = "created"
        # 簡易の is_empty 判定
        is_empty = True
        try:
            result = store.get_word_pack(wp_id)
            if result is not None:
                _, data_json, _, _ = result
                d = json.loads(data_json)
                senses_empty = not d.get("senses")
                ex = d.get("examples") or {}
                examples_empty = all(not (ex.get(k) or []) for k in ["Dev","CS","LLM","Business","Common"])
                study_empty = not bool((d.get("study_card") or "").strip())
                is_empty = bool(senses_empty and examples_empty and study_empty)
        except Exception:
            is_empty = True
        links.append(ArticleWordPackLink(word_pack_id=wp_id, lemma=lemma, status=status, is_empty=is_empty))

    # 記事保存
    article_id = f"art:{uuid.uuid4().hex[:12]}"
    store.save_article(
        article_id,
        title_en=title_en,
        body_en=body_en,
        body_ja=body_ja,
        notes_ja=notes_ja,
        related_word_packs=[(l.word_pack_id, l.lemma, l.status) for l in links],
    )
    # 保存後のメタ（作成/更新時刻）を取得
    meta = store.get_article(article_id)
    created_at = meta[4] if meta else ""
    updated_at = meta[5] if meta else ""

    return ArticleDetailResponse(
        id=article_id,
        title_en=title_en,
        body_en=body_en,
        body_ja=body_ja,
        notes_ja=notes_ja,
        related_word_packs=links,
        created_at=created_at,
        updated_at=updated_at,
    )


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
    title_en, body_en, body_ja, notes_ja, created_at, updated_at, links = result
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


