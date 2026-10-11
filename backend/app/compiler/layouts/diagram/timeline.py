"""Timeline diagram layout: horizontal milestone axis with alternating cards.

Draws a continuous horizontal axis line across the region with circular
milestone markers at equidistant steps. Places milestone label and sublabel
cards alternately above and below the axis to prevent horizontal collisions,
wrapping text within milestone column widths and applying emphasis colors to
the circular milestone markers.
"""

from __future__ import annotations

from typing import Any

from app.compiler.layouts.diagram.rect import Rect
from app.compiler.palette import MUTED_TEXT, style_for_emphasis
from app.compiler.skeleton import SkeletonBuilder
from app.compiler.text_metrics import measure, wrap
from app.ir.schemas import DiagramBlock


def layout_timeline(
    block: DiagramBlock,
    region: Rect,
    font_size: float = 28.0,
) -> tuple[list[dict[str, Any]], list[str], Rect]:
    """Render horizontal timeline axis with alternating milestone cards.

    Returns (elements, warnings, bounding_box).
    """
    builder = SkeletonBuilder(width=1920, height=1080)
    warnings: list[str] = []

    n = len(block.nodes)
    if n == 0:
        return [], warnings, region

    axis_y = region.cy
    card_w = min(320.0, (region.w - 80.0) / n - 24.0) if n > 1 else min(320.0, region.w - 80.0)
    axis_start_x = region.x + card_w / 2.0 + 20.0
    axis_end_x = region.right - card_w / 2.0 - 20.0
    total_w = max(0.0, axis_end_x - axis_start_x)

    step = total_w / max(1, n - 1) if n > 1 else 0.0

    # 1. Main axis line
    builder.line(
        id="timeline_axis",
        x=axis_start_x,
        y=axis_y,
        width=total_w,
        height=0.0,
        points=[[0.0, 0.0], [total_w, 0.0]],
        stroke_color="#868e96",
        stroke_width=3,
    )

    top_bound = axis_y - 20.0
    bot_bound = axis_y + 20.0

    # 2. Milestones
    for idx, node in enumerate(block.nodes):
        mx = axis_start_x + idx * step if n > 1 else region.cx
        colors = style_for_emphasis(node.emphasis)

        # Milestone circular marker (diameter 32)
        marker_d = 32.0
        builder.shape(
            id=f"marker_{node.id}",
            shape_type="ellipse",
            x=mx - marker_d / 2.0,
            y=axis_y - marker_d / 2.0,
            width=marker_d,
            height=marker_d,
            stroke_color=colors.stroke,
            background_color=colors.fill if colors.fill != "transparent" else "#ffffff",
            fill_style="solid",
            stroke_width=3,
        )

        # Text wrap
        wrapped_label = "\n".join(wrap(node.label, font_size=font_size, max_width=card_w))
        lw, lh = measure(wrapped_label, font_size)

        sw, sh = 0.0, 0.0
        wrapped_sub = ""
        if node.sublabel:
            wrapped_sub = "\n".join(wrap(node.sublabel, font_size=24.0, max_width=card_w))
            sw, sh = measure(wrapped_sub, 24.0)

        card_h = lh + (sh + 6.0 if node.sublabel else 0.0)
        card_x = mx - card_w / 2.0

        is_above = (idx % 2 == 0)
        if is_above:
            card_y = axis_y - 36.0 - card_h
            top_bound = min(top_bound, card_y)
        else:
            card_y = axis_y + 36.0
            bot_bound = max(bot_bound, card_y + card_h)

        # Label element
        builder.text(
            id=f"n_{node.id}",
            text=wrapped_label,
            x=card_x,
            y=card_y,
            width=card_w,
            height=lh,
            font_size=font_size,
            stroke_color=colors.text,
            text_align="center",
            vertical_align="top",
        )

        # Sublabel element
        if node.sublabel:
            builder.text(
                id=f"sub_{node.id}",
                text=wrapped_sub,
                x=card_x,
                y=card_y + lh + 6.0,
                width=card_w,
                height=sh,
                font_size=24.0,
                stroke_color=MUTED_TEXT,
                text_align="center",
                vertical_align="top",
            )

        # Subtle connecting tick line from marker to card
        if is_above:
            builder.line(
                id=f"tick_{node.id}",
                x=mx,
                y=axis_y - marker_d / 2.0,
                width=0.0,
                height=20.0,
                points=[[0.0, 0.0], [0.0, -20.0]],
                stroke_color="#adb5bd",
                stroke_width=1,
            )
        else:
            builder.line(
                id=f"tick_{node.id}",
                x=mx,
                y=axis_y + marker_d / 2.0,
                width=0.0,
                height=20.0,
                points=[[0.0, 0.0], [0.0, 20.0]],
                stroke_color="#adb5bd",
                stroke_width=1,
            )

    content_bb = Rect(
        axis_start_x - card_w / 2.0,
        top_bound,
        total_w + card_w,
        bot_bound - top_bound,
    )
    return builder.elements, warnings, content_bb
