"""Authorization helpers for feature gating based on user role."""

from typing import Literal, Optional

from fastapi import Depends, HTTPException, Request

from .config import settings

UserRole = Literal["admin", "viewer"]


def _extract_email(raw: str | None) -> Optional[str]:
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None
    if ":" in text:
        # Google IAP 形式: accounts.google.com:someone@example.com
        text = text.split(":", 1)[1]
    text = text.strip()
    if not text:
        return None
    return text.lower()


def get_request_user_email(request: Request) -> Optional[str]:
    """Extract the authenticated user email from headers (Google login aware)."""

    preferred = request.headers.get(settings.user_email_header)
    email = _extract_email(preferred)
    if email:
        return email

    # Google IAP が付与するヘッダ（accounts.google.com:email の形式）
    google_header_name = settings.google_iap_user_header or "X-Goog-Authenticated-User-Email"
    email = _extract_email(request.headers.get(google_header_name))
    if email:
        return email

    # Fallback: 慣用的なヘッダ名も一応確認
    email = _extract_email(request.headers.get("X-Goog-Authenticated-User-Email"))
    if email:
        return email
    email = _extract_email(request.headers.get("X-Forwarded-Email"))
    return email


def resolve_user_role(request: Request) -> UserRole:
    """Determine the current user role based on email allowlists and defaults."""

    email = get_request_user_email(request)
    if email:
        domain = email.split("@", 1)[1] if "@" in email else None

        if email in settings.admin_email_allowlist:
            return "admin"
        if domain and domain in settings.admin_email_domain_allowlist:
            return "admin"

        if email in settings.viewer_email_allowlist:
            return "viewer"
        if domain and domain in settings.viewer_email_domain_allowlist:
            return "viewer"

    return settings.user_role


def ensure_ai_access(user_role: UserRole = Depends(resolve_user_role)) -> None:
    """Raise 403 when AI features are disabled for the current user role."""

    if user_role == "viewer":
        raise HTTPException(
            status_code=403,
            detail="AI features are disabled for viewer role",
        )
