from __future__ import annotations

from typing import Protocol


class ExampleRepository(Protocol):
    def list_examples(self, *, limit: int, offset: int, **filters):
        ...

    def count_examples(self, **filters) -> int:
        ...
