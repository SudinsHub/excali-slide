import uuid

from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.errors import BadRequestError
from app.schemas.asset import AssetRead
from app.services.assets import get_asset, save_asset
from app.services.storage import storage

deck_assets_router = APIRouter(prefix="/decks/{deck_id}/assets", tags=["assets"])
assets_router = APIRouter(prefix="/assets", tags=["assets"])


@deck_assets_router.put("/{file_id}", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    deck_id: uuid.UUID,
    file_id: str,
    request: Request,
    content_type: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> AssetRead:
    body = await request.body()
    if not body:
        raise BadRequestError(code="empty_file", message="Uploaded asset payload is empty")

    mime = (content_type or "image/png").split(";")[0].strip()

    asset = await save_asset(
        db=db,
        storage=storage,
        deck_id=deck_id,
        file_id=file_id,
        data=body,
        mime=mime,
    )
    return AssetRead(
        id=asset.id,
        deck_id=asset.deck_id,
        storage_key=asset.storage_key,
        mime=asset.mime,
        width=asset.width,
        height=asset.height,
        created_at=asset.created_at,
    )


@assets_router.get("/{asset_id}")
async def fetch_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    asset, data = await get_asset(db=db, storage=storage, asset_id=asset_id)
    return Response(
        content=data,
        media_type=asset.mime,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
        },
    )
