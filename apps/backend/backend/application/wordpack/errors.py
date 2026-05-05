from __future__ import annotations

from typing import Any, Callable, Mapping

from fastapi import HTTPException

from ...config import settings
from ...logging import logger


def resolve_http_exception(
    mapping: Mapping[str, Callable[..., HTTPException]] | None,
    key: str,
    **kwargs: Any,
) -> HTTPException | None:
    if not mapping:
        return None
    handler = mapping.get(key)
    if handler is None:
        return None
    try:
        return handler(**kwargs)
    except HTTPException as exc:
        return exc
    except Exception as exc:
        logger.warning(
            "wordpack_error_mapping_failed",
            key=key,
            error=str(exc),
        )
        return None


def handle_flow_runtime_error(
    exc: RuntimeError,
    *,
    lemma: str,
    http_error_mapping: Mapping[str, Callable[..., HTTPException]] | None,
) -> None:
    msg = str(exc)
    low = msg.lower()
    if "failed to parse llm json" in low and settings.strict_mode:
        custom_exc = resolve_http_exception(http_error_mapping, "llm_json_parse", lemma=lemma)
        if custom_exc:
            raise custom_exc from exc
        raise HTTPException(
            status_code=502,
            detail={
                "message": "LLM output JSON parse failed (strict mode)",
                "reason_code": "LLM_JSON_PARSE",
                "diagnostics": {"lemma": lemma},
                "hint": "モデル/プロンプトの安定化、text.verbosity を lower に、または strict_mode を無効化して挙動を確認してください。ログの wordpack_llm_json_parse_failed を参照。",
            },
        ) from exc

    if "reason_code=" in msg:
        if "reason_code=TIMEOUT" in msg:
            raise HTTPException(
                status_code=504,
                detail={
                    "message": "LLM request timed out",
                    "reason_code": "TIMEOUT",
                    "hint": "LLM_TIMEOUT_MS を増やす（例: 90000）、HTTP全体のタイムアウトは +5秒。リトライも検討。",
                },
            ) from exc
        if "reason_code=RATE_LIMIT" in msg:
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "LLM provider rate limited",
                    "reason_code": "RATE_LIMIT",
                    "hint": "少し待って再試行。モデル/アカウントのレート制限を確認。リトライ上限を増やす。",
                },
            ) from exc
        if (
            "reason_code=AUTH" in msg
            or "invalid api key" in low
            or "unauthorized" in low
        ):
            raise HTTPException(
                status_code=401,
                detail={
                    "message": "LLM provider authentication failed",
                    "reason_code": "AUTH",
                    "hint": "OPENAI_API_KEY を確認（有効/権限/課金）。コンテナ環境変数に反映されているか確認。",
                },
            ) from exc
        if "reason_code=PARAM_UNSUPPORTED" in msg:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "LLM parameter not supported by model",
                    "reason_code": "PARAM_UNSUPPORTED",
                    "hint": "モデルの仕様変更により 'max_tokens' 非対応の可能性。最新SDK/パラメータを使用してください。",
                },
            ) from exc

    reason_code = getattr(exc, "reason_code", None)
    diagnostics = getattr(exc, "diagnostics", None)
    if reason_code == "EMPTY_CONTENT":
        custom_exc = resolve_http_exception(
            http_error_mapping,
            "empty_content",
            lemma=lemma,
            diagnostics=diagnostics or {},
        )
        if custom_exc:
            raise custom_exc from exc
        raise HTTPException(
            status_code=502,
            detail={
                "message": "WordPack generation returned empty content (no senses/examples)",
                "reason_code": reason_code,
                "diagnostics": diagnostics or {},
                "hint": "LLM_TIMEOUT_MS/LLM_MAX_TOKENS/モデル安定タグを調整してください。ログの wordpack_llm_* を確認。",
            },
        ) from exc
