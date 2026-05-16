from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

ExampleListTuple = tuple[
    int,
    str,
    str,
    str,
    str,
    str,
    str | None,
    str,
    str | None,
    int,
    int,
    int,
]


class ExampleRepository(Protocol):
    def list_examples(self, *, limit: int, offset: int, **filters: Any) -> list[ExampleListTuple]:
        ...

    def count_examples(self, **filters: Any) -> int:
        ...

    def append_examples(
        self, word_pack_id: str, category: str, items: Sequence[Mapping[str, Any]]
    ) -> int:
        ...

    def delete_example(self, word_pack_id: str, category: str, index: int) -> int | None:
        ...

    def delete_examples_by_ids(self, example_ids: Sequence[int]) -> tuple[int, list[int]]:
        ...

    def update_example_study_progress(
        self, example_id: int, checked_increment: int, learned_increment: int
    ) -> tuple[str, int, int] | None:
        ...

    def update_example_transcription_typing(
        self, example_id: int, input_length: int
    ) -> int | None:
        ...
