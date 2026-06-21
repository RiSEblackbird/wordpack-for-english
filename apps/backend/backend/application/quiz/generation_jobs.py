from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Literal

import anyio

from ...flows.quiz_generate import QuizGenerateFlow
from ...models.quiz import Quiz, QuizGenerateRequest, QuizGenerationJobResponse


def _now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


@dataclass
class QuizGenerationJob:
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    quiz_id: str | None = None
    result: Quiz | None = None
    error: str | None = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_response(self) -> QuizGenerationJobResponse:
        return QuizGenerationJobResponse(
            job_id=self.job_id,
            status=self.status,
            quiz_id=self.quiz_id,
            result=self.result,
            error=self.error,
        )


_quiz_generation_jobs: dict[str, QuizGenerationJob] = {}
_quiz_generation_lock = asyncio.Lock()


async def enqueue_quiz_generation_job(req: QuizGenerateRequest, store: object) -> QuizGenerationJobResponse:
    import uuid

    job_id = f"quiz-job:{uuid.uuid4().hex}"
    job = QuizGenerationJob(job_id=job_id, status="queued")
    async with _quiz_generation_lock:
        _quiz_generation_jobs[job_id] = job
    asyncio.create_task(_run_quiz_generation_job(job_id, req, store))
    return job.to_response()


async def get_quiz_generation_job(job_id: str) -> QuizGenerationJobResponse | None:
    async with _quiz_generation_lock:
        job = _quiz_generation_jobs.get(job_id)
        return job.to_response() if job else None


async def _run_quiz_generation_job(job_id: str, req: QuizGenerateRequest, store: object) -> None:
    async with _quiz_generation_lock:
        job = _quiz_generation_jobs.get(job_id)
        if job is None:
            return
        job.status = "running"
        job.updated_at = _now_iso()
    try:
        flow = QuizGenerateFlow(store=store)
        quiz = await anyio.to_thread.run_sync(flow.run, req)
    except Exception as exc:
        async with _quiz_generation_lock:
            job = _quiz_generation_jobs.get(job_id)
            if job is not None:
                job.status = "failed"
                job.error = str(exc)
                job.updated_at = _now_iso()
        return
    async with _quiz_generation_lock:
        job = _quiz_generation_jobs.get(job_id)
        if job is not None:
            job.status = "succeeded"
            job.quiz_id = quiz.id
            job.result = quiz
            job.updated_at = _now_iso()
