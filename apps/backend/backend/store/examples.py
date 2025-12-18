from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .common import normalize_non_negative_int

# WordPack 例文カテゴリの固定順序。UI/Firestore 双方で共有する。
EXAMPLE_CATEGORIES: tuple[str, ...] = ("Dev", "CS", "LLM", "Business", "Common")


def iter_example_rows(examples: Mapping[str, Any]) -> Iterable[tuple]:
    """例文ペイロードを正規化し、永続化層が扱いやすい行タプルへ変換する。

    Firestore/エミュレータ/フェイクのいずれでも同じ入力整形を使うことで、
    ストレージ差分による挙動の揺れを防ぐ。
    """

    for category in EXAMPLE_CATEGORIES:
        arr = examples.get(category)
        if not isinstance(arr, Sequence):
            continue
        for pos, item in enumerate(arr):
            if not isinstance(item, Mapping):
                continue
            en = str(item.get("en") or "").strip()
            ja = str(item.get("ja") or "").strip()
            if not en or not ja:
                continue
            grammar_ja = str(item.get("grammar_ja") or "").strip() or None
            llm_model = str(item.get("llm_model") or "").strip() or None
            llm_params = str(item.get("llm_params") or "").strip() or None
            checked_only_count = normalize_non_negative_int(
                (item or {}).get("checked_only_count")
            )
            learned_count = normalize_non_negative_int((item or {}).get("learned_count"))
            transcription_typing_count = normalize_non_negative_int(
                (item or {}).get("transcription_typing_count")
            )
            yield (
                category,
                pos,
                en,
                ja,
                grammar_ja,
                llm_model,
                llm_params,
                checked_only_count,
                learned_count,
                transcription_typing_count,
            )
