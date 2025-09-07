from typing import Any, List, Dict, Any as AnyType

# LangGraph は必須。未導入やAPI不一致なら起動失敗とする。
# まずは正式な import（サブモジュールからの直接 import）を試み、
# 失敗した場合は tests のスタブ（sys.modules["langgraph"] に SimpleNamespace を入れる）
# に対応するためのフォールバックを行う。
try:
    from langgraph.graph import StateGraph  # type: ignore
except Exception:
    try:
        import langgraph  # type: ignore
        StateGraph = langgraph.graph.StateGraph  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - library required
        raise ImportError(
            "FeedbackFlow requires the 'langgraph' package (expected langgraph.graph.StateGraph)."
        ) from exc

from ..models.sentence import SentenceCheckResponse, Issue, Revision, MiniExercise
from ..models.common import Citation, ConfidenceLevel
from ..providers import chroma_query_with_policy, COL_DOMAIN_TERMS
from ..config import settings


class FeedbackFlow:
    """Minimal feedback generator.

    文の診断フィードバックを最小構成で生成するフロー。
    MVP では固定の3要素（issues/revisions/exercise）をダミー生成。
    将来的には LLM によるエラー検出・説明・修正案、および
    ミニ演習（穴埋め等）の自動生成に置き換える想定。
    """

    def __init__(self, llm: Any | None = None, *, chroma_client: Any | None = None) -> None:
        """LLM クライアント等を受け取り、LangGraph の状態遷移を初期化。

        Parameters
        ----------
        llm: Any | None
            フィードバック生成に用いる LLM クライアント（任意）。
        """
        self.llm = llm
        self.chroma = chroma_client
        self.graph = StateGraph()

    def run(self, sentence: str) -> SentenceCheckResponse:
        """与えられた文を解析し、フィードバックを返す（MVP ダミー）。

        現状は入力文をそのまま用いて 2 種類の書き換え案と、
        サンプルの指摘/演習を返す。
        """
        issues = [Issue(what="語法", why="対象語の使い分け不正確", fix="共起に合わせて置換")]  # type: ignore[arg-type]
        revisions = [
            Revision(style="natural", text=sentence),
            Revision(style="formal", text=sentence),
        ]
        exercise = MiniExercise(q="Fill the blank: ...", a="...")
        # 可能ならRAGの引用を付与
        citations: List[Citation] = []
        if settings.rag_enabled and self.chroma and getattr(self.chroma, "get_or_create_collection", None):
            res = chroma_query_with_policy(
                self.chroma,
                collection=COL_DOMAIN_TERMS,
                query_text=sentence.split()[0] if sentence.split() else "",
                n_results=3,
            )
            if res:
                docs = (res.get("documents") or [[]])[0]
                metas = (res.get("metadatas") or [[]])[0]
                for d, m in zip(docs, metas):
                    citations.append(Citation(text=d, meta=m))
        confidence = ConfidenceLevel.medium if citations else ConfidenceLevel.low
        return SentenceCheckResponse(issues=issues, revisions=revisions, exercise=exercise, citations=citations, confidence=confidence)
