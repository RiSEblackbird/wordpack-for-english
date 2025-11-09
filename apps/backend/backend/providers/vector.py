"""ベクターストア（Chroma）向けの補助クラス群。"""

from __future__ import annotations

from typing import Any, List

COL_WORD_SNIPPETS = "word_snippets"
COL_DOMAIN_TERMS = "domain_terms"


class _ChromaClientAdapter:
    """Chroma クライアントへ埋め込み関数を確実に注入する薄いラッパー。"""

    def __init__(self, underlying: Any, embedding_fn: Any) -> None:
        self._underlying = underlying
        self._embedding_fn = embedding_fn

    def get_or_create_collection(self, name: str) -> Any:
        return self._underlying.get_or_create_collection(
            name=name, embedding_function=self._embedding_fn
        )  # type: ignore[attr-defined]


class _InMemoryCollection:
    """テスト用の最小限な Chroma 互換コレクション。"""

    def __init__(self, embedding_function: Any) -> None:
        self._embedding_function = embedding_function
        self._docs: List[str] = []
        self._metas: List[dict[str, Any]] = []
        self._ids: List[str] = []
        self._embs: List[List[float]] = []

    def _ensure_embeddings(self, documents: List[str]) -> List[List[float]]:
        try:
            return self._embedding_function(documents)
        except Exception:
            return [[0.0] * 8 for _ in documents]

    def add(
        self,
        *,
        ids: List[str],
        documents: List[str],
        metadatas: List[dict[str, Any]] | None = None,
    ) -> None:  # type: ignore[override]
        metadatas = metadatas or [{} for _ in documents]
        embeddings = self._ensure_embeddings(documents)
        self._ids.extend(ids)
        self._docs.extend(documents)
        self._metas.extend(metadatas)
        self._embs.extend(embeddings)

    def upsert(
        self,
        *,
        ids: List[str],
        documents: List[str],
        metadatas: List[dict[str, Any]] | None = None,
    ) -> None:  # type: ignore[override]
        existing = {item: idx for idx, item in enumerate(self._ids)}
        for identifier, doc, meta in zip(ids, documents, metadatas or [{} for _ in documents]):
            if identifier in existing:
                idx = existing[identifier]
                self._ids[idx] = identifier
                self._docs[idx] = doc
                self._metas[idx] = meta
                self._embs[idx] = self._ensure_embeddings([doc])[0]
            else:
                self.add(ids=[identifier], documents=[doc], metadatas=[meta])

    def query(self, *, query_texts: List[str], n_results: int = 3) -> dict[str, Any]:  # type: ignore[override]
        def cosine(a: List[float], b: List[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            na = sum(x * x for x in a) ** 0.5 or 1.0
            nb = sum(y * y for y in b) ** 0.5 or 1.0
            return dot / (na * nb)

        query_embs = self._ensure_embeddings(query_texts)
        all_docs: List[List[str]] = []
        all_metas: List[List[dict[str, Any]]] = []
        all_ids: List[List[str]] = []
        for query_emb in query_embs:
            sims = [(cosine(query_emb, doc_emb), idx) for idx, doc_emb in enumerate(self._embs)]
            sims.sort(reverse=True)
            top = sims[: max(0, n_results)]
            indices = [index for _, index in top]
            all_docs.append([self._docs[i] for i in indices])
            all_metas.append([self._metas[i] for i in indices])
            all_ids.append([self._ids[i] for i in indices])
        return {"ids": all_ids, "documents": all_docs, "metadatas": all_metas}


class _InMemoryChromaClient:
    """ChromaDB のテスト代替実装。"""

    def __init__(self, embedding_function: Any) -> None:
        self._embedding_function = embedding_function
        self._collections: dict[str, _InMemoryCollection] = {}

    def get_or_create_collection(
        self, name: str, embedding_function: Any | None = None
    ) -> _InMemoryCollection:  # type: ignore[override]
        if name not in self._collections:
            ef = embedding_function or self._embedding_function
            self._collections[name] = _InMemoryCollection(ef)
        return self._collections[name]


__all__ = [
    "COL_WORD_SNIPPETS",
    "COL_DOMAIN_TERMS",
    "_ChromaClientAdapter",
    "_InMemoryChromaClient",
]
