from __future__ import annotations

import json
import uuid
from threading import Lock
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from google.api_core import exceptions as gexc
from google.api_core.exceptions import AlreadyExists
from google.cloud import firestore as _firestore

from ..batch import coerce_firestore_snapshot, extract_count_from_aggregation
from ..google_module import resolve_firestore_module
from ..mappers.example_mapper import (
    build_search_payload,
    extract_search_terms,
    normalize_search_text,
)
from ..mappers.wordpack_mapper import extract_example_total
from ..payloads import (
    EXAMPLE_CATEGORIES,
    build_sense_title,
    iter_example_rows,
    merge_core_with_examples,
    normalize_non_negative_int,
    split_examples_from_payload,
)
from ....logging import logger

firestore = resolve_firestore_module(_firestore)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _extract_count_from_aggregation(aggregation: Sequence[Any] | None) -> int:
    return extract_count_from_aggregation(aggregation)


def _normalize_search_text(text: str | None) -> str:
    return normalize_search_text(text)


def _extract_search_terms(normalized_text: str) -> list[str]:
    return extract_search_terms(normalized_text)


def _build_search_payload(en: str) -> dict[str, Any]:
    return build_search_payload(en)


def _extract_example_total(metadata: Mapping[str, Any] | None) -> tuple[int, bool]:
    return extract_example_total(metadata)


def _coerce_firestore_snapshot(candidate: Any) -> firestore.DocumentSnapshot | None:
    return coerce_firestore_snapshot(candidate)


class FirestoreBaseRepository:
    """Firestore concrete repository 共通のヘルパー。"""

    def __init__(self, client: firestore.Client):
        self._client = client

    def _now_iso(self) -> str:
        return _now_iso()

    def _extract_count_from_aggregation(self, aggregation: Sequence[Any] | None) -> int:
        return _extract_count_from_aggregation(aggregation)

    def _normalize_search_text(self, text: str | None) -> str:
        return _normalize_search_text(text)

    def _extract_search_terms(self, normalized_text: str) -> list[str]:
        return _extract_search_terms(normalized_text)

    def _build_search_payload(self, en: str) -> dict[str, Any]:
        return _build_search_payload(en)

    def _extract_example_total(self, metadata: Mapping[str, Any] | None) -> tuple[int, bool]:
        return _extract_example_total(metadata)

    def _coerce_firestore_snapshot(self, candidate: Any) -> firestore.DocumentSnapshot | None:
        return _coerce_firestore_snapshot(candidate)


FirestoreBaseStore = FirestoreBaseRepository

__all__ = [
    "AlreadyExists",
    "Any",
    "EXAMPLE_CATEGORIES",
    "FirestoreBaseRepository",
    "FirestoreBaseStore",
    "Iterable",
    "Lock",
    "Mapping",
    "Sequence",
    "UTC",
    "datetime",
    "defaultdict",
    "firestore",
    "gexc",
    "json",
    "logger",
    "normalize_non_negative_int",
    "uuid",
    "_build_search_payload",
    "_coerce_firestore_snapshot",
    "_extract_count_from_aggregation",
    "_extract_example_total",
    "_extract_search_terms",
    "_normalize_search_text",
    "_now_iso",
]
