from __future__ import annotations

from typing import Protocol


class WordPackRepository(Protocol):
    def get_word_pack(self, word_pack_id: str):
        ...

    def save_word_pack(self, word_pack_id: str, lemma: str, data_json: str) -> None:
        ...

    def delete_word_pack(self, word_pack_id: str) -> bool:
        ...

    def find_word_pack_id_by_lemma(self, lemma: str) -> str | None:
        ...
