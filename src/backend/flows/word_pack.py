from typing import Any, Dict, List
import json
import re

from . import create_state_graph

# ChromaDB import removed - RAG functionality disabled

from ..models.word import (
    WordPack,
    Sense,
    Collocations,
    CollocationLists,
    Etymology,
    Pronunciation,
    Examples,
    ContrastItem,
    RegenerateScope,
)
from ..models.common import ConfidenceLevel, Citation
from ..pronunciation import generate_pronunciation
from ..logging import logger
from ..config import settings
# RAG imports removed - functionality disabled


class WordPackFlow:
    """Word pack generation flow (no dummy outputs).

    単語学習パックを生成するフロー。ダミー生成は行わず、取得できない情報は
    可能な限り空（未設定）で返す。RAG が有効かつ引用が得られない場合は、
    strict モードではエラーを送出する。
    """

    def __init__(self, chroma_client: Any | None = None, *, llm: Any | None = None) -> None:
        """ベクトルDB クライアントを受け取り、LangGraph を初期化。

        Parameters
        ----------
        chroma_client: Any | None
            語義・共起取得などの検索に利用するクライアント（任意）。
        """
        self.chroma = chroma_client
        self.llm = llm
        self.graph = create_state_graph()

    # --- 発音推定（cmudict/g2p-en 利用、フォールバック付き） ---
    def _generate_pronunciation(self, lemma: str) -> Pronunciation:
        return generate_pronunciation(lemma)

    def _retrieve(self, lemma: str) -> Dict[str, Any]:
        """語の情報を取得。OpenAI LLM を使用してセクション別のJSONを生成・解析。"""
        citations: List[Citation] = []
        llm_data: Dict[str, Any] | None = None

        def _strip_code_fences(text: str) -> str:
            t = text.strip()
            # ```json ... ``` を除去
            t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
            t = re.sub(r"```\s*$", "", t)
            # 先頭の最初の { から末尾の最後の } までを抜き出し
            m1 = t.find("{")
            m2 = t.rfind("}")
            if m1 != -1 and m2 != -1 and m2 > m1:
                return t[m1 : m2 + 1]
            return t

        # OpenAI LLM を使用して語の詳細情報を生成
        try:
            if self.llm is not None and hasattr(self.llm, "complete"):
                prompt = (
                    "You are a lexicographer. Return ONLY one JSON object, no prose.\n"
                    "Target word: "
                    f"{lemma}\n\n"
                    "Schema (keys and types must match exactly):\n"
                    "{\n"
                    "  \"senses\": [ { \"id\": \"s1\", \"gloss_ja\": \"...\", \"patterns\": [\"...\"] } ],\n"
                    "  \"collocations\": {\n"
                    "    \"general\": { \"verb_object\": [\"...\"], \"adj_noun\": [\"...\"], \"prep_noun\": [\"...\"] },\n"
                    "    \"academic\": { \"verb_object\": [\"...\"], \"adj_noun\": [\"...\"], \"prep_noun\": [\"...\"] }\n"
                    "  },\n"
                    "  \"contrast\": [ { \"with\": \"...\", \"diff_ja\": \"...\" } ],\n"
                    "  \"examples\": {\n"
                    "    \"A1\": [ { \"en\": \"...\", \"ja\": \"...\" } ],\n"
                    "    \"B1\": [ { \"en\": \"...\", \"ja\": \"...\" } ],\n"
                    "    \"C1\": [ { \"en\": \"...\", \"ja\": \"...\" } ],\n"
                    "    \"tech\": [ { \"en\": \"...\", \"ja\": \"...\" } ]\n"
                    "  },\n"
                    "  \"etymology\": { \"note\": \"...\", \"confidence\": \"low|medium|high\" },\n"
                    "  \"study_card\": \"1文の要点(日本語)\",\n"
                    "  \"pronunciation\": { \"ipa_RP\": \"/.../\" }\n"
                    "}\n"
                    "Notes: \n- gloss_ja は日本語。\n- 例文は自然で簡潔に。\n- 配列は重複・空文字を避ける。\n"
                )

                out = self.llm.complete(prompt)  # type: ignore[attr-defined]
                if isinstance(out, str) and out.strip():
                    raw = _strip_code_fences(out)
                    try:
                        llm_data = json.loads(raw)
                        citations.append(
                            Citation(
                                text=f"LLM-generated information for {lemma}",
                                meta={"source": "openai_llm", "word": lemma},
                            )
                        )
                    except json.JSONDecodeError:
                        citations.append(Citation(text=out.strip(), meta={"source": "openai_llm", "word": lemma}))
        except Exception:
            if settings.strict_mode:
                raise
            # 非 strict では静かにフォールバック

        return {"lemma": lemma, "citations": citations, "llm_data": llm_data}

    def _synthesize(
        self,
        lemma: str,
        *,
        pronunciation_enabled: bool = True,
        regenerate_scope: RegenerateScope | str = RegenerateScope.all,
        citations: List[Citation] | None = None,
    ) -> WordPack:
        """取得結果を整形し `WordPack` を構成。OpenAI LLM の情報を使用。"""
        pronunciation = (
            self._generate_pronunciation(lemma)
            if pronunciation_enabled
            else Pronunciation(ipa_GA=None, ipa_RP=None, syllables=None, stress_index=None, linking_notes=[])
        )
        
        # 初期値
        senses: List[Sense] = []
        collocations = Collocations()
        examples = Examples()
        etymology = Etymology(note="", confidence=ConfidenceLevel.low)
        study_card = ""
        
        # citations からは信頼度判断のみ。構造化は llm_data を優先
        confidence = ConfidenceLevel.low
        if citations:
            confidence = ConfidenceLevel.medium

        # 直近の _retrieve の結果を graph/state 経由ではなく run から受け取れないため、
        # 呼び出し側で渡される citations のみを基準にしつつ、RP は LLM データに含まれる場合だけ上書き
        # 呼び出し元から llm_data は直接渡していないので、_retrieve の戻りを run 経由で受けるよう run を拡張
        # このメソッドは run から適切に llm_data を渡されることを前提とする（後段で run を修正）。
        # 型: citations 引数はそのまま使用。

        # 既存引数に llm_data を追加できないため、暫定として self に一時格納された値を見る
        llm_payload: Dict[str, Any] | None = getattr(self, "_last_llm_data", None)

        if isinstance(llm_payload, dict):
            # senses
            try:
                s_list = llm_payload.get("senses") or []
                tmp_senses: List[Sense] = []
                for idx, s in enumerate(s_list):
                    if not isinstance(s, dict):
                        continue
                    gid = str(s.get("id") or f"s{idx+1}")
                    gloss_ja = str(s.get("gloss_ja") or "").strip()
                    if not gloss_ja:
                        continue
                    patterns = [str(p) for p in (s.get("patterns") or []) if str(p).strip()]
                    register = s.get("register")
                    tmp_senses.append(Sense(id=gid, gloss_ja=gloss_ja, patterns=patterns, register=register))
                if tmp_senses:
                    senses = tmp_senses
                    confidence = ConfidenceLevel.high
            except Exception:
                pass

            # collocations
            try:
                col = llm_payload.get("collocations") or {}
                def _lists(src: Dict[str, Any]) -> CollocationLists:
                    return CollocationLists(
                        verb_object=[str(x) for x in (src.get("verb_object") or []) if str(x).strip()],
                        adj_noun=[str(x) for x in (src.get("adj_noun") or []) if str(x).strip()],
                        prep_noun=[str(x) for x in (src.get("prep_noun") or []) if str(x).strip()],
                    )
                collocations = Collocations(
                    general=_lists(col.get("general") or {}),
                    academic=_lists(col.get("academic") or {}),
                )
            except Exception:
                pass

            # contrast
            contrast_items: List[ContrastItem] = []
            try:
                for it in (llm_payload.get("contrast") or []):
                    if isinstance(it, dict):
                        w = str(it.get("with") or "").strip()
                        d = str(it.get("diff_ja") or "").strip()
                        if w and d:
                            contrast_items.append(ContrastItem(with_=w, diff_ja=d))
            except Exception:
                pass

            # examples
            try:
                ex = llm_payload.get("examples") or {}
                def _ex_list(v: Any) -> List[Examples.ExampleItem]:  # type: ignore[attr-defined]
                    out: List[Examples.ExampleItem] = []  # type: ignore[name-defined]
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict):
                                en = str(item.get("en") or "").strip()
                                ja = str(item.get("ja") or "").strip()
                                if en and ja:
                                    out.append(Examples.ExampleItem(en=en, ja=ja))  # type: ignore[attr-defined]
                    return out
                examples = Examples(
                    A1=_ex_list(ex.get("A1")),
                    B1=_ex_list(ex.get("B1")),
                    C1=_ex_list(ex.get("C1")),
                    tech=_ex_list(ex.get("tech")),
                )
            except Exception:
                pass

            # etymology
            try:
                ety = llm_payload.get("etymology") or {}
                note = str(ety.get("note") or "").strip()
                conf = str(ety.get("confidence") or "low").strip().lower()
                cl = ConfidenceLevel.low
                if conf in {"medium", "med"}:
                    cl = ConfidenceLevel.medium
                elif conf in {"high", "hi"}:
                    cl = ConfidenceLevel.high
                etymology = Etymology(note=note, confidence=cl)
            except Exception:
                pass

            # study_card
            try:
                sc = str(llm_payload.get("study_card") or "").strip()
                if sc:
                    study_card = sc
            except Exception:
                pass

            # pronunciation (RP only; GA は内部生成を使用)
            try:
                pr = llm_payload.get("pronunciation") or {}
                rp = str(pr.get("ipa_RP") or "").strip()
                if rp:
                    pronunciation.ipa_RP = rp
            except Exception:
                pass
        
        pack = WordPack(
            lemma=lemma,
            pronunciation=pronunciation,
            senses=senses,
            collocations=collocations,
            contrast=contrast_items if 'contrast_items' in locals() else [],
            examples=examples,
            etymology=etymology,
            study_card=study_card,
            citations=citations or [],
            confidence=confidence,
        )
        return pack

    def run(self, lemma: str, *, pronunciation_enabled: bool = True, regenerate_scope: RegenerateScope | str = RegenerateScope.all) -> WordPack:
        """語を入力として `WordPack` を生成して返す（ダミー生成なし）。"""
        data = self._retrieve(lemma)
        # 後続の _synthesize で LLM 生成物を参照できるように一時保存
        self._last_llm_data = data.get("llm_data")
        return self._synthesize(
            lemma,
            pronunciation_enabled=pronunciation_enabled,
            regenerate_scope=regenerate_scope,
            citations=data.get("citations"),
        )
