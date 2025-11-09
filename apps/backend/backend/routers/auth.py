from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from http import HTTPStatus

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel, Field

from ..auth import issue_session_token
from ..config import settings
from ..logging import logger
from ..store import store

router = APIRouter(tags=["auth"])
_google_request = google_requests.Request()


class GoogleAuthRequest(BaseModel):
    """Payload containing a Google-issued ID token from the frontend."""

    id_token: str = Field(..., description="Google ID token generated on the client")


class GoogleAuthResponse(BaseModel):
    """Response carrying the persisted user profile."""

    user: dict[str, str]


@router.post("/api/auth/google", response_model=GoogleAuthResponse)
async def authenticate_with_google(payload: GoogleAuthRequest, request: Request) -> JSONResponse:
    """Verify Google ID token, persist the user, and issue a signed session cookie."""

    if not settings.google_client_id:
        logger.error(
            "google_auth_failed",
            user_id=None,
            reason="missing_client_id",
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Google authentication is not configured",
        )
    if not settings.session_secret_key:
        logger.error(
            "google_auth_failed",
            user_id=None,
            reason="missing_session_secret",
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Session secret key is not configured",
        )

    try:
        # 許容する時計ずれ（nbf/iat/exp の境界緩和）。古い google-auth 互換のため TypeError 時は従来呼び出しにフォールバック。
        _skew = max(0, int(getattr(settings, "google_clock_skew_seconds", 0) or 0))
        try:
            id_info = id_token.verify_oauth2_token(
                payload.id_token,
                _google_request,
                settings.google_client_id,
                clock_skew_in_seconds=_skew,
            )
        except TypeError:
            id_info = id_token.verify_oauth2_token(
                payload.id_token,
                _google_request,
                settings.google_client_id,
            )
    except ValueError as exc:
        logger.warning(
            "google_auth_failed",
            user_id=None,
            reason="invalid_token",
            error=repr(exc),
        )
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Invalid ID token") from exc

    google_sub = id_info.get("sub")
    email = id_info.get("email")
    display_name = id_info.get("name") or id_info.get("email")
    hosted_domain = id_info.get("hd") or id_info.get("hostedDomain")
    email_hash = _hash_for_log(email)

    missing_claims = [
        claim
        for claim, value in (("sub", google_sub), ("email", email))
        if not value
    ]

    if not google_sub or not email or not display_name:
        logger.warning(
            "google_auth_failed",
            user_id=google_sub,
            reason="missing_claims",
            missing_claims=missing_claims,
            email_hash=email_hash,
        )
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="ID token is missing required claims")

    allowed_hd = (settings.google_allowed_hd or "").strip()
    if allowed_hd and hosted_domain != allowed_hd:
        logger.warning(
            "google_auth_denied",
            user_id=google_sub,
            reason="domain_mismatch",
            hosted_domain=hosted_domain,
            allowed_domain=allowed_hd,
            email_hash=email_hash,
        )
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Google account domain is not allowed")

    # 許可されたメールアドレス一覧が設定されている場合は、完全一致で照合して拒否理由を明示的に記録する。
    allowlisted_emails = getattr(settings, "admin_email_allowlist", ())
    if allowlisted_emails:
        normalised_email = email.strip().lower()
        if normalised_email not in allowlisted_emails:
            logger.warning(
                "google_auth_denied",
                user_id=google_sub,
                reason="email_not_allowlisted",
                hosted_domain=hosted_domain,
                email_hash=email_hash,
                allowlist_size=len(allowlisted_emails),
            )
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail="Google account email is not allowlisted",
            )

    user = store.record_user_login(
        google_sub=google_sub,
        email=email,
        display_name=display_name,
        login_at=datetime.now(UTC),
    )
    session_token = issue_session_token(google_sub)

    response = JSONResponse(status_code=HTTPStatus.OK, content={"user": user})
    response.set_cookie(
        key=settings.session_cookie_name or "wp_session",
        value=session_token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=_session_cookie_max_age(),
    )
    request.state.user = user
    request.state.user_id = google_sub
    # 成功ログは個人情報を直接出力しないよう `_log_google_auth_success` へ委譲する。
    _log_google_auth_success(google_sub, email, display_name)
    return response


def _session_cookie_max_age() -> int:
    """Resolve the cookie lifetime from configuration."""

    try:
        return max(60, int(settings.session_max_age_seconds))
    except (TypeError, ValueError):  # pragma: no cover - defensive fallback
        return 60 * 60 * 24 * 14


def _hash_for_log(value: str | None) -> str | None:
    """Hash sensitive identifiers before logging to avoid leaking PII."""

    if not value:
        return None
    # Google アカウントのメールアドレスなどの PII を直接出力しないよう、
    # SHA-256 の先頭12文字に圧縮してロギングする。SRE がインシデント時に
    # 該当アカウントを特定できる粒度を残しつつ漏洩リスクを抑える意図。
    digest = hashlib.sha256(value.lower().encode("utf-8")).hexdigest()
    return digest[:12]


def _log_google_auth_success(
    user_id: str,
    email: str | None,
    display_name: str | None,
) -> None:
    """Log sanitized Google auth success events for Cloud Logging compliance.

    新規メンバーでも誤って平文の識別子を記録しないよう、この関数経由で
    ログを出力する。必要なときは `_hash_for_log` を再利用して display_name も
    ハッシュ化する方針を徹底する。
    """

    logger.info(
        "google_auth_succeeded",
        user_id=user_id,
        reason="authenticated",
        email_hash=_hash_for_log(email),
        display_name_hash=_hash_for_log(display_name),
    )
