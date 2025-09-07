from typing import Any

# LangGraph は必須
try:
    from langgraph.graph import StateGraph  # type: ignore
except Exception as exc:  # pragma: no cover - library required
    raise ImportError(
        "ReadingAssistFlow requires the 'langgraph' package (expected langgraph.graph.StateGraph)."
    ) from exc

try:
    import chromadb
except Exception:  # pragma: no cover - library optional
    chromadb = Any  # type: ignore


class ReadingAssistFlow:
    """Flow that assists reading comprehension with RAG."""

    def __init__(self, chroma_client: Any | None = None) -> None:
        self.chroma = chroma_client
        self.graph = None

    def run(self, text: str) -> dict[str, Any]:
        """Return assistance data for the supplied text."""
        # TODO: implement reading assistance logic.
        return {}
