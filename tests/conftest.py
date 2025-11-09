"""Pytest configuration to ensure session-less backend access during tests."""

import os

# Disable session authentication by default so API tests can call endpoints without
# provisioning cookies. Individual tests can override this via monkeypatch when needed.
os.environ.setdefault("DISABLE_SESSION_AUTH", "true")
