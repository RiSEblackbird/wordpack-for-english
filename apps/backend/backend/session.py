from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional

from itsdangerous import BadSignature, URLSafeSerializer

from .config import settings


class SessionData(Dict[str, Any]):
    email: str
    name: str | None
    picture: str | None
    expires_at: dt.datetime


class SessionManager:
    def __init__(self, secret: str, salt: str = "wordpack-session") -> None:
        if not secret:
            raise ValueError("Session secret is required")
        self._serializer = URLSafeSerializer(secret, salt=salt)

    def encode(self, payload: SessionData) -> str:
        data = dict(payload)
        data["expires_at"] = payload["expires_at"].isoformat()
        return self._serializer.dumps(data)

    def decode(self, token: str) -> Optional[SessionData]:
        if not token:
            return None
        try:
            data = self._serializer.loads(token)
        except BadSignature:
            return None
        expires_at = data.get("expires_at")
        if not isinstance(expires_at, str):
            return None
        try:
            exp = dt.datetime.fromisoformat(expires_at)
        except ValueError:
            return None
        if dt.datetime.utcnow() > exp:
            return None
        data["expires_at"] = exp
        return SessionData(data)


session_manager = SessionManager(settings.session_secret or "development-secret")

