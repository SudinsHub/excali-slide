import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.errors import NotFoundError
from app.models.deck import Deck
from app.models.slide import Slide
from app.schemas.deck import DeckCreate, DeckRead, DeckSettings, DeckUpdate


async def create_deck(db: AsyncSession, data: DeckCreate) -> Deck:
    deck = Deck(
        title=data.title,
        status="draft",
        settings=data.settings.model_dump(),
    )
    db.add(deck)
    await db.commit()
    await db.refresh(deck)
    return deck


async def list_decks(db: AsyncSession) -> list[DeckRead]:
    # Query decks with count of non-deleted slides
    stmt = (
        select(
            Deck,
            func.count(Slide.id).filter(Slide.deleted_at.is_(None)).label("slide_count"),
        )
        .outerjoin(Slide, Slide.deck_id == Deck.id)
        .group_by(Deck.id)
        .order_by(Deck.updated_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    deck_reads: list[DeckRead] = []
    for deck, count in rows:
        deck_reads.append(
            DeckRead(
                id=deck.id,
                title=deck.title,
                status=deck.status,
                settings=DeckSettings(**deck.settings),
                current_plan_id=deck.current_plan_id,
                slide_count=count,
                created_at=deck.created_at,
                updated_at=deck.updated_at,
            )
        )
    return deck_reads


async def get_deck(db: AsyncSession, deck_id: uuid.UUID) -> Deck:
    stmt = (
        select(Deck)
        .where(Deck.id == deck_id)
        .options(selectinload(Deck.slides.and_(Slide.deleted_at.is_(None))))
    )
    result = await db.execute(stmt)
    deck = result.scalar_one_or_none()
    if not deck:
        raise NotFoundError(
            message=f"Deck '{deck_id}' not found", details={"deck_id": str(deck_id)}
        )
    return deck


async def get_deck_read(db: AsyncSession, deck_id: uuid.UUID) -> DeckRead:
    stmt = (
        select(
            Deck,
            func.count(Slide.id).filter(Slide.deleted_at.is_(None)).label("slide_count"),
        )
        .outerjoin(Slide, Slide.deck_id == Deck.id)
        .where(Deck.id == deck_id)
        .group_by(Deck.id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise NotFoundError(
            message=f"Deck '{deck_id}' not found", details={"deck_id": str(deck_id)}
        )
    deck, count = row
    return DeckRead(
        id=deck.id,
        title=deck.title,
        status=deck.status,
        settings=DeckSettings(**deck.settings),
        current_plan_id=deck.current_plan_id,
        slide_count=count,
        created_at=deck.created_at,
        updated_at=deck.updated_at,
    )


async def update_deck(db: AsyncSession, deck_id: uuid.UUID, data: DeckUpdate) -> DeckRead:
    deck = await get_deck(db, deck_id)
    if data.title is not None:
        deck.title = data.title
    if data.settings is not None:
        deck.settings = data.settings.model_dump()
    await db.commit()
    await db.refresh(deck)
    return await get_deck_read(db, deck_id)


async def delete_deck(db: AsyncSession, deck_id: uuid.UUID) -> None:
    deck = await get_deck(db, deck_id)
    await db.delete(deck)
    await db.commit()
