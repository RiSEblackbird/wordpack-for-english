from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import settings
from .logging import logger
from .store import store

_SESSION_SALT = "wordpack.session"


def _build_serializer() -> URLSafeTimedSerializer:
    """Construct a serializer for signing and verifying session tokens."""

    secret = settings.session_secret_key.strip()
    if not secret:
        raise RuntimeError("SESSION_SECRET_KEY is not configured")
    return URLSafeTimedSerializer(secret, salt=_SESSION_SALT)


def _session_max_age() -> int:
    """Return the configured session lifetime in seconds."""

    try:
        max_age = int(getattr(settings, "session_max_age_seconds", 0))
    except (TypeError, ValueError):  # pragma: no cover - defensive fallback
        max_age = 0
    return max(60, max_age or 60 * 60 * 24 * 14)


def issue_session_token(google_sub: str) -> str:
    """Generate a signed session token tied to the Google subject identifier."""

    serializer = _build_serializer()
    payload = {
        "sid": uuid.uuid4().hex,
        "sub": google_sub,
        "issued_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    return serializer.dumps(payload)


def verify_session_token(token: str) -> dict:
    """Decode a signed session token and return the embedded payload."""

    serializer = _build_serializer()
    return serializer.loads(token, max_age=_session_max_age())


async def get_current_user(request: Request) -> dict[str, str]:
    """Validate session cookie and attach the authenticated user to the request state."""

    cookie_name = settings.session_cookie_name or "wp_session"
    raw_token = request.cookies.get(cookie_name)
    if not raw_token:
        logger.warning(
            "session_validation_failed",
            user_id=None,
            reason="missing_cookie",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session cookie is missing",
        )

    try:
        payload = verify_session_token(raw_token)
    except SignatureExpired as exc:
        logger.warning(
            "session_validation_failed",
            user_id=None,
            reason="expired",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        ) from exc
    except BadSignature as exc:
        logger.warning(
            "session_validation_failed",
            user_id=None,
            reason="bad_signature",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
        ) from exc
    except RuntimeError as exc:
        logger.error(
            "session_validation_failed",
            user_id=None,
            reason="configuration_error",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session configuration error",
        ) from exc

    sub = payload.get("sub") if isinstance(payload, dict) else None
    if not sub:
        logger.warning(
            "session_validation_failed",
            user_id=None,
            reason="missing_sub",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session payload",
        )

    user = store.get_user_by_google_sub(sub)
    if user is None:
        logger.warning(
            "session_validation_failed",
            user_id=sub,
            reason="user_not_found",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    request.state.user = user
    request.state.user_id = sub
    return user
