"""Diagram layout engine dispatcher with density fitting loop."""

from __future__ import annotations

from typing import Any, NamedTuple

from app.compiler.layouts.diagram.comparison import layout_comparison
from app.compiler.layouts.diagram.cycle import layout_cycle
from app.compiler.layouts.diagram.dot import layout_dot
from app.compiler.layouts.diagram.layers import layout_layers
from app.compiler.layouts.diagram.mindmap import layout_mindmap
from app.compiler.layouts.diagram.rect import Rect
from app.compiler.layouts.diagram.timeline import layout_timeline
from app.ir.schemas import DiagramBlock


class DiagramLayout(NamedTuple):
    elements: list[dict[str, Any]]
    warnings: list[str]
    bounding_box: Rect
    min_font_used: float


def layout_diagram(
    block: DiagramBlock,
    region: Rect,
    ctx: Any = None,
) -> DiagramLayout:
    """Compute diagram layout with progressive stepwise font reduction and gap tightening.

    Steps font down 28 -> 26 -> 24. Emits ValueError with code 'diagram_too_dense'
    if the diagram cannot fit within the region at font 24.
    """
    kind = block.kind
    font_candidates = [28.0, 26.0, 24.0]

    for font in font_candidates:
        # Adjust gaps based on font step
        gap_scale = 1.0 if font == 28.0 else (0.8 if font == 26.0 else 0.6)

        if kind in ("flow", "hierarchy"):
            elements, warnings, bb = layout_dot(
                block=block,
                region=region,
                font_size=font,
                nodesep_px=40.0 * gap_scale,
                ranksep_px=60.0 * gap_scale,
            )
        elif kind == "layers":
            elements, warnings, bb = layout_layers(block, region, font_size=font)
        elif kind == "cycle":
            elements, warnings, bb = layout_cycle(block, region, font_size=font)
        elif kind == "timeline":
            elements, warnings, bb = layout_timeline(block, region, font_size=font)
        elif kind == "comparison":
            elements, warnings, bb = layout_comparison(block, region, font_size=font)
        elif kind == "mindmap":
            elements, warnings, bb = layout_mindmap(block, region, font_size=font)
        else:
            raise ValueError(f"Unsupported diagram kind: {kind}")

        # Check if bounding box fits region
        if bb.w <= region.w and bb.h <= region.h:
            return DiagramLayout(
                elements=elements,
                warnings=warnings,
                bounding_box=bb,
                min_font_used=font,
            )

    raise ValueError(
        f"diagram_too_dense: Diagram with {len(block.nodes)} nodes cannot fit into the available "
        f"region ({region.w:.0f}x{region.h:.0f}px) at minimum font 24. "
        "Suggestion: reduce node count or split the slide."
    )
