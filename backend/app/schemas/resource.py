import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ResourceImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: str
    caption: str | None = None
    locator: str | None = None


class ResourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    deck_id: uuid.UUID
    kind: str
    filename: str
    mime: str
    size: int
    status: str
    text: str | None = None
    meta: dict[str, Any] | None = None
    error: str | None = None
    images: list[ResourceImageRead] = []
    created_at: datetime
    updated_at: datetime
