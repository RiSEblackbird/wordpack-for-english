"""Chroma クライアントのファクトリを提供するモジュール。"""

from __future__ import annotations

import sys
from typing import Any, Optional

from ..config import settings
from ..logging import logger
from . import _get_client_cache
from .embeddings import get_embedding_provider
from .vector import _ChromaClientAdapter, _InMemoryChromaClient

try:  # pragma: no cover - chromadb は任意依存
    import chromadb  # type: ignore
except Exception:  # pragma: no cover - 任意依存
    chromadb = None  # type: ignore


class ChromaClientFactory:
    """ChromaDB クライアントを初期化し、必要に応じてフォールバックする。"""

    def __init__(self, persist_directory: Optional[str] = None) -> None:
        self.persist_directory = persist_directory or ".chroma"

    def create_client(self) -> Any | None:
        """Chroma クライアントを生成する。利用不可ならインメモリ実装を返す。"""

        cache = _get_client_cache()
        key = f"url:{getattr(settings, 'chroma_server_url', None) or ''}|persist:{self.persist_directory}"
        if key in cache:
            return cache[key]

        if not settings.strict_mode:
            client = _InMemoryChromaClient(get_embedding_provider())
            cache[key] = client
            return client

        if chromadb is None or "chromadb" not in sys.modules:
            raise RuntimeError("chromadb module is required (strict mode)")

        underlying: Any | None = None
        if getattr(settings, "chroma_server_url", None):
            try:
                http_cls = getattr(chromadb, "HttpClient", None) or getattr(chromadb, "Client", None)  # type: ignore[attr-defined]
                underlying = http_cls(host=settings.chroma_server_url)  # type: ignore[call-arg]
            except Exception as exc:
                logger.warning("chroma_http_client_init_failed", error=str(exc))
        else:
            try:
                underlying = chromadb.PersistentClient(path=self.persist_directory)  # type: ignore[attr-defined]
            except Exception as exc:
                logger.warning("chroma_persistent_client_init_failed", error=str(exc))
                try:
                    underlying = chromadb.Client()  # type: ignore[attr-defined]
                except Exception as inner:
                    logger.warning("chroma_memory_client_init_failed", error=str(inner))
                    underlying = None
        if underlying is None:
            raise RuntimeError("Failed to initialize Chroma client (strict mode)")
        client = _ChromaClientAdapter(underlying, get_embedding_provider())
        cache[key] = client
        return client

    def get_or_create_collection(self, client: Any, name: str) -> Any | None:
        """コレクション取得に失敗したら None を返す安全ラッパー。"""

        if client is None:  # pragma: no cover - 呼び出し側の保険
            return None
        try:
            return client.get_or_create_collection(name=name)
        except Exception:
            return None
