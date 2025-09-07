from __future__ import annotations

import argparse
from typing import Any, List, Dict

from .providers import ChromaClientFactory


def _ensure_docs(col: Any, ids: List[str], docs: List[str], metadatas: List[Dict[str, Any]]) -> None:
    try:
        # Upsert is supported in chromadb>=0.4; add() is fine for MVP since ids are unique
        if hasattr(col, "upsert"):
            col.upsert(ids=ids, documents=docs, metadatas=metadatas)  # type: ignore[attr-defined]
        else:
            col.add(ids=ids, documents=docs, metadatas=metadatas)  # type: ignore[attr-defined]
    except Exception:
        # best-effort for MVP
        pass


def seed_word_snippets(client: Any) -> None:
    col = client.get_or_create_collection(name="word_snippets")
    ids = [
        "ws_1",
        "ws_2",
        "ws_3",
    ]
    docs = [
        "Converge: to come together from different directions.",
        "Diverge: to separate and go in different directions.",
        "Assumption: a thing that is accepted as true without proof.",
    ]
    metas = [
        {"source": "mini-seed", "tag": "definition"},
        {"source": "mini-seed", "tag": "definition"},
        {"source": "mini-seed", "tag": "term"},
    ]
    _ensure_docs(col, ids, docs, metas)


def seed_domain_terms(client: Any) -> None:
    col = client.get_or_create_collection(name="domain_terms")
    ids = [
        "dt_1",
        "dt_2",
        "dt_3",
    ]
    docs = [
        "algorithm: a process or set of rules to be followed in problem-solving.",
        "gradient: vector of partial derivatives of a function.",
        "assumption: premise taken to be true for the purpose of argument.",
    ]
    metas = [
        {"domain": "cs", "level": "intro"},
        {"domain": "math", "level": "intro"},
        {"domain": "logic", "level": "intro"},
    ]
    _ensure_docs(col, ids, docs, metas)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed ChromaDB collections for RAG")
    parser.add_argument("--persist", default=".chroma", help="Chroma persist directory")
    args = parser.parse_args()

    client = ChromaClientFactory(persist_directory=args.persist).create_client()
    if client is None:
        print("ChromaDB is not available. Skipping seeding.")
        return 0

    seed_word_snippets(client)
    seed_domain_terms(client)
    print("Seeded collections: word_snippets, domain_terms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


