from __future__ import annotations

import ipaddress
import logging
from typing import Iterable, Sequence
from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from ..config import settings


class ForwardedHostTrustedHostMiddleware:
    """Validate Host/X-Forwarded-Host against an allowlist, respecting trusted proxies.

    なぜ: 信頼できないプロキシから付与された Host ヘッダーをそのまま受け入れると、
    キャッシュ汚染や Open Redirect などのホスト偽装が発生する。信頼済みプロキシの
    みが提供する X-Forwarded-Host を優先し、それ以外は Host からポートを除いた値
    で照合することで、外部からのホストヘッダー注入を防ぎつつ、正当な経路の
    リバースプロキシ配下でも柔軟に動作させる。
    """

    logger = logging.getLogger("host-check")

    def __init__(
        self,
        app: ASGIApp,
        *,
        allowed_hosts: Sequence[str] | str,
        trusted_proxy_ips: Sequence[str] | str,
    ) -> None:
        self.app = app
        self._allowed_hosts = self._parse_allowed_hosts(allowed_hosts)
        self._trusted_proxies = self._parse_trusted_proxies(trusted_proxy_ips)
        self._trust_all_proxies = any(entry == "*" for entry in self._trusted_proxies)
        self._environment = settings.environment

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        raw_host_header = headers.get("host", "")
        forwarded_host_header = headers.get("x-forwarded-host", "")
        forwarded_for_header = headers.get("x-forwarded-for", "")
        client_ip = scope.get("client", (None, None))[0]

        # 許可判定前に受信ヘッダーの観測ログを残し、トラブルシュート時の手掛かりとする。
        log_context = {
            "path": scope.get("path", ""),
            "raw_host": raw_host_header,
            "x_forwarded_host": forwarded_host_header,
            "x_forwarded_for": forwarded_for_header,
            "client_ip": client_ip,
            "allowed_hosts": list(self._allowed_hosts),
        }
        self.logger.info(
            "host_check_request context=%s", log_context, extra={"context": log_context}
        )

        # 信頼できるプロキシが先頭に並んでいる場合のみ、転送元のホストを有効とする。
        selected_host = self._select_host(
            raw_host_header, forwarded_host_header, forwarded_for_header
        )
        if selected_host and self._is_allowed(selected_host):
            await self.app(scope, receive, send)
            return

        await self._handle_rejection(
            scope,
            receive,
            send,
            host=selected_host,
            raw_host=raw_host_header,
            x_forwarded_host=forwarded_host_header,
            x_forwarded_for=forwarded_for_header,
            client_ip=client_ip,
            path=scope.get("path", ""),
        )

    def _select_host(self, host: str, forwarded_host: str, forwarded_for: str) -> str:
        """Choose the effective host, stripping any port component."""

        candidate_host = host
        forwarded_ip = self._first_forwarded_ip(forwarded_for)
        if forwarded_ip and self._is_trusted_proxy(forwarded_ip):
            first_forwarded_host = self._first_forwarded_host(forwarded_host)
            if first_forwarded_host:
                candidate_host = first_forwarded_host

        return self._strip_port(candidate_host)

    def _is_allowed(self, host: str) -> bool:
        """Check the host against exact entries and leading wildcard patterns."""

        host_value = (host or "").strip().lower()
        if not host_value:
            return False

        for allowed in self._allowed_hosts:
            allowed_host = allowed.lower()
            if allowed_host == "*":
                return True
            if allowed_host.startswith("*."):
                suffix = allowed_host[1:]
                if host_value.endswith(suffix) and host_value != suffix.lstrip("."):
                    return True
            if host_value == allowed_host:
                return True
        return False

    async def _handle_rejection(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        *,
        host: str,
        raw_host: str,
        x_forwarded_host: str,
        x_forwarded_for: str,
        client_ip: str | None,
        path: str,
    ) -> None:
        """Log the mismatch context and send a 400 response."""

        rejection_context = {
            "path": path,
            "selected_host": host,
            "raw_host": raw_host,
            "x_forwarded_host": x_forwarded_host,
            "x_forwarded_for": x_forwarded_for,
            "client_ip": client_ip,
            "allowed_hosts": self._allowed_hosts,
            "environment": self._environment,
        }
        # 拒否理由を構造化して残し、調査時に HTTP 経路やヘッダーの差異を追跡しやすくする。
        self.logger.warning(
            "host_not_allowed context=%s", rejection_context, extra={"context": rejection_context}
        )
        response = PlainTextResponse("Invalid host header", status_code=400)
        await response(scope, receive, send)

    @staticmethod
    def _first_forwarded_ip(forwarded_for: str) -> str | None:
        if not forwarded_for:
            return None
        first = forwarded_for.split(",", 1)[0].strip()
        return first or None

    @staticmethod
    def _first_forwarded_host(forwarded_host: str) -> str | None:
        if not forwarded_host:
            return None
        first = forwarded_host.split(",", 1)[0].strip()
        return first or None

    def _is_trusted_proxy(self, ip_str: str) -> bool:
        if self._trust_all_proxies:
            return True
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False

        return any(
            isinstance(network, (ipaddress.IPv4Network, ipaddress.IPv6Network))
            and ip in network
            for network in self._trusted_proxies
        )

    @staticmethod
    def _strip_port(host_value: str) -> str:
        parsed = urlsplit(f"//{host_value}")
        return parsed.hostname or ""

    @staticmethod
    def _parse_allowed_hosts(raw_hosts: Sequence[str] | str) -> list[str]:
        candidates = ForwardedHostTrustedHostMiddleware._to_sequence(raw_hosts)
        seen: set[str] = set()
        parsed: list[str] = []
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            trimmed = candidate.strip()
            if not trimmed or trimmed in seen:
                continue
            seen.add(trimmed)
            parsed.append(trimmed)
        return parsed

    @staticmethod
    def _parse_trusted_proxies(
        raw_proxies: Sequence[str] | str,
    ) -> list[str | ipaddress.IPv4Network | ipaddress.IPv6Network]:
        proxies = ForwardedHostTrustedHostMiddleware._to_sequence(raw_proxies)
        parsed: list[str | ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for candidate in proxies:
            if not isinstance(candidate, str):
                continue
            trimmed = candidate.strip()
            if not trimmed:
                continue
            if trimmed == "*":
                parsed.append(trimmed)
                continue
            try:
                parsed.append(ipaddress.ip_network(trimmed, strict=False))
            except ValueError:
                continue
        return parsed

    @staticmethod
    def _to_sequence(value: Sequence[str] | str | None) -> Iterable[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return value.split(",")
        return value


__all__ = ["ForwardedHostTrustedHostMiddleware"]
