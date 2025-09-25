"""Utilities for sanitizing and deriving WordPack sense titles."""

from __future__ import annotations

from typing import Iterable

_PLACEHOLDER = "語義タイトル未設定"


def _contains_japanese(text: str) -> bool:
    """Return True if *text* appears to contain Japanese characters."""

    for ch in text:
        code = ord(ch)
        if (
            0x3040 <= code <= 0x309F  # Hiragana
            or 0x30A0 <= code <= 0x30FF  # Katakana
            or 0x4E00 <= code <= 0x9FFF  # CJK Unified Ideographs
            or ch in {"々", "〆", "〤", "ー"}
        ):
            return True
    return False


def choose_sense_title(
    raw_title: str | None,
    candidates: Iterable[str],
    *,
    lemma: str = "",
    limit: int = 20,
) -> str:
    """Pick a short Japanese title for WordPack listings.

    The function prefers the LLM supplied title if it already contains Japanese
    characters. Otherwise it scans *candidates* (typically gloss fields from
    senses) and finally falls back to ``_PLACEHOLDER``. ``lemma`` is only used
    when it already contains Japanese characters, in which case it is also
    considered as a candidate.
    """

    ordered: list[str] = []
    if raw_title is not None:
        ordered.append(raw_title)
    ordered.extend(candidates)
    if lemma:
        ordered.append(lemma)

    for text in ordered:
        candidate = (text or "").strip()
        if not candidate:
            continue
        truncated = candidate[:limit]
        if _contains_japanese(truncated):
            return truncated

    # 仕様変更: 日本語候補がない場合は lemma をそのまま（または切り詰めて）返す
    lemma_trimmed = (lemma or "").strip()
    if lemma_trimmed:
        return lemma_trimmed[:limit]

    return _PLACEHOLDER


__all__ = ["choose_sense_title"]
