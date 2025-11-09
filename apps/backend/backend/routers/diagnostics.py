"""Diagnostics router for capturing OAuth telemetry from the frontend."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, ConfigDict, Field

from ..logging import logger


router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])

_SENSITIVE_TOKEN_KEYS = {"access_token", "id_token", "refresh_token", "code"}


def _mask_secret(value: str) -> str:
    """Mask OAuth secrets to avoid leaking raw credentials into logs."""

    if not value:
        return "***"
    if len(value) <= 4:
        return "***"
    return f"{value[:2]}…{value[-1]}"


def _mask_email(value: str) -> str:
    """Apply coarse masking for email addresses (local part only)."""

    local, _, domain = value.partition("@")
    if not domain:
        return _mask_secret(value)
    if len(local) <= 2:
        return f"{(local[:1] or '*')}***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


def _sanitize_token_response(data: dict[str, Any] | None) -> dict[str, Any]:
    """Recursively sanitize token payloads for safe logging."""

    if not data:
        return {}
    sanitized: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            if key in _SENSITIVE_TOKEN_KEYS:
                sanitized[key] = _mask_secret(value)
            elif "@" in value:
                sanitized[key] = _mask_email(value)
            else:
                sanitized[key] = value
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_token_response(value)
        else:
            sanitized[key] = value
    return sanitized


class OAuthTelemetryPayload(BaseModel):
    """Minimal payload forwarded by the frontend when ID token acquisition fails."""

    model_config = ConfigDict(populate_by_name=True)

    event: str
    google_client_id: str | None = Field(default=None, alias="googleClientId")
    error_category: str = Field(alias="errorCategory")
    token_response: dict[str, Any] | None = Field(default=None, alias="tokenResponse")


@router.post("/oauth-telemetry", status_code=status.HTTP_204_NO_CONTENT)
async def report_oauth_telemetry(payload: OAuthTelemetryPayload) -> Response:
    """Record structured telemetry for missing Google ID tokens."""

    context = {
        "reported_event": payload.event,
        "google_client_id": payload.google_client_id,
        "error_category": payload.error_category,
        "token_response": _sanitize_token_response(payload.token_response),
    }
    logger.warning("google_login_missing_id_token", **context)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
