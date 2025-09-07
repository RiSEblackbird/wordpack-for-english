from typing import Any, Dict, List

# LangGraph は必須
# 正式 import を試し、失敗時は tests スタブ互換のフォールバック。
try:
    from langgraph.graph import StateGraph  # type: ignore
except Exception:
    try:
        import langgraph  # type: ignore
        StateGraph = langgraph.graph.StateGraph  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - library required
        raise ImportError(
            "WordPackFlow requires the 'langgraph' package (expected langgraph.graph.StateGraph)."
        ) from exc

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
)


class WordPackFlow:
    """Word pack generation via a minimal LangGraph pipeline.

    MVP 実装ではダミーの RAG ステップを通し、スキーマに沿った固定形の
    `WordPack` を返す。実際の RAG/LLM は providers から差し替え予定。
    """

    def __init__(self, chroma_client: Any | None = None) -> None:
        self.chroma = chroma_client
        self.graph = StateGraph()

    def _retrieve(self, lemma: str) -> Dict[str, Any]:
        # 将来: chroma から近傍取得
        return {"lemma": lemma}

    def _synthesize(self, lemma: str) -> WordPack:
        # 将来: LLM で整形
        return WordPack(
            lemma=lemma,
            pronunciation=Pronunciation(ipa_GA=None, syllables=None, stress_index=None),
            senses=[Sense(id="s1", gloss_ja="意味（暫定）", patterns=[], register=None)],
            collocations=Collocations(),
            contrast=[],
            examples=Examples(A1=[f"{lemma} example."], tech=[]),
            etymology=Etymology(note="TBD", confidence="low"),
            study_card="この語の要点（暫定）。",
        )

    def run(self, lemma: str) -> WordPack:
        _ = self._retrieve(lemma)
        return self._synthesize(lemma)
