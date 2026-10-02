import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DeckSettings(BaseModel):
    slide_count: int | None = Field(default=None, ge=3, le=30)
    tone: Literal["professional", "casual", "playful", "technical", "persuasive"] = "professional"
    diagram_intensity: Literal["low", "medium", "high"] = "medium"
    density: Literal["light", "standard", "dense"] = "standard"
    audience: str = "general"
    language: str = "English"
    extra_instructions: str = ""


class DeckCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    settings: DeckSettings = Field(default_factory=DeckSettings)


class DeckUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    settings: DeckSettings | None = None


class DeckRead(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    settings: DeckSettings
    current_plan_id: uuid.UUID | None = None
    slide_count: int = 0
    created_at: datetime
    updated_at: datetime
