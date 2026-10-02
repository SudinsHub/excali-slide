import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.draft import DraftUpdate
from app.schemas.slide import SlideDetail
from app.services.drafts import save_draft
from app.services.slides import get_slide_detail

router = APIRouter(prefix="/slides/{slide_id}/draft", tags=["drafts"])


@router.put("", response_model=SlideDetail)
async def update_slide_draft(
    slide_id: uuid.UUID,
    data: DraftUpdate,
    db: AsyncSession = Depends(get_db),
) -> SlideDetail:
    await save_draft(db, slide_id, data)
    return await get_slide_detail(db, slide_id)
