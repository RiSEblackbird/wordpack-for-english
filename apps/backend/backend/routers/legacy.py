from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["legacy"])


class _SentenceCheckRequest(BaseModel):
    sentence: str = Field(..., description="Input sentence to check")


class _ReviewGradeByLemmaRequest(BaseModel):
    lemma: str = Field(..., min_length=1)
    grade: int = Field(..., ge=0, le=2)


@router.post("/sentence/check")
async def sentence_check(_: _SentenceCheckRequest) -> dict[str, Any]:
    """Legacy stub endpoint kept for load regression tests."""

    return {
        "ok": True,
        "message": "Sentence check is not implemented; returning legacy stub response.",
    }


@router.get("/review/stats")
async def review_stats() -> dict[str, Any]:
    """Return static review progress metrics for regression compatibility."""

    return {"due_now": 0, "reviewed_today": 0, "recent": []}


@router.post("/review/grade_by_lemma")
async def review_grade_by_lemma(_: _ReviewGradeByLemmaRequest) -> dict[str, Any]:
    """Accept grading requests and respond with a static next due timestamp."""

    next_due = datetime.now(UTC).isoformat()
    return {"ok": True, "next_due": next_due}
