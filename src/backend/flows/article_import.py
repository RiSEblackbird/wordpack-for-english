from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict
import json
import uuid

from ..config import settings
from ..logging import logger
from ..providers import get_llm_provider
from ..store import store
from ..models.word import WordPack
from ..models.article import (
    ArticleImportRequest,
    ArticleDetailResponse,
    ArticleWordPackLink,
)
from . import create_state_graph, StateGraph
from ..observability import span
from fastapi import HTTPException


class _ArticleState(TypedDict, total=False):
    original_text: str
    # 以下は段階的生成の出力を保持する
    lemmas: List[str]
    links: List[ArticleWordPackLink]
    article_id: str
    title_en: str
    body_en: str
    body_ja: str
    notes_ja: Optional[str]
    created_at: str
    updated_at: str


class ArticleImportFlow:
    """Article import AI flow orchestrated with LangGraph.

    入力テキストからタイトル/訳/注釈/lemmas をLLMで抽出し、
    lemmas を WordPack に連携（既存確認/未存在なら空パック作成）した上で
    記事データとして保存する。
    """

    _STOP_LEMMAS: set[str] = {
        "a","an","the","i","you","he","she","it","we","they","me","him","her","us","them",
        "my","your","his","her","its","our","their","mine","yours","hers","ours","theirs",
        "am","is","are","was","were","be","been","being","do","does","did","done","doing",
        "have","has","had","having","will","would","shall","should","can","could","may","might","must",
        "to","of","in","on","for","at","by","with","about","as","into","like","through","after","over","between","out","against","during","without","before","under","around","among",
        "and","or","but","if","because","so","than","too","very","not","no","nor","also","then","there","here",
    }

    # ---- 役割別プロンプト（サブグラフ相当） ----
    def _prompt_title(self, text: str) -> str:
        return (
            """Write a very short English title (<= 10 words) that faithfully reflects the input.
Constraints:
- Do not paraphrase the content beyond what is necessary for a concise title.
- Output only the title text without quotes.
Input:
<INPUT_START>\n""" + text + """\n<INPUT_END>"""
        )

    def _prompt_translation(self, text: str) -> str:
        return (
            """Translate the input English text into Japanese faithfully.
Constraints:
- Do not summarize or paraphrase.
- Keep the meaning accurate and complete.
Output only the translated Japanese text without additional commentary.
Input:
<INPUT_START>\n""" + text + """\n<INPUT_END>"""
        )

    def _prompt_explanation(self, text: str) -> str:
        return (
            """Write a concise Japanese explanation (1-3 sentences) for the input English text.
Focus on usage notes, key terms, or context that helps Japanese learners.
Output only the explanation sentences without quotes.
Input:
<INPUT_START>\n""" + text + """\n<INPUT_END>"""
        )

    def _prompt_lemmas(self, text: str) -> str:
        return (
            """From the input English text, list learning-worthy lemmas and multi-word expressions.
STRICT FILTER: exclude function words (articles, auxiliaries, copulas, simple pronouns, basic prepositions/conjunctions)
and trivial tokens like I, am, a, the, be, is, are, to, of, and, in, on, for, with, at, by, from, as.
Include academic/professional terms and multi-word expressions (phrasal verbs, idioms, collocations).
Aim for ~5-30 items.
Return a JSON array of strings. Example: ["supply chain", "mitigate", "trade-off"].
Input:
<INPUT_START>\n""" + text + """\n<INPUT_END>"""
        )

    def _strip_code_fences(self, text: str) -> str:
        """Remove surrounding Markdown code fences like ```json ... ``` if present.

        入力文字列の前後に存在する Markdown のコードフェンスを取り除く。
        """
        t = str(text or "").strip()
        if t.startswith("```"):
            # 先頭フェンス（言語指定を含む行）を除去
            t2 = t[3:]
            nl = t2.find("\n")
            if nl != -1:
                t2 = t2[nl + 1 :]
            else:
                t2 = t2
            # 末尾フェンスを除去
            if t2.endswith("```"):
                t2 = t2[:-3]
            t = t2.strip()
        return t

    def _post_filter_lemmas(self, raw: List[str]) -> List[str]:
        uniq: list[str] = []
        seen: set[str] = set()
        for t in raw:
            s = (t or "").strip()
            if not s:
                continue
            if " " in s:
                key = s.lower()
                if key not in seen:
                    uniq.append(s)
                    seen.add(key)
                continue
            token = s.strip()
            if not all(ch.isalpha() or ch in {'-', '\''} for ch in token):
                continue
            low = token.lower()
            if low in self._STOP_LEMMAS:
                continue
            if len(token) <= 2 and not (token.isupper() and 2 <= len(token) <= 4):
                continue
            key = low
            if key not in seen:
                norm = token if token.isupper() else low
                uniq.append(norm)
                seen.add(key)
        return uniq

    def run(self, req: ArticleImportRequest) -> ArticleDetailResponse:
        if not req.text or not req.text.strip():
            logger.info("article_import_empty_text")
            raise HTTPException(status_code=400, detail="text is required")

        llm = get_llm_provider(
            model_override=getattr(req, "model", None),
            temperature_override=getattr(req, "temperature", None),
            reasoning_override=getattr(req, "reasoning", None),
            text_override=getattr(req, "text_opts", None),
        )

        original_text = req.text.strip()

        try:
            graph = create_state_graph()
            # 初期 state（段階出力を段階的に埋めていく）
            state: _ArticleState = {
                "original_text": original_text,
                "lemmas": [],
                "links": [],
                "title_en": "",
                "body_en": original_text,
                "body_ja": "",
                "notes_ja": None,
            }
            # 保存済みIDを閉包で保持（LangGraphの差分返却による欠落対策）
            saved_article_id: Optional[str] = None
            # 入力の要点を構造化ログ
            import hashlib as _hf  # local import
            preview = original_text[:120]
            payload = {
                "text_chars": len(original_text),
                "text_preview": preview,
            }
            if original_text:
                try:
                    payload["text_sha256"] = _hf.sha256(original_text.encode("utf-8", errors="ignore")).hexdigest()
                except Exception:
                    pass
            logger.info("article_import_start", **payload)

            # ---- 役割別 生成ノード ----
            def _generate_title(s: _ArticleState) -> _ArticleState:
                # LangGraph の最小スキーマで state から "original_text" が脱落する場合があるため、
                # クロージャの original_text を直接参照する。
                txt = original_text
                pr = self._prompt_title(txt)
                payload = {"prompt_chars": len(pr), "prompt_preview": pr[:200]}
                with span(trace=None, name="article.title.prompt", input=payload):
                    pass
                with span(trace=None, name="article.title.llm", input={"prompt_chars": len(pr)}):
                    out = llm.complete(pr)
                t = str(out or "").strip()
                t = self._strip_code_fences(t)
                # 安全側: 空なら Untitled（UI互換）。ダミー生成ではなく保存時に明示化するだけ。
                s["title_en"] = t or "Untitled"
                logger.info("article_import_title_generated", title_len=len(s["title_en"]))
                return s

            def _generate_translation(s: _ArticleState) -> _ArticleState:
                txt = original_text
                pr = self._prompt_translation(txt)
                with span(trace=None, name="article.translation.prompt", input={"prompt_chars": len(pr)}):
                    pass
                with span(trace=None, name="article.translation.llm", input={"prompt_chars": len(pr)}):
                    out = llm.complete(pr)
                ja = str(out or "").strip()
                ja = self._strip_code_fences(ja)
                s["body_ja"] = ja
                logger.info("article_import_translation_generated", body_ja_chars=len(ja))
                return s

            def _generate_explanation(s: _ArticleState) -> _ArticleState:
                txt = original_text
                pr = self._prompt_explanation(txt)
                with span(trace=None, name="article.explanation.prompt", input={"prompt_chars": len(pr)}):
                    pass
                with span(trace=None, name="article.explanation.llm", input={"prompt_chars": len(pr)}):
                    out = llm.complete(pr)
                note = str(out or "").strip()
                note = self._strip_code_fences(note)
                s["notes_ja"] = note or None
                logger.info("article_import_explanation_generated", notes_ja_chars=len(note or ""))
                return s

            def _parse_lemmas_json(raw: str) -> List[str]:
                try:
                    cleaned = self._strip_code_fences(str(raw))
                    data = json.loads(cleaned)
                    if isinstance(data, list):
                        return [str(x) for x in data]
                    if isinstance(data, dict) and isinstance(data.get("lemmas"), list):
                        return [str(x) for x in data.get("lemmas", [])]
                except Exception as exc:
                    logger.info("article_import_lemmas_json_parse_failed", error=str(exc))
                return []

            def _generate_lemmas(s: _ArticleState) -> _ArticleState:
                txt = original_text
                pr = self._prompt_lemmas(txt)
                with span(trace=None, name="article.lemmas.prompt", input={"prompt_chars": len(pr)}):
                    pass
                with span(trace=None, name="article.lemmas.llm", input={"prompt_chars": len(pr)}):
                    out = llm.complete(pr)
                raw_list = _parse_lemmas_json(str(out or ""))
                s["lemmas"] = raw_list
                logger.info("article_import_lemmas_generated", count=len(raw_list))
                return s

            def _filter_lemmas(s: _ArticleState) -> _ArticleState:
                with span(trace=None, name="article.filter_lemmas"):
                    try:
                        raw_list = [str(x) for x in (s.get("lemmas") or [])]
                        lemmas = self._post_filter_lemmas(raw_list)
                    except Exception:
                        lemmas = []
                s["lemmas"] = lemmas
                logger.info(
                    "article_import_lemmas_filtered",
                    input_count=len((raw_list if 'raw_list' in locals() else [])),
                    output_count=len(lemmas),
                )
                return s

            def _link_or_create_wordpacks(s: _ArticleState) -> _ArticleState:
                lemmas = s.get("lemmas", [])
                links: list[ArticleWordPackLink] = []
                with span(trace=None, name="article.link_or_create_wordpacks", input={"lemma_count": len(lemmas)}):
                    for lemma in lemmas:
                        wp_id = store.find_word_pack_id_by_lemma(lemma)
                        status = "existing"
                        if wp_id is None:
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
                s["links"] = links
                created = sum(1 for l in links if l.status == "created")
                logger.info("article_import_link_or_create_done", total=len(links), created=created, existing=len(links) - created)
                return s

            def _save_article(s: _ArticleState) -> _ArticleState:
                title_en = str(s.get("title_en") or "Untitled").strip() or "Untitled"
                body_en = original_text  # 英語原文はそのまま
                body_ja = str(s.get("body_ja") or "").strip()
                notes_ja = str(s.get("notes_ja") or "").strip() or None

                with span(trace=None, name="article.save_article"):
                    article_id = f"art:{uuid.uuid4().hex[:12]}"
                    # 閉包へも確実に退避
                    nonlocal saved_article_id
                    saved_article_id = article_id
                    store.save_article(
                        article_id,
                        title_en=title_en,
                        body_en=body_en,
                        body_ja=body_ja,
                        notes_ja=notes_ja,
                        related_word_packs=[(l.word_pack_id, l.lemma, l.status) for l in s.get("links", [])],
                    )
                    meta = store.get_article(article_id)
                    created_at = meta[4] if meta else ""
                    updated_at = meta[5] if meta else ""
                s.update({
                    "article_id": article_id,
                    "title_en": title_en,
                    "body_en": body_en,
                    "body_ja": body_ja,
                    "notes_ja": notes_ja,
                    "created_at": created_at,
                    "updated_at": updated_at,
                })
                logger.info(
                    "article_import_saved",
                    article_id=article_id,
                    title_len=len(title_en),
                    body_en_chars=len(body_en),
                    body_ja_chars=len(body_ja),
                    links=len(s.get("links", [])),
                )
                return s

            # ノード登録（役割別サブグラフ風の逐次構成）
            try:
                # StateGraph API 差異に耐える登録
                graph.add_node("generate_title", _generate_title)  # type: ignore[attr-defined]
                graph.add_node("generate_translation", _generate_translation)  # type: ignore[attr-defined]
                graph.add_node("generate_explanation", _generate_explanation)  # type: ignore[attr-defined]
                graph.add_node("generate_lemmas", _generate_lemmas)  # type: ignore[attr-defined]
                graph.add_node("filter_lemmas", _filter_lemmas)  # type: ignore[attr-defined]
                graph.add_node("link_or_create", _link_or_create_wordpacks)  # type: ignore[attr-defined]
                graph.add_node("save_article", _save_article)  # type: ignore[attr-defined]

                graph.set_entry_point("generate_title")  # type: ignore[attr-defined]
                graph.add_edge("generate_title", "generate_translation")  # type: ignore[attr-defined]
                graph.add_edge("generate_translation", "generate_explanation")  # type: ignore[attr-defined]
                graph.add_edge("generate_explanation", "generate_lemmas")  # type: ignore[attr-defined]
                graph.add_edge("generate_lemmas", "filter_lemmas")  # type: ignore[attr-defined]
                graph.add_edge("filter_lemmas", "link_or_create")  # type: ignore[attr-defined]
                graph.add_edge("link_or_create", "save_article")  # type: ignore[attr-defined]

                compiled = graph.compile()  # type: ignore[attr-defined]
                out_state = compiled.invoke(state)  # type: ignore[attr-defined]
                # 差分返却の場合でも初期stateを混ぜて欠落させない。ただし初期stateではなく、out_stateをそのまま優先。
                s = out_state if isinstance(out_state, dict) else state
            except Exception:
                # LangGraph が使えない/非互換のときは順次実行
                s = state
                s = _generate_title(s)
                s = _generate_translation(s)
                s = _generate_explanation(s)
                s = _generate_lemmas(s)
                s = _filter_lemmas(s)
                s = _link_or_create_wordpacks(s)
                s = _save_article(s)
        except Exception:
            # グラフ初期化失敗時の最終フォールバック
            s = _ArticleState(original_text=original_text)
            s = _generate_title(s)  # type: ignore[name-defined]
            s = _generate_translation(s)  # type: ignore[name-defined]
            s = _generate_explanation(s)  # type: ignore[name-defined]
            s = _generate_lemmas(s)  # type: ignore[name-defined]
            s = _filter_lemmas(s)  # type: ignore[name-defined]
            s = _link_or_create_wordpacks(s)  # type: ignore[name-defined]
            s = _save_article(s)  # type: ignore[name-defined]

        # 最終応答は保存済みのDB値を読み直して返す（同期ズレ防止）。失敗時は明確にエラーを返す。
        try:
            # LangGraphの差分返却で state から key が落ちるケースに備え、閉包の saved_article_id を優先
            try:
                aid_local = locals().get("saved_article_id")  # type: ignore[assignment]
            except Exception:
                aid_local = None
            aid = str((aid_local or s.get("article_id") or ""))
            got = store.get_article(aid)
            if got is None:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "message": "Failed to reload article after save",
                        "reason_code": "ARTICLE_DB_RELOAD_NONE",
                        "diagnostics": {"article_id": aid},
                    },
                )
            title_en, body_en_db, body_ja_db, notes_ja_db, created_at, updated_at, links = got
            link_models: list[ArticleWordPackLink] = [
                ArticleWordPackLink(word_pack_id=wp, lemma=lm, status=st, is_empty=True) for (wp, lm, st) in links
            ]
            # is_empty はUI用の推定のため簡易再判定
            try:
                for i, (wp, lm, st) in enumerate(links):
                    is_empty = True
                    try:
                        got_wp = store.get_word_pack(wp)
                        if got_wp is not None:
                            _, data_json, _, _ = got_wp
                            d = json.loads(data_json)
                            senses_empty = not d.get("senses")
                            ex = d.get("examples") or {}
                            examples_empty = all(not (ex.get(k) or []) for k in ["Dev","CS","LLM","Business","Common"]) 
                            study_empty = not bool((d.get("study_card") or "").strip())
                            is_empty = bool(senses_empty and examples_empty and study_empty)
                    except Exception:
                        is_empty = True
                    link_models[i].is_empty = is_empty
            except Exception:
                # is_empty の再計算に失敗しても致命ではない
                pass

            return ArticleDetailResponse(
                id=aid,
                title_en=title_en,
                body_en=body_en_db,
                body_ja=body_ja_db,
                notes_ja=(notes_ja_db or None),
                related_word_packs=link_models,
                created_at=created_at,
                updated_at=updated_at,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Exception while reloading article after save",
                    "reason_code": "ARTICLE_DB_RELOAD_ERROR",
                    "diagnostics": {"error": str(exc), "article_id": str(s.get("article_id") or "")},
                },
            )
