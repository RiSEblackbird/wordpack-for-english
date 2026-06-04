from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import Any, TypeVar

SnapshotT = TypeVar("SnapshotT")


def extract_count_from_aggregation(aggregation: Sequence[Any] | None) -> int:
    """Firestore aggregation count の SDK 差分を吸収して int に正規化する。"""

    if not aggregation:
        return 0
    count_value = _extract_aggregation_count_value(aggregation[0])
    return int(count_value or 0)


def _extract_aggregation_count_value(candidate: Any) -> Any | None:
    """Return a count value from Firestore aggregation result variants."""

    if candidate is None:
        return None
    if isinstance(candidate, (int, float)):
        return candidate
    if isinstance(candidate, str):
        return candidate if candidate.isdigit() else None
    if isinstance(candidate, Mapping):
        for key in ("count", "total", "integerValue"):
            if key in candidate:
                return candidate[key]
        aggregate_fields = candidate.get("aggregateFields")
        if isinstance(aggregate_fields, Mapping):
            return _extract_count_from_mapping_values(aggregate_fields)
    if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
        for item in candidate:
            value = _extract_aggregation_count_value(item)
            if value is not None:
                return value
        return None

    aggregate_fields = getattr(candidate, "aggregate_fields", None)
    if isinstance(aggregate_fields, Mapping):
        value = _extract_count_from_mapping_values(aggregate_fields)
        if value is not None:
            return value

    value = getattr(candidate, "value", None)
    if value is not None:
        return value
    return None


def _extract_count_from_mapping_values(fields: Mapping[str, Any]) -> Any | None:
    for key in ("count", "total", "field_1"):
        if key in fields:
            return _extract_aggregation_count_value(fields[key])
    if len(fields) == 1:
        return _extract_aggregation_count_value(next(iter(fields.values())))
    return None


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
