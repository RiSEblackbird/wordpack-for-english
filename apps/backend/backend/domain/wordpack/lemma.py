from __future__ import annotations

import re

LEMMA_ALLOWED_PATTERN = re.compile(r"^[A-Za-z0-9\-\' ]+$")


def validate_lemma(value: str) -> str:
    """Firestore に安全な見出し語だけを受け付ける。"""

    if not LEMMA_ALLOWED_PATTERN.match(value):
        raise ValueError(
            "lemma must match ^[A-Za-z0-9\\-\\' ]+$ (英数字・半角スペース・ハイフン・アポストロフィのみ)"
        )
    if any(ord(ch) < 0x20 for ch in value):
        raise ValueError("lemma must not contain control characters")
    return value
