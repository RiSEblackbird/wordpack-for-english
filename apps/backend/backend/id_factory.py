"""ID 生成ユーティリティ。

WordPack の document ID は Firestore のパス制約に抵触しない文字だけで構成し、
既存データの互換性を保つため prefix "wp:" を維持したまま UUID を使用する。
"""

from __future__ import annotations

import uuid


def generate_word_pack_id() -> str:
    """WordPack の新規 ID を生成する。

    これまでの `wp:{lemma}:{short_uuid}` 形式から lemma を排除し、
    Firestore のパス制約を確実に回避するため純粋な UUID を採用する。
    旧形式の ID もそのまま扱えるため、既存データとの互換性を損なわない。
    """

    return f"wp:{uuid.uuid4().hex}"
