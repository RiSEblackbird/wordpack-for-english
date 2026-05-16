from __future__ import annotations

import sys

from fastapi import APIRouter, Depends, HTTPException

from ...application.wordpack import regenerate_jobs as regenerate_jobs_module
from ...application.wordpack.regenerate_jobs import (
    RegenerateJob,
    _regenerate_jobs,
    _regenerate_lock,
    enqueue_regenerate_job,
    get_regenerate_job,
)
from ...models.word import WordPack, WordPackRegenerateRequest
from .dependencies import get_run_wordpack_flow, get_store, require_authenticated_user
from .error_mapping import regeneration_error_mapping

router = APIRouter()


def _word_router_package():
    return sys.modules.get("backend.routers.word")


def _sync_regenerate_job_dependencies() -> None:
    package = _word_router_package()
    regenerate_jobs_module.store = get_store()
    regenerate_jobs_module.run_wordpack_flow = get_run_wordpack_flow()
    regenerate_jobs_module._regenerate_jobs = getattr(
        package, "_regenerate_jobs", _regenerate_jobs
    )
    regenerate_jobs_module._regenerate_lock = getattr(
        package, "_regenerate_lock", _regenerate_lock
    )


@router.post(
    "/packs/{word_pack_id}/regenerate",
    response_model=WordPack,
    response_model_exclude_none=True,
    summary="WordPackを再生成",
    response_description="既存のWordPackを再生成して返します",
)
async def regenerate_word_pack(
    word_pack_id: str,
    req: WordPackRegenerateRequest,
    _user: dict[str, str] = Depends(require_authenticated_user),
) -> WordPack:
    """既存のWordPackを再生成する。"""

    repository = get_store()
    result = repository.get_word_pack(word_pack_id)
    if result is None:
        raise HTTPException(status_code=404, detail="WordPack not found")

    lemma, _, _, _ = result

    try:
        word_pack, _ = await get_run_wordpack_flow()(
            lemma=lemma,
            req_opts=req,
            scope=req.regenerate_scope,
            http_error_mapping=regeneration_error_mapping(),
        )

        repository.save_word_pack(word_pack_id, lemma, word_pack.model_dump_json())
        return word_pack
    except RuntimeError:
        # run_wordpack_flow 内で HTTPException へ変換済み。それ以外は既定処理へ委譲。
        raise


@router.post(
    "/packs/{word_pack_id}/regenerate/async",
    response_model=RegenerateJob,
    status_code=202,
    summary="WordPackを非同期で再生成（ジョブIDを返す）",
)
async def enqueue_regenerate_word_pack(
    word_pack_id: str,
    req: WordPackRegenerateRequest,
    _user: dict[str, str] = Depends(require_authenticated_user),
) -> RegenerateJob:
    """Enqueue an async regenerate job and return job ID immediately."""

    _sync_regenerate_job_dependencies()
    return await enqueue_regenerate_job(word_pack_id, req)


@router.get(
    "/packs/{word_pack_id}/regenerate/jobs/{job_id}",
    response_model=RegenerateJob,
    summary="非同期再生成ジョブの状態を取得",
)
async def get_regenerate_job_status(
    word_pack_id: str, job_id: str
) -> RegenerateJob:
    """Return current job status and result when available."""

    _sync_regenerate_job_dependencies()
    return await get_regenerate_job(word_pack_id, job_id)
