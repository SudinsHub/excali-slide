import io
import uuid

from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import BadRequestError, NotFoundError
from app.models.asset import Asset
from app.services.storage import Storage

ALLOWED_MIMES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "image/svg+xml",
}


async def save_asset(
    db: AsyncSession,
    storage: Storage,
    deck_id: uuid.UUID,
    file_id: str,
    data: bytes,
    mime: str,
) -> Asset:
    if mime not in ALLOWED_MIMES:
        raise BadRequestError(
            code="invalid_mime",
            message=f"MIME type '{mime}' is not supported. Supported: {', '.join(sorted(ALLOWED_MIMES))}",
            details={"mime": mime},
        )

    # Idempotent: check if asset already exists
    stmt = select(Asset).where(Asset.id == file_id)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing:
        return existing

    width: int | None = None
    height: int | None = None

    if mime != "image/svg+xml":
        try:
            with Image.open(io.BytesIO(data)) as img:
                width, height = img.size
        except Exception:
            # If Pillow fails to parse image dimensions, proceed without dimensions
            pass

    storage_key = f"assets/{deck_id}/{file_id}"
    storage.put(storage_key, data)

    asset = Asset(
        id=file_id,
        deck_id=deck_id,
        storage_key=storage_key,
        mime=mime,
        width=width,
        height=height,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


async def get_asset(
    db: AsyncSession,
    storage: Storage,
    asset_id: str,
) -> tuple[Asset, bytes]:
    stmt = select(Asset).where(Asset.id == asset_id)
    res = await db.execute(stmt)
    asset = res.scalar_one_or_none()
    if not asset:
        raise NotFoundError(message=f"Asset '{asset_id}' not found", details={"asset_id": asset_id})

    data = storage.get(asset.storage_key)
    return asset, data
