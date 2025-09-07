from typing import Any

# LangGraph は必須
try:
    from langgraph.graph import StateGraph  # type: ignore
except Exception as exc:  # pragma: no cover - library required
    raise ImportError(
        "WordPackFlow requires the 'langgraph' package (expected langgraph.graph.StateGraph)."
    ) from exc

try:
    import chromadb
except Exception:  # pragma: no cover - library optional
    chromadb = Any  # type: ignore


class WordPackFlow:
    """Flow that generates word packs using RAG with ChromaDB."""

    def __init__(self, chroma_client: Any | None = None) -> None:
        self.chroma = chroma_client
        self.graph = None

    def run(self, topic: str) -> list[str]:
        """Generate a list of words related to ``topic``."""
        # TODO: implement RAG logic.
        return []
