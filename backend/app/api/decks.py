import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.deck import DeckCreate, DeckRead, DeckUpdate
from app.services.decks import create_deck, delete_deck, get_deck_read, list_decks, update_deck

router = APIRouter(prefix="/decks", tags=["decks"])


@router.post("", response_model=DeckRead, status_code=status.HTTP_201_CREATED)
async def create_new_deck(data: DeckCreate, db: AsyncSession = Depends(get_db)) -> DeckRead:
    deck = await create_deck(db, data)
    return await get_deck_read(db, deck.id)


@router.get("", response_model=list[DeckRead])
async def get_all_decks(db: AsyncSession = Depends(get_db)) -> list[DeckRead]:
    return await list_decks(db)


@router.get("/{deck_id}", response_model=DeckRead)
async def get_single_deck(deck_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> DeckRead:
    return await get_deck_read(db, deck_id)


@router.patch("/{deck_id}", response_model=DeckRead)
async def update_single_deck(
    deck_id: uuid.UUID, data: DeckUpdate, db: AsyncSession = Depends(get_db)
) -> DeckRead:
    return await update_deck(db, deck_id, data)


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_single_deck(deck_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    await delete_deck(db, deck_id)
