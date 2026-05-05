from __future__ import annotations

STOP_LEMMAS: set[str] = {
    "a",
    "an",
    "the",
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "me",
    "him",
    "her",
    "us",
    "them",
    "my",
    "your",
    "his",
    "its",
    "our",
    "their",
    "mine",
    "yours",
    "hers",
    "ours",
    "theirs",
    "am",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "do",
    "does",
    "did",
    "done",
    "doing",
    "have",
    "has",
    "had",
    "having",
    "will",
    "would",
    "shall",
    "should",
    "can",
    "could",
    "may",
    "might",
    "must",
    "to",
    "of",
    "in",
    "on",
    "for",
    "at",
    "by",
    "with",
    "about",
    "as",
    "into",
    "like",
    "through",
    "after",
    "over",
    "between",
    "out",
    "against",
    "during",
    "without",
    "before",
    "under",
    "around",
    "among",
    "and",
    "or",
    "but",
    "if",
    "because",
    "so",
    "than",
    "too",
    "very",
    "not",
    "no",
    "nor",
    "also",
    "then",
    "there",
    "here",
}


def filter_article_lemmas(
    raw: list[str],
    *,
    basic_lemmas: set[str] | frozenset[str] | None = None,
) -> list[str]:
    uniq: list[str] = []
    seen: set[str] = set()
    basic = basic_lemmas or set()
    for t in raw:
        s = (t or "").strip()
        if not s:
            continue
        if " " in s:
            key = s.lower()
            if key not in seen:
                uniq.append(s)
                seen.add(key)
            continue
        token = s.strip()
        if not all(ch.isalpha() or ch in {"-", "'"} for ch in token):
            continue
        low = token.lower()
        if low in STOP_LEMMAS:
            continue
        if low in basic:
            continue
        if len(token) <= 2 and not (token.isupper() and 2 <= len(token) <= 4):
            continue
        key = low
        if key not in seen:
            norm = token if token.isupper() else low
            uniq.append(norm)
            seen.add(key)
    return uniq
