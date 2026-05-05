from __future__ import annotations

from fastapi import FastAPI

from .app.factory import create_app as _create_app
from .app.lifecycle import on_shutdown, on_startup_seed
from .config import settings
from .logging import logger
from .observability import AccessLogAndMetricsMiddleware, parse_cloud_trace_header


async def _on_shutdown() -> None:
    """Compatibility hook for tests and older imports."""

    await on_shutdown()


async def _on_startup_seed() -> None:
    """Compatibility hook for tests and older imports."""

    await on_startup_seed(settings)


def _parse_cloud_trace_header(raw_header: str | None) -> dict[str, object]:
    """Compatibility wrapper for the old `backend.main` helper."""

    return parse_cloud_trace_header(raw_header, gcp_project_id=settings.gcp_project_id)


def create_app() -> FastAPI:
    """Create the FastAPI app using `backend.main` compatibility globals."""

    return _create_app(
        app_settings=settings,
        startup_seed=_on_startup_seed,
        shutdown=_on_shutdown,
    )


app = create_app()

__all__ = [
    "AccessLogAndMetricsMiddleware",
    "app",
    "create_app",
    "settings",
    "logger",
    "_on_shutdown",
    "_on_startup_seed",
    "_parse_cloud_trace_header",
]
