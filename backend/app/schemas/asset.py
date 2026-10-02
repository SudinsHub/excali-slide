import uuid
from datetime import datetime

from pydantic import BaseModel


class AssetRead(BaseModel):
    id: str
    deck_id: uuid.UUID
    storage_key: str
    mime: str
    width: int | None = None
    height: int | None = None
    created_at: datetime
