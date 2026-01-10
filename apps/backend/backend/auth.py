from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import settings
from .logging import logger
from .store import store

_SESSION_SALT = "wordpack.session"
_GUEST_SESSION_SALT = "wordpack.guest_session"
_FIREBASE_SESSION_COOKIE = "__session"


def _build_serializer(salt: str = _SESSION_SALT) -> URLSafeTimedSerializer:
    """Construct a serializer for signing and verifying session tokens."""

    secret = settings.session_secret_key.strip()
    if not secret:
        raise RuntimeError("SESSION_SECRET_KEY is not configured")
    return URLSafeTimedSerializer(secret, salt=salt)


def _session_max_age() -> int:
    """Return the configured session lifetime in seconds."""

    try:
        max_age = int(getattr(settings, "session_max_age_seconds", 0))
    except (TypeError, ValueError):  # pragma: no cover - defensive fallback
        max_age = 0
    return max(60, max_age or 60 * 60 * 24 * 14)


def _guest_session_max_age() -> int:
    """Return the configured guest session lifetime in seconds."""

    try:
        max_age = int(getattr(settings, "guest_session_max_age_seconds", 0))
    except (TypeError, ValueError):  # pragma: no cover - defensive fallback
        max_age = 0
    return max(60, max_age or 60 * 60 * 24)


def guest_session_cookie_max_age() -> int:
    """Return the guest session cookie max-age in seconds."""

    return _guest_session_max_age()


def issue_session_token(google_sub: str) -> str:
    """Generate a signed session token tied to the Google subject identifier."""

    serializer = _build_serializer(_SESSION_SALT)
    payload = {
        "sid": uuid.uuid4().hex,
        "sub": google_sub,
        "issued_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    return serializer.dumps(payload)


def verify_session_token(token: str) -> dict:
    """Decode a signed session token and return the embedded payload."""

    serializer = _build_serializer(_SESSION_SALT)
    return serializer.loads(token, max_age=_session_max_age())


def issue_guest_session_token() -> str:
    """Generate a signed guest session token for read-only browsing."""

    serializer = _build_serializer(_GUEST_SESSION_SALT)
    payload = {
        "gid": uuid.uuid4().hex,
        "issued_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "mode": "guest",
    }
    return serializer.dumps(payload)


def verify_guest_session_token(token: str) -> dict:
    """Decode a signed guest session token and return the embedded payload."""

    serializer = _build_serializer(_GUEST_SESSION_SALT)
    return serializer.loads(token, max_age=_guest_session_max_age())


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


def session_cookie_names() -> tuple[str, ...]:
    """Return ordered cookie names that should carry the session token.

    なぜ: Firebase Hosting は `__session` 以外の Cookie を Cloud Run へ転送しないため、
    既定名（wp_session など）に加えて __session も必ずミラーする。
    """

    configured = (settings.session_cookie_name or "wp_session").strip()
    primary = configured or "wp_session"
    names = [primary]
    if _FIREBASE_SESSION_COOKIE not in names:
        names.append(_FIREBASE_SESSION_COOKIE)
    # dict.fromkeys preserves insertion order while removing duplicates.
    return tuple(dict.fromkeys(names))


def guest_session_cookie_name() -> str:
    """Return the cookie name used for signed guest sessions."""

    configured = (settings.guest_session_cookie_name or "wp_guest").strip()
    return configured or "wp_guest"


def resolve_guest_session_cookie(request: Request) -> str | None:
    """Return the signed guest session token when present."""

    cookie_name = guest_session_cookie_name()
    return read_session_cookie(request, cookie_name)


def _guest_log_context(request: Request, *, reason: str) -> dict[str, object]:
    """Compose structured log context for guest-session failures."""

    client_ip = request.client.host if request.client else "unknown"
    return {
        "reason": reason,
        "path": request.url.path,
        "client_ip": client_ip,
        "user_agent": request.headers.get("user-agent"),
        "request_id": getattr(request.state, "request_id", None),
    }


def resolve_session_cookie(request: Request) -> tuple[str | None, str | None]:
    """Return the first available session cookie value along with its name."""

    for cookie_name in session_cookie_names():
        token = read_session_cookie(request, cookie_name)
        if token:
            return cookie_name, token
    return None, None


def _resolve_authenticated_user(
    request: Request,
    *,
    log_missing: bool,
) -> dict[str, str] | None:
    """Resolve an authenticated user from session cookies or return None."""

    _cookie_name, raw_token = resolve_session_cookie(request)
    if not raw_token:
        if log_missing:
            logger.warning(
                "session_validation_failed",
                **_session_log_context(request, reason="missing_cookie", user_id=None),
            )
        return None

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


async def get_current_user(request: Request) -> dict[str, str]:
    """Validate session cookie and attach the authenticated user to the request state."""

    user = _resolve_authenticated_user(request, log_missing=True)
    if user is not None:
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session cookie is missing",
    )


async def get_current_user_or_guest(request: Request) -> dict[str, str]:
    """Allow authenticated users or signed guest sessions for read-only access."""

    user = _resolve_authenticated_user(request, log_missing=False)
    if user is not None:
        return user

    guest_token = resolve_guest_session_cookie(request)
    if not guest_token:
        logger.warning(
            "guest_session_invalid",
            **_guest_log_context(request, reason="missing_cookie"),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session or guest cookie is missing",
        )

    try:
        payload = verify_guest_session_token(guest_token)
    except SignatureExpired as exc:
        logger.warning(
            "guest_session_invalid",
            **_guest_log_context(request, reason="expired"),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest session expired",
        ) from exc
    except BadSignature as exc:
        logger.warning(
            "guest_session_invalid",
            **_guest_log_context(request, reason="bad_signature"),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid guest session token",
        ) from exc
    except RuntimeError as exc:
        logger.error(
            "guest_session_invalid",
            **_guest_log_context(request, reason="configuration_error"),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Guest session configuration error",
        ) from exc

    if isinstance(payload, dict) and payload.get("mode") != "guest":
        logger.warning(
            "guest_session_invalid",
            **_guest_log_context(request, reason="missing_guest_mode"),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid guest session payload",
        )

    request.state.guest = True
    return {"mode": "guest"}
