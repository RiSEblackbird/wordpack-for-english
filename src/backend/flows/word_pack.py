from typing import Any, Dict, List, Optional
import json
import re

from . import create_state_graph

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
    ExampleCategory,
)
from ..models.common import ConfidenceLevel, Citation
from ..pronunciation import generate_pronunciation
from ..logging import logger
from ..config import settings


# --- 例文生成プロンプト: Notes 分割（共通/カテゴリ別） ---
def _examples_common_notes_text() -> str:
    """カテゴリ共通の Notes。カテゴリ固有の規定は含めない。"""
    return (
        "Notes: \n"
        "- gloss_ja / definition_ja / nuances_ja / grammar_ja / notes_ja は日本語。\n"
        "- もし対象語が名詞（一般名詞/固有名詞）や専門用語である場合、\n"
        "  term_overview_ja（3〜5文の概要）と term_core_ja（3〜5文の本質）を必ず日本語で記述する。\n"
        "  名詞以外（動詞/形容詞など）の場合、これら2つのキーは省略してよい。\n"
        "- 例文は自然で、約55語（±5語）の英文にする。各英例文には必ず対象語（lemma）を含める。\n"
        "- 本リクエストでは Target category のみを生成し、件数は末尾の Override 指示に厳密に従う。\n"
        "- 各例文の grammar_ja は2段落の詳細解説にする：\n"
        "  1) 品詞分解：形態素/句を『／』で区切り、語の後に【品詞/統語役割】を付す。必要に応じて句の内部構造も『＝』で示す（例：I【代/主】／sent【動/過去】／the documents【名/目】／via email【前置詞句＝via(前)+email(名)：手段】／to ensure quick delivery【不定詞句＝to+ensure(動)+quick(形)+delivery(名)：目的】）。\n"
        "  2) 解説：文の核（S/V/O/C）、修飾関係（手段/目的/時/理由など）、冠詞・可算/不可算の扱い等を日本語で簡潔に説明。\n"
        "- 『動詞+前置詞』のような表層的ラベルだけの説明は禁止。具体的に機能・役割まで述べる。\n"
    )

def _examples_category_notes_text(category: ExampleCategory) -> str:
    """カテゴリ固有の Notes（対象カテゴリのみに適用）。"""
    base_map: dict[ExampleCategory, str] = {
        ExampleCategory.Dev: (
            "カテゴリ別ガイドライン（Target のみに適用）：\n"
            "- Dev: ソフトウェア開発の文脈。実務的で具体、学術調は避ける。\n"
        ),
        ExampleCategory.CS: (
            "カテゴリ別ガイドライン（Target のみに適用）：\n"
            "- CS: 計算機科学の学術文脈。精密・中立・フォーマル。\n"
        ),
        ExampleCategory.LLM: (
            "カテゴリ別ガイドライン（Target のみに適用）：\n"
            "- LLM: 機械学習/LLM 文脈。用語は技術的/学術的に正確、マーケ調は避ける。\n"
        ),
        ExampleCategory.Business: (
            "カテゴリ別ガイドライン（Target のみに適用）：\n"
            "- Business: ビジネス文脈（関係者/指標/KPI/スケジュール/トレードオフ/調整/戦略/財務/マーケティング）。丁寧で簡潔、スラング禁止。\n"
        ),
        ExampleCategory.Common: (
            "カテゴリ別ガイドライン（Target のみに適用）：\n"
            "- Common: 日常会話（友人/同僚とのチャット・通話/待ち合わせ/日常の小さな出来事/小さなやり取り）。ビジネス/過度なフォーマル語彙は避け、軽い口語を適度に用いる（下品表現は不可）。\n"
        ),
    }
    extra_common: str = (
        "- Common の英例文は“ビジネス英語ではなく”カジュアルな日常会話のトーンで。友達/家族/同僚との軽いチャット想定。丁寧すぎる表現やフォーマルな語彙（therefore, thus, regarding, via など）は避け、口語（gonna, kinda, hey などは過度に使いすぎない範囲で可）、よくあるシーン（メッセ/通話/待ち合わせ/日常の小さな出来事）を取り入れる。\n"
        "- Common は短い感嘆や相づち・依頼も自然に含めてよい（e.g., Could you shoot me a text?, Mind sending me the link?）。ただしスラングや下品な表現は避ける。\n"
    )
    text = base_map.get(category, "")
    if category is ExampleCategory.Common:
        text += extra_common
    return text


class WordPackFlow:
    """Word pack generation flow (no dummy outputs).

    単語学習パックを生成するフロー。ダミー生成は行わず、取得できない情報は
    可能な限り空（未設定）で返す。strict モードでは不正な生成結果はエラーを送出する。
    """

    def __init__(self, chroma_client: Any | None = None, *, llm: Any | None = None, llm_info: Optional[dict[str, Any]] = None) -> None:
        """ベクトルDB クライアントを受け取り、LangGraph を初期化。

        Parameters
        ----------
        chroma_client: Any | None
            語義・共起取得などの検索に利用するクライアント（任意）。
        """
        self.chroma = chroma_client
        self.llm = llm
        # 生成に使用した LLM のメタ（モデル名やパラメータ文字列表現）
        self._llm_info: dict[str, Any] = llm_info or {}
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
                logger.info("wordpack_llm_prompt_built", lemma=lemma)
                prompt = (
                    "You are a lexicographer. Return ONLY one JSON object, no prose.\n"
                    "Target word: "
                    f"{lemma}\n\n"
                    "Schema (keys and types must match exactly):\n"
                    "{\n"
                    "  \"senses\": [ { \"id\": \"s1\", \"gloss_ja\": \"...\", \"definition_ja\": \"...\", \"nuances_ja\": \"...\", \"patterns\": [\"...\"], \"synonyms\": [\"...\"], \"antonyms\": [\"...\"], \"register\": \"...\", \"notes_ja\": \"...\", \"term_overview_ja\": \"...\", \"term_core_ja\": \"...\" } ],\n"
                    "  \"collocations\": {\n"
                    "    \"general\": { \"verb_object\": [\"...\"], \"adj_noun\": [\"...\"], \"prep_noun\": [\"...\"] },\n"
                    "    \"academic\": { \"verb_object\": [\"...\"], \"adj_noun\": [\"...\"], \"prep_noun\": [\"...\"] }\n"
                    "  },\n"
                    "  \"contrast\": [ { \"with\": \"...\", \"diff_ja\": \"...\" } ],\n"
                    "  \"etymology\": { \"note\": \"...\", \"confidence\": \"low|medium|high\" },\n"
                    "  \"study_card\": \"1文の要点(日本語)\",\n"
                    "  \"pronunciation\": { \"ipa_RP\": \"/.../\" }\n"
                    "}\n"
                    "Notes: \n"
                    "- gloss_ja / definition_ja / nuances_ja / notes_ja は日本語。\n"
                    "- もし対象語が名詞（一般名詞/固有名詞）や専門用語である場合、\n"
                    "  term_overview_ja（3〜5文の概要）と term_core_ja（3〜5文の本質）を必ず日本語で記述する。\n"
                    "  名詞以外（動詞/形容詞など）の場合、これら2つのキーは省略してよい。\n"
                )

                out = self.llm.complete(prompt)  # type: ignore[attr-defined]
                logger.info("wordpack_llm_output_received", lemma=lemma, output_chars=len(out or ""))
                if isinstance(out, str) and out.strip():
                    raw = _strip_code_fences(out)
                    try:
                        llm_data = json.loads(raw)
                        logger.info(
                            "wordpack_llm_json_parsed",
                            lemma=lemma,
                            has_senses=isinstance(llm_data.get("senses"), list),
                        )
                        citations.append(
                            Citation(
                                text=f"LLM-generated information for {lemma}",
                                meta={"source": "openai_llm", "word": lemma},
                            )
                        )
                    except json.JSONDecodeError:
                        logger.info("wordpack_llm_json_parse_failed", lemma=lemma)
                        citations.append(Citation(text=out.strip(), meta={"source": "openai_llm", "word": lemma}))
                        if settings.strict_mode:
                            raise RuntimeError("Failed to parse LLM JSON in strict mode")
        except Exception as exc:
            if settings.strict_mode:
                # strict: LLM 呼び出し失敗/タイムアウトは即エラー
                raise
            # 非 strict では静かにフォールバック

        # strict: LLM 出力が空/未解析ならエラー
        if settings.strict_mode and (
            llm_data is None or (isinstance(llm_data, dict) and not llm_data.get("senses"))
        ):
            raise RuntimeError("LLM returned no usable data (strict mode)")

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
        logger.info("wordpack_synthesize_start", lemma=lemma)
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
        # LLMが使用されている場合は最低でもmedium
        if self.llm is not None and hasattr(self.llm, "complete"):
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
                    definition_ja = str(s.get("definition_ja") or "").strip() or None
                    nuances_ja = str(s.get("nuances_ja") or "").strip() or None
                    synonyms = [str(x) for x in (s.get("synonyms") or []) if str(x).strip()]
                    antonyms = [str(x) for x in (s.get("antonyms") or []) if str(x).strip()]
                    notes_ja = str(s.get("notes_ja") or "").strip() or None
                    tmp_senses.append(Sense(
                        id=gid,
                        gloss_ja=gloss_ja,
                        definition_ja=definition_ja,
                        nuances_ja=nuances_ja,
                        patterns=patterns,
                        synonyms=synonyms,
                        antonyms=antonyms,
                        register=register,
                        notes_ja=notes_ja,
                        term_overview_ja=(str(s.get("term_overview_ja") or "").strip() or None),
                        term_core_ja=(str(s.get("term_core_ja") or "").strip() or None),
                    ))
                if tmp_senses:
                    senses = tmp_senses
                    confidence = ConfidenceLevel.high
                logger.info("wordpack_senses_built", lemma=lemma, senses_count=len(senses))
            except Exception:
                logger.info("wordpack_senses_build_error", lemma=lemma)
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

            # examples: 初期生成でも追加生成でも同一のプロンプト/処理系を使う
            try:
                # デフォルト計画（将来の拡張に備えて集中管理）
                plan: dict[ExampleCategory, int] = {
                    ExampleCategory.Dev: 2,
                    ExampleCategory.CS: 2,
                    ExampleCategory.LLM: 2,
                    ExampleCategory.Business: 2,
                    ExampleCategory.Common: 2,
                }
                gen = self.generate_examples_for_categories(lemma, plan)
                examples = Examples(
                    Dev=gen.get(ExampleCategory.Dev, []),
                    CS=gen.get(ExampleCategory.CS, []),
                    LLM=gen.get(ExampleCategory.LLM, []),
                    Business=gen.get(ExampleCategory.Business, []),
                    Common=gen.get(ExampleCategory.Common, []),
                )
                logger.info(
                    "wordpack_examples_built_unified",
                    lemma=lemma,
                    Dev=len(examples.Dev),
                    CS=len(examples.CS),
                    LLM=len(examples.LLM),
                    Business=len(examples.Business),
                    Common=len(examples.Common),
                )
            except Exception as exc:
                # 統合フローのみを使用（旧ロジックのサルベージは廃止）
                logger.info("wordpack_examples_build_error_unified", lemma=lemma, error=str(exc))
                examples = Examples()

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
        logger.info(
            "wordpack_synthesize_done",
            lemma=lemma,
            senses_count=len(pack.senses),
            examples_total=(
                len(pack.examples.Dev)
                + len(pack.examples.CS)
                + len(pack.examples.LLM)
                + len(pack.examples.Business)
                + len(pack.examples.Common)
            ),
            has_definition_any=any(bool(s.definition_ja) for s in pack.senses),
        )
        # 厳格モードでは、語義と例文がともにゼロの場合はエラーとして扱う（ダミーを返さない）
        try:
            from ..config import settings as _settings  # 局所importで循環回避
        except Exception:
            _settings = None  # type: ignore[assignment]
        if _settings and getattr(_settings, "strict_mode", False):
            total_examples = (
                len(pack.examples.Dev)
                + len(pack.examples.CS)
                + len(pack.examples.LLM)
                + len(pack.examples.Business)
                + len(pack.examples.Common)
            )
            if len(pack.senses) == 0 and total_examples == 0:
                # 例外クラスをローカル定義（ルータ側で詳細HTTPにマップ）
                class WordPackGenerationError(RuntimeError):
                    def __init__(self, message: str, *, reason_code: str, diagnostics: dict[str, object]):
                        super().__init__(message)
                        self.reason_code = reason_code
                        self.diagnostics = diagnostics

                raise WordPackGenerationError(
                    "No senses or examples generated",
                    reason_code="EMPTY_CONTENT",
                    diagnostics={
                        "lemma": lemma,
                        "senses_count": 0,
                        "examples_counts": {
                            "Dev": len(examples.Dev),
                            "CS": len(examples.CS),
                            "LLM": len(examples.LLM),
                            "Business": len(examples.Business),
                            "Common": len(examples.Common),
                        },
                    },
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

    # --- Unified examples generation (initial/additional) ---
    def _build_examples_prompt(self, lemma: str, category: ExampleCategory, count: int) -> str:
        """添付プロンプト（正）をパーツ化し、例文のみを要求するプロンプトを構築する。

        - 本文の英語ヘッダと Notes/ガイドラインは原型を維持
        - 例文スキーマは examples 配列のみ
        - 件数は既定の記述を尊重しつつ、最後に count 件のオーバーライド制約を追加
        """
        # 英語ヘッダ＋スキーマの枠は "正" の冒頭に揃える
        header = (
            "You are a lexicographer. Return ONLY one JSON object, no prose.\n"
            "Target word: "
            f"{lemma}\n\n"
            "Schema (keys and types must match exactly):\n"
            "{\n"
            "  \"examples\": [ { \"en\": \"...\", \"ja\": \"...\", \"grammar_ja\": \"...\" } ]\n"
            "}\n"
        )

        # Notes を共通とカテゴリ別に分割
        notes_common = _examples_common_notes_text()
        category_notes = _examples_category_notes_text(category)
        enforce = "Apply these category-specific rules to the Target category only.\n"

        # カテゴリを明示し、このリクエストでは当該カテゴリのみ生成する旨を指定
        # 件数は最後に厳密指定（正の文言は保持しつつ上書き制約）
        tail = (
            f"Target category: {category.value}\n"
            "Return strictly one JSON object. No prose. No code fences.\n"
            f"Override: examples must be exactly {count} items.\n"
        )

        prompt = header + notes_common + category_notes + enforce + tail
        # プロンプト長だけをログ（全文は Langfuse オプションで別途制御）
        try:
            logger.info(
                "wordpack_examples_prompt_built",
                lemma=lemma,
                category=category.value,
                count=count,
                prompt_chars=len(prompt),
            )
        except Exception:
            pass
        return prompt

    def _parse_examples_json(self, raw: str) -> list[dict[str, str]]:
        import json as _json
        import re as _re
        def _strip_code_fences(text: str) -> str:
            t = text.strip()
            t = _re.sub(r"^```(?:json)?\\s*", "", t, flags=_re.IGNORECASE)
            t = _re.sub(r"```\\s*$", "", t)
            # 先頭の { から末尾の } のみを抜き出す（過剰出力の保険）
            m1 = t.find("{")
            m2 = t.rfind("}")
            if m1 != -1 and m2 != -1 and m2 > m1:
                t = t[m1:m2+1]
            return t.strip()
        text = _strip_code_fences(raw or "")
        obj = _json.loads(text)
        if isinstance(obj, list):
            return [x for x in obj if isinstance(x, dict)]
        if isinstance(obj, dict) and isinstance(obj.get("examples"), list):
            return [x for x in obj.get("examples") if isinstance(x, dict)]
        raise ValueError("Invalid LLM JSON shape (expected array or {\"examples\": [...]})")

    def generate_examples_for_categories(self, lemma: str, plan: dict[ExampleCategory, int]) -> dict[ExampleCategory, list[Examples.ExampleItem]]:
        """カテゴリごとの要求数に従って例文を生成する（LangGraph相当の逐次計画、フォールバック実装あり）。"""
        # 生成結果
        results: dict[ExampleCategory, list[Examples.ExampleItem]] = {k: [] for k in plan.keys()}

        # LangGraph が利用可能なら軽量なノードを組み立て、失敗したら順次実行
        try:
            graph = create_state_graph()
            state: dict[str, object] = {
                "queue": [(k, int(v)) for k, v in plan.items()],
                "lemma": lemma,
                "outputs": [],
            }

            def _generate_node(s: dict[str, object]) -> dict[str, object]:
                q: list[tuple[ExampleCategory, int]] = s.get("queue", [])  # type: ignore[assignment]
                if not q:
                    return s
                cat, num = q.pop(0)
                prompt = self._build_examples_prompt(lemma, cat, num)
                out = self.llm.complete(prompt) if self.llm is not None else "{}"  # type: ignore[attr-defined]
                parsed = self._parse_examples_json(out if isinstance(out, str) else "{}")
                # メタ付与
                def _llm_meta_values() -> tuple[Optional[str], Optional[str]]:
                    try:
                        return (
                            str(self._llm_info.get("model") or "").strip() or None,
                            str(self._llm_info.get("params") or "").strip() or None,
                        )
                    except Exception:
                        return (None, None)
                m, p = _llm_meta_values()
                items: list[Examples.ExampleItem] = []
                for it in parsed[:num]:
                    en = str(it.get("en") or "").strip()
                    ja = str(it.get("ja") or "").strip()
                    if not en or not ja:
                        continue
                    grammar_ja = str(it.get("grammar_ja") or "").strip() or None
                    items.append(Examples.ExampleItem(en=en, ja=ja, grammar_ja=grammar_ja, category=cat, llm_model=m, llm_params=p))
                s.setdefault("outputs", []).append((cat, items))  # type: ignore[assignment]
                return s

            # 可能なAPIに合わせてノードを追加
            try:
                graph.add_node("generate", _generate_node)  # type: ignore[attr-defined]
                graph.set_entry_point("generate")  # type: ignore[attr-defined]
                # 自己ループでキューが空になるまで
                graph.add_edge("generate", "generate")  # type: ignore[attr-defined]
                compiled = graph.compile()  # type: ignore[attr-defined]
                out_state = compiled.invoke(state)  # type: ignore[attr-defined]
                outs = out_state.get("outputs", []) if isinstance(out_state, dict) else state.get("outputs", [])
            except Exception:
                # グラフAPI不一致時は順次実行にフォールバック
                outs = []
                s = state
                while s.get("queue"):
                    s = _generate_node(s)  # type: ignore[assignment]
                outs = s.get("outputs", [])
        except Exception:
            # グラフ初期化に失敗した場合の安全フォールバック（順次）
            outs = []
            for cat, num in plan.items():
                prompt = self._build_examples_prompt(lemma, cat, num)
                out = self.llm.complete(prompt) if self.llm is not None else "{}"  # type: ignore[attr-defined]
                parsed = self._parse_examples_json(out if isinstance(out, str) else "{}")
                # メタ
                model_name = str(self._llm_info.get("model") or "").strip() or None
                params_str = str(self._llm_info.get("params") or "").strip() or None
                items: list[Examples.ExampleItem] = []
                for it in parsed[:num]:
                    en = str(it.get("en") or "").strip()
                    ja = str(it.get("ja") or "").strip()
                    if not en or not ja:
                        continue
                    grammar_ja = str(it.get("grammar_ja") or "").strip() or None
                    items.append(Examples.ExampleItem(en=en, ja=ja, grammar_ja=grammar_ja, category=cat, llm_model=model_name, llm_params=params_str))
                outs.append((cat, items))

        # 結果反映
        for cat, items in outs:  # type: ignore[assignment]
            if cat in results:
                results[cat] = items
        return results
