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


def _session_log_context(
    request: Request, *, reason: str, user_id: str | None
) -> dict[str, object]:
    """Compose structured log context aligned with AccessLog fields.

    なぜ: Cloud Run 上でセッション検証失敗を素早くフィルタできるよう、
    AccessLog と同一キー（path/client_ip/user_agent/request_id）で
    失敗理由を記録する。
    """

    client_ip = request.client.host if request.client else "unknown"
    return {
        "user_id": user_id,
        "reason": reason,
        "path": request.url.path,
        "client_ip": client_ip,
        "user_agent": request.headers.get("user-agent"),
        "request_id": getattr(request.state, "request_id", None),
    }


def read_session_cookie(request: Request, cookie_name: str) -> str | None:
    """Robustly read the session cookie even when other cookies are non‑RFC compliant.

    なぜ: Google Identity Services が発行する `g_state` など一部の Cookie は、値に
    JSON 文字列をそのまま含めるため `Cookie` ヘッダー全体が RFC に厳密ではなくなり、
    Python 標準の ``SimpleCookie`` パーサが例外を投げて `request.cookies` を空にして
    しまうケースがある。その場合でもセッションクッキーだけは確実に取得したいので、
    まず `request.cookies` を試しつつ、失敗時は生のヘッダーを手動で分解して取得する。
    """

    # 通常ケース: Starlette が正しく Cookie を構築している場合はこちらで十分。
    try:
        value = request.cookies.get(cookie_name)  # type: ignore[assignment]
    except Exception:  # pragma: no cover - defensive guard
        value = None
    if value:
        return value  # type: ignore[return-value]

    # フォールバック: Cookie ヘッダーを手動パース（`;` 区切りの単純な形式を前提）。
    raw_header = request.headers.get("cookie") or request.headers.get("Cookie")
    if not raw_header:
        return None
    for part in raw_header.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, raw_value = part.split("=", 1)
        if name.strip() == cookie_name:
            return raw_value.strip()
    return None


async def get_current_user(request: Request) -> dict[str, str]:
    """Validate session cookie and attach the authenticated user to the request state."""

    cookie_name = settings.session_cookie_name or "wp_session"
    raw_token = read_session_cookie(request, cookie_name)
    if not raw_token:
        logger.warning(
            "session_validation_failed",
            **_session_log_context(request, reason="missing_cookie", user_id=None),
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
            **_session_log_context(request, reason="expired", user_id=None),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        ) from exc
    except BadSignature as exc:
        logger.warning(
            "session_validation_failed",
            **_session_log_context(request, reason="bad_signature", user_id=None),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
        ) from exc
    except RuntimeError as exc:
        logger.error(
            "session_validation_failed",
            **_session_log_context(request, reason="configuration_error", user_id=None),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session configuration error",
        ) from exc

    sub = payload.get("sub") if isinstance(payload, dict) else None
    if not sub:
        logger.warning(
            "session_validation_failed",
            **_session_log_context(request, reason="missing_sub", user_id=None),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session payload",
        )

    user = store.get_user_by_google_sub(sub)
    if user is None:
        logger.warning(
            "session_validation_failed",
            **_session_log_context(request, reason="user_not_found", user_id=sub),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    request.state.user = user
    request.state.user_id = sub
    return user
