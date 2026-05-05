from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArticleRecord:
    id: str
    title: str | None
    text: str
    created_at: str | None = None
    updated_at: str | None = None
