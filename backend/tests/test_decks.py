import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_deck_crud(client: AsyncClient):
    # 1. Create deck
    create_res = await client.post(
        "/api/decks",
        json={
            "title": "My Test Deck",
            "settings": {
                "tone": "casual",
                "diagram_intensity": "high",
                "density": "dense",
                "audience": "Engineers",
            },
        },
    )
    assert create_res.status_code == 201
    deck_data = create_res.json()
    assert deck_data["title"] == "My Test Deck"
    assert deck_data["settings"]["tone"] == "casual"
    assert deck_data["slide_count"] == 0
    deck_id = deck_data["id"]

    # 2. Get deck
    get_res = await client.get(f"/api/decks/{deck_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == deck_id

    # 3. List decks
    list_res = await client.get("/api/decks")
    assert list_res.status_code == 200
    decks = list_res.json()
    assert len(decks) == 1
    assert decks[0]["id"] == deck_id

    # 4. Patch deck
    patch_res = await client.patch(
        f"/api/decks/{deck_id}",
        json={"title": "Updated Deck Title"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Updated Deck Title"

    # 5. Delete deck
    del_res = await client.delete(f"/api/decks/{deck_id}")
    assert del_res.status_code == 204

    # 6. Verify 404
    get_after_del = await client.get(f"/api/decks/{deck_id}")
    assert get_after_del.status_code == 404
    assert get_after_del.json()["error"]["code"] == "not_found"
