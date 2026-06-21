from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from ..application.quiz.generation_jobs import enqueue_quiz_generation_job, get_quiz_generation_job
from ..application.quiz.scoring import score_quiz_attempt
from ..models.quiz import (
    Quiz,
    QuizAttemptRequest,
    QuizAttemptResponse,
    QuizGenerateRequest,
    QuizGenerationJobResponse,
    QuizListItem,
    QuizListResponse,
)
from .word.dependencies import get_store, require_authenticated_user

router = APIRouter(tags=["quiz"])


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _question_count(quiz: Quiz) -> int:
    return sum(len(section.questions) for section in quiz.sections)


def _list_item_from_quiz(quiz: Quiz) -> QuizListItem:
    return QuizListItem(
        id=quiz.id,
        title_en=quiz.title_en,
        format_profile=quiz.format_profile,
        generation_domain=quiz.generation_domain,
        domain_intensity=quiz.domain_intensity,
        difficulty=quiz.difficulty,
        question_count=_question_count(quiz),
        passage_count=len(quiz.passages),
        source_lemmas=quiz.source_lemmas,
        created_at=quiz.created_at,
        updated_at=quiz.updated_at,
        guest_public=quiz.guest_public,
    )


@router.post(
    "/generate/jobs",
    response_model=QuizGenerationJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Quiz生成ジョブを開始",
)
async def create_quiz_generation_job(
    req: QuizGenerateRequest,
    _user: dict[str, str] = Depends(require_authenticated_user),
) -> QuizGenerationJobResponse:
    return await enqueue_quiz_generation_job(req, get_store())


@router.get(
    "/generate/jobs/{job_id}",
    response_model=QuizGenerationJobResponse,
    summary="Quiz生成ジョブの状態を取得",
)
async def get_quiz_generation_job_status(
    job_id: str,
    _user: dict[str, str] = Depends(require_authenticated_user),
) -> QuizGenerationJobResponse:
    job = await get_quiz_generation_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Quiz generation job not found")
    return job


@router.get(
    "",
    response_model=QuizListResponse,
    summary="保存済みQuiz一覧を取得",
)
async def list_quizzes(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> QuizListResponse:
    repository = get_store()
    public_only = bool(getattr(request.state, "guest", False))
    rows = repository.list_quizzes(limit=limit, offset=offset, public_only=public_only)
    total = repository.count_quizzes(public_only=public_only)
    items = [_list_item_from_quiz(Quiz.model_validate(row)) for row in rows]
    return QuizListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{quiz_id}",
    response_model=Quiz,
    summary="保存済みQuiz詳細を取得",
)
async def get_quiz(request: Request, quiz_id: str) -> Quiz:
    row = get_store().get_quiz(quiz_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    quiz = Quiz.model_validate(row)
    if bool(getattr(request.state, "guest", False)) and not quiz.guest_public:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz


@router.delete(
    "/{quiz_id}",
    summary="Quizを削除",
)
async def delete_quiz(
    quiz_id: str,
    _user: dict[str, str] = Depends(require_authenticated_user),
) -> dict[str, str]:
    success = get_store().delete_quiz(quiz_id)
    if not success:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return {"message": "Quiz deleted successfully"}


@router.post(
    "/{quiz_id}/attempts",
    response_model=QuizAttemptResponse,
    summary="Quizを採点してAttemptを保存",
)
async def submit_quiz_attempt(
    quiz_id: str,
    req: QuizAttemptRequest,
    _user: dict[str, str] = Depends(require_authenticated_user),
) -> QuizAttemptResponse:
    row = get_store().get_quiz(quiz_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    quiz = Quiz.model_validate(row)
    score, total, results = score_quiz_attempt(quiz, req.answers)
    submitted_at = _now_iso()
    percentage = (score / total * 100.0) if total else 0.0
    attempt_id = f"quiz-attempt:{uuid.uuid4().hex}"
    response = QuizAttemptResponse(
        id=attempt_id,
        quiz_id=quiz_id,
        score=score,
        total=total,
        percentage=percentage,
        results=results,
        started_at=req.started_at,
        submitted_at=submitted_at,
        elapsed_ms=req.elapsed_ms,
    )
    get_store().save_quiz_attempt(
        attempt_id,
        {
            "quiz_id": quiz_id,
            "answers": [answer.model_dump(mode="json") for answer in req.answers],
            "score": score,
            "total": total,
            "percentage": percentage,
            "results": [result.model_dump(mode="json") for result in results],
            "started_at": req.started_at,
            "submitted_at": submitted_at,
            "elapsed_ms": req.elapsed_ms,
            "created_at": submitted_at,
        },
    )
    return response


@router.get(
    "/{quiz_id}/attempts",
    response_model=list[QuizAttemptResponse],
    summary="QuizのAttempt履歴を取得",
)
async def list_quiz_attempts(
    quiz_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _user: dict[str, str] = Depends(require_authenticated_user),
) -> list[QuizAttemptResponse]:
    if get_store().get_quiz(quiz_id) is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    rows = get_store().list_quiz_attempts(quiz_id, limit=limit, offset=offset)
    return [QuizAttemptResponse.model_validate(row) for row in rows]
