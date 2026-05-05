from __future__ import annotations

import asyncio
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel

from ...logging import logger
from ...models.word import WordPack, WordPackRegenerateRequest
from ...store import store
from .generate_wordpack import run_wordpack_flow


class RegenerateJob(BaseModel):
    job_id: str
    word_pack_id: str
    status: Literal["pending", "running", "succeeded", "failed"]
    result: WordPack | None = None
    error: str | None = None


_regenerate_jobs: dict[str, RegenerateJob] = {}
_regenerate_lock = asyncio.Lock()


def _regeneration_error_mapping(category: str | None = None):
    def diagnostics_for(lemma: str, diagnostics):
        if diagnostics:
            return diagnostics
        result = {"lemma": lemma}
        if category:
            result["category"] = category
        return result

    return {
        "llm_json_parse": lambda *, lemma, **__: HTTPException(
            status_code=502,
            detail={
                "message": "LLM output JSON parse failed (strict mode)",
                "reason_code": "LLM_JSON_PARSE",
                "diagnostics": diagnostics_for(lemma, None),
                "hint": "モデル/プロンプトの安定化、text.verbosity を lower に、または strict_mode を無効化して挙動を確認してください。ログの wordpack_llm_json_parse_failed を参照。",
            },
        ),
        "empty_content": lambda *, lemma, diagnostics, **__: HTTPException(
            status_code=502,
            detail={
                "message": "WordPack regeneration returned empty content (no senses/examples)",
                "reason_code": "EMPTY_CONTENT",
                "diagnostics": diagnostics or diagnostics_for(lemma, diagnostics),
                "hint": "LLM_TIMEOUT_MS/LLM_MAX_TOKENS/モデル安定タグを調整してください。ログの wordpack_llm_* を確認。",
            },
        ),
    }


async def run_regenerate_job(
    job_id: str, word_pack_id: str, req: WordPackRegenerateRequest
) -> None:
    async with _regenerate_lock:
        job = _regenerate_jobs.get(job_id)
        if not job:
            return
        job.status = "running"
        _regenerate_jobs[job_id] = job
    try:
        result = store.get_word_pack(word_pack_id)
        if result is None:
            raise HTTPException(status_code=404, detail="WordPack not found")
        lemma, _, _, _ = result
        word_pack, _ = await run_wordpack_flow(
            lemma=lemma,
            req_opts=req,
            scope=req.regenerate_scope,
            http_error_mapping=_regeneration_error_mapping(),
        )
        store.save_word_pack(word_pack_id, lemma, word_pack.model_dump_json())
        async with _regenerate_lock:
            job = _regenerate_jobs.get(job_id)
            if job:
                job.status = "succeeded"
                job.result = word_pack
                _regenerate_jobs[job_id] = job
        logger.info(
            "wordpack_regenerate_async_succeeded",
            word_pack_id=word_pack_id,
            lemma=lemma,
            job_id=job_id,
        )
    except Exception as exc:
        err_msg = str(exc)
        async with _regenerate_lock:
            job = _regenerate_jobs.get(job_id)
            if job:
                job.status = "failed"
                job.error = err_msg[:500]
                _regenerate_jobs[job_id] = job
        logger.error(
            "wordpack_regenerate_async_failed",
            word_pack_id=word_pack_id,
            job_id=job_id,
            error_type=exc.__class__.__name__,
            error_message=err_msg[:200],
        )


async def enqueue_regenerate_job(
    word_pack_id: str,
    req: WordPackRegenerateRequest,
) -> RegenerateJob:
    if store.get_word_pack(word_pack_id) is None:
        raise HTTPException(status_code=404, detail="WordPack not found")
    job_id = uuid4().hex
    job = RegenerateJob(
        job_id=job_id, word_pack_id=word_pack_id, status="pending", result=None
    )
    async with _regenerate_lock:
        _regenerate_jobs[job_id] = job
    asyncio.create_task(run_regenerate_job(job_id, word_pack_id, req))
    logger.info(
        "wordpack_regenerate_async_enqueued",
        word_pack_id=word_pack_id,
        job_id=job_id,
        regenerate_scope=req.regenerate_scope,
    )
    return job


async def get_regenerate_job(word_pack_id: str, job_id: str) -> RegenerateJob:
    async with _regenerate_lock:
        job = _regenerate_jobs.get(job_id)
    if job is None or job.word_pack_id != word_pack_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
