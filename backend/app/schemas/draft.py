import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DraftUpdate(BaseModel):
    scene: dict[str, Any] = Field(..., description="Excalidraw scene JSON")
    if_rev: int = Field(..., ge=0, description="Expected draft revision to avoid lost updates")
    normalizing_version_id: uuid.UUID | None = Field(
        default=None,
        description="If specified and matches current version without scene, also saves to version.scene once",
    )


class DraftRead(BaseModel):
    scene: dict[str, Any] | None = None
    rev: int = 0
    hash: str | None = None
    updated_at: datetime | None = None
