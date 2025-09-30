from __future__ import annotations

import threading
import time
import uuid
from typing import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from .config import settings
from .session import session_manager


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign a request ID to each incoming request and expose it in headers.

    - Sets `request.state.request_id`
    - Adds `X-Request-ID` to the response headers
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:  # type: ignore[override]
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        try:
            response.headers["X-Request-ID"] = request_id
        except Exception:
            # Some response types may not allow header mutation after body start
            pass
        return response


class _TokenBucket:
    """Thread-safe token bucket that refills to capacity every fixed interval (seconds)."""

    def __init__(self, capacity: int, refill_interval_sec: float) -> None:
        self.capacity = max(1, capacity)
        self.tokens = self.capacity
        self.refill_interval = max(1.0, float(refill_interval_sec))
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def allow(self) -> tuple[bool, int]:
        """Consume one token if available and return the remaining count."""
        now = time.time()
        with self._lock:
            elapsed = now - self.last_refill
            if elapsed >= self.refill_interval:
                self.tokens = self.capacity
                self.last_refill = now
            if self.tokens > 0:
                self.tokens -= 1
                return True, self.tokens
            return False, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple IP/User rate limiting using token buckets.

    Two independent buckets:
    - per IP address
    - per user (via header `X-User-Id`)

    If either bucket is exhausted, respond 429.
    """

    def __init__(
        self,
        app,
        *,
        ip_capacity_per_minute: int,
        user_capacity_per_minute: int,
        user_header: str = "X-User-Id",
    ) -> None:
        super().__init__(app)
        self._ip_capacity = max(1, int(ip_capacity_per_minute))
        self._user_capacity = max(1, int(user_capacity_per_minute))
        self._user_header = user_header.lower()
        self._ip_buckets: dict[str, _TokenBucket] = {}
        self._user_buckets: dict[str, _TokenBucket] = {}
        self._lock = threading.Lock()

    def _get_bucket(
        self, mapping: dict[str, _TokenBucket], key: str, capacity: int
    ) -> _TokenBucket:
        with self._lock:
            if key not in mapping:
                mapping[key] = _TokenBucket(capacity=capacity, refill_interval_sec=60.0)
            return mapping[key]

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:  # type: ignore[override]
        # Identify caller
        client_ip = request.client.host if request.client else "unknown"
        user_id = request.headers.get(self._user_header) or ""
        ip_bucket = self._get_bucket(self._ip_buckets, client_ip, self._ip_capacity)
        ok_ip, remaining_ip = ip_bucket.allow()
        if not ok_ip:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too Many Requests (per IP)"},
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit-Ip": str(self._ip_capacity),
                    "X-RateLimit-Remaining-Ip": str(remaining_ip),
                },
            )

        if user_id:
            user_bucket = self._get_bucket(
                self._user_buckets, user_id, self._user_capacity
            )
            ok_user, remaining_user = user_bucket.allow()
            if not ok_user:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too Many Requests (per User)"},
                    headers={
                        "Retry-After": "60",
                        "X-RateLimit-Limit-User": str(self._user_capacity),
                        "X-RateLimit-Remaining-User": str(remaining_user),
                    },
                )

        response = await call_next(request)
        # Optionally expose current remaining counts (best-effort)
        try:
            response.headers.setdefault("X-RateLimit-Limit-Ip", str(self._ip_capacity))
            response.headers.setdefault("X-RateLimit-Remaining-Ip", str(remaining_ip))
            if user_id:
                response.headers.setdefault(
                    "X-RateLimit-Limit-User", str(self._user_capacity)
                )
                response.headers.setdefault(
                    "X-RateLimit-Remaining-User", str(remaining_user)
                )
        except Exception:
            pass
        return response


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:  # type: ignore[override]
        cookie_name = getattr(request.app.state, "session_cookie_name", settings.session_cookie_name)
        raw_cookie = request.cookies.get(cookie_name)
        session = session_manager.decode(raw_cookie) if raw_cookie else None
        request.state.session_user = session
        response = await call_next(request)
        return response
