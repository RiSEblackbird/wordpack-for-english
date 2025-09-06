from typing import Any

from .config import settings


def get_llm_provider() -> Any:
    """Return an LLM client based on the configured provider.

    TODO: instantiate a real LLM client depending on ``settings.llm_provider``.
    """
    # Placeholder implementation.
    return None


def get_embedding_provider() -> Any:
    """Return an embedding client based on the configured provider.

    TODO: instantiate a real embedding client depending on ``settings.embedding_provider``.
    """
    # Placeholder implementation.
    return None
