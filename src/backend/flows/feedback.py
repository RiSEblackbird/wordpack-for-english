from typing import Any

# LangGraph は必須。未導入やAPI不一致なら起動失敗とする。
try:
    from langgraph.graph import StateGraph  # type: ignore
except Exception as exc:  # pragma: no cover - library required
    raise ImportError(
        "FeedbackFlow requires the 'langgraph' package (expected langgraph.graph.StateGraph)."
    ) from exc


class FeedbackFlow:
    """Flow that provides feedback for sentences or answers."""

    def __init__(self, llm: Any | None = None) -> None:
        self.llm = llm
        # 実グラフは実装時に構築する（StateGraph が利用可能であることはインポート時に保証）
        self.graph = None

    def run(self, sentence: str) -> dict[str, Any]:
        """Return feedback for a given sentence."""
        # TODO: implement feedback logic.
        return {}
