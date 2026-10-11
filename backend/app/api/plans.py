import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.errors import BadRequestError, NotFoundError
from app.ir.schemas import Plan
from app.jobs.queue import enqueue
from app.models.deck import Deck
from app.models.plan import Plan as PlanModel
from app.models.resource import Resource
from app.models.slide import Slide
from app.schemas.plan import PlanRead, PlanRegenerateRequest
from app.services.drafts import flush_drafts

router = APIRouter(prefix="/decks/{deck_id}/plan", tags=["plan"])


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_deck_plan(
    deck_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    deck = await db.get(Deck, deck_id)
    if not deck:
        raise NotFoundError("Deck not found")

    if deck.status not in ("draft", "plan_review", "failed"):
        raise BadRequestError(
            code="invalid_state",
            message=f"Cannot generate plan while deck is in status '{deck.status}'",
            details={"current_status": deck.status},
        )

    # Check if any resources are still parsing
    res_stmt = select(Resource).where(Resource.deck_id == deck_id, Resource.status == "parsing")
    parsing_res = (await db.execute(res_stmt)).scalars().all()
    if parsing_res:
        raise BadRequestError(
            code="resources_parsing",
            message="Some resources are still being parsed. Please wait for parsing to finish.",
            details={"parsing_count": len(parsing_res)},
        )

    deck.status = "planning"
    deck.updated_at = datetime.now(UTC)

    job = await enqueue(
        db,
        kind="generate_plan",
        deck_id=deck_id,
        priority=8,
    )
    await db.commit()

    return {"job_id": str(job.id), "status": "planning"}


@router.get("", response_model=PlanRead)
async def get_current_plan(
    deck_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PlanRead:
    deck = await db.get(Deck, deck_id)
    if not deck:
        raise NotFoundError("Deck not found")

    if not deck.current_plan_id:
        raise NotFoundError("No plan currently exists for this deck")

    plan = await db.get(PlanModel, deck.current_plan_id)
    if not plan:
        raise NotFoundError("Plan record not found")

    return PlanRead.model_validate(plan)


@router.put("", response_model=PlanRead)
async def update_deck_plan(
    deck_id: uuid.UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> PlanRead:
    deck = await db.get(Deck, deck_id)
    if not deck:
        raise NotFoundError("Deck not found")

    # Validate payload strictly with Plan schema
    try:
        validated_plan = Plan.model_validate(payload)
    except Exception as exc:
        raise BadRequestError(
            code="invalid_plan_schema",
            message=f"Plan payload failed schema validation: {exc}",
            details={"error": str(exc)},
        ) from exc

    # Enforce stable keys s1..sN if missing or duplicate
    for i, slide in enumerate(validated_plan.slides, start=1):
        if not slide.key:
            slide.key = f"s{i}"

    # Determine next version
    ver_stmt = select(func.max(PlanModel.version)).where(PlanModel.deck_id == deck_id)
    max_ver = (await db.execute(ver_stmt)).scalar() or 0
    next_ver = max_ver + 1

    new_plan = PlanModel(
        deck_id=deck_id,
        version=next_ver,
        status="draft",
        content=validated_plan.model_dump(),
        created_by="user",
    )
    db.add(new_plan)
    await db.flush()

    deck.current_plan_id = new_plan.id
    deck.status = "plan_review"
    deck.updated_at = datetime.now(UTC)
    await db.commit()

    return PlanRead.model_validate(new_plan)


@router.post("/regenerate", status_code=status.HTTP_202_ACCEPTED)
async def regenerate_deck_plan(
    deck_id: uuid.UUID,
    req: PlanRegenerateRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    deck = await db.get(Deck, deck_id)
    if not deck:
        raise NotFoundError("Deck not found")

    feedback = req.feedback if req else None
    prev_id = deck.current_plan_id

    deck.status = "planning"
    deck.updated_at = datetime.now(UTC)

    job = await enqueue(
        db,
        kind="generate_plan",
        deck_id=deck_id,
        payload={"feedback": feedback, "previous_plan_id": str(prev_id) if prev_id else None},
        priority=8,
    )
    await db.commit()

    return {"job_id": str(job.id), "status": "planning"}


@router.post("/approve", status_code=status.HTTP_200_OK)
async def approve_deck_plan(
    deck_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    deck = await db.get(Deck, deck_id)
    if not deck:
        raise NotFoundError("Deck not found")

    if not deck.current_plan_id:
        raise BadRequestError("No plan to approve")

    plan = await db.get(PlanModel, deck.current_plan_id)
    if not plan:
        raise NotFoundError("Plan not found")

    plan.status = "approved"
    plan.updated_at = datetime.now(UTC)

    # Flush dirty drafts first to preserve user work
    await flush_drafts(db, deck_id)

    # Soft-delete earlier slides if re-approving a plan
    old_slides_stmt = select(Slide).where(Slide.deck_id == deck_id, Slide.deleted_at.is_(None))
    old_slides = list((await db.execute(old_slides_stmt)).scalars().all())
    now = datetime.now(UTC)
    for old_slide in old_slides:
        old_slide.deleted_at = now
        old_slide.updated_at = now

    # Create new slides from plan outline
    plan_data = Plan.model_validate(plan.content)
    created_slides: list[Slide] = []
    for idx, ps in enumerate(plan_data.slides):
        slide = Slide(
            deck_id=deck_id,
            position=idx,
            plan_key=ps.key,
            status="queued",
            error=None,
        )
        db.add(slide)
        created_slides.append(slide)

    await db.flush()

    # Enqueue generate_slide jobs for each new slide
    for slide in created_slides:
        await enqueue(
            db,
            kind="generate_slide",
            deck_id=deck_id,
            slide_id=slide.id,
            priority=5,
        )

    deck.status = "generating"
    deck.updated_at = now
    await db.commit()

    return {"status": "generating", "slides_count": len(created_slides)}
