from __future__ import annotations

from typing import Any


def normalize_search_text(text: str | None) -> str:
    """検索用に英文を正規化（小文字化・前後空白除去）する。"""

    return str((text or "").strip()).lower()


def extract_search_terms(normalized_text: str) -> list[str]:
    """部分一致検索のために短いN-gramとトークンを抽出する。"""

    compact = normalized_text.replace("\n", " ")
    terms: set[str] = set()
    for token in compact.replace("/", " ").replace(",", " ").split():
        stripped = token.strip()
        if stripped:
            terms.add(stripped)
    condensed = normalized_text.replace(" ", "")
    for size in (1, 2, 3):
        if len(condensed) < size:
            continue
        for idx in range(len(condensed) - size + 1):
            terms.add(condensed[idx : idx + size])
    return sorted(terms)


def build_search_payload(en: str) -> dict[str, Any]:
    normalized = normalize_search_text(en)
    return {
        "search_en": normalized,
        "search_en_reversed": normalized[::-1],
        "search_terms": extract_search_terms(normalized),
    }
