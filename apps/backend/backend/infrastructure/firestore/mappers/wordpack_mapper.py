from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..payloads import EXAMPLE_CATEGORIES


def extract_example_total(metadata: Mapping[str, Any] | None) -> tuple[int, bool]:
    """examples_category_counts から合計件数を抽出し、信頼性の有無を返す。"""

    raw_counts = (metadata or {}).get("examples_category_counts")
    if not isinstance(raw_counts, Mapping):
        return 0, False
    try:
        total = sum(int(raw_counts.get(cat, 0) or 0) for cat in EXAMPLE_CATEGORIES)
    except Exception:
        return 0, False
    return max(0, total), True
