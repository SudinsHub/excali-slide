"""Tests for IR & Plan schemas, JSON schema export, and budget computations."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.ir import (
    PlanSlide,
    SlideIR,
    TextBlock,
    budgets_for,
    plan_json_schema,
    slide_ir_json_schema,
)
from app.schemas.deck import DeckSettings


def test_deck_budgets_mapping():
    light = budgets_for(DeckSettings(density="light", diagram_intensity="low"))
    assert light.max_nodes == 8
    assert light.bullets == 3
    assert light.words_per_bullet == 8
    assert light.diagram_share == 0.25

    standard = budgets_for(DeckSettings(density="standard", diagram_intensity="medium"))
    assert standard.max_nodes == 12
    assert standard.bullets == 4
    assert standard.words_per_bullet == 12
    assert standard.diagram_share == 0.50

    dense = budgets_for(DeckSettings(density="dense", diagram_intensity="high"))
    assert dense.max_nodes == 16
    assert dense.bullets == 6
    assert dense.words_per_bullet == 16
    assert dense.diagram_share == 0.75

    default = budgets_for(None)
    assert default == standard


def test_json_schemas_export_validity():
    ir_schema = slide_ir_json_schema()
    assert ir_schema["type"] == "object"
    assert "properties" in ir_schema
    assert "layout" in ir_schema["properties"]
    assert "blocks" in ir_schema["properties"]
    # Verify discriminated union
    defs = ir_schema.get("$defs", {})
    assert any("Block" in k or "TextBlock" in k for k in defs)

    plan_schema = plan_json_schema()
    assert plan_schema["type"] == "object"
    assert "slides" in plan_schema["properties"]


def test_schema_extra_forbid():
    with pytest.raises(ValidationError):
        SlideIR(
            schema_version=1,
            slide_key="s1",
            layout="text",
            title="Title",
            unexpected_field="disallowed",
        )

    with pytest.raises(ValidationError):
        TextBlock(
            type="text",
            style="bullets",
            items=["Item 1"],
            forbidden_key=123,
        )


def test_plan_slide_model():
    slide = PlanSlide(
        key="s1",
        role="content",
        title="Valid Title",
        kind="text",
        intent="Explain key concepts",
    )
    assert slide.key == "s1"
    assert slide.kind == "text"
