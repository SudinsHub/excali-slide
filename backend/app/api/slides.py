import uuid
from datetime import UTC

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.slide import SlideCreate, SlideDetail, SlideReadLight, SlideReorder
from app.services.slides import (
    create_blank_slide,
    delete_slide,
    duplicate_slide,
    get_slide_detail,
    list_slides,
    reorder_slide,
)

deck_slides_router = APIRouter(prefix="/decks/{deck_id}/slides", tags=["slides"])
slides_router = APIRouter(prefix="/slides", tags=["slides"])


@deck_slides_router.get("", response_model=list[SlideReadLight])
async def get_deck_slides(
    deck_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> list[SlideReadLight]:
    return await list_slides(db, deck_id)


@deck_slides_router.post("", response_model=SlideDetail, status_code=status.HTTP_201_CREATED)
async def create_new_blank_slide(
    deck_id: uuid.UUID,
    data: SlideCreate | None = None,
    db: AsyncSession = Depends(get_db),
) -> SlideDetail:
    pos = data.position if data else None
    slide = await create_blank_slide(db, deck_id, pos)
    return await get_slide_detail(db, slide.id)


@slides_router.get("/{slide_id}", response_model=SlideDetail)
async def get_single_slide(slide_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> SlideDetail:
    return await get_slide_detail(db, slide_id)


@slides_router.patch("/{slide_id}", response_model=SlideDetail)
async def reorder_single_slide(
    slide_id: uuid.UUID,
    data: SlideReorder,
    db: AsyncSession = Depends(get_db),
) -> SlideDetail:
    slide = await reorder_slide(db, slide_id, data.position)
    return await get_slide_detail(db, slide.id)


@slides_router.delete("/{slide_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_single_slide(slide_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    await delete_slide(db, slide_id)


@slides_router.post(
    "/{slide_id}/duplicate", response_model=SlideDetail, status_code=status.HTTP_201_CREATED
)
async def duplicate_single_slide(
    slide_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> SlideDetail:
    new_slide = await duplicate_slide(db, slide_id)
    return await get_slide_detail(db, new_slide.id)


@slides_router.post("/{slide_id}/regenerate", status_code=status.HTTP_202_ACCEPTED)
async def regenerate_single_slide(
    slide_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    from datetime import datetime

    from app.errors import NotFoundError
    from app.jobs.queue import enqueue
    from app.models.slide import Slide

    slide = await db.get(Slide, slide_id)
    if not slide or slide.deleted_at is not None:
        raise NotFoundError("Slide not found")

    slide.status = "queued"
    slide.error = None
    slide.updated_at = datetime.now(UTC)

    job = await enqueue(
        db,
        kind="generate_slide",
        deck_id=slide.deck_id,
        slide_id=slide.id,
        priority=6,
    )
    await db.commit()
    return {"job_id": str(job.id), "status": "queued"}
