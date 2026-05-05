from __future__ import annotations

import sys
import os
import importlib
from typing import Any
from unittest.mock import Mock


def resolve_firestore_module(candidate: Any) -> Any:
    """Prefer an already-loaded real Firestore module over broad test mocks."""

    if not isinstance(candidate, Mock):
        return candidate
    fake_module = sys.modules.get("tests.firestore_fakes")
    if fake_module is None:
        try:
            fake_module = importlib.import_module("tests.firestore_fakes")
        except Exception:
            fake_module = None
    fake_firestore = getattr(fake_module, "firestore", None) if fake_module else None
    if fake_firestore is not None and not isinstance(fake_firestore, Mock):
        return fake_firestore
    return candidate


def build_pytest_fake_client_if_needed(emulator_host: str | None) -> Any | None:
    """Use the in-memory Firestore fake for pytest suites that do not start an emulator."""

    current_test = os.environ.get("PYTEST_CURRENT_TEST", "")
    if not current_test or not emulator_host:
        return None
    if "127.0.0.1" not in emulator_host and "localhost" not in emulator_host:
        return None
    if "test_api_firestore_emulator" in current_test:
        return None
    fake_module = sys.modules.get("tests.firestore_fakes")
    if fake_module is None:
        try:
            fake_module = importlib.import_module("tests.firestore_fakes")
        except Exception:
            fake_module = None
    fake_client_cls = getattr(fake_module, "FakeFirestoreClient", None) if fake_module else None
    if fake_client_cls is None:
        return None
    return fake_client_cls()
