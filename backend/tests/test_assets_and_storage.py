import hashlib

import pytest
from httpx import AsyncClient

from app.errors import BadRequestError
from app.services.storage import LocalStorage


def test_storage_path_traversal(tmp_path):
    storage = LocalStorage(base_dir=tmp_path)
    # Happy path
    storage.put("sub/item.txt", b"hello world")
    assert storage.get("sub/item.txt") == b"hello world"
    assert storage.exists("sub/item.txt") is True

    # Path traversal attempts
    with pytest.raises(BadRequestError) as exc_info:
        storage.get("../../../etc/passwd")
    assert exc_info.value.code == "path_traversal"

    with pytest.raises(BadRequestError) as exc_info:
        storage.put("..\\..\\secret.txt", b"dangerous")
    assert exc_info.value.code == "path_traversal"


@pytest.mark.asyncio
async def test_assets_api_and_idempotency(client: AsyncClient):
    deck_res = await client.post("/api/decks", json={"title": "Asset Test Deck"})
    deck_id = deck_res.json()["id"]

    # 1x1 transparent PNG
    tiny_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15"
        b"\xc4\x89\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    file_id = hashlib.sha1(tiny_png).hexdigest()

    # Upload asset
    upload_res = await client.put(
        f"/api/decks/{deck_id}/assets/{file_id}",
        content=tiny_png,
        headers={"Content-Type": "image/png"},
    )
    assert upload_res.status_code == 201
    asset_data = upload_res.json()
    assert asset_data["id"] == file_id
    assert asset_data["width"] == 1
    assert asset_data["height"] == 1

    # Idempotent upload: same fileId returns existing without error
    upload_res2 = await client.put(
        f"/api/decks/{deck_id}/assets/{file_id}",
        content=tiny_png,
        headers={"Content-Type": "image/png"},
    )
    assert upload_res2.status_code == 201
    assert upload_res2.json()["id"] == file_id

    # Fetch asset
    get_res = await client.get(f"/api/assets/{file_id}")
    assert get_res.status_code == 200
    assert get_res.content == tiny_png
    assert get_res.headers["content-type"] == "image/png"
    assert "public, max-age=" in get_res.headers["cache-control"]
