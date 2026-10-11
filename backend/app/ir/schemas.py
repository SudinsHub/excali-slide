"""Pydantic v2 models for presentation plans and SlideIR according to SPEC §6."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# --- Plan Schemas (SPEC §6.2) ---

Role = Literal[
    "cover",
    "agenda",
    "section",
    "content",
    "process",
    "comparison",
    "data",
    "summary",
    "closing",
]

PlanKind = Literal["text", "diagram", "hybrid"]

Layout = Literal[
    "cover",
    "section",
    "statement",
    "text",
    "diagram",
    "split",
    "two_column",
    "image_text",
    "closing",
]

DiagramKind = Literal[
    "flow",
    "hierarchy",
    "layers",
    "cycle",
    "timeline",
    "comparison",
    "mindmap",
]

NodeShape = Literal["rounded", "rect", "ellipse", "diamond", "text"]

Emphasis = Literal["normal", "primary", "accent", "positive", "negative", "muted"]

Direction = Literal["LR", "TB"]

TextSide = Literal["left", "right"]
ImageSide = Literal["left", "right"]


class SourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource_id: uuid.UUID
    locator: str | None = None


class GlossaryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    term: str = Field(..., min_length=1, max_length=100)
    short_label: str = Field(..., min_length=1, max_length=50)


class DiagramHint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: DiagramKind
    description: str = Field(..., min_length=1, max_length=300)


class PlanSlide(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(..., pattern=r"^s[0-9]+$")
    role: Role
    title: str = Field(..., min_length=1, max_length=200)
    kind: PlanKind
    layout_hint: Layout | None = None
    diagram_hint: DiagramHint | None = None
    key_points: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)
    image_ids: list[str] = Field(default_factory=list)
    intent: str = Field(..., min_length=1, max_length=300)


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(..., min_length=1, max_length=200)
    audience: str = Field(..., min_length=1, max_length=100)
    goal: str = Field(..., min_length=1, max_length=300)
    narrative_summary: str = Field(..., min_length=1)
    glossary: list[GlossaryItem] = Field(default_factory=list)
    slides: list[PlanSlide] = Field(..., min_length=1)


# --- SlideIR Schemas (SPEC §6.3) ---

TextStyle = Literal["bullets", "numbered", "paragraph", "quote"]


class TextBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["text"] = "text"
    style: TextStyle = "bullets"
    heading: str | None = None
    items: list[str] = Field(..., min_length=1)


class Node(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., pattern=r"^[a-z][a-z0-9_]{0,31}$")
    label: str = Field(..., min_length=1)
    sublabel: str | None = None
    shape: NodeShape = "rounded"
    emphasis: Emphasis = "normal"
    group_id: str | None = None


class Edge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str = Field(..., min_length=1)
    target: str = Field(..., min_length=1)
    label: str | None = None
    directed: bool = True
    dashed: bool = False


class Group(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., pattern=r"^[a-z][a-z0-9_]{0,31}$")
    label: str = Field(..., min_length=1)
    node_ids: list[str] | None = None


class DiagramBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["diagram"] = "diagram"
    kind: DiagramKind
    direction: Direction = "LR"
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    groups: list[Group] = Field(default_factory=list)
    caption: str | None = None


class ImageBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["image"] = "image"
    asset_id: str = Field(..., min_length=1)
    caption: str | None = None


Block = Annotated[
    TextBlock | DiagramBlock | ImageBlock,
    Field(discriminator="type"),
]


class SlideIR(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    slide_key: str = Field(..., min_length=1, max_length=50)
    layout: Layout
    title: str | None = None
    subtitle: str | None = None
    blocks: list[Block] = Field(default_factory=list)
    text_side: TextSide | None = None
    image_side: ImageSide | None = None


def slide_ir_json_schema() -> dict:
    """Export clean, non-recursive JSON schema for SlideIR for LLM structured output."""
    return SlideIR.model_json_schema()


def plan_json_schema() -> dict:
    """Export clean, non-recursive JSON schema for Plan for LLM structured output."""
    return Plan.model_json_schema()
