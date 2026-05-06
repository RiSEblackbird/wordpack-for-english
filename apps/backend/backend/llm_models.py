from __future__ import annotations

SUPPORTED_LLM_MODELS: tuple[str, ...] = ("gpt-5.4-mini", "gpt-5.4-nano")
DEFAULT_LLM_MODEL = SUPPORTED_LLM_MODELS[0]


def ensure_supported_llm_model(model: str | None) -> str:
    selected = (model or DEFAULT_LLM_MODEL).strip()
    if selected not in SUPPORTED_LLM_MODELS:
        allowed = ", ".join(SUPPORTED_LLM_MODELS)
        raise ValueError(f"Unsupported LLM model: {selected}. Allowed models: {allowed}")
    return selected
