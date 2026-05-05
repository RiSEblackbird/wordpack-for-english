from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, Field

from ...models.word import ExampleCategory


class WordLookupExample(BaseModel):
    en: str
    ja: str
    grammar_ja: str | None = None
    category: ExampleCategory


class WordLookupResponse(BaseModel):
    lemma: str
    sense_title: str | None
    definition: str | None
    word_pack_id: str | None = None
    examples: list[WordLookupExample] = Field(default_factory=list)
    llm_model: str | None = None
    llm_params: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


def extract_definition_from_senses(data: Mapping[str, Any]) -> str | None:
    senses = data.get("senses") or []
    for sense in senses if isinstance(senses, list) else []:
        if not isinstance(sense, Mapping):
            continue
        definition = str(sense.get("definition_ja") or "").strip()
        if definition:
            return definition
        gloss = str(sense.get("gloss_ja") or "").strip()
        if gloss:
            return gloss
    return None


def collect_examples_for_lookup(data: Mapping[str, Any]) -> list[WordLookupExample]:
    examples: list[WordLookupExample] = []
    raw_examples = data.get("examples") or {}
    if not isinstance(raw_examples, Mapping):
        return examples

    for category, items in raw_examples.items():
        if not isinstance(items, list):
            continue
        try:
            cat_enum = ExampleCategory(category)
        except ValueError:
            continue
        for item in items:
            if not isinstance(item, Mapping):
                continue
            examples.append(
                WordLookupExample(
                    en=str(item.get("en") or ""),
                    ja=str(item.get("ja") or ""),
                    grammar_ja=(item.get("grammar_ja") or None),
                    category=cat_enum,
                )
            )
    return examples


def build_lookup_response(
    *,
    lemma: str,
    sense_title: str | None,
    word_pack_id: str | None,
    word_pack_data: Mapping[str, Any],
    created_at: str | None,
    updated_at: str | None,
) -> WordLookupResponse:
    return WordLookupResponse(
        lemma=lemma,
        sense_title=str(sense_title or word_pack_data.get("sense_title") or "") or None,
        definition=extract_definition_from_senses(word_pack_data),
        word_pack_id=word_pack_id,
        examples=collect_examples_for_lookup(word_pack_data),
        llm_model=word_pack_data.get("llm_model"),
        llm_params=word_pack_data.get("llm_params"),
        created_at=created_at,
        updated_at=updated_at,
    )
