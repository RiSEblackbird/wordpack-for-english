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
        pack = WordPack(
            lemma=lemma,
            pronunciation=pronunciation,
            senses=[Sense(id="s1", gloss_ja="意味（暫定）", patterns=[], register=None)],
            collocations=Collocations(),
            contrast=[],
            examples=Examples(A1=[f"{lemma} example."], tech=[]),
            etymology=Etymology(note="TBD", confidence=ConfidenceLevel.low),
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
            pack.examples = Examples(A1=[f"{lemma} example.", f"{lemma} example 2."], tech=[])
        elif scope_val == RegenerateScope.collocations.value:
            # ダミーで collocations.general に 1 つ追加
            pack.collocations.general.verb_object = [f"use {lemma}"]
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
