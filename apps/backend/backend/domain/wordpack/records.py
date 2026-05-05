from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WordPackListRow:
    id: str
    lemma: str
    created_at: str | None
    updated_at: str | None
    preview: dict[str, Any]
    guest_public: bool
    example_counts: dict[str, int]
