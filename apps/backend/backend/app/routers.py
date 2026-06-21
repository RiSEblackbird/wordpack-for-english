from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI

from ..auth import get_current_user_or_guest
from ..logging import logger
from ..routers import article as article_router
from ..routers import auth as auth_router
from ..routers import config as cfg
from ..routers import quiz as quiz_router
from ..routers import debug, diagnostics, health, tts, word


def include_routers(app: FastAPI, app_settings: Any) -> None:
    if app_settings.disable_session_auth:
        logger.warning(
            "session_auth_disabled",
            reason="config_flag",
        )
        protected_dependency: list[Any] = []
    else:
        protected_dependency = [Depends(get_current_user_or_guest)]

    app.include_router(auth_router.router)
    app.include_router(word.router, prefix="/api/word", dependencies=protected_dependency)
    app.include_router(
        article_router.router,
        prefix="/api/article",
        dependencies=protected_dependency,
    )
    app.include_router(
        quiz_router.router,
        prefix="/api/quiz",
        dependencies=protected_dependency,
    )
    app.include_router(debug.router)
    app.include_router(diagnostics.router)
    app.include_router(health.router)
    app.include_router(cfg.router, prefix="/api")
    app.include_router(tts.router, dependencies=protected_dependency)
