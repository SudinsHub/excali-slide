import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class VersionReadLight(BaseModel):
    id: uuid.UUID
    seq: int
    origin: str
    summary: str | None = None
    created_at: datetime
    has_ir: bool = False


class VersionDetail(BaseModel):
    id: uuid.UUID
    slide_id: uuid.UUID
    seq: int
    parent_version_id: uuid.UUID | None = None
    origin: str
    prompt: str | None = None
    summary: str | None = None
    ir: dict[str, Any] | None = None
    skeleton: dict[str, Any] | None = None
    scene: dict[str, Any] | None = None
    scene_hash: str | None = None
    warnings: list[Any] = Field(default_factory=list)
    created_at: datetime


class VersionCreate(BaseModel):
    summary: str | None = Field(
        default=None, max_length=255, description="Optional checkpoint summary/label"
    )


class RestoreRequest(BaseModel):
    version_id: uuid.UUID
