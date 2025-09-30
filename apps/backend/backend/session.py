from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass

from itsdangerous import BadSignature, URLSafeSerializer

from .config import settings


UTC = dt.timezone.utc


@dataclass(frozen=True)
class SessionData:
    email: str
    name: str | None = None
    picture: str | None = None
    expires_at: dt.datetime = dt.datetime.now(UTC)


class SessionManager:
    def __init__(self, secret: str, salt: str = "wordpack-session") -> None:
        if not secret:
            raise ValueError("Session secret is required")
        self._serializer = URLSafeSerializer(secret, salt=salt)

    def encode(self, payload: SessionData) -> str:
        data = asdict(payload)
        data["expires_at"] = payload.expires_at.isoformat()
        return self._serializer.dumps(data)

    def decode(self, token: str) -> SessionData | None:
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
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)
        if dt.datetime.now(UTC) > exp:
            return None
        email_raw = data.get("email")
        if not isinstance(email_raw, str) or not email_raw:
            return None
        return SessionData(
            email=email_raw.lower(),
            name=data.get("name"),
            picture=data.get("picture"),
            expires_at=exp,
        )


session_secret = settings.session_secret
if not session_secret:
    if settings.strict_mode:
        raise ValueError("SESSION_SECRET must be set in strict mode")
    session_secret = "development-secret"

session_manager = SessionManager(session_secret)

