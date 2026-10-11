"""Comprehensive tests for compiler correctness, determinism, golden snapshots, and quality gate."""

from __future__ import annotations

import json
from pathlib import Path

from app.compiler import CompileCtx, compile
from app.compiler.quality import check_quality
from app.ir.schemas import SlideIR

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ir"
GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"

SAMPLE_ASSET_DIMS = {
    "asset_sample_chart_1": (800, 600),
    "tall_mockup_asset": (400, 800),
    "wide_dashboard_asset": (1200, 600),
}


def test_all_fixtures_compile_cleanly(request):
    """Verify that every fixture in tests/fixtures/ir compiles with zero errors and matches golden snapshots."""
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    update_golden = request.config.getoption("--update-golden", default=False)

    fixture_files = sorted(FIXTURES_DIR.glob("*.json"))
    assert len(fixture_files) >= 16, f"Expected at least 16 fixtures, found {len(fixture_files)}"

    ctx = CompileCtx(asset_dims=SAMPLE_ASSET_DIMS)

    for f_path in fixture_files:
        ir_data = json.loads(f_path.read_text(encoding="utf-8"))
        ir = SlideIR.model_validate(ir_data)

        res = compile(ir, ctx)
        assert res.errors == [], f"Fixture '{f_path.name}' failed compilation: {res.errors}"
        assert res.skeleton is not None, f"Fixture '{f_path.name}' produced no skeleton"
        assert res.skeleton["elements"][0]["type"] == "frame"

        # Golden snapshot handling
        golden_path = GOLDEN_DIR / f_path.name
        curr_json = json.dumps(res.skeleton, indent=2, sort_keys=True)

        if update_golden or not golden_path.exists():
            golden_path.write_text(curr_json, encoding="utf-8")
        else:
            expected_json = golden_path.read_text(encoding="utf-8")
            assert curr_json == expected_json, (
                f"Skeleton for fixture '{f_path.name}' does not match golden snapshot. "
                "Run with --update-golden if changes were intentional."
            )


def test_compiler_determinism():
    """Verify that compiling the same IR twice yields byte-identical JSON output."""
    f_path = FIXTURES_DIR / "diagram_flow_lr.json"
    ir_data = json.loads(f_path.read_text(encoding="utf-8"))
    ir = SlideIR.model_validate(ir_data)
    ctx = CompileCtx(asset_dims=SAMPLE_ASSET_DIMS)

    res1 = compile(ir, ctx)
    res2 = compile(ir, ctx)

    json1 = json.dumps(res1.skeleton, sort_keys=True)
    json2 = json.dumps(res2.skeleton, sort_keys=True)
    assert json1 == json2


def test_quality_gate_outside_frame():
    bad_skeleton = {
        "version": 1,
        "frame": {"width": 1920, "height": 1080},
        "elements": [
            {"type": "frame", "id": "slide-frame", "width": 1920, "height": 1080},
            {"type": "rectangle", "id": "out_of_bounds", "x": 1900, "y": 1000, "width": 100, "height": 100},
        ],
    }
    issues = check_quality(bad_skeleton)
    assert any(i.code == "element_outside_frame" and i.severity == "error" for i in issues)


def test_quality_gate_overlapping_elements():
    bad_skeleton = {
        "version": 1,
        "frame": {"width": 1920, "height": 1080},
        "elements": [
            {"type": "frame", "id": "slide-frame", "width": 1920, "height": 1080},
            {"type": "rectangle", "id": "box_a", "x": 200, "y": 300, "width": 200, "height": 100},
            {"type": "rectangle", "id": "box_b", "x": 250, "y": 320, "width": 200, "height": 100},
        ],
    }
    issues = check_quality(bad_skeleton)
    assert any(i.code == "elements_overlap" and i.severity == "error" for i in issues)


def test_quality_gate_font_too_small():
    bad_skeleton = {
        "version": 1,
        "frame": {"width": 1920, "height": 1080},
        "elements": [
            {"type": "frame", "id": "slide-frame", "width": 1920, "height": 1080},
            {"type": "text", "id": "tiny_text", "x": 200, "y": 300, "width": 100, "height": 40, "fontSize": 18},
        ],
    }
    issues = check_quality(bad_skeleton)
    assert any(i.code == "font_too_small" and i.severity == "error" for i in issues)
