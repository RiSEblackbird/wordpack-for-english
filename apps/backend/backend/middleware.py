from __future__ import annotations

import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from typing import Awaitable, Callable

from fastapi import Request
from itsdangerous import BadSignature, SignatureExpired
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from .auth import verify_session_token
from .config import settings
from .logging import logger


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


@dataclass
class _TrackedBucket:
    """Bundle a token bucket with its last access timestamp for eviction control."""

    bucket: _TokenBucket
    last_seen: float


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting per IP and per authenticated session using token buckets.

    なぜ: セッション Cookie を検証したユーザー単位でバケットを割り当て、
    任意ヘッダ偽装による制限回避を防ぐ。同時にバケットの最終利用時刻を追跡し、
    長時間アクセスのないキーを捨てることでメモリ使用量を抑える。
    """

    def __init__(
        self,
        app,
        *,
        ip_capacity_per_minute: int,
        user_capacity_per_minute: int,
        user_bucket_ttl_seconds: float = 15 * 60,
        max_user_buckets: int = 10_000,
    ) -> None:
        super().__init__(app)
        self._ip_capacity = max(1, int(ip_capacity_per_minute))
        self._user_capacity = max(1, int(user_capacity_per_minute))
        self._ip_buckets: dict[str, _TokenBucket] = {}
        self._user_buckets: OrderedDict[str, _TrackedBucket] = OrderedDict()
        self._lock = threading.Lock()
        self._session_cookie_name = settings.session_cookie_name or "wp_session"
        self._anon_bucket_key = "anon"
        self._user_bucket_ttl = max(1.0, float(user_bucket_ttl_seconds))
        self._max_user_buckets = max(1, int(max_user_buckets))

    def _get_ip_bucket(self, key: str) -> _TokenBucket:
        with self._lock:
            if key not in self._ip_buckets:
                self._ip_buckets[key] = _TokenBucket(
                    capacity=self._ip_capacity,
                    refill_interval_sec=60.0,
                )
            return self._ip_buckets[key]

    def _prune_user_buckets(self, now: float) -> None:
        """Remove stale buckets and trim the OrderedDict to the configured max."""

        expired_keys = [
            key
            for key, entry in self._user_buckets.items()
            if now - entry.last_seen > self._user_bucket_ttl
        ]
        for key in expired_keys:
            self._user_buckets.pop(key, None)
        while len(self._user_buckets) >= self._max_user_buckets:
            # OrderedDict preserves insertion order; pop oldest entries first.
            self._user_buckets.popitem(last=False)

    def _get_user_bucket(self, key: str, now: float) -> _TokenBucket:
        with self._lock:
            self._prune_user_buckets(now)
            entry = self._user_buckets.get(key)
            if entry is None:
                entry = _TrackedBucket(
                    bucket=_TokenBucket(
                        capacity=self._user_capacity,
                        refill_interval_sec=60.0,
                    ),
                    last_seen=now,
                )
                self._user_buckets[key] = entry
            else:
                entry.last_seen = now
                self._user_buckets.move_to_end(key, last=True)
            return entry.bucket

    def _resolve_user_key(self, request: Request, client_ip: str) -> tuple[str, bool]:
        """Resolve the logical session identifier from the signed cookie."""

        raw_token = request.cookies.get(self._session_cookie_name)
        if not raw_token:
            logger.debug("rate_limit_session_missing", client_ip=client_ip)
            return self._anon_bucket_key, False

        try:
            payload = verify_session_token(raw_token)
        except SignatureExpired:
            logger.debug(
                "rate_limit_session_invalid",
                reason="expired",
                client_ip=client_ip,
            )
            return self._anon_bucket_key, False
        except BadSignature:
            logger.debug(
                "rate_limit_session_invalid",
                reason="bad_signature",
                client_ip=client_ip,
            )
            return self._anon_bucket_key, False
        except RuntimeError:
            logger.error(
                "rate_limit_session_invalid",
                reason="configuration_error",
                client_ip=client_ip,
            )
            return self._anon_bucket_key, False
        except Exception:  # pragma: no cover - defensive guard for unexpected errors
            logger.debug(
                "rate_limit_session_invalid",
                reason="unexpected_error",
                client_ip=client_ip,
            )
            return self._anon_bucket_key, False

        sub = payload.get("sub") if isinstance(payload, dict) else None
        if isinstance(sub, str) and sub:
            return sub, True

        logger.debug(
            "rate_limit_session_invalid",
            reason="missing_sub",
            client_ip=client_ip,
        )
        return self._anon_bucket_key, False

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:  # type: ignore[override]
        # Identify caller
        client_ip = request.client.host if request.client else "unknown"
        user_key, is_authenticated = self._resolve_user_key(request, client_ip)
        now = time.time()
        ip_bucket = self._get_ip_bucket(client_ip)
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

        ok_user = True
        remaining_user: int | None = None
        if is_authenticated:
            user_bucket = self._get_user_bucket(user_key, now)
            ok_user, remaining_user = user_bucket.allow()

        if not ok_user:
            detail = (
                "Too Many Requests (per User)"
                if is_authenticated
                else "Too Many Requests (per Session)"
            )
            headers = {
                "Retry-After": "60",
                "X-RateLimit-Limit-Ip": str(self._ip_capacity),
                "X-RateLimit-Remaining-Ip": str(remaining_ip),
            }
            if is_authenticated:
                headers["X-RateLimit-Limit-User"] = str(self._user_capacity)
                headers["X-RateLimit-Remaining-User"] = str(remaining_user)
            return JSONResponse(
                status_code=429,
                content={"detail": detail},
                headers=headers,
            )

        response = await call_next(request)
        # Optionally expose current remaining counts (best-effort)
        try:
            response.headers.setdefault("X-RateLimit-Limit-Ip", str(self._ip_capacity))
            response.headers.setdefault("X-RateLimit-Remaining-Ip", str(remaining_ip))
            if is_authenticated:
                response.headers.setdefault(
                    "X-RateLimit-Limit-User", str(self._user_capacity)
                )
                response.headers.setdefault(
                    "X-RateLimit-Remaining-User", str(remaining_user)
                )
        except Exception:
            pass
        return response
