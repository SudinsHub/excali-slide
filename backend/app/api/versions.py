import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.slide import SlideDetail
from app.schemas.version import RestoreRequest, VersionCreate, VersionDetail, VersionReadLight
from app.services.slides import get_slide_detail
from app.services.versions import checkpoint_slide, list_versions, restore_version

router = APIRouter(prefix="/slides/{slide_id}", tags=["versions"])


@router.get("/versions", response_model=list[VersionReadLight])
async def get_slide_versions(
    slide_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> list[VersionReadLight]:
    return await list_versions(db, slide_id)


@router.post("/versions", response_model=VersionDetail, status_code=status.HTTP_201_CREATED)
async def create_slide_checkpoint(
    slide_id: uuid.UUID,
    data: VersionCreate | None = None,
    db: AsyncSession = Depends(get_db),
) -> VersionDetail:
    summary = data.summary if data else None
    v = await checkpoint_slide(db, slide_id, summary)
    return VersionDetail(
        id=v.id,
        slide_id=v.slide_id,
        seq=v.seq,
        parent_version_id=v.parent_version_id,
        origin=v.origin,
        prompt=v.prompt,
        summary=v.summary,
        ir=v.ir,
        skeleton=v.skeleton,
        scene=v.scene,
        scene_hash=v.scene_hash,
        warnings=v.warnings or [],
        created_at=v.created_at,
    )


@router.post("/restore", response_model=SlideDetail)
async def restore_slide_version(
    slide_id: uuid.UUID,
    data: RestoreRequest,
    db: AsyncSession = Depends(get_db),
) -> SlideDetail:
    await restore_version(db, slide_id, data.version_id)
    return await get_slide_detail(db, slide_id)
