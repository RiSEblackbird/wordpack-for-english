from typing import Any, Dict, List

from . import create_state_graph

try:
    import chromadb
except Exception:  # pragma: no cover - library optional
    chromadb = Any  # type: ignore

from ..models.word import (
    WordPack,
    Sense,
    Collocations,
    Etymology,
    Pronunciation,
    Examples,
    RegenerateScope,
)
from ..models.common import ConfidenceLevel, Citation
from ..pronunciation import generate_pronunciation
from ..logging import logger
from ..config import settings
from ..providers import chroma_query_with_policy, COL_WORD_SNIPPETS


class WordPackFlow:
    """Word pack generation via a minimal LangGraph pipeline.

    単語学習パックを生成する最小構成のフロー。
    MVP ではダミーの RAG ステップを通し、スキーマに沿った固定形の
    `WordPack` を返す。実際の RAG/LLM は `providers` から差し替え予定。
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
        """語の近傍情報を取得（将来: chroma からベクトル近傍）。"""
        citations: List[Citation] = []
        if settings.rag_enabled and self.chroma and getattr(self.chroma, "get_or_create_collection", None):
            res = chroma_query_with_policy(
                self.chroma,
                collection=COL_WORD_SNIPPETS,
                query_text=lemma,
                n_results=3,
            )
            if res:
                docs = (res.get("documents") or [[]])[0]
                metas = (res.get("metadatas") or [[]])[0]
                for d, m in zip(docs, metas):
                    citations.append(Citation(text=d, meta=m))
        # strict_mode の場合、RAG 有効で引用が得られなければエラーで早期に気付けるようにする
        if settings.rag_enabled and not citations:
            if settings.strict_mode:
                raise RuntimeError("RAG is enabled but no citations were retrieved (strict mode)")
            # 非 strict: 最低限のフォールバック（テスト/開発用途）
            citations.append(Citation(text=f"{lemma}: example snippet (fallback).", meta={"source": "fallback"}))
        return {"lemma": lemma, "citations": citations}

    def _synthesize(
        self,
        lemma: str,
        *,
        pronunciation_enabled: bool = True,
        regenerate_scope: RegenerateScope | str = RegenerateScope.all,
        citations: List[Citation] | None = None,
    ) -> WordPack:
        """取得結果を整形し `WordPack` を構成（将来: LLM で整形）。"""
        pronunciation = (
            self._generate_pronunciation(lemma)
            if pronunciation_enabled
            else Pronunciation(ipa_GA=None, ipa_RP=None, syllables=None, stress_index=None, linking_notes=[])
        )
        confidence = ConfidenceLevel.medium if citations else ConfidenceLevel.low
        # 例文（A1）: 英文と訳文を5件（MVPのテンプレ生成）
        ex_a1 = [
            Examples.ExampleItem(en=f"This is an {lemma}.", ja=f"これは{lemma}です。"),
            Examples.ExampleItem(en=f"I study the {lemma}.", ja=f"私はその{lemma}を勉強します。"),
            Examples.ExampleItem(en=f"We use an {lemma} every day.", ja=f"私たちは毎日{lemma}を使います。"),
            Examples.ExampleItem(en=f"The {lemma} works well.", ja=f"その{lemma}はうまく機能します。"),
            Examples.ExampleItem(en=f"Can you explain the {lemma}?", ja=f"その{lemma}を説明できますか？"),
        ]
        # B1/C1/tech も最低限を補う（将来はLLMで整形）
        ex_b1 = [
            Examples.ExampleItem(en=f"They improved the {lemma} for better results.", ja=f"彼らはより良い結果のために{lemma}を改良しました。"),
        ]
        ex_c1 = [
            Examples.ExampleItem(en=f"The {lemma} achieves convergence under mild assumptions.", ja=f"その{lemma}は緩やかな仮定の下で収束します。"),
        ]
        ex_tech = [
            Examples.ExampleItem(en=f"This library implements a fast {lemma} for large datasets.", ja=f"このライブラリは大規模データ向けの高速な{lemma}を実装しています。"),
            Examples.ExampleItem(en=f"We compare the baseline {lemma} with a heuristic method.", ja=f"ベースラインの{lemma}をヒューリスティック手法と比較します。"),
        ]

        pack = WordPack(
            lemma=lemma,
            pronunciation=pronunciation,
            senses=[
                Sense(id="s1", gloss_ja=f"{lemma}：手順や計算方法（暫定）", patterns=[], register=None),
            ],
            collocations=Collocations(
                general=
                    CollocationLists(
                        verb_object=[f"use {lemma}", f"develop {lemma}", f"apply {lemma}"],
                        adj_noun=[f"efficient {lemma}", f"robust {lemma}", f"simple {lemma}"],
                        prep_noun=[f"{lemma} for sorting", f"{lemma} for optimization"],
                    ),
                academic=
                    CollocationLists(
                        verb_object=[f"analyze {lemma}", f"propose {lemma}"],
                        adj_noun=[f"novel {lemma}", f"baseline {lemma}"],
                        prep_noun=[f"{lemma} in practice", f"{lemma} in theory"],
                    ),
            ),
            contrast=[
                # 'with' はエイリアス名なので with_ で指定
                ContrastItem(with_="heuristic", diff_ja="アルゴリズム=厳密手順、ヒューリスティック=経験則。"),
                ContrastItem(with_="program", diff_ja="プログラム=コード全体、アルゴリズム=その核心手順。"),
            ],
            examples=Examples(A1=ex_a1, B1=ex_b1, C1=ex_c1, tech=ex_tech),
            etymology=Etymology(note=f"語源：中世ラテン語 algoritmi（アル・フワーリズミに由来）。項目 {lemma} に関する暫定メモ。", confidence=ConfidenceLevel.low),
            study_card="この語の要点（暫定）。",
            citations=citations or [],
            confidence=confidence,
        )
        # 任意のLLMが利用可能なら、簡易に例文を拡張（将来の本実装の置換点）
        try:
            if self.llm is not None and hasattr(self.llm, "complete"):
                _ = self.llm.complete(f"Give one simple A1 example sentence using the word '{lemma}'.")  # type: ignore[attr-defined]
                # 応答のパースは省略（将来の本実装で整形）
        except Exception:
            pass
        # regenerate_scope は将来の部分更新用。MVP では生成内容の軽微な差分に留める。
        scope_val = regenerate_scope.value if isinstance(regenerate_scope, RegenerateScope) else regenerate_scope
        if scope_val == RegenerateScope.examples.value:
            pack.examples = Examples(A1=ex_a1, B1=ex_b1, C1=ex_c1, tech=ex_tech)
        elif scope_val == RegenerateScope.collocations.value:
            # collocations を補強
            pack.collocations.general.verb_object = [f"use {lemma}", f"develop {lemma}"]
            pack.collocations.general.adj_noun = [f"efficient {lemma}"]
        return pack

    def run(self, lemma: str, *, pronunciation_enabled: bool = True, regenerate_scope: RegenerateScope | str = RegenerateScope.all) -> WordPack:
        """語を入力として `WordPack` を生成して返す（MVP ダミー）。"""
        data = self._retrieve(lemma)
        return self._synthesize(
            lemma,
            pronunciation_enabled=pronunciation_enabled,
            regenerate_scope=regenerate_scope,
            citations=data.get("citations"),
        )
