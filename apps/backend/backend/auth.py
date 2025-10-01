from __future__ import annotations

import datetime as dt
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Response
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from .config import settings
from .logging import logger
from .session import SessionData, session_manager

router = APIRouter(prefix="/api/auth", tags=["auth"])


def verify_google_token(token: str) -> Dict[str, Any]:
    if not settings.google_oauth_client_id:
        raise ValueError("Google OAuth client id not configured")
    try:
        return id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.google_oauth_client_id,
            clock_skew_in_seconds=30,
        )
    except Exception as exc:  # pragma: no cover
        raise ValueError("Invalid token") from exc


def _build_session_payload(user_info: Dict[str, Any]) -> SessionData:
    email = user_info.get("email")
    if not isinstance(email, str) or not email:
        raise ValueError("Google credential missing email")
    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=settings.session_cookie_max_age_sec)
    return SessionData(
        email=email.lower(),
        name=str(user_info.get("name") or ""),
        picture=str(user_info.get("picture") or ""),
        expires_at=expires_at,
    )


@router.get("/meta")
async def get_auth_meta() -> dict[str, str | None]:
    return {"client_id": settings.google_oauth_client_id}


@router.post("/login")
async def login(payload: dict[str, str], response: Response) -> dict[str, Any]:
    credential = payload.get("credential")
    if not credential:
        raise HTTPException(status_code=400, detail="Missing credential")
    try:
        claims = verify_google_token(credential)
        session_payload = _build_session_payload(claims)
    except ValueError as exc:
        logger.warning("auth_login_failed", reason=str(exc))
        raise HTTPException(status_code=401, detail="Invalid credential")

    cookie_value = session_manager.encode(session_payload)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=cookie_value,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_same_site,
        max_age=settings.session_cookie_max_age_sec,
        expires=session_payload.expires_at,
        path="/",
    )
    return {
        "email": session_payload.email,
        "name": session_payload.name,
        "picture": session_payload.picture,
        "role": "viewer",
        "expires_at": session_payload.expires_at.isoformat(),
    }


@router.post("/logout")
async def logout(response: Response) -> Response:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_same_site,
        path="/",
    )
    response.set_cookie(
        key=settings.session_cookie_name,
        value="",
        expires=0,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_same_site,
    )
    return Response(status_code=204) 