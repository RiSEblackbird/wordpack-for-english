from typing import Any

try:
    from langgraph import Graph
except Exception as exc:  # pragma: no cover - library required
    raise ImportError(
        "FeedbackFlow requires the 'langgraph' package. Install it to use this flow."
    ) from exc


class FeedbackFlow:
    """Flow that provides feedback for sentences or answers."""

    def __init__(self, llm: Any | None = None) -> None:
        self.llm = llm
        self.graph = Graph()  # type: ignore[call-arg]
        # TODO: construct graph nodes for evaluation and feedback generation.

    def run(self, sentence: str) -> dict[str, Any]:
        """Return feedback for a given sentence."""
        # TODO: implement feedback logic.
        return {}
