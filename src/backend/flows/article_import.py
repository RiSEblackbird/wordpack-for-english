from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict
import json
import uuid

from ..config import settings
from ..logging import logger
from ..providers import get_llm_provider
from ..srs import store
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
    prompt: str
    llm_output: str
    parsed: Dict[str, Any]
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

    def _prompt_for_article_import(self, text: str) -> str:
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
Use the exact text inside the following markers as the input. Do not claim it is empty.
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
            # 明示的スキーマに合わせた初期 state を作る
            state: _ArticleState = {
                "original_text": original_text,
                "prompt": "",
                "llm_output": "",
                "parsed": {},
                "lemmas": [],
                "links": [],
            }
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

            def _build_prompt(s: _ArticleState) -> _ArticleState:
                txt = str(s.get("original_text") or "")
                pr = self._prompt_for_article_import(txt)
                try:
                    if getattr(settings, "langfuse_log_full_prompt", False):
                        payload = {"prompt_chars": len(pr), "prompt": pr[: int(getattr(settings, "langfuse_prompt_max_chars", 40000))]}
                    else:
                        payload = {"prompt_chars": len(pr), "prompt_preview": pr[:500]}
                except Exception:
                    payload = {"prompt_chars": len(pr)}
                with span(trace=None, name="article.build_prompt", input=payload):
                    s["prompt"] = pr
                # 生成したプロンプトのメタをログ
                try:
                    import hashlib as _hf2
                    logger.info(
                        "article_import_prompt_built",
                        prompt_chars=len(pr),
                        prompt_sha256=_hf2.sha256(pr.encode("utf-8", errors="ignore")).hexdigest(),
                    )
                except Exception:
                    logger.info("article_import_prompt_built", prompt_chars=len(pr))
                return s

            def _llm_call(s: _ArticleState) -> _ArticleState:
                pr = s.get("prompt") or ""
                if not pr:
                    # スキーマ保全の観点で、ここで再計算するのではなくエラーにする
                    raise HTTPException(status_code=500, detail="prompt missing before LLM call (graph state loss)")
                logger.info("article_import_llm_call", prompt_chars=len(pr))
                with span(trace=None, name="article.llm.complete", input={"prompt_chars": len(pr)}):
                    out = llm.complete(pr)
                if not out:
                    raise HTTPException(status_code=502, detail="LLM returned empty content")
                s["llm_output"] = out
                logger.info(
                    "article_import_llm_result",
                    content_chars=len(out or ""),
                    starts_with_brace=str(out).lstrip().startswith("{"),
                )
                return s

            def _parse_json(s: _ArticleState) -> _ArticleState:
                raw = s.get("llm_output")
                with span(trace=None, name="article.parse_json", input={"output_chars": len(str(raw) or "")}):
                    try:
                        cleaned = self._strip_code_fences(str(raw))
                        data = json.loads(cleaned)
                    except Exception as exc:
                        logger.info("article_import_json_parse_failed", error=str(exc))
                        # LLM出力がJSONでない場合は保存せずにエラー応答（非strictでも）
                        raise HTTPException(status_code=502, detail="LLM JSON parse failed")
                s["parsed"] = data
                try:
                    keys = list(data.keys())[:10] if isinstance(data, dict) else []
                    lem_ct = len((data or {}).get("lemmas", [])) if isinstance(data, dict) else 0
                    logger.info("article_import_parsed", keys=keys, lemmas_in_json=lem_ct)
                except Exception:
                    pass
                # 検証: 本文とlemmasが共に空ならエラーにする（保存しない）
                try:
                    if not isinstance(data, dict):
                        raise HTTPException(status_code=502, detail="LLM JSON is not an object")
                    body_ja_text = str((data or {}).get("body_ja", ""))
                    body_ja_nonempty = bool(body_ja_text.strip())
                    lem_list = (data or {}).get("lemmas") or []
                    if not isinstance(lem_list, list):
                        lem_list = []
                    lem_ct2 = len(lem_list)
                    if not body_ja_nonempty and lem_ct2 == 0:
                        logger.info("article_import_validation_failed", reason="empty_body_ja_and_lemmas")
                        raise HTTPException(status_code=502, detail="LLM returned empty translation and lemmas")
                except Exception:
                    pass
                return s

            def _filter_lemmas(s: _ArticleState) -> _ArticleState:
                data = s.get("parsed", {})
                with span(trace=None, name="article.filter_lemmas"):
                    try:
                        raw_list = [str(x) for x in (data.get("lemmas") or [])]  # type: ignore[assignment]
                        lemmas = self._post_filter_lemmas(raw_list)
                    except Exception:
                        lemmas = []
                s["lemmas"] = lemmas
                logger.info(
                    "article_import_lemmas_filtered",
                    input_count=len((data or {}).get("lemmas", [])) if isinstance(data, dict) else 0,
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
                data = s.get("parsed", {})
                title_en = str(data.get("title_en") or "Untitled").strip() or "Untitled"
                # original_text は LangGraph の最終stateで脱落する場合があるため外側の値を直接採用
                body_en = original_text
                body_ja = str(data.get("body_ja") or "").strip()
                notes_ja = str(data.get("notes_ja") or "").strip() or None

                with span(trace=None, name="article.save_article"):
                    article_id = f"art:{uuid.uuid4().hex[:12]}"
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

            # ノード登録
            try:
                # StateGraph API 差異に耐える登録
                graph.add_node("build_prompt", _build_prompt)  # type: ignore[attr-defined]
                graph.add_node("llm_call", _llm_call)  # type: ignore[attr-defined]
                graph.add_node("parse_json", _parse_json)  # type: ignore[attr-defined]
                graph.add_node("filter_lemmas", _filter_lemmas)  # type: ignore[attr-defined]
                graph.add_node("link_or_create", _link_or_create_wordpacks)  # type: ignore[attr-defined]
                graph.add_node("save_article", _save_article)  # type: ignore[attr-defined]

                graph.set_entry_point("build_prompt")  # type: ignore[attr-defined]
                graph.add_edge("build_prompt", "llm_call")  # type: ignore[attr-defined]
                graph.add_edge("llm_call", "parse_json")  # type: ignore[attr-defined]
                graph.add_edge("parse_json", "filter_lemmas")  # type: ignore[attr-defined]
                graph.add_edge("filter_lemmas", "link_or_create")  # type: ignore[attr-defined]
                graph.add_edge("link_or_create", "save_article")  # type: ignore[attr-defined]

                compiled = graph.compile()  # type: ignore[attr-defined]
                out_state = compiled.invoke(state)  # type: ignore[attr-defined]
                # LangGraph 実装差で差分のみ返るケースに備え、初期 state をマージ
                if isinstance(out_state, dict):
                    merged: _ArticleState = {**state, **out_state}  # type: ignore[misc]
                    s = merged
                else:
                    s = state
            except Exception:
                # LangGraph が使えない/非互換のときは順次実行
                s = state
                s = _build_prompt(s)
                s = _llm_call(s)
                s = _parse_json(s)
                s = _filter_lemmas(s)
                s = _link_or_create_wordpacks(s)
                s = _save_article(s)
        except Exception:
            # グラフ初期化失敗時の最終フォールバック
            s = _ArticleState(original_text=original_text)
            s = _build_prompt(s)  # type: ignore[name-defined]
            s = _llm_call(s)  # type: ignore[name-defined]
            s = _parse_json(s)  # type: ignore[name-defined]
            s = _filter_lemmas(s)  # type: ignore[name-defined]
            s = _link_or_create_wordpacks(s)  # type: ignore[name-defined]
            s = _save_article(s)  # type: ignore[name-defined]

        return ArticleDetailResponse(
            id=str(s.get("article_id")),
            title_en=str(s.get("title_en") or "Untitled"),
            body_en=str(s.get("body_en") or ""),
            body_ja=str(s.get("body_ja") or ""),
            notes_ja=s.get("notes_ja"),
            related_word_packs=s.get("links", []),
            created_at=str(s.get("created_at") or ""),
            updated_at=str(s.get("updated_at") or ""),
        )
