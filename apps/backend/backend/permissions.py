"""Simple authorization helpers for feature gating."""

from fastapi import HTTPException

from .config import settings


def ensure_ai_access() -> None:
    """Raise 403 when AI features are disabled for the current user role."""
    if settings.user_role == "viewer":
        raise HTTPException(
            status_code=403,
            detail="AI features are disabled for viewer role",
        )
