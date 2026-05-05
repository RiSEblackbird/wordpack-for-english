from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExampleRecord:
    id: int
    word_pack_id: str
    category: str
    text: str
