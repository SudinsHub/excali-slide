import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.errors import BadRequestError, ConflictError, NotFoundError, PayloadTooLargeError
from app.models.slide import Slide
from app.models.slide_version import SlideVersion
from app.schemas.draft import DraftUpdate

MAX_SCENE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def compute_scene_hash(scene: dict[str, Any] | None) -> str:
    if not scene:
        return ""
    canonical = json.dumps(scene, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()


def validate_scene_shape(scene: dict[str, Any]) -> None:
    if not isinstance(scene, dict):
        raise BadRequestError(code="invalid_scene", message="Scene must be a JSON object")
    raw_str = json.dumps(scene)
    if len(raw_str.encode("utf-8")) > MAX_SCENE_SIZE_BYTES:
        raise PayloadTooLargeError(message="Scene payload exceeds 5 MB limit")

    elements = scene.get("elements")
    if not isinstance(elements, list):
        raise BadRequestError(code="invalid_scene", message="Scene must contain an 'elements' list")
    for idx, elem in enumerate(elements):
        if not isinstance(elem, dict) or "id" not in elem or "type" not in elem:
            raise BadRequestError(
                code="invalid_scene",
                message=f"Element at index {idx} must be an object with 'id' and 'type'",
                details={"element_index": idx},
            )


async def save_draft(db: AsyncSession, slide_id: uuid.UUID, update: DraftUpdate) -> Slide:
    validate_scene_shape(update.scene)

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

    # Optimistic concurrency check
    if update.if_rev != slide.draft_rev:
        raise ConflictError(
            code="draft_conflict",
            message="Draft revision conflict. Reload the slide to see latest version.",
            details={"current_rev": slide.draft_rev, "expected_rev": update.if_rev},
        )

    new_hash = compute_scene_hash(update.scene)
    slide.draft_scene = update.scene
    slide.draft_hash = new_hash
    slide.draft_rev += 1
    slide.draft_updated_at = datetime.now(UTC)

    # If normalizing_version_id matches current version and version.scene is null, fill it once
    if update.normalizing_version_id and slide.current_version_id == update.normalizing_version_id:
        v_stmt = select(SlideVersion).where(SlideVersion.id == update.normalizing_version_id)
        v_res = await db.execute(v_stmt)
        version = v_res.scalar_one_or_none()
        if version and version.scene is None:
            version.scene = update.scene
            version.scene_hash = new_hash

    await db.commit()
    await db.refresh(slide)
    return slide


async def commit_draft(
    db: AsyncSession,
    slide: Slide,
    origin: str = "user_checkpoint",
    summary: str | None = None,
) -> SlideVersion:
    # Check if current version exists
    current_version: SlideVersion | None = None
    if slide.current_version_id:
        v_stmt = select(SlideVersion).where(SlideVersion.id == slide.current_version_id)
        v_res = await db.execute(v_stmt)
        current_version = v_res.scalar_one_or_none()

    # Check dirty state
    is_dirty = True
    if current_version and current_version.scene_hash and slide.draft_hash:
        is_dirty = current_version.scene_hash != slide.draft_hash

    if not is_dirty and origin == "user_checkpoint":
        raise ConflictError(
            code="nothing_to_commit",
            message="Slide has no changes to checkpoint",
            details={"slide_id": str(slide.id)},
        )

    # Next sequence
    seq_stmt = select(func.coalesce(func.max(SlideVersion.seq), 0)).where(
        SlideVersion.slide_id == slide.id
    )
    seq_res = await db.execute(seq_stmt)
    next_seq = (seq_res.scalar() or 0) + 1

    scene_to_commit = slide.draft_scene or (current_version.scene if current_version else None)
    hash_to_commit = slide.draft_hash or (current_version.scene_hash if current_version else None)

    new_version = SlideVersion(
        slide_id=slide.id,
        seq=next_seq,
        parent_version_id=slide.current_version_id,
        origin=origin,
        summary=summary,
        ir=None,  # Canvas was edited directly, IR no longer describes it
        skeleton=None,
        scene=scene_to_commit,
        scene_hash=hash_to_commit,
        warnings=[],
    )
    db.add(new_version)
    await db.flush()

    slide.current_version_id = new_version.id
    await db.commit()
    await db.refresh(new_version)
    return new_version


async def flush_drafts(db: AsyncSession, deck_id: uuid.UUID) -> list[SlideVersion]:
    stmt = (
        select(Slide)
        .where(Slide.deck_id == deck_id, Slide.deleted_at.is_(None))
        .options(selectinload(Slide.versions))
    )
    result = await db.execute(stmt)
    slides = result.scalars().all()

    committed_versions: list[SlideVersion] = []
    for slide in slides:
        if not slide.current_version_id or not slide.draft_scene:
            continue
        v_stmt = select(SlideVersion).where(SlideVersion.id == slide.current_version_id)
        v_res = await db.execute(v_stmt)
        curr_v = v_res.scalar_one_or_none()
        if curr_v and curr_v.scene_hash != slide.draft_hash:
            v = await commit_draft(
                db,
                slide,
                origin="user_save",
                summary="Auto-saved before operation",
            )
            committed_versions.append(v)
    return committed_versions
