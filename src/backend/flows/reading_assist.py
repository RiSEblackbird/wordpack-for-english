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
            "ReadingAssistFlow requires the 'langgraph' package (expected langgraph.graph.StateGraph)."
        ) from exc

try:
    import chromadb
except Exception:  # pragma: no cover - library optional
    chromadb = Any  # type: ignore

from ..models.text import (
    TextAssistResponse,
    AssistedSentence,
    SyntaxInfo,
    TermInfo,
)


class ReadingAssistFlow:
    """Minimal reading assistance via LangGraph.

    MVP では段落を文に単純分割し、ダミーの構文情報と用語注を返す。
    実装置換ポイント：RAG 用語検出、IPA 付与、パラフレーズ生成。
    """

    def __init__(self, chroma_client: Any | None = None) -> None:
        self.chroma = chroma_client
        self.graph = StateGraph()

    def _segment(self, paragraph: str) -> List[str]:
        return [s.strip() for s in paragraph.replace("\n", " ").split(".") if s.strip()]

    def _analyze(self, sentence: str) -> AssistedSentence:
        return AssistedSentence(
            raw=sentence,
            syntax=SyntaxInfo(subject=None, predicate=None, mods=[]),
            terms=[TermInfo(lemma=w, gloss_ja=None, ipa=None) for w in sentence.split()[:1]],
            paraphrase=sentence,
        )

    def run(self, paragraph: str) -> TextAssistResponse:
        sentences = [self._analyze(s) for s in self._segment(paragraph)]
        return TextAssistResponse(sentences=sentences, summary=None, citations=[])
