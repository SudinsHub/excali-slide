import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    deck_id: uuid.UUID
    version: int
    status: str
    content: dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime


class PlanRegenerateRequest(BaseModel):
    feedback: str | None = None
