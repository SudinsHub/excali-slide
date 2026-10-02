import copy
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.errors import NotFoundError
from app.models.deck import Deck
from app.models.slide import Slide
from app.models.slide_version import SlideVersion
from app.schemas.draft import DraftRead
from app.schemas.slide import SlideDetail, SlideReadLight
from app.schemas.version import VersionDetail

BLANK_FRAME_SKELETON: dict[str, Any] = {
    "version": 1,
    "frame": {"width": 1920, "height": 1080},
    "elements": [
        {
            "type": "frame",
            "id": "slide-frame",
            "name": "",
            "x": 0,
            "y": 0,
            "width": 1920,
            "height": 1080,
            "children": [],
        }
    ],
    "asset_ids": [],
}


def _extract_title_from_content(
    version: SlideVersion | None, draft_scene: dict[str, Any] | None
) -> str | None:
    # 1. From IR if exists
    if version and version.ir and isinstance(version.ir, dict):
        title = version.ir.get("title")
        if title:
            return str(title)

    # 2. From skeleton title element if exists
    if version and version.skeleton and isinstance(version.skeleton, dict):
        for el in version.skeleton.get("elements", []):
            if isinstance(el, dict) and el.get("id") == "title":
                label = el.get("label")
                if isinstance(label, dict) and "text" in label:
                    return str(label["text"]).split("\n")[0]
                text = el.get("text")
                if text:
                    return str(text).split("\n")[0]

    # 3. From draft or version scene
    scene = draft_scene or (version.scene if version else None)
    if scene and isinstance(scene, dict):
        for el in scene.get("elements", []):
            if isinstance(el, dict) and el.get("id") == "title" and not el.get("isDeleted"):
                text = el.get("text")
                if text:
                    return str(text).split("\n")[0]
            if isinstance(el, dict) and el.get("type") == "text" and not el.get("isDeleted"):
                text = el.get("text")
                if text and len(text.strip()) > 0:
                    return str(text).split("\n")[0][:60]

    return None


async def list_slides(db: AsyncSession, deck_id: uuid.UUID) -> list[SlideReadLight]:
    # Verify deck exists
    deck_stmt = select(Deck).where(Deck.id == deck_id)
    deck_res = await db.execute(deck_stmt)
    if not deck_res.scalar_one_or_none():
        raise NotFoundError(
            message=f"Deck '{deck_id}' not found", details={"deck_id": str(deck_id)}
        )

    stmt = (
        select(Slide)
        .where(Slide.deck_id == deck_id, Slide.deleted_at.is_(None))
        .order_by(Slide.position)
        .options(selectinload(Slide.versions))
    )
    result = await db.execute(stmt)
    slides = result.scalars().all()

    items: list[SlideReadLight] = []
    for s in slides:
        curr_v: SlideVersion | None = None
        if s.current_version_id:
            for v in s.versions:
                if v.id == s.current_version_id:
                    curr_v = v
                    break

        title = _extract_title_from_content(curr_v, s.draft_scene)

        # Check dirty
        is_dirty = False
        if curr_v and s.draft_hash:
            is_dirty = curr_v.scene_hash != s.draft_hash
        elif s.draft_scene is not None and (not curr_v or not curr_v.scene):
            is_dirty = True

        items.append(
            SlideReadLight(
                id=s.id,
                position=s.position,
                status=s.status,
                title=title,
                current_version_id=s.current_version_id,
                draft_rev=s.draft_rev,
                is_dirty=is_dirty,
            )
        )
    return items


async def create_blank_slide(
    db: AsyncSession, deck_id: uuid.UUID, position: int | None = None
) -> Slide:
    deck_stmt = select(Deck).where(Deck.id == deck_id)
    deck_res = await db.execute(deck_stmt)
    if not deck_res.scalar_one_or_none():
        raise NotFoundError(
            message=f"Deck '{deck_id}' not found", details={"deck_id": str(deck_id)}
        )

    # Count existing slides
    count_stmt = select(func.count(Slide.id)).where(
        Slide.deck_id == deck_id, Slide.deleted_at.is_(None)
    )
    count_res = await db.execute(count_stmt)
    total_slides = count_res.scalar() or 0

    target_pos = (
        position if (position is not None and 0 <= position <= total_slides) else total_slides
    )

    # Shift subsequent slides if inserting
    if target_pos < total_slides:
        shift_stmt = (
            update(Slide)
            .where(
                Slide.deck_id == deck_id,
                Slide.deleted_at.is_(None),
                Slide.position >= target_pos,
            )
            .values(position=Slide.position + 1)
        )
        await db.execute(shift_stmt)

    new_slide = Slide(
        deck_id=deck_id,
        position=target_pos,
        status="ready",
        draft_rev=0,
    )
    db.add(new_slide)
    await db.flush()

    v1 = SlideVersion(
        slide_id=new_slide.id,
        seq=1,
        origin="manual",
        summary="Initial blank slide",
        skeleton=copy.deepcopy(BLANK_FRAME_SKELETON),
        scene=None,
        warnings=[],
    )
    db.add(v1)
    await db.flush()

    new_slide.current_version_id = v1.id
    await db.commit()
    await db.refresh(new_slide)
    return new_slide


async def get_slide_detail(db: AsyncSession, slide_id: uuid.UUID) -> SlideDetail:
    stmt = (
        select(Slide)
        .where(Slide.id == slide_id, Slide.deleted_at.is_(None))
        .options(selectinload(Slide.versions))
    )
    result = await db.execute(stmt)
    slide = result.scalar_one_or_none()
    if not slide:
        raise NotFoundError(
            message=f"Slide '{slide_id}' not found", details={"slide_id": str(slide_id)}
        )

    curr_version: SlideVersion | None = None
    if slide.current_version_id:
        for v in slide.versions:
            if v.id == slide.current_version_id:
                curr_version = v
                break

    version_detail: VersionDetail | None = None
    if curr_version:
        version_detail = VersionDetail(
            id=curr_version.id,
            slide_id=curr_version.slide_id,
            seq=curr_version.seq,
            parent_version_id=curr_version.parent_version_id,
            origin=curr_version.origin,
            prompt=curr_version.prompt,
            summary=curr_version.summary,
            ir=curr_version.ir,
            skeleton=curr_version.skeleton,
            scene=curr_version.scene,
            scene_hash=curr_version.scene_hash,
            warnings=curr_version.warnings or [],
            created_at=curr_version.created_at,
        )

    draft_read: DraftRead | None = None
    if slide.draft_scene is not None or slide.draft_rev > 0:
        draft_read = DraftRead(
            scene=slide.draft_scene,
            rev=slide.draft_rev,
            hash=slide.draft_hash,
            updated_at=slide.draft_updated_at,
        )

    is_dirty = False
    if curr_version and slide.draft_hash:
        is_dirty = curr_version.scene_hash != slide.draft_hash
    elif slide.draft_scene is not None and (not curr_version or not curr_version.scene):
        is_dirty = True

    return SlideDetail(
        id=slide.id,
        deck_id=slide.deck_id,
        position=slide.position,
        plan_key=slide.plan_key,
        status=slide.status,
        error=slide.error,
        current_version=version_detail,
        draft=draft_read,
        is_dirty=is_dirty,
    )


async def reorder_slide(db: AsyncSession, slide_id: uuid.UUID, new_position: int) -> Slide:
    stmt = select(Slide).where(Slide.id == slide_id, Slide.deleted_at.is_(None))
    res = await db.execute(stmt)
    slide = res.scalar_one_or_none()
    if not slide:
        raise NotFoundError(
            message=f"Slide '{slide_id}' not found", details={"slide_id": str(slide_id)}
        )

    # Fetch all active slides of the deck ordered by position
    all_stmt = (
        select(Slide)
        .where(Slide.deck_id == slide.deck_id, Slide.deleted_at.is_(None))
        .order_by(Slide.position)
    )
    all_res = await db.execute(all_stmt)
    slides = list(all_res.scalars().all())

    old_idx = -1
    for idx, s in enumerate(slides):
        if s.id == slide_id:
            old_idx = idx
            break

    if old_idx == -1:
        raise NotFoundError(message="Slide not found in deck")

    # Bound check
    new_position = max(0, min(new_position, len(slides) - 1))
    if old_idx == new_position:
        return slide

    # Reorder list
    moving_slide = slides.pop(old_idx)
    slides.insert(new_position, moving_slide)

    # Re-assign contiguous positions
    for idx, s in enumerate(slides):
        s.position = idx

    await db.commit()
    await db.refresh(slide)
    return slide


async def delete_slide(db: AsyncSession, slide_id: uuid.UUID) -> None:
    stmt = select(Slide).where(Slide.id == slide_id, Slide.deleted_at.is_(None))
    res = await db.execute(stmt)
    slide = res.scalar_one_or_none()
    if not slide:
        raise NotFoundError(
            message=f"Slide '{slide_id}' not found", details={"slide_id": str(slide_id)}
        )

    slide.deleted_at = datetime.now(UTC)
    await db.flush()

    # Compact remaining slides
    all_stmt = (
        select(Slide)
        .where(Slide.deck_id == slide.deck_id, Slide.deleted_at.is_(None))
        .order_by(Slide.position)
    )
    all_res = await db.execute(all_stmt)
    remaining_slides = all_res.scalars().all()

    for idx, s in enumerate(remaining_slides):
        s.position = idx

    await db.commit()


async def duplicate_slide(db: AsyncSession, slide_id: uuid.UUID) -> Slide:
    stmt = (
        select(Slide)
        .where(Slide.id == slide_id, Slide.deleted_at.is_(None))
        .options(selectinload(Slide.versions))
    )
    res = await db.execute(stmt)
    source_slide = res.scalar_one_or_none()
    if not source_slide:
        raise NotFoundError(
            message=f"Slide '{slide_id}' not found", details={"slide_id": str(slide_id)}
        )

    curr_version: SlideVersion | None = None
    if source_slide.current_version_id:
        for v in source_slide.versions:
            if v.id == source_slide.current_version_id:
                curr_version = v
                break

    target_pos = source_slide.position + 1

    # Shift subsequent slides
    shift_stmt = (
        update(Slide)
        .where(
            Slide.deck_id == source_slide.deck_id,
            Slide.deleted_at.is_(None),
            Slide.position >= target_pos,
        )
        .values(position=Slide.position + 1)
    )
    await db.execute(shift_stmt)

    new_slide = Slide(
        deck_id=source_slide.deck_id,
        position=target_pos,
        status="ready",
        draft_scene=copy.deepcopy(source_slide.draft_scene) if source_slide.draft_scene else None,
        draft_hash=source_slide.draft_hash,
        draft_rev=0,
    )
    db.add(new_slide)
    await db.flush()

    # Create v1 copied from current draft/version
    skeleton_to_copy = (
        copy.deepcopy(curr_version.skeleton) if (curr_version and curr_version.skeleton) else None
    )
    scene_to_copy = copy.deepcopy(
        source_slide.draft_scene or (curr_version.scene if curr_version else None)
    )
    ir_to_copy = copy.deepcopy(curr_version.ir) if (curr_version and curr_version.ir) else None

    # Fallback to blank frame if nothing
    if not skeleton_to_copy and not scene_to_copy:
        skeleton_to_copy = copy.deepcopy(BLANK_FRAME_SKELETON)

    v1 = SlideVersion(
        slide_id=new_slide.id,
        seq=1,
        origin="manual",
        summary="Duplicated slide",
        ir=ir_to_copy,
        skeleton=skeleton_to_copy,
        scene=scene_to_copy,
        scene_hash=source_slide.draft_hash,
        warnings=[],
    )
    db.add(v1)
    await db.flush()

    new_slide.current_version_id = v1.id
    await db.commit()
    await db.refresh(new_slide)
    return new_slide
