from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException


def llm_json_parse_error(*, lemma: str, **_: Any) -> HTTPException:
    return HTTPException(
        status_code=502,
        detail={
            "message": "LLM output JSON parse failed (strict mode)",
            "reason_code": "LLM_JSON_PARSE",
            "diagnostics": {"lemma": lemma},
            "hint": "モデル/プロンプトの安定化、text.verbosity を lower に、または strict_mode を無効化して挙動を確認してください。ログの wordpack_llm_json_parse_failed を参照。",
        },
    )


def wordpack_empty_content_error(
    *, diagnostics: dict[str, Any] | None, **_: Any
) -> HTTPException:
    return HTTPException(
        status_code=502,
        detail={
            "message": "WordPack generation returned empty content (no senses/examples)",
            "reason_code": "EMPTY_CONTENT",
            "diagnostics": diagnostics or {},
            "hint": "LLM_TIMEOUT_MS/LLM_MAX_TOKENS/モデル安定タグを調整してください。ログの wordpack_llm_* を確認。",
        },
    )


def wordpack_regeneration_empty_content_error(
    *, diagnostics: dict[str, Any] | None, **_: Any
) -> HTTPException:
    return HTTPException(
        status_code=502,
        detail={
            "message": "WordPack regeneration returned empty content (no senses/examples)",
            "reason_code": "EMPTY_CONTENT",
            "diagnostics": diagnostics or {},
            "hint": "LLM_TIMEOUT_MS/LLM_MAX_TOKENS/モデル安定タグを調整してください。ログの wordpack_llm_* を確認。",
        },
    )


def example_empty_content_error(
    *, lemma: str, diagnostics: dict[str, Any] | None, category: str, **_: Any
) -> HTTPException:
    return HTTPException(
        status_code=502,
        detail={
            "message": "Example generation returned empty content",
            "reason_code": "EMPTY_CONTENT",
            "diagnostics": diagnostics or {"lemma": lemma, "category": category},
            "hint": "LLM_TIMEOUT_MS/LLM_MAX_TOKENS/モデル安定タグを調整してください。ログの wordpack_llm_* を確認。",
        },
    )


def generation_error_mapping() -> dict[str, Callable[..., HTTPException]]:
    return {
        "llm_json_parse": llm_json_parse_error,
        "empty_content": wordpack_empty_content_error,
    }


def regeneration_error_mapping() -> dict[str, Callable[..., HTTPException]]:
    return {
        "llm_json_parse": llm_json_parse_error,
        "empty_content": wordpack_regeneration_empty_content_error,
    }


def example_error_mapping(category: str) -> dict[str, Callable[..., HTTPException]]:
    return {
        "llm_json_parse": lambda *, lemma, **__: HTTPException(
            status_code=502,
            detail={
                "message": "LLM output JSON parse failed (strict mode)",
                "reason_code": "LLM_JSON_PARSE",
                "diagnostics": {"lemma": lemma, "category": category},
                "hint": "モデル/プロンプトの安定化、text.verbosity を lower に、または strict_mode を無効化して挙動を確認してください。ログの wordpack_llm_json_parse_failed を参照。",
            },
        ),
        "empty_content": lambda *, lemma, diagnostics, **kwargs: example_empty_content_error(
            lemma=lemma,
            diagnostics=diagnostics,
            category=category,
            **kwargs,
        ),
    }
