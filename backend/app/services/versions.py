import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NotFoundError
from app.models.slide import Slide
from app.models.slide_version import SlideVersion
from app.schemas.version import VersionReadLight
from app.services.drafts import commit_draft


async def list_versions(db: AsyncSession, slide_id: uuid.UUID) -> list[VersionReadLight]:
    # Check slide exists
    slide_stmt = select(Slide).where(Slide.id == slide_id, Slide.deleted_at.is_(None))
    s_res = await db.execute(slide_stmt)
    if not s_res.scalar_one_or_none():
        raise NotFoundError(
            message=f"Slide '{slide_id}' not found", details={"slide_id": str(slide_id)}
        )

    stmt = (
        select(SlideVersion)
        .where(SlideVersion.slide_id == slide_id)
        .order_by(SlideVersion.seq.desc())
    )
    result = await db.execute(stmt)
    versions = result.scalars().all()

    return [
        VersionReadLight(
            id=v.id,
            seq=v.seq,
            origin=v.origin,
            summary=v.summary,
            created_at=v.created_at,
            has_ir=v.ir is not None,
        )
        for v in versions
    ]


async def checkpoint_slide(
    db: AsyncSession, slide_id: uuid.UUID, summary: str | None = None
) -> SlideVersion:
    slide_stmt = select(Slide).where(Slide.id == slide_id, Slide.deleted_at.is_(None))
    result = await db.execute(slide_stmt)
    slide = result.scalar_one_or_none()
    if not slide:
        raise NotFoundError(
            message=f"Slide '{slide_id}' not found", details={"slide_id": str(slide_id)}
        )

    return await commit_draft(
        db,
        slide,
        origin="user_checkpoint",
        summary=summary or f"Checkpoint rev {slide.draft_rev}",
    )


async def restore_version(
    db: AsyncSession, slide_id: uuid.UUID, target_version_id: uuid.UUID
) -> SlideVersion:
    slide_stmt = select(Slide).where(Slide.id == slide_id, Slide.deleted_at.is_(None))
    result = await db.execute(slide_stmt)
    slide = result.scalar_one_or_none()
    if not slide:
        raise NotFoundError(
            message=f"Slide '{slide_id}' not found", details={"slide_id": str(slide_id)}
        )

    target_stmt = select(SlideVersion).where(
        SlideVersion.id == target_version_id, SlideVersion.slide_id == slide_id
    )
    target_res = await db.execute(target_stmt)
    target_v = target_res.scalar_one_or_none()
    if not target_v:
        raise NotFoundError(
            message=f"Version '{target_version_id}' not found for slide '{slide_id}'",
            details={"version_id": str(target_version_id), "slide_id": str(slide_id)},
        )

    # Next seq
    seq_stmt = select(func.coalesce(func.max(SlideVersion.seq), 0)).where(
        SlideVersion.slide_id == slide_id
    )
    seq_res = await db.execute(seq_stmt)
    next_seq = (seq_res.scalar() or 0) + 1

    # Create new version representing the restore
    restore_v = SlideVersion(
        slide_id=slide_id,
        seq=next_seq,
        parent_version_id=slide.current_version_id,
        origin="restore",
        summary=f"Restored from version {target_v.seq}",
        ir=target_v.ir,
        skeleton=target_v.skeleton,
        scene=target_v.scene,
        scene_hash=target_v.scene_hash,
        warnings=target_v.warnings or [],
    )
    db.add(restore_v)
    await db.flush()

    # Update slide
    slide.current_version_id = restore_v.id
    slide.draft_scene = target_v.scene
    slide.draft_hash = target_v.scene_hash
    slide.draft_rev += 1
    slide.draft_updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(restore_v)
    return restore_v
