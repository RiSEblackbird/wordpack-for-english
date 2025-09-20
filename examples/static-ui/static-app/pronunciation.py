"""互換ラッパ: 本実装は `apps/backend/backend/pronunciation.py` に統一。

既存コードが `app.pronunciation.to_ipa` を参照している場合の後方互換目的。
将来的には本モジュールの利用を廃止し、`backend` 実装へ移行してください。
"""

from typing import Optional

try:
    # ランタイムで backend 側の実装を参照
    from backend.pronunciation import generate_pronunciation  # type: ignore
except Exception:  # pragma: no cover
    generate_pronunciation = None  # type: ignore


def to_ipa(word: str) -> str:
    if generate_pronunciation is None:
        raise NotImplementedError("Pronunciation module not available")
    p = generate_pronunciation(word)
    return p.ipa_GA or ""
