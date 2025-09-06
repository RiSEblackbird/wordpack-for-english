from pydantic import BaseModel


class ReviewTodayResponse(BaseModel):
    """Response model for today's review items."""

    items: list[str]


class ReviewGradeRequest(BaseModel):
    """Request model for submitting a review grade."""

    item_id: str
    grade: int
