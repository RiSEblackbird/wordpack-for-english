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


class FeedbackFlow:
    """Minimal feedback generator.

    文の診断フィードバックを最小構成で生成するフロー。
    MVP では固定の3要素（issues/revisions/exercise）をダミー生成。
    将来的には LLM によるエラー検出・説明・修正案、および
    ミニ演習（穴埋め等）の自動生成に置き換える想定。
    """

    def __init__(self, llm: Any | None = None) -> None:
        """LLM クライアント等を受け取り、LangGraph の状態遷移を初期化。

        Parameters
        ----------
        llm: Any | None
            フィードバック生成に用いる LLM クライアント（任意）。
        """
        self.llm = llm
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
        # RAGの引用（将来）。現状は空。低信頼。
        citations: List[Dict[str, Any]] = []
        return SentenceCheckResponse(issues=issues, revisions=revisions, exercise=exercise, citations=citations, confidence="low")
