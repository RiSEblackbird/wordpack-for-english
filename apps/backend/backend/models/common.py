from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class ConfidenceLevel(str, Enum):
    """Confidence indicator for generated content."""

    low = "low"
    medium = "medium"
    high = "high"


class Citation(BaseModel):
    """Structured citation metadata attached to WordPack outputs."""

    model_config = ConfigDict(extra="ignore")

    text: str
    meta: dict[str, Any] | None = None
