from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from ..sense_title import choose_sense_title
from .common import normalize_non_negative_int
from .examples import EXAMPLE_CATEGORIES


def split_examples_from_payload(
    data: str | Mapping[str, Any]
) -> tuple[
    str,
    Mapping[str, Any] | None,
    str,
    list[str],
    tuple[int, int],
    tuple[str | None, str | None],
]:
    """WordPack 入力 JSON から例文部分を分離し、コア情報を返す。

    Firestore への保存ではコア情報と例文を別コレクションへ分割するため、
    ここで事前に抽出しておく。パース不能な入力は安全な空 JSON として扱う。
    """

    checked_only_count = 0
    learned_count = 0
    lemma_llm_model: str | None = None
    lemma_llm_params: str | None = None

    if isinstance(data, Mapping):
        parsed: Mapping[str, Any] = dict(data)
    else:
        try:
            parsed = json.loads(data) if data else {}
        except Exception:
            empty_json = json.dumps({}, ensure_ascii=False)
            return (
                data if isinstance(data, str) else empty_json,
                None,
                "",
                [],
                (checked_only_count, learned_count),
                (lemma_llm_model, lemma_llm_params),
            )
        if not isinstance(parsed, Mapping):
            empty_json = json.dumps({}, ensure_ascii=False)
            return (
                data if isinstance(data, str) else empty_json,
                None,
                "",
                [],
                (checked_only_count, learned_count),
                (lemma_llm_model, lemma_llm_params),
            )

    sense_title = ""
    sense_candidates: list[str] = []
    try:
        sense_title = str(parsed.get("sense_title") or "").strip()
    except Exception:
        sense_title = ""

    try:
        val = str(parsed.get("llm_model") or "").strip()
        lemma_llm_model = val or None
    except Exception:
        lemma_llm_model = None
    try:
        val = str(parsed.get("llm_params") or "").strip()
        lemma_llm_params = val or None
    except Exception:
        lemma_llm_params = None

    try:
        checked_only_count = normalize_non_negative_int((parsed or {}).get("checked_only_count"))
    except Exception:
        checked_only_count = 0
    try:
        learned_count = normalize_non_negative_int((parsed or {}).get("learned_count"))
    except Exception:
        learned_count = 0

    senses_payload = parsed.get("senses") if isinstance(parsed, Mapping) else None
    if isinstance(senses_payload, Sequence):
        for sense in senses_payload:
            if not isinstance(sense, Mapping):
                continue
            for key in (
                "gloss_ja",
                "term_overview_ja",
                "term_core_ja",
                "definition_ja",
                "nuances_ja",
            ):
                try:
                    val = str(sense.get(key) or "").strip()
                except Exception:
                    val = ""
                if val:
                    sense_candidates.append(val)

    examples = parsed.get("examples") if isinstance(parsed, Mapping) else None
    if isinstance(examples, Mapping):
        core = dict(parsed)
        core.pop("examples", None)
        return (
            json.dumps(core, ensure_ascii=False),
            examples,
            sense_title,
            sense_candidates,
            (checked_only_count, learned_count),
            (lemma_llm_model, lemma_llm_params),
        )
    serialized = json.dumps(parsed, ensure_ascii=False) if not isinstance(data, str) else data
    return (
        serialized,
        None,
        sense_title,
        sense_candidates,
        (checked_only_count, learned_count),
        (lemma_llm_model, lemma_llm_params),
    )


def merge_core_with_examples(
    core_json: str, rows: Sequence[Mapping[str, Any]]
) -> str:
    """WordPack 本体 JSON に例文一覧を合成して返す。"""

    try:
        core = json.loads(core_json) if core_json else {}
    except Exception:
        core = {}
    examples: dict[str, list[dict[str, Any]]] = {cat: [] for cat in EXAMPLE_CATEGORIES}
    for r in rows:
        category = r["category"]
        item: dict[str, Any] = {"en": r["en"], "ja": r["ja"]}
        if r.get("grammar_ja"):
            item["grammar_ja"] = r["grammar_ja"]
        if r.get("llm_model"):
            item["llm_model"] = r["llm_model"]
        if r.get("llm_params"):
            item["llm_params"] = r["llm_params"]
        item["checked_only_count"] = normalize_non_negative_int(r.get("checked_only_count"))
        item["learned_count"] = normalize_non_negative_int(r.get("learned_count"))
        item["transcription_typing_count"] = normalize_non_negative_int(
            r.get("transcription_typing_count")
        )
        examples.setdefault(category, []).append(item)
    for cat in EXAMPLE_CATEGORIES:
        examples.setdefault(cat, [])
    core["examples"] = examples
    return json.dumps(core, ensure_ascii=False)


def build_sense_title(lemma: str, sense_title_raw: str, sense_candidates: list[str]) -> str:
    """Firestore 用に見出し語の日本語タイトルを決定する。

    SQLite 時代と同じ優先順位（候補 → sense_title → lemma）で返すことで、
    既存のテストや UI との挙動整合性を維持する。
    """

    return choose_sense_title(
        sense_title_raw,
        sense_candidates,
        lemma=lemma,
        limit=40,
    )
