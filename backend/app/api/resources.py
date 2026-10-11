import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.errors import NotFoundError, PayloadTooLargeError
from app.ingest.sniff import detect_resource_kind
from app.jobs.queue import enqueue
from app.models.deck import Deck
from app.models.resource import Resource, ResourceImage
from app.schemas.resource import ResourceImageRead, ResourceRead
from app.services.storage import storage

router = APIRouter(tags=["resources"])


@router.post(
    "/decks/{deck_id}/resources",
    response_model=list[ResourceRead],
    status_code=status.HTTP_201_CREATED,
)
async def upload_deck_resources(
    deck_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> list[ResourceRead]:
    deck = await db.get(Deck, deck_id)
    if not deck:
        raise NotFoundError("Deck not found")

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    created_resources: list[Resource] = []

    for file in files:
        contents = await file.read()
        if len(contents) > max_bytes:
            raise PayloadTooLargeError(
                message=f"File '{file.filename}' exceeds {settings.MAX_UPLOAD_MB}MB limit",
                details={
                    "filename": file.filename,
                    "size": len(contents),
                    "limit_mb": settings.MAX_UPLOAD_MB,
                },
            )

        filename = file.filename or "uploaded_file"
        header = contents[:32]
        kind, mime = detect_resource_kind(filename, header)

        # Store raw file
        storage_key = f"resources/{deck_id}/{uuid.uuid4()}_{filename}"
        storage.put(storage_key, contents)

        resource = Resource(
            deck_id=deck_id,
            kind=kind,
            filename=filename,
            mime=mime,
            size=len(contents),
            storage_key=storage_key,
            status="uploaded",
        )
        db.add(resource)
        await db.flush()

        # Enqueue ingestion job
        await enqueue(
            db,
            kind="ingest_resource",
            deck_id=deck_id,
            payload={"resource_id": str(resource.id)},
            priority=10,
        )
        created_resources.append(resource)

    await db.commit()

    # Format response
    result: list[ResourceRead] = []
    for r in created_resources:
        result.append(
            ResourceRead(
                id=r.id,
                deck_id=r.deck_id,
                kind=r.kind,
                filename=r.filename,
                mime=r.mime,
                size=r.size,
                status=r.status,
                text=r.text,
                meta=r.meta,
                error=r.error,
                images=[],
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )
    return result


@router.get("/decks/{deck_id}/resources", response_model=list[ResourceRead])
async def list_deck_resources(
    deck_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ResourceRead]:
    deck = await db.get(Deck, deck_id)
    if not deck:
        raise NotFoundError("Deck not found")

    stmt = select(Resource).where(Resource.deck_id == deck_id).order_by(Resource.created_at.asc())
    resources = list((await db.execute(stmt)).scalars().all())

    # Get images for all resources
    res_ids = [r.id for r in resources]
    images_by_res: dict[uuid.UUID, list[ResourceImageRead]] = {rid: [] for rid in res_ids}
    if res_ids:
        img_stmt = select(ResourceImage).where(ResourceImage.resource_id.in_(res_ids))
        all_imgs = (await db.execute(img_stmt)).scalars().all()
        for img in all_imgs:
            images_by_res[img.resource_id].append(
                ResourceImageRead(
                    id=img.id,
                    asset_id=img.asset_id,
                    caption=img.caption,
                    locator=img.locator,
                )
            )

    return [
        ResourceRead(
            id=r.id,
            deck_id=r.deck_id,
            kind=r.kind,
            filename=r.filename,
            mime=r.mime,
            size=r.size,
            status=r.status,
            text=r.text,
            meta=r.meta,
            error=r.error,
            images=images_by_res.get(r.id, []),
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in resources
    ]


@router.delete("/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    resource = await db.get(Resource, resource_id)
    if not resource:
        raise NotFoundError("Resource not found")

    if resource.storage_key and storage.exists(resource.storage_key):
        storage.delete(resource.storage_key)

    await db.delete(resource)
    await db.commit()
