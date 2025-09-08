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
from ..providers import chroma_query_with_policy, COL_WORD_SNIPPETS


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
        return {"lemma": lemma, "citations": citations}

    def _synthesize(
        self,
        lemma: str,
        *,
        pronunciation_enabled: bool = True,
        regenerate_scope: RegenerateScope | str = RegenerateScope.all,
        citations: List[Citation] | None = None,
    ) -> WordPack:
        """取得結果を整形し `WordPack` を構成（ダミーは生成しない）。"""
        pronunciation = (
            self._generate_pronunciation(lemma)
            if pronunciation_enabled
            else Pronunciation(ipa_GA=None, ipa_RP=None, syllables=None, stress_index=None, linking_notes=[])
        )
        confidence = ConfidenceLevel.medium if citations else ConfidenceLevel.low
        pack = WordPack(
            lemma=lemma,
            pronunciation=pronunciation,
            senses=[],
            collocations=Collocations(),
            contrast=[],
            examples=Examples(),
            etymology=Etymology(note="", confidence=ConfidenceLevel.low),
            study_card="",
            citations=citations or [],
            confidence=confidence,
        )
        return pack

    def run(self, lemma: str, *, pronunciation_enabled: bool = True, regenerate_scope: RegenerateScope | str = RegenerateScope.all) -> WordPack:
        """語を入力として `WordPack` を生成して返す（ダミー生成なし）。"""
        data = self._retrieve(lemma)
        return self._synthesize(
            lemma,
            pronunciation_enabled=pronunciation_enabled,
            regenerate_scope=regenerate_scope,
            citations=data.get("citations"),
        )
