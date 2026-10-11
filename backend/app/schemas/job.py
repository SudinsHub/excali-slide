import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    deck_id: uuid.UUID
    slide_id: uuid.UUID | None = None
    kind: str
    status: str
    priority: int
    progress: dict[str, Any] = {}
    result: dict[str, Any] | None = None
    attempts: int
    error: str | None = None
    cancel_requested: bool
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
