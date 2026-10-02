import pytest
from httpx import AsyncClient

from app.services.drafts import flush_drafts


@pytest.mark.asyncio
async def test_draft_and_versions(client: AsyncClient, db_session):
    # Setup deck & slide
    deck_res = await client.post("/api/decks", json={"title": "Draft Test Deck"})
    deck_id = deck_res.json()["id"]

    slide_res = await client.post(f"/api/decks/{deck_id}/slides")
    slide_id = slide_res.json()["id"]
    curr_v_id = slide_res.json()["current_version"]["id"]

    # 1. Normalization draft PUT: fills version.scene once
    mock_scene = {
        "elements": [
            {"id": "slide-frame", "type": "frame", "x": 0, "y": 0, "width": 1920, "height": 1080},
            {"id": "n1", "type": "rectangle", "x": 100, "y": 100, "width": 200, "height": 100},
        ],
        "appState": {"viewBackgroundColor": "#ffffff"},
    }

    put_res = await client.put(
        f"/api/slides/{slide_id}/draft",
        json={
            "scene": mock_scene,
            "if_rev": 0,
            "normalizing_version_id": curr_v_id,
        },
    )
    assert put_res.status_code == 200
    slide_data = put_res.json()
    assert slide_data["draft"]["rev"] == 1
    assert slide_data["draft"]["hash"] is not None
    assert slide_data["current_version"]["scene"] is not None
    assert slide_data["current_version"]["scene_hash"] == slide_data["draft"]["hash"]
    # Because version.scene_hash == draft.hash, it's not dirty
    assert slide_data["is_dirty"] is False

    # 2. Checkpoint on clean slide -> 409 nothing_to_commit
    cp_clean_res = await client.post(f"/api/slides/{slide_id}/versions")
    assert cp_clean_res.status_code == 409
    assert cp_clean_res.json()["error"]["code"] == "nothing_to_commit"

    # 3. Conflict on stale if_rev
    conflict_res = await client.put(
        f"/api/slides/{slide_id}/draft",
        json={"scene": mock_scene, "if_rev": 0},  # current is 1
    )
    assert conflict_res.status_code == 409
    assert conflict_res.json()["error"]["code"] == "draft_conflict"

    # 4. Modify draft (making it dirty)
    modified_scene = {
        "elements": [
            {"id": "slide-frame", "type": "frame", "x": 0, "y": 0, "width": 1920, "height": 1080},
            {"id": "n1", "type": "rectangle", "x": 150, "y": 150, "width": 250, "height": 120},
        ],
        "appState": {"viewBackgroundColor": "#ffffff"},
    }
    put_res2 = await client.put(
        f"/api/slides/{slide_id}/draft",
        json={"scene": modified_scene, "if_rev": 1},
    )
    assert put_res2.status_code == 200
    slide_data2 = put_res2.json()
    assert slide_data2["draft"]["rev"] == 2
    assert slide_data2["is_dirty"] is True

    # 5. Checkpoint dirty slide -> creates version 2
    cp_res = await client.post(
        f"/api/slides/{slide_id}/versions",
        json={"summary": "My manual checkpoint"},
    )
    assert cp_res.status_code == 201
    v2_data = cp_res.json()
    assert v2_data["seq"] == 2
    assert v2_data["origin"] == "user_checkpoint"
    assert v2_data["summary"] == "My manual checkpoint"

    # 6. List versions
    versions_res = await client.get(f"/api/slides/{slide_id}/versions")
    assert versions_res.status_code == 200
    versions = versions_res.json()
    assert len(versions) == 2
    assert versions[0]["seq"] == 2
    assert versions[1]["seq"] == 1

    # 7. Restore version 1 -> creates version 3 with origin=restore (history never rewinds)
    restore_res = await client.post(
        f"/api/slides/{slide_id}/restore",
        json={"version_id": curr_v_id},
    )
    assert restore_res.status_code == 200
    restored_slide = restore_res.json()
    assert restored_slide["current_version"]["seq"] == 3
    assert restored_slide["current_version"]["origin"] == "restore"
    assert restored_slide["draft"]["rev"] == 3

    # Verify version count in DB
    versions_res2 = await client.get(f"/api/slides/{slide_id}/versions")
    assert len(versions_res2.json()) == 3


@pytest.mark.asyncio
async def test_flush_drafts(client: AsyncClient, db_session):
    # Setup deck with 2 slides
    deck_res = await client.post("/api/decks", json={"title": "Flush Test Deck"})
    deck_id = deck_res.json()["id"]

    s1_res = await client.post(f"/api/decks/{deck_id}/slides")
    s1_id = s1_res.json()["id"]
    s1_v1 = s1_res.json()["current_version"]["id"]

    await client.post(f"/api/decks/{deck_id}/slides")

    # Normalize s1
    scene1 = {
        "elements": [
            {"id": "slide-frame", "type": "frame", "x": 0, "y": 0, "width": 1920, "height": 1080}
        ],
        "appState": {"viewBackgroundColor": "#ffffff"},
    }
    await client.put(
        f"/api/slides/{s1_id}/draft",
        json={"scene": scene1, "if_rev": 0, "normalizing_version_id": s1_v1},
    )

    # Edit s1 (now dirty)
    scene1_dirty = {
        "elements": [
            {"id": "slide-frame", "type": "frame", "x": 0, "y": 0, "width": 1920, "height": 1080},
            {"id": "box", "type": "rectangle", "x": 50, "y": 50, "width": 100, "height": 100},
        ],
        "appState": {"viewBackgroundColor": "#ffffff"},
    }
    await client.put(
        f"/api/slides/{s1_id}/draft",
        json={"scene": scene1_dirty, "if_rev": 1},
    )

    # s2 remains unchanged (clean)
    committed = await flush_drafts(db_session, deck_id)
    # Only s1 was dirty, so only 1 version committed
    assert len(committed) == 1
    assert str(committed[0].slide_id) == s1_id
    assert committed[0].origin == "user_save"
