from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import Any, TypeVar

SnapshotT = TypeVar("SnapshotT")


def extract_count_from_aggregation(aggregation: Sequence[Any] | None) -> int:
    """Firestore aggregation count の SDK 差分を吸収して int に正規化する。"""

    if not aggregation:
        return 0
    result = aggregation[0]
    count_value: Any | None = None
    try:
        count_value = result["count"]  # type: ignore[index]
    except Exception:
        aggregate_fields = getattr(result, "aggregate_fields", None)
        if isinstance(aggregate_fields, Mapping):
            count_value = aggregate_fields.get("count")
    if count_value is None and getattr(result, "alias", None) == "count":
        count_value = getattr(result, "value", None)
    return int(count_value or 0)


def coerce_firestore_snapshot(candidate: Any) -> SnapshotT | None:
    """transaction.get の戻り値（snapshot/generator/list）を単一 snapshot に正規化する。"""

    if candidate is None:
        return None
    if hasattr(candidate, "exists"):
        return candidate
    if isinstance(candidate, Iterator):
        return next(candidate, None)
    if isinstance(candidate, Iterable) and not isinstance(candidate, (str, bytes, Mapping)):
        iterator = iter(candidate)
        return next(iterator, None)
    return None
