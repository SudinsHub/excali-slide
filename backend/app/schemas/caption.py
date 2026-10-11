from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CaptionKind = Literal["photo", "screenshot", "chart", "diagram", "logo", "other"]


class ImageCaption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    caption: str = Field(..., max_length=160)
    kind: CaptionKind
