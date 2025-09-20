from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict
from datetime import datetime
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
from ..flows.word_pack import WordPackFlow


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
    llm_model: Optional[str]
    llm_params: Optional[str]
    generation_category: Optional[str]
    generation_started_at: Optional[str]
    generation_completed_at: Optional[str]
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

    _BASIC_LEMMAS: set[str] = {
        "about","above","across","action","actually","after","again","against","age","ago","air","all","almost",
        "alone","along","already","always","american","among","another","answer","any","anyone","anything","area",
        "around","ask","away","back","bad","base","because","become","before","begin","behind","believe","best",
        "better","big","black","body","book","both","business","call","called","car","care","case","center",
        "change","child","children","city","class","clear","close","cold","college","come","common","company",
        "country","course","create","day","days","development","different","difficult","direction","door","down",
        "early","education","enough","even","evening","event","ever","every","everyone","everything","example",
        "experience","family","far","father","feel","felt","few","find","first","follow","food","form","friend",
        "friends","front","full","game","general","get","girl","give","given","good","government","great","group",
        "hand","hands","happen","happened","hard","head","health","hear","heard","help","high","history","home",
        "house","idea","important","interest","interesting","issue","job","keep","kind","know","known","large",
        "last","later","learn","least","leave","left","letter","life","like","line","little","local","long",
        "look","lot","love","main","major","make","making","man","many","matter","mean","member","men","might",
        "million","money","month","months","morning","most","mother","move","much","music","name","national",
        "need","never","new","next","night","nothing","number","often","old","once","open","order","other",
        "others","part","people","perhaps","place","plan","play","point","power","present","president","problem",
        "public","question","quite","real","really","reason","receive","research","right","room","run","school",
        "set","several","show","small","someone","something","sometimes","start","state","story","student","study",
        "such","system","take","team","tell","term","thing","think","thought","though","together","today","told",
        "toward","town","try","turn","understand","university","use","used","using","very","want","war","water",
        "week","weeks","while","white","whole","why","woman","women","word","work","world","write","year","years",
        "young",
        # 典型的な挨拶・日常語
        "hello","hi","thanks","thank","please","okay","ok","bye","welcome","sorry","yeah","yep",
        # 曜日・月
        "monday","tuesday","wednesday","thursday","friday","saturday","sunday",
        "january","february","march","april","may","june","july","august","september","october","november","december",
    }

    # ---- 役割別プロンプト（サブグラフ相当） ----
    def _prompt_title(self, text: str) -> str:
        return (
            """入力テキストの内容を忠実に反映した、10語以内の非常に短い英語タイトルを作成する。
制約:
- 簡潔なタイトルに必要な範囲を超えて言い換えない。
- 引用符などを付けず、タイトル本文のみを出力する。
入力:
<INPUT_START>\n""" + text + """\n<INPUT_END>"""
        )

    def _prompt_translation(self, text: str) -> str:
        return (
            """入力された英語テキストを日本語へ忠実に翻訳する。
制約:
- 要約や言い換えを行わない。
- 意味を完全かつ正確に保持する。
出力は翻訳された日本語本文のみ（追加の解説は禁止）。
入力:
<INPUT_START>\n""" + text + """\n<INPUT_END>"""
        )

    def _prompt_explanation(self, text: str) -> str:
        return (
            """入力された英語テキストについて、日本語で 2〜4 文の詳細な解説を書く。
文法分析を最優先し、主要な文構造や時制・相・態の選択理由を明示する。
慣用表現・句動詞・コロケーション・定型表現があれば、そのニュアンスと使用制約を説明する。
専門用語が登場する場合は、文中でどのように機能しているかを簡潔に示す。
大学教育を受けた学習者向けに、指導的で具体的な解説にする。
出力は解説文のみとし、引用符などは付けない。
入力:
<INPUT_START>\n""" + text + """\n<INPUT_END>"""
        )

    def _prompt_lemmas(self, text: str) -> str:
        return (
            """入力英語テキストから、学習価値の高い lemma と複数語表現のみを抽出して列挙する。
厳格フィルタ: 機能語（冠詞・助動詞・be 動詞・単純な代名詞・基本的な前置詞/接続詞）や、I, am, a, the, be, is, are, to, of, and, in, on, for, with, at, by, from, as といった些末語を除外する。
CEFR A1〜A2 の日常語（挨拶・カレンダー/時間語・基本動詞 get/go/make/take など）も除外する。
大学生以上向けの語彙（CEFR B2+）を中心に、洗練された一般学術語（例: resilience, articulate）と専門・技術用語を含める。
高度な用法を示す複数語表現（句動詞・イディオム・コロケーション）も取り入れる。
同じ語が一般語と専門語で並んで現れた場合は、より精密で希少な語を優先しつつ、信頼できる学術語であれば広く使われていても除外しない。
目安は 5〜30 件。
返却形式: 文字列の JSON 配列。例: ["supply chain", "mitigate", "trade-off"]。
入力:
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
            if low in self._BASIC_LEMMAS:
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
        # UI/契約と整合する LLM パラメータ表示用の簡易連結
        def _fmt_llm_params() -> str | None:
            parts: list[str] = []
            try:
                if getattr(req, 'temperature', None) is not None:
                    parts.append(f"temperature={float(req.temperature):.2f}")
                r = getattr(req, 'reasoning', None) or {}
                if isinstance(r, dict) and r.get('effort'):
                    parts.append(f"reasoning.effort={r.get('effort')}")
                t = getattr(req, 'text_opts', None) or {}
                if isinstance(t, dict) and t.get('verbosity'):
                    parts.append(f"text.verbosity={t.get('verbosity')}")
            except Exception:
                pass
            return ";".join(parts) if parts else None

        original_text = req.text.strip()
        selected_llm_model = getattr(req, "model", None) or settings.llm_model
        formatted_llm_params = _fmt_llm_params()
        generation_category = None
        try:
            cat = getattr(req, "generation_category", None)
            if cat:
                generation_category = getattr(cat, "value", None) or str(cat)
        except Exception:
            generation_category = None
        generation_started_at = datetime.utcnow().isoformat()

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
                "llm_model": selected_llm_model,
                "llm_params": formatted_llm_params,
                "generation_category": generation_category,
                "generation_started_at": generation_started_at,
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
                llm_model = str(s.get("llm_model") or "").strip() or None
                llm_params = str(s.get("llm_params") or "").strip() or None
                generation_category_local = str(s.get("generation_category") or "").strip() or None
                started_at = str(s.get("generation_started_at") or "").strip() or None
                completed_at = datetime.utcnow().isoformat()
                s["generation_completed_at"] = completed_at

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
                        llm_model=llm_model,
                        llm_params=llm_params,
                        generation_category=generation_category_local,
                        related_word_packs=[(l.word_pack_id, l.lemma, l.status) for l in s.get("links", [])],
                        created_at=started_at,
                        updated_at=completed_at,
                    )
                    meta = store.get_article(article_id)
                    created_at = meta[7] if meta else ""
                    updated_at = meta[8] if meta else ""
                    if meta and len(meta) >= 9:
                        s["generation_category"] = (meta[6] or generation_category_local)
                        s["generation_started_at"] = created_at or started_at or generation_started_at
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
                if isinstance(s, dict):
                    s.setdefault("llm_model", selected_llm_model)
                    s.setdefault("llm_params", formatted_llm_params)
                    s.setdefault("generation_category", generation_category)
                    s.setdefault("generation_started_at", generation_started_at)
            except Exception:
                # LangGraph が使えない/非互換のときは順次実行
                s = state
                s = _generate_title(s)
                s = _generate_translation(s)
                s = _generate_explanation(s)
                s = _generate_lemmas(s)
                s = _filter_lemmas(s)
                s = _link_or_create_wordpacks(s)
                # LLM 情報を state に反映
                try:
                    s["llm_model"] = getattr(req, 'model', None) or settings.llm_model
                    s["llm_params"] = _fmt_llm_params()
                    s["generation_category"] = generation_category
                    if "generation_started_at" not in s:
                        s["generation_started_at"] = generation_started_at
                except Exception:
                    pass
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
            # LLM 情報を state に反映
            try:
                s["llm_model"] = getattr(req, 'model', None) or settings.llm_model
                s["llm_params"] = _fmt_llm_params()
                s["generation_category"] = generation_category
                if "generation_started_at" not in s:
                    s["generation_started_at"] = generation_started_at
            except Exception:
                pass
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
            title_en, body_en_db, body_ja_db, notes_ja_db, llm_model_db, llm_params_db, generation_category_db, created_at, updated_at, links = got
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
                llm_model=(llm_model_db or None),
                llm_params=(llm_params_db or None),
                generation_category=(generation_category_db or None),
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
