from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, ConfigDict


class ConfidenceLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Citation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str
    meta: Optional[Dict[str, Any]] = None


