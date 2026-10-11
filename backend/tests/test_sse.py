import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.api.events import deck_event_generator
from app.models.deck import Deck
from app.models.slide import Slide


@pytest.mark.asyncio
async def test_sse_snapshot_and_delta(test_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    # 1. Create a deck and a slide in DB
    deck_id = uuid.uuid4()
    slide_id = uuid.uuid4()
    async with session_factory() as session:
        deck = Deck(id=deck_id, title="SSE Test Deck", status="draft", settings={})
        slide = Slide(id=slide_id, deck_id=deck_id, position=0, status="ready", plan_key="s1")
        session.add(deck)
        session.add(slide)
        await session.commit()

    # 2. Mock request
    mock_request = MagicMock()
    disconnected = False

    async def check_disconnected():
        return disconnected

    mock_request.is_disconnected = check_disconnected

    # 3. Instantiate generator directly
    gen = deck_event_generator(deck_id, mock_request, session_factory)

    # 4. First event: snapshot
    first_chunk = await anext(gen)
    assert "event: snapshot" in first_chunk

    # 5. Mutate deck status in DB
    async with session_factory() as session:
        db_deck = await session.get(Deck, deck_id)
        db_deck.status = "planning"
        db_deck.updated_at = datetime.now(UTC)
        await session.commit()

    # 6. Next event: delta event for deck
    second_chunk = await asyncio.wait_for(anext(gen), timeout=5.0)
    assert "event: deck" in second_chunk

    # Cleanup generator cleanly
    disconnected = True
    await gen.aclose()
