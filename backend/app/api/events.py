import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session_factory, get_db
from app.errors import NotFoundError
from app.models.deck import Deck
from app.models.job import Job
from app.models.resource import Resource
from app.models.slide import Slide

router = APIRouter(tags=["events"])
logger = logging.getLogger("api.events")


def _format_sse(event: str, data: Any) -> str:
    payload = json.dumps(data) if not isinstance(data, str) else data
    return f"event: {event}\ndata: {payload}\n\n"


async def deck_event_generator(
    deck_id: uuid.UUID,
    request: Request,
    session_factory: Any = None,
) -> AsyncGenerator[str, None]:
    last_seen = datetime.now(UTC)
    last_ping = asyncio.get_event_loop().time()
    sf = session_factory or async_session_factory

    # 1. On connect: Send snapshot event
    async with sf() as session:
        deck = await session.get(Deck, deck_id)
        if not deck:
            yield _format_sse("error", {"message": "Deck not found"})
            return

        slides_stmt = (
            select(Slide)
            .where(Slide.deck_id == deck_id, Slide.deleted_at.is_(None))
            .order_by(Slide.position.asc())
        )
        slides = list((await session.execute(slides_stmt)).scalars().all())

        jobs_stmt = (
            select(Job)
            .where(
                Job.deck_id == deck_id,
                Job.status.in_(["queued", "running"]),
            )
            .order_by(Job.created_at.desc())
        )
        jobs = list((await session.execute(jobs_stmt)).scalars().all())

        res_stmt = (
            select(Resource).where(Resource.deck_id == deck_id).order_by(Resource.created_at.asc())
        )
        resources = list((await session.execute(res_stmt)).scalars().all())

        snapshot_payload = {
            "deck": {
                "id": str(deck.id),
                "status": deck.status,
                "current_plan_id": str(deck.current_plan_id) if deck.current_plan_id else None,
                "title": deck.title,
            },
            "slides": [
                {
                    "id": str(s.id),
                    "position": s.position,
                    "plan_key": s.plan_key,
                    "status": s.status,
                    "error": s.error,
                    "current_version_id": str(s.current_version_id)
                    if s.current_version_id
                    else None,
                }
                for s in slides
            ],
            "jobs": [
                {
                    "id": str(j.id),
                    "kind": j.kind,
                    "status": j.status,
                    "progress": j.progress,
                    "error": j.error,
                }
                for j in jobs
            ],
            "resources": [
                {
                    "id": str(r.id),
                    "kind": r.kind,
                    "filename": r.filename,
                    "status": r.status,
                    "error": r.error,
                }
                for r in resources
            ],
        }
        yield _format_sse("snapshot", snapshot_payload)

    # 2. Polling loop every ~700 ms
    while True:
        if await request.is_disconnected():
            logger.debug(f"SSE client disconnected for deck {deck_id}")
            break

        await asyncio.sleep(0.7)
        now = datetime.now(UTC)
        current_time = asyncio.get_event_loop().time()

        # Send ping comment every 15 seconds
        if current_time - last_ping >= 15.0:
            yield ": ping\n\n"
            last_ping = current_time

        try:
            async with sf() as session:
                # Check deck changes
                deck = await session.get(Deck, deck_id)
                if deck and deck.updated_at > last_seen:
                    yield _format_sse(
                        "deck",
                        {
                            "id": str(deck.id),
                            "status": deck.status,
                            "current_plan_id": str(deck.current_plan_id)
                            if deck.current_plan_id
                            else None,
                        },
                    )

                # Check slide changes
                changed_slides_stmt = select(Slide).where(
                    Slide.deck_id == deck_id,
                    Slide.updated_at > last_seen,
                )
                changed_slides = list((await session.execute(changed_slides_stmt)).scalars().all())
                for s in changed_slides:
                    yield _format_sse(
                        "slide",
                        {
                            "id": str(s.id),
                            "position": s.position,
                            "plan_key": s.plan_key,
                            "status": s.status,
                            "error": s.error,
                            "current_version_id": str(s.current_version_id)
                            if s.current_version_id
                            else None,
                            "deleted": s.deleted_at is not None,
                        },
                    )

                # Check job changes
                changed_jobs_stmt = select(Job).where(
                    Job.deck_id == deck_id,
                    Job.updated_at > last_seen,
                )
                changed_jobs = list((await session.execute(changed_jobs_stmt)).scalars().all())
                for j in changed_jobs:
                    yield _format_sse(
                        "job",
                        {
                            "id": str(j.id),
                            "slide_id": str(j.slide_id) if j.slide_id else None,
                            "kind": j.kind,
                            "status": j.status,
                            "progress": j.progress,
                            "error": j.error,
                        },
                    )

                # Check resource changes
                changed_res_stmt = select(Resource).where(
                    Resource.deck_id == deck_id,
                    Resource.updated_at > last_seen,
                )
                changed_res = list((await session.execute(changed_res_stmt)).scalars().all())
                for r in changed_res:
                    yield _format_sse(
                        "resource",
                        {
                            "id": str(r.id),
                            "kind": r.kind,
                            "filename": r.filename,
                            "status": r.status,
                            "error": r.error,
                        },
                    )

                last_seen = now

        except Exception as e:
            logger.warning(f"Error in SSE tick for deck {deck_id}: {e}")
            await asyncio.sleep(1.0)


@router.get("/decks/{deck_id}/events")
async def stream_deck_events(
    deck_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    deck = await db.get(Deck, deck_id)
    if not deck:
        raise NotFoundError("Deck not found")

    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(bind=db.bind, expire_on_commit=False)

    return StreamingResponse(
        deck_event_generator(deck_id, request, session_factory),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
