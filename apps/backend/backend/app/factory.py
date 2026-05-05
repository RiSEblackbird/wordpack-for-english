from __future__ import annotations

from typing import Any, Awaitable, Callable

from fastapi import FastAPI

from ..logging import configure_logging, logger
from .lifecycle import build_lifespan, on_shutdown, on_startup_seed
from .middleware_stack import configure_middleware
from .routers import include_routers

LifecycleHook = Callable[[], Awaitable[None]]


def create_app(
    *,
    app_settings: Any | None = None,
    startup_seed: LifecycleHook | None = None,
    shutdown: LifecycleHook | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application instance."""

    from ..config import settings

    active_settings = app_settings or settings
    configure_logging()
    logger.info(
        "ALLOWED_HOSTS init raw=%r parsed=%r",
        active_settings.allowed_hosts_raw,
        active_settings.allowed_hosts,
    )
    startup_hook = startup_seed or (lambda: on_startup_seed(active_settings))
    shutdown_hook = shutdown or on_shutdown
    app = FastAPI(
        title="WordPack API",
        version="0.3.1",
        lifespan=build_lifespan(startup_seed=startup_hook, shutdown=shutdown_hook),
    )
    configure_middleware(app, active_settings)
    include_routers(app, active_settings)
    return app
