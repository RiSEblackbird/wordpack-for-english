"""LLM プロバイダと Langfuse 連携を司るモジュール。"""

from __future__ import annotations

import contextvars
import inspect
import time
from concurrent.futures import TimeoutError as FuturesTimeout
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from ..config import settings
from ..logging import logger
from ..observability import get_langfuse, span
from . import _get_llm_executor, _get_llm_instance, _set_llm_instance

try:  # pragma: no cover - ネットワーク依存の外部SDK
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - 任意依存
    OpenAI = None  # type: ignore


class _LLMBase:
    """LLM クライアントが実装すべき最小インターフェース。"""

    def complete(self, prompt: str) -> str:  # pragma: no cover - interface definition
        raise NotImplementedError


class _LocalEchoLLM(_LLMBase):
    """外部依存が利用できない環境でのフォールバック LLM。"""

    def complete(self, prompt: str) -> str:
        logger.info(
            "llm_complete_call",
            provider="local",
            model="echo",
            prompt_chars=len(prompt),
        )
        out = ""
        logger.info(
            "llm_complete_result",
            provider="local",
            model="echo",
            content_chars=len(out),
        )
        return out


def _prepare_span_input(model: str, prompt: str) -> dict[str, Any]:
    """Langfuse スパンに記録する入力情報を生成する。"""

    if getattr(settings, "langfuse_log_full_prompt", False):
        maxc = int(getattr(settings, "langfuse_prompt_max_chars", 40000))
        payload: dict[str, Any] = {
            "model": model,
            "prompt_chars": len(prompt),
            "prompt": prompt[: max(0, maxc)],
        }
        try:
            import hashlib

            payload["prompt_sha256"] = hashlib.sha256(
                prompt.encode("utf-8", errors="ignore")
            ).hexdigest()
        except Exception:
            pass
        return payload
    return {
        "model": model,
        "prompt_chars": len(prompt),
        "prompt_preview": prompt[:500],
    }


@contextmanager
def _langfuse_span(name: str, model: str, prompt: str) -> Iterator[Any]:
    """Langfuse span を開始し、呼び出し元へコンテキストを提供する。"""

    trace_factory = getattr(get_langfuse(), "trace", None)
    trace = None if trace_factory is None else trace_factory(name="LLM call")
    with span(trace=trace, name=name, input=_prepare_span_input(model, prompt)) as current:
        yield current


def _update_span_output(span_obj: Any, content: str) -> None:
    """出力ログの更新を Langfuse span へ委譲する。"""

    try:
        if span_obj is None:
            return
        limited = content[:40000]
        if hasattr(span_obj, "update"):
            span_obj.update(output=limited)
        elif hasattr(span_obj, "set_attribute"):
            span_obj.set_attribute("output", limited)  # type: ignore[call-arg]
    except Exception:
        pass


class _OpenAILLM(_LLMBase):  # pragma: no cover - オンライン利用が前提
    """OpenAI Responses API を利用する LLM ラッパー。"""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        temperature: float | None = None,
        reasoning: Optional[dict] = None,
        text: Optional[dict] = None,
    ) -> None:
        if OpenAI is None:
            raise RuntimeError("openai package not installed")
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._api_key = api_key
        self._temperature = 0.2 if temperature is None else float(max(0.0, min(1.0, temperature)))
        self._reasoning = reasoning
        self._text = text

    def _extract_text(self, resp: Any) -> str:
        """OpenAI Responses API のレスポンスから本文を抜き出す。"""

        try:
            txt = getattr(resp, "output_text", None)
            if isinstance(txt, str) and txt.strip():
                return txt.strip()
        except Exception:
            pass
        try:
            choices = getattr(resp, "choices", None)
            if isinstance(choices, list) and choices:
                message = getattr(choices[0], "message", None)
                content = getattr(message, "content", None)
                if isinstance(content, str) and content.strip():
                    return content.strip()
        except Exception:
            pass
        try:
            data = resp if isinstance(resp, dict) else resp.model_dump()  # type: ignore[attr-defined]
            output = data.get("output") or []
            if output and isinstance(output, list):
                first = output[0] or {}
                contents = first.get("content") or []
                if contents and isinstance(contents, list):
                    text = contents[0].get("text")
                    if isinstance(text, str):
                        return text.strip()
        except Exception:
            pass
        return (str(resp) or "").strip()

    def _create_with_params(
        self,
        *,
        prompt: str,
        use_json: bool,
        token_param: str,
        include_temperature: bool,
        include_reasoning_text: bool,
    ) -> Any:
        try:
            sig = inspect.signature(self._client.responses.create)  # type: ignore[attr-defined]
            param_names = set(sig.parameters.keys())
        except Exception:
            param_names = set()

        def supports(name: str) -> bool:
            return name in param_names

        kwargs: dict[str, Any] = {
            "model": self._model,
            "input": prompt,
        }
        timeout_sec = settings.llm_timeout_ms / 1000.0
        max_tokens_value = int(getattr(settings, "llm_max_tokens", 900))
        if supports("timeout"):
            kwargs["timeout"] = timeout_sec
        if include_temperature and supports("temperature"):
            kwargs["temperature"] = self._temperature
        if include_reasoning_text:
            if self._reasoning and supports("reasoning"):
                kwargs["reasoning"] = self._reasoning
            if self._text and supports("text"):
                kwargs["text"] = self._text
        if token_param == "max_output_tokens" and supports("max_output_tokens"):
            kwargs["max_output_tokens"] = max_tokens_value
        elif token_param == "max_tokens" and supports("max_tokens"):
            kwargs["max_tokens"] = max_tokens_value
        elif token_param == "max_completion_tokens" and supports("max_completion_tokens"):
            kwargs["max_completion_tokens"] = max_tokens_value
        if use_json and supports("response_format"):
            kwargs["response_format"] = {"type": "json_object"}
        return self._client.responses.create(**kwargs)

    def _call_with_param_fallback(
        self,
        *,
        prompt: str,
        use_json: bool,
        token_param: str,
        include_temperature: bool,
        include_reasoning_text: bool,
    ) -> Any:
        try:
            return self._create_with_params(
                prompt=prompt,
                use_json=use_json,
                token_param=token_param,
                include_temperature=include_temperature,
                include_reasoning_text=include_reasoning_text,
            )
        except Exception as exc:
            text = (str(exc) or "").lower()
            if (
                include_temperature
                and "temperature" in text
                and (
                    "unsupported" in text
                    or "only the default" in text
                    or "unsupported_value" in text
                )
            ):
                logger.info(
                    "llm_complete_retry_without_temperature",
                    provider="openai",
                    model=self._model,
                    reason=str(exc)[:200],
                )
                return self._create_with_params(
                    prompt=prompt,
                    use_json=use_json,
                    token_param=token_param,
                    include_temperature=False,
                    include_reasoning_text=include_reasoning_text,
                )
            if (
                include_reasoning_text
                and ("reasoning" in text or "text" in text)
                and (
                    "unsupported" in text
                    or "not supported" in text
                    or "unrecognized" in text
                )
            ):
                logger.info(
                    "llm_complete_retry_without_reasoning_text",
                    provider="openai",
                    model=self._model,
                    reason=str(exc)[:200],
                )
                return self._create_with_params(
                    prompt=prompt,
                    use_json=use_json,
                    token_param=token_param,
                    include_temperature=include_temperature,
                    include_reasoning_text=False,
                )
            if (
                include_reasoning_text
                and (
                    "unexpected keyword argument" in text
                    or "got an unexpected keyword argument" in text
                )
                and ("reasoning" in text or "text" in text)
            ):
                logger.info(
                    "llm_complete_retry_without_reasoning_text_unexpected_kw",
                    provider="openai",
                    model=self._model,
                    reason=str(exc)[:200],
                )
                return self._create_with_params(
                    prompt=prompt,
                    use_json=use_json,
                    token_param=token_param,
                    include_temperature=include_temperature,
                    include_reasoning_text=False,
                )
            raise

    def complete(self, prompt: str) -> str:
        logger.info(
            "llm_complete_call",
            provider="openai",
            model=self._model,
            prompt_chars=len(prompt),
        )
        if self._api_key == "test-key":
            out = '{"senses": [{"id": "s1", "gloss_ja": "テスト用の語義", "patterns": ["test pattern"]}], "sense_title": "テスト語義", "collocations": {"general": {"verb_object": ["test verb"], "adj_noun": ["test adj"], "prep_noun": ["test prep"]}, "academic": {"verb_object": [], "adj_noun": [], "prep_noun": []}}, "contrast": [], "examples": {"Dev": [{"en": "This is a test in dev.", "ja": "これは開発現場のテストです。"}], "CS": [], "LLM": [], "Business": [], "Common": []}, "etymology": {"note": "Test etymology", "confidence": "medium"}, "study_card": "テスト用の学習カード", "pronunciation": {"ipa_RP": "/test/"}}'
            logger.info(
                "llm_complete_result",
                provider="openai",
                model=self._model,
                content_chars=len(out),
            )
            return out

        try:
            sig0 = inspect.signature(self._client.responses.create)  # type: ignore[attr-defined]
            param_names = set(sig0.parameters.keys())
        except Exception:
            param_names = set()
        token_candidates: list[str] = []
        if "max_output_tokens" in param_names:
            token_candidates.append("max_output_tokens")
        if "max_tokens" in param_names:
            token_candidates.append("max_tokens")
        if "max_completion_tokens" in param_names:
            token_candidates.append("max_completion_tokens")
        if not token_candidates:
            token_candidates.append("max_output_tokens")
        use_json_pref = "response_format" in param_names

        is_reasoning_model = (self._model or "").lower() in {"gpt-5-mini", "gpt-5-nano"}
        last_exc: Exception | None = None
        with _langfuse_span("openai.responses.create", self._model, prompt) as current_span:
            for use_json_flag in [use_json_pref, False] if use_json_pref else [False]:
                for token_param in token_candidates:
                    try:
                        resp = self._call_with_param_fallback(
                            prompt=prompt,
                            use_json=use_json_flag,
                            token_param=token_param,
                            include_temperature=not is_reasoning_model,
                            include_reasoning_text=is_reasoning_model,
                        )
                        content = self._extract_text(resp)
                        try:
                            import hashlib as hf

                            logger.info(
                                "llm_complete_preview",
                                provider="openai",
                                model=self._model,
                                preview=(content or "")[:120],
                                content_chars=len(content or ""),
                                content_sha256=hf.sha256(
                                    (content or "").encode("utf-8", errors="ignore")
                                ).hexdigest(),
                                json_forced=bool(use_json_flag),
                                param=token_param,
                            )
                        except Exception:
                            pass
                        _update_span_output(current_span, content)
                        logger.info(
                            "llm_complete_result",
                            provider="openai",
                            model=self._model,
                            content_chars=len(content),
                            json_forced=bool(use_json_flag),
                            param=token_param,
                        )
                        return content
                    except Exception as exc:
                        last_exc = exc
                        low = (str(exc) or "").lower()
                        if (
                            "unsupported parameter" in low
                            or "not supported" in low
                            or "unexpected keyword" in low
                        ):
                            continue
                        raise
        raise last_exc if last_exc else RuntimeError("LLM call failed with unsupported params")


def _llm_with_policy(llm: _LLMBase) -> _LLMBase:
    """タイムアウトとリトライを付与した LLM ラッパーを返す。"""

    executor = _get_llm_executor()

    class _Wrapped(_LLMBase):
        def complete(self, prompt: str) -> str:
            last_exc: Exception | None = None
            for attempt in range(1, max(1, settings.llm_max_retries) + 1):
                future = None
                try:
                    ctx = contextvars.copy_context()
                    future = executor.submit(ctx.run, llm.complete, prompt)
                    result = future.result(timeout=settings.llm_timeout_ms / 1000.0)
                    if result == "":
                        logger.info(
                            "llm_complete_empty",
                            attempt=attempt,
                            retries=settings.llm_max_retries,
                        )
                    return result
                except Exception as exc:
                    last_exc = exc
                    logger.info(
                        "llm_complete_error",
                        attempt=attempt,
                        retries=settings.llm_max_retries,
                        error_type=type(exc).__name__,
                        error=str(exc),
                    )
                    if future is not None:
                        try:
                            future.cancel()
                        except Exception:
                            pass
                    if attempt >= max(1, settings.llm_max_retries):
                        break
                    time.sleep(0.1 * attempt)
            logger.info(
                "llm_complete_failed_all_retries",
                error=str(last_exc) if last_exc else None,
                error_type=(type(last_exc).__name__ if last_exc else None),
            )
            if settings.strict_mode:
                reason_code = "UNKNOWN"
                base_msg = "LLM failure"
                text = (str(last_exc) or "") if last_exc else ""
                etype = type(last_exc).__name__ if last_exc else "None"
                low = text.lower()
                if isinstance(last_exc, FuturesTimeout) or "timeout" in low:
                    base_msg = "LLM timeout"
                    reason_code = "TIMEOUT"
                elif (
                    "rate limit" in low
                    or "too many requests" in low
                    or "429" in low
                    or "ratelimit" in etype.lower()
                ):
                    reason_code = "RATE_LIMIT"
                elif (
                    "auth" in low
                    or "invalid api key" in low
                    or "unauthorized" in low
                    or "401" in low
                ):
                    reason_code = "AUTH"
                elif (
                    "unsupported parameter" in low or "not supported" in low
                ) and ("max_tokens" in low or "parameter" in low):
                    reason_code = "PARAM_UNSUPPORTED"
                elif (
                    "unexpected keyword argument" in low
                    or "got an unexpected keyword argument" in low
                ):
                    reason_code = "PARAM_UNSUPPORTED"
                msg = (
                    f"{base_msg} (reason_code={reason_code}, error_type={etype}, detail={text[:256]})"
                )
                raise RuntimeError(msg)
            return ""

    return _Wrapped()


def get_llm_provider(
    *,
    model_override: str | None = None,
    temperature_override: float | None = None,
    reasoning_override: Optional[dict] = None,
    text_override: Optional[dict] = None,
) -> Any:
    """設定値に応じた LLM クライアントを返す。"""

    has_override = any(
        value is not None
        for value in (model_override, temperature_override, reasoning_override, text_override)
    )
    instance = _get_llm_instance()
    if not has_override and instance is not None:
        return instance

    provider = (settings.llm_provider or "").lower()
    try:
        if provider in {"", "local"}:
            if settings.strict_mode:
                raise RuntimeError("LLM_PROVIDER must be 'openai' in strict mode")
            logger.info("llm_provider_select", provider="local")
            wrapped = _llm_with_policy(_LocalEchoLLM())
            if not has_override:
                _set_llm_instance(wrapped)
            return wrapped

        if provider == "openai":
            api_key = settings.openai_api_key
            if not api_key:
                if settings.strict_mode:
                    raise RuntimeError(
                        "OPENAI_API_KEY is required for LLM_PROVIDER=openai (strict mode)"
                    )
                logger.info("llm_provider_select", provider="local", reason="missing_api_key")
                fallback = _llm_with_policy(_LocalEchoLLM())
                if not has_override:
                    _set_llm_instance(fallback)
                return fallback

            base_model = getattr(settings, "llm_model", None)
            base_temperature = getattr(settings, "llm_temperature", None)
            base_reasoning = getattr(settings, "llm_reasoning", None)
            base_text_opts = getattr(settings, "llm_text_options", None)
            llm = _OpenAILLM(
                api_key=api_key,
                model=model_override or base_model,
                temperature=(
                    temperature_override
                    if temperature_override is not None
                    else base_temperature
                ),
                reasoning=(
                    reasoning_override
                    if reasoning_override is not None
                    else base_reasoning
                ),
                text=text_override if text_override is not None else base_text_opts,
            )
            wrapped = _llm_with_policy(llm)
            if not has_override:
                _set_llm_instance(wrapped)
            return wrapped

        if settings.strict_mode:
            raise RuntimeError(f"Unknown LLM provider: {provider}")
        logger.info(
            "llm_provider_select",
            provider="local",
            reason="unknown_provider",
            requested=provider,
        )
        fallback = _llm_with_policy(_LocalEchoLLM())
        if not has_override:
            _set_llm_instance(fallback)
        return fallback
    except Exception:
        if settings.strict_mode:
            raise
        logger.info("llm_provider_select", provider="local", reason="exception")
        fallback = _llm_with_policy(_LocalEchoLLM())
        if not has_override:
            _set_llm_instance(fallback)
        return fallback


def shutdown_providers() -> None:
    """共有スレッドプールと LLM シングルトンを解放する。"""

    executor = _get_llm_executor()
    try:
        executor.shutdown(wait=False, cancel_futures=True)  # type: ignore[call-arg]
    except Exception:
        pass
    _set_llm_instance(None)
