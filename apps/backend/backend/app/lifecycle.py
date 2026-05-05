from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable

from fastapi import FastAPI

from ..indexing import seed_domain_terms, seed_from_jsonl, seed_word_snippets
from ..logging import logger
from ..providers import ChromaClientFactory, shutdown_providers

LifecycleHook = Callable[[], Awaitable[None]]


async def on_shutdown() -> None:
    """Ensure providers (Chroma, LLM clients) are gracefully terminated."""

    shutdown_providers()


async def on_startup_seed(app_settings: Any | None = None) -> None:
    """Optionally seed Chroma collections at application startup."""

    from ..config import settings

    active_settings = app_settings or settings
    try:
        if not active_settings.auto_seed_on_startup:
            return
        client = ChromaClientFactory().create_client()
        if client is None:
            return
        wj = (
            Path(active_settings.auto_seed_word_jsonl)
            if active_settings.auto_seed_word_jsonl
            else None
        )
        tj = (
            Path(active_settings.auto_seed_terms_jsonl)
            if active_settings.auto_seed_terms_jsonl
            else None
        )
        if (wj and wj.exists()) or (tj and tj.exists()):
            seed_from_jsonl(client, word_snippets_path=wj, domain_terms_path=tj)
            logger.info(
                "auto_seed",
                mode="jsonl",
                word_jsonl=str(wj) if wj else None,
                terms_jsonl=str(tj) if tj else None,
            )
        else:
            seed_word_snippets(client)
            seed_domain_terms(client)
            logger.info("auto_seed", mode="minimal")
    except Exception as exc:  # pragma: no cover - 起動時エラーは継続
        logger.warning("auto_seed_failed", error=repr(exc))


def build_lifespan(
    *,
    startup_seed: LifecycleHook,
    shutdown: LifecycleHook,
):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await startup_seed()
        try:
            yield
        finally:
            await shutdown()

    return lifespan
