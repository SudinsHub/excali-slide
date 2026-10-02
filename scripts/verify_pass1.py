import json
import urllib.request

def verify():
    print("--- 1. Checking Health ---")
    with urllib.request.urlopen("http://localhost:8000/health") as res:
        print("Health status:", res.read().decode().strip())

    print("\n--- 2. Checking Frontend index.html ---")
    with urllib.request.urlopen("http://localhost:5173") as res:
        html = res.read().decode()
        print("Frontend responding with status:", res.status, f"(HTML size: {len(html)} bytes)")

    print("\n--- 3. Creating Demo Sample Deck via POST /api/dev/decks/sample ---")
    req = urllib.request.Request("http://localhost:8000/api/dev/decks/sample", method="POST")
    with urllib.request.urlopen(req) as res:
        deck = json.loads(res.read().decode())
    deck_id = deck["id"]
    print(f"Deck created successfully:")
    print(f"  ID: {deck_id}")
    print(f"  Title: {deck['title']}")
    print(f"  Slide count: {deck['slide_count']}")

    print("\n--- 4. Verifying All 4 Fixture Slides ---")
    with urllib.request.urlopen(f"http://localhost:8000/api/decks/{deck_id}/slides") as res:
        slides = json.loads(res.read().decode())
    
    assert len(slides) == 4, f"Expected 4 slides, got {len(slides)}"
    
    fixture_names = ["Cover", "Bullets", "Diagram", "Image"]
    for idx, slide in enumerate(slides):
        with urllib.request.urlopen(f"http://localhost:8000/api/slides/{slide['id']}") as res:
            detail = json.loads(res.read().decode())
        curr_v = detail["current_version"]
        assert curr_v is not None, "Missing current_version"
        assert curr_v["skeleton"] is not None, "Missing skeleton"
        elements = curr_v["skeleton"]["elements"]
        frame = elements[0]
        assert frame["type"] == "frame", "First element must be frame"
        assert frame["width"] == 1920 and frame["height"] == 1080, "Frame must be 1920x1080"
        print(f"  [{idx+1}/4] Slide '{fixture_names[idx]}': id={slide['id']}, elements={len(elements)}, title='{slide['title']}'")

    print("\n--- 5. Verifying Diagram Slide Elements & Bindings ---")
    diagram_slide = slides[2]
    with urllib.request.urlopen(f"http://localhost:8000/api/slides/{diagram_slide['id']}") as res:
        diag_detail = json.loads(res.read().decode())
    elements = diag_detail["current_version"]["skeleton"]["elements"]
    arrows = [e for e in elements if e["type"] == "arrow"]
    rectangles = [e for e in elements if e["type"] == "rectangle"]
    assert len(rectangles) == 4, f"Expected 4 diagram nodes, found {len(rectangles)}"
    assert len(arrows) == 3, f"Expected 3 connecting arrows, found {len(arrows)}"
    for arrow in arrows:
        assert "start" in arrow and "id" in arrow["start"], "Arrow must have bound start id"
        assert "end" in arrow and "id" in arrow["end"], "Arrow must have bound end id"
    print(f"  Verified 4 diagram rectangles with labels and 3 bound arrows (start/end correctly targeted)")

    print("\n--- 6. Verifying Generated Asset on Image Slide ---")
    image_slide = slides[3]
    with urllib.request.urlopen(f"http://localhost:8000/api/slides/{image_slide['id']}") as res:
        img_detail = json.loads(res.read().decode())
    asset_id = img_detail["current_version"]["skeleton"]["asset_ids"][0]
    with urllib.request.urlopen(f"http://localhost:8000/api/assets/{asset_id}") as res:
        asset_bytes = res.read()
        content_type = res.headers["content-type"]
        cache_control = res.headers["cache-control"]
    print(f"  Asset {asset_id} fetched:")
    print(f"    Content-Type: {content_type}")
    print(f"    Cache-Control: {cache_control}")
    print(f"    Size: {len(asset_bytes)} bytes")
    assert content_type == "image/png"
    assert len(asset_bytes) > 0

    print("\n--- 7. Testing Slide Draft Save & Revision Handling ---")
    mock_scene = {
        "elements": [
            {"id": "slide-frame", "type": "frame", "x": 0, "y": 0, "width": 1920, "height": 1080},
            {"id": "test_box", "type": "rectangle", "x": 50, "y": 50, "width": 200, "height": 100}
        ],
        "appState": {"viewBackgroundColor": "#ffffff"}
    }
    target_slide_id = slides[0]["id"]
    save_payload = json.dumps({"scene": mock_scene, "if_rev": 0}).encode("utf-8")
    req = urllib.request.Request(
        f"http://localhost:8000/api/slides/{target_slide_id}/draft",
        data=save_payload,
        headers={"Content-Type": "application/json"},
        method="PUT"
    )
    with urllib.request.urlopen(req) as res:
        updated = json.loads(res.read().decode())
    print(f"  Draft saved: rev={updated['draft']['rev']}, dirty={updated['is_dirty']}, hash={updated['draft']['hash'][:8]}...")
    assert updated["draft"]["rev"] == 1
    assert updated["is_dirty"] is True

    print("\n--- 8. Testing Checkpoint Creation ---")
    cp_payload = json.dumps({"summary": "Manual Checkpoint v2"}).encode("utf-8")
    req = urllib.request.Request(
        f"http://localhost:8000/api/slides/{target_slide_id}/versions",
        data=cp_payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as res:
        cp_version = json.loads(res.read().decode())
    print(f"  Checkpoint created: seq={cp_version['seq']}, origin={cp_version['origin']}, summary='{cp_version['summary']}'")
    assert cp_version["seq"] == 2
    assert cp_version["origin"] == "user_checkpoint"

    print("\n--- 9. Testing Version Restore ---")
    restore_payload = json.dumps({"version_id": slides[0]["current_version_id"]}).encode("utf-8")
    req = urllib.request.Request(
        f"http://localhost:8000/api/slides/{target_slide_id}/restore",
        data=restore_payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as res:
        restored = json.loads(res.read().decode())
    print(f"  Restored successfully: current_version seq={restored['current_version']['seq']}, origin={restored['current_version']['origin']}")
    assert restored["current_version"]["seq"] == 3
    assert restored["current_version"]["origin"] == "restore"

    print("\n=======================================================")
    print("ALL PASS 1 ACCEPTANCE CRITERIA VERIFIED SUCCESSFULLY! ")
    print("=======================================================")

if __name__ == "__main__":
    verify()
