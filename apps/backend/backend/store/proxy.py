from __future__ import annotations

import sys
from typing import Any


class CurrentStoreProxy:
    """Resolve backend.store.store at call time while keeping old imports usable."""

    def __init__(self, default_store: Any) -> None:
        self._default_store = default_store

    def _target(self) -> Any:
        store_module = sys.modules.get("backend.store")
        current = getattr(store_module, "store", None) if store_module else None
        if current is None or current is self:
            return self._default_store
        return current

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target(), name)
