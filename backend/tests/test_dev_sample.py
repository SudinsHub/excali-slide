import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dev_sample_deck(client: AsyncClient):
    res = await client.post("/api/dev/decks/sample")
    assert res.status_code == 201
    deck = res.json()
    assert deck["title"] == "Excalidraw Slide Studio Demo Deck"
    assert deck["slide_count"] == 4
    deck_id = deck["id"]

    # Check the 4 slides
    slides_res = await client.get(f"/api/decks/{deck_id}/slides")
    assert slides_res.status_code == 200
    slides = slides_res.json()
    assert len(slides) == 4

    # Verify each slide has its skeleton
    for s in slides:
        s_detail = (await client.get(f"/api/slides/{s['id']}")).json()
        assert s_detail["current_version"] is not None
        skeleton = s_detail["current_version"]["skeleton"]
        assert skeleton is not None
        assert skeleton["version"] == 1
        assert skeleton["frame"]["width"] == 1920
        assert skeleton["frame"]["height"] == 1080
        assert skeleton["elements"][0]["type"] == "frame"
