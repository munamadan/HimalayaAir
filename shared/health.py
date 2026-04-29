from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from shared.time_utils import utc_now


class HealthPayload(BaseModel):
    service: str
    status: Literal["ok", "degraded", "failed"]
    checked_at: datetime = Field(default_factory=utc_now)
    version: str = "unknown"
    details: dict[str, Any] = Field(default_factory=dict)

