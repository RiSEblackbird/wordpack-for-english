from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, List, Dict, Iterable

from .providers import ChromaClientFactory, COL_WORD_SNIPPETS, COL_DOMAIN_TERMS
from .config import settings


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
    col = client.get_or_create_collection(name=COL_WORD_SNIPPETS)
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
    col = client.get_or_create_collection(name=COL_DOMAIN_TERMS)
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


def _load_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def seed_from_jsonl(client: Any, *, word_snippets_path: Path | None = None, domain_terms_path: Path | None = None) -> None:
    if word_snippets_path and word_snippets_path.exists():
        col = client.get_or_create_collection(name=COL_WORD_SNIPPETS)
        ids: List[str] = []
        docs: List[str] = []
        metas: List[Dict[str, Any]] = []
        for i, row in enumerate(_load_jsonl(word_snippets_path), start=1):
            ids.append(row.get("id") or f"ws_{i}")
            docs.append(row.get("text") or "")
            m = {k: v for k, v in row.items() if k not in {"id", "text"}}
            metas.append(m)
        if ids:
            _ensure_docs(col, ids, docs, metas)
    if domain_terms_path and domain_terms_path.exists():
        col = client.get_or_create_collection(name=COL_DOMAIN_TERMS)
        ids = []
        docs = []
        metas = []
        for i, row in enumerate(_load_jsonl(domain_terms_path), start=1):
            ids.append(row.get("id") or f"dt_{i}")
            docs.append(row.get("text") or "")
            m = {k: v for k, v in row.items() if k not in {"id", "text"}}
            metas.append(m)
        if ids:
            _ensure_docs(col, ids, docs, metas)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed ChromaDB collections for RAG")
    parser.add_argument("--persist", default=None, help="Chroma persist directory (overrides settings)")
    parser.add_argument("--word-jsonl", default=None, help="Path to word_snippets JSONL")
    parser.add_argument("--terms-jsonl", default=None, help="Path to domain_terms JSONL")
    args = parser.parse_args()

    persist_dir = args.persist or settings.chroma_persist_dir
    client = ChromaClientFactory(persist_directory=persist_dir).create_client()
    if client is None:
        print("ChromaDB is not available. Skipping seeding.")
        return 0

    # JSONL が指定されればそれを優先。なければ最小シード。
    wj = Path(args.word_jsonl) if args.word_jsonl else None
    tj = Path(args.terms_jsonl) if args.terms_jsonl else None
    if (wj and wj.exists()) or (tj and tj.exists()):
        seed_from_jsonl(client, word_snippets_path=wj, domain_terms_path=tj)
        print("Seeded collections from JSONL")
    else:
        seed_word_snippets(client)
        seed_domain_terms(client)
        print("Seeded collections: word_snippets, domain_terms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


