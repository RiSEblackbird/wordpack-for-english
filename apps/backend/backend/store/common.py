from __future__ import annotations

from typing import Any


def normalize_non_negative_int(value: Any) -> int:
    """与えられた値を非負整数に正規化する。

    数値の正規化を I/O 層から切り離すことで、Firestore やエミュレータには常に
    整合した値だけが保存される。学習進捗カウンタは UI のバグで負値が送られて
    しまうと再採番が破綻するため、ここでゼロ以上に矯正しておく。"""

    try:
        ivalue = int(value)
    except (TypeError, ValueError):
        return 0
    return ivalue if ivalue >= 0 else 0
