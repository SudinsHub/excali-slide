import uuid

from pydantic import BaseModel, Field

from app.schemas.draft import DraftRead
from app.schemas.version import VersionDetail


class SlideCreate(BaseModel):
    position: int | None = Field(default=None, ge=0)


class SlideReadLight(BaseModel):
    id: uuid.UUID
    position: int
    status: str
    title: str | None = None
    current_version_id: uuid.UUID | None = None
    draft_rev: int = 0
    is_dirty: bool = False


class SlideDetail(BaseModel):
    id: uuid.UUID
    deck_id: uuid.UUID
    position: int
    plan_key: str | None = None
    status: str
    error: str | None = None
    current_version: VersionDetail | None = None
    draft: DraftRead | None = None
    is_dirty: bool = False


class SlideReorder(BaseModel):
    position: int = Field(..., ge=0)
