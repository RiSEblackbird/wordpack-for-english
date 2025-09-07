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

    LangGraph を用いた簡易なリーディング支援フロー。
    MVP では段落を文に単純分割し、ダミーの構文情報と用語注を返す。
    将来的には RAG による用語検出、IPA（発音記号）付与、
    文意のパラフレーズ生成、引用元提示等を追加する想定。
    """

    def __init__(self, chroma_client: Any | None = None) -> None:
        """ChromaDB クライアント等を受け取り、LangGraph を初期化。

        Parameters
        ----------
        chroma_client: Any | None
            用語サーチ/RAG に用いるベクトルDB クライアント（任意）。
        """
        self.chroma = chroma_client
        self.graph = StateGraph()

    def _segment(self, paragraph: str) -> List[str]:
        """段落を単純なピリオド分割で文リストに変換（MVP）。"""
        return [s.strip() for s in paragraph.replace("\n", " ").split(".") if s.strip()]

    def _analyze(self, sentence: str) -> AssistedSentence:
        """文を解析し、構文情報・用語注・パラフレーズを付与（MVP）。"""
        return AssistedSentence(
            raw=sentence,
            syntax=SyntaxInfo(subject=None, predicate=None, mods=[]),
            terms=[TermInfo(lemma=w, gloss_ja=None, ipa=None) for w in sentence.split()[:1]],
            paraphrase=sentence,
        )

    def run(self, paragraph: str) -> TextAssistResponse:
        """段落を入力として文ごとの支援情報を返す（MVP ダミー）。"""
        sentences = [self._analyze(s) for s in self._segment(paragraph)]
        return TextAssistResponse(sentences=sentences, summary=None, citations=[])
