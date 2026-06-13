from __future__ import annotations

import asyncio
from collections.abc import Mapping
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


def _store_supports_persistent_jobs() -> bool:
    return all(
        callable(getattr(store, name, None))
        for name in (
            "create_regenerate_job",
            "update_regenerate_job",
            "get_regenerate_job",
        )
    )


def _job_from_record(
    record: Mapping[str, object],
    *,
    result: WordPack | None = None,
) -> RegenerateJob:
    status = str(record.get("status") or "pending")
    if status not in {"pending", "running", "succeeded", "failed"}:
        status = "failed"
    error = record.get("error")
    return RegenerateJob(
        job_id=str(record.get("job_id") or ""),
        word_pack_id=str(record.get("word_pack_id") or ""),
        status=status,  # type: ignore[arg-type]
        result=result,
        error=str(error) if error is not None else None,
    )


def _load_saved_word_pack_result(word_pack_id: str) -> WordPack | None:
    result = store.get_word_pack(word_pack_id)
    if result is None:
        return None
    _, data_json, _, _ = result
    try:
        return WordPack.model_validate_json(data_json)
    except Exception as exc:  # pragma: no cover - defensive logging for corrupt data
        logger.error(
            "wordpack_regenerate_result_parse_failed",
            word_pack_id=word_pack_id,
            error_type=exc.__class__.__name__,
            error_message=str(exc)[:200],
        )
        return None


def _create_job_record(job_id: str, word_pack_id: str) -> RegenerateJob:
    if _store_supports_persistent_jobs():
        record = store.create_regenerate_job(
            job_id=job_id,
            word_pack_id=word_pack_id,
            status="pending",
        )
        return _job_from_record(record)
    return RegenerateJob(
        job_id=job_id, word_pack_id=word_pack_id, status="pending", result=None
    )


def _update_job_record(
    job_id: str,
    *,
    status: Literal["pending", "running", "succeeded", "failed"],
    error: str | None = None,
) -> RegenerateJob | None:
    if _store_supports_persistent_jobs():
        record = store.update_regenerate_job(job_id, status=status, error=error)
        if record is None:
            return None
        return _job_from_record(record)
    job = _regenerate_jobs.get(job_id)
    if not job:
        return None
    job.status = status
    if error is not None:
        job.error = error
    _regenerate_jobs[job_id] = job
    return job


def _get_job_record(job_id: str) -> RegenerateJob | None:
    if _store_supports_persistent_jobs():
        record = store.get_regenerate_job(job_id)
        if record is None:
            return None
        base_job = _job_from_record(record)
        result = (
            _load_saved_word_pack_result(base_job.word_pack_id)
            if base_job.status == "succeeded"
            else None
        )
        return base_job.model_copy(update={"result": result})
    return _regenerate_jobs.get(job_id)


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
        job = _update_job_record(job_id, status="running")
        if not job:
            return
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
            _update_job_record(job_id, status="succeeded")
        logger.info(
            "wordpack_regenerate_async_succeeded",
            word_pack_id=word_pack_id,
            lemma=lemma,
            job_id=job_id,
        )
    except Exception as exc:
        err_msg = str(exc)
        async with _regenerate_lock:
            _update_job_record(job_id, status="failed", error=err_msg[:500])
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
    job = _create_job_record(job_id, word_pack_id)
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
        job = _get_job_record(job_id)
    if job is None or job.word_pack_id != word_pack_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
