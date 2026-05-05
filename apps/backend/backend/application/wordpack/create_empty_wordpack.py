from __future__ import annotations

from fastapi import HTTPException

from ...config import settings
from ...models.word import DEFAULT_ETYMOLOGY_PLACEHOLDER, WordPack
from ...providers import get_llm_provider
from ...sense_title import choose_sense_title


def generate_sense_title_for_empty_wordpack(lemma: str) -> str | None:
    generated_title: str | None = None
    try:
        llm = get_llm_provider()
        prompt = (
            "次の英語の見出し語に対して、日本語の短い語義タイトルを1つだけ返してください。\n"
            "条件: 最大12文字、名詞句ベース、日本語のみ、説明文や引用符や記号は不要。\n"
            "見出し語: "
            f"{lemma}\n"
            "出力:"
        )
        try:
            out: str = llm.complete(prompt)  # type: ignore[attr-defined]
        except Exception as exc:
            if settings.strict_mode:
                raise HTTPException(
                    status_code=502,
                    detail={
                        "message": "LLM failed to generate sense_title (strict mode)",
                        "reason_code": "LLM_FAILURE",
                        "diagnostics": {"lemma": lemma, "error": str(exc)[:200]},
                    },
                ) from exc
            out = ""
        cand = (out or "").strip().splitlines()[0] if isinstance(out, str) else ""
        cand = cand.strip().strip('"').strip("'")
        if cand:
            generated_title = cand[:20]
    except HTTPException:
        raise
    except Exception:
        generated_title = None
    return generated_title


def build_empty_wordpack(lemma: str) -> WordPack:
    generated_title = generate_sense_title_for_empty_wordpack(lemma)
    return WordPack(
        lemma=lemma,
        sense_title=(
            generated_title or choose_sense_title(None, [], lemma=lemma, limit=20)
        ),
        pronunciation={
            "ipa_GA": None,
            "ipa_RP": None,
            "syllables": None,
            "stress_index": None,
            "linking_notes": [],
        },
        senses=[],
        collocations={
            "general": {"verb_object": [], "adj_noun": [], "prep_noun": []},
            "academic": {"verb_object": [], "adj_noun": [], "prep_noun": []},
        },
        contrast=[],
        examples={"Dev": [], "CS": [], "LLM": [], "Business": [], "Common": []},
        etymology={"note": DEFAULT_ETYMOLOGY_PLACEHOLDER, "confidence": "low"},
        study_card="",
        citations=[],
        confidence="low",
    )
