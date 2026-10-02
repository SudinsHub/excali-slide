import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_slides_lifecycle_and_reorder(client: AsyncClient):
    # Create deck
    deck_res = await client.post("/api/decks", json={"title": "Slides Test Deck"})
    deck_id = deck_res.json()["id"]

    # 1. Create blank slides
    s1_res = await client.post(f"/api/decks/{deck_id}/slides")
    assert s1_res.status_code == 201
    s1 = s1_res.json()
    assert s1["position"] == 0
    assert s1["current_version"] is not None
    assert s1["current_version"]["seq"] == 1
    assert s1["current_version"]["origin"] == "manual"
    assert s1["current_version"]["skeleton"]["elements"][0]["type"] == "frame"

    s2_res = await client.post(f"/api/decks/{deck_id}/slides")
    s2 = s2_res.json()
    assert s2["position"] == 1

    s3_res = await client.post(f"/api/decks/{deck_id}/slides")
    s3 = s3_res.json()
    assert s3["position"] == 2

    # 2. List slides (light)
    list_res = await client.get(f"/api/decks/{deck_id}/slides")
    assert list_res.status_code == 200
    slides = list_res.json()
    assert len(slides) == 3
    assert [s["position"] for s in slides] == [0, 1, 2]
    # Check that scene body is not present in light list
    assert "scene" not in slides[0]

    # 3. Reorder s3 to position 0
    reorder_res = await client.patch(
        f"/api/slides/{s3['id']}",
        json={"position": 0},
    )
    assert reorder_res.status_code == 200

    list_res2 = await client.get(f"/api/decks/{deck_id}/slides")
    slides2 = list_res2.json()
    # s3 should now be at position 0, s1 at 1, s2 at 2
    assert slides2[0]["id"] == s3["id"]
    assert slides2[0]["position"] == 0
    assert slides2[1]["id"] == s1["id"]
    assert slides2[1]["position"] == 1
    assert slides2[2]["id"] == s2["id"]
    assert slides2[2]["position"] == 2

    # 4. Soft delete middle slide (s1)
    del_res = await client.delete(f"/api/slides/{s1['id']}")
    assert del_res.status_code == 204

    # Check compaction
    list_res3 = await client.get(f"/api/decks/{deck_id}/slides")
    slides3 = list_res3.json()
    assert len(slides3) == 2
    assert slides3[0]["id"] == s3["id"]
    assert slides3[0]["position"] == 0
    assert slides3[1]["id"] == s2["id"]
    assert slides3[1]["position"] == 1

    # 5. Duplicate s3
    dup_res = await client.post(f"/api/slides/{s3['id']}/duplicate")
    assert dup_res.status_code == 201
    dup_slide = dup_res.json()
    assert dup_slide["position"] == 1

    # Positions should now be 0, 1, 2
    list_res4 = await client.get(f"/api/decks/{deck_id}/slides")
    slides4 = list_res4.json()
    assert len(slides4) == 3
    assert [s["position"] for s in slides4] == [0, 1, 2]
