from typing import Any, List

# LangGraph は必須。未導入やAPI不一致なら起動失敗とする。
try:
    from langgraph.graph import StateGraph  # type: ignore
except Exception as exc:  # pragma: no cover - library required
    raise ImportError(
        "FeedbackFlow requires the 'langgraph' package (expected langgraph.graph.StateGraph)."
    ) from exc

from ..models.sentence import SentenceCheckResponse, Issue, Revision, MiniExercise


class FeedbackFlow:
    """Minimal feedback generator.

    MVP では固定の3要素（issues/revisions/exercise）をダミー生成。
    実装置換ポイント：LLM による診断と修正案生成。
    """

    def __init__(self, llm: Any | None = None) -> None:
        self.llm = llm
        self.graph = StateGraph()

    def run(self, sentence: str) -> SentenceCheckResponse:
        issues = [Issue(what="語法", why="対象語の使い分け不正確", fix="共起に合わせて置換")]  # type: ignore[arg-type]
        revisions = [
            Revision(style="natural", text=sentence),
            Revision(style="formal", text=sentence),
        ]
        exercise = MiniExercise(q="Fill the blank: ...", a="...")
        return SentenceCheckResponse(issues=issues, revisions=revisions, exercise=exercise)
