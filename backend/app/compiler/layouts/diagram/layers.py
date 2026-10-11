"""Layers diagram layout: stacked full-width horizontal architectural bands.

Calculates equal vertical heights for all layers based on maximum content
metrics, stacks them in top-to-bottom list order across the region width,
renders left-aligned labels with right-aligned sublabels inside each band,
and connects consecutive layers with small down-pointing arrows when edges
exist between them.
"""

from __future__ import annotations

from typing import Any

from app.compiler.layouts.diagram.rect import Rect
from app.compiler.palette import DEFAULT_STROKE, MUTED_TEXT, style_for_emphasis
from app.compiler.skeleton import SkeletonBuilder
from app.compiler.text_metrics import measure, wrap
from app.ir.schemas import DiagramBlock


def layout_layers(
    block: DiagramBlock,
    region: Rect,
    font_size: float = 28.0,
) -> tuple[list[dict[str, Any]], list[str], Rect]:
    """Stack nodes vertically as full-width architectural layers.

    Returns (elements, warnings, bounding_box).
    """
    builder = SkeletonBuilder(width=1920, height=1080)
    warnings: list[str] = []

    n = len(block.nodes)
    if n == 0:
        return [], warnings, region

    # Determine band height and spacing
    total_gap = (n - 1) * 24.0
    avail_h = region.h - total_gap
    band_h = max(72.0, min(120.0, avail_h / n))
    actual_total_h = n * band_h + (n - 1) * 24.0

    start_y = region.y + max(0.0, (region.h - actual_total_h) / 2.0)
    band_w = region.w
    band_x = region.x

    node_ids_in_order = [node.id for node in block.nodes]

    for idx, node in enumerate(block.nodes):
        y = start_y + idx * (band_h + 24.0)
        colors = style_for_emphasis(node.emphasis)

        # Main container band
        builder.shape(
            id=f"n_{node.id}",
            shape_type="rounded",
            x=band_x,
            y=y,
            width=band_w,
            height=band_h,
            stroke_color=colors.stroke,
            background_color=colors.fill,
            fill_style=colors.fill_style,
        )

        # Left-aligned primary label
        wrapped_label = "\n".join(wrap(node.label, font_size=font_size, max_width=band_w * 0.6))
        lw, lh = measure(wrapped_label, font_size)
        builder.text(
            id=f"lbl_{node.id}",
            text=wrapped_label,
            x=band_x + 36.0,
            y=y + (band_h - lh) / 2.0,
            width=lw,
            height=lh,
            font_size=font_size,
            stroke_color=colors.text,
            text_align="left",
            vertical_align="middle",
        )

        # Right-aligned sublabel if present
        if node.sublabel:
            wrapped_sub = "\n".join(wrap(node.sublabel, font_size=24.0, max_width=band_w * 0.35))
            sw, sh = measure(wrapped_sub, 24.0)
            builder.text(
                id=f"sub_{node.id}",
                text=wrapped_sub,
                x=band_x + band_w - sw - 36.0,
                y=y + (band_h - sh) / 2.0,
                width=sw,
                height=sh,
                font_size=24.0,
                stroke_color=MUTED_TEXT,
                text_align="right",
                vertical_align="middle",
            )

        # Down arrow to next layer if edge exists or requested
        if idx < n - 1:
            next_id = node_ids_in_order[idx + 1]
            edge_exists = any(
                e.source == node.id and e.target == next_id for e in block.edges
            ) or (not block.edges)  # Default connecting arrow if no explicit edges
            if edge_exists:
                arrow_y = y + band_h
                cx = band_x + band_w / 2.0
                builder.arrow(
                    id=f"e_{node.id}_{next_id}",
                    x=cx,
                    y=arrow_y,
                    width=0.0,
                    height=24.0,
                    start_id=f"n_{node.id}",
                    end_id=f"n_{next_id}",
                    stroke_color=DEFAULT_STROKE,
                    points=[[0.0, 0.0], [0.0, 24.0]],
                )

    content_bb = Rect(band_x, start_y, band_w, actual_total_h)
    return builder.elements, warnings, content_bb
