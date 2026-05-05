from __future__ import annotations

import os

from google.cloud import firestore as _firestore

from ..config import settings
from ..infrastructure.firestore.google_module import (
    build_pytest_fake_client_if_needed,
    resolve_firestore_module,
)
from .examples import EXAMPLE_CATEGORIES
from .firestore_store import AppFirestoreStore

firestore = resolve_firestore_module(_firestore)


def _normalize_emulator_host(raw_host: str | None) -> str | None:
    host = (raw_host or "").strip()
    if not host:
        return None
    if host.startswith(("http://", "https://")):
        return host
    return f"http://{host}"


def _build_firestore_client():
    emulator_host = _normalize_emulator_host(
        settings.firestore_emulator_host or os.environ.get("FIRESTORE_EMULATOR_HOST")
    )
    project_id = settings.firestore_project_id or settings.gcp_project_id
    fake_client = build_pytest_fake_client_if_needed(emulator_host)
    if fake_client is not None:
        return fake_client
    if emulator_host:
        os.environ.setdefault(
            "FIRESTORE_EMULATOR_HOST",
            emulator_host.replace("http://", "").replace("https://", ""),
        )
        return firestore.Client(
            project=project_id,
            client_options={"api_endpoint": emulator_host},
        )
    return firestore.Client(project=project_id)


def _create_store() -> AppFirestoreStore:
    return AppFirestoreStore(client=_build_firestore_client())


store = _create_store()

__all__ = [
    "AppFirestoreStore",
    "store",
    "EXAMPLE_CATEGORIES",
    "firestore",
    "settings",
    "_build_firestore_client",
    "_create_store",
    "_normalize_emulator_host",
]
