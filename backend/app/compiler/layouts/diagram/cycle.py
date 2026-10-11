"""Cycle diagram layout: circular clockwise workflow arrangement.

Arranges nodes along a circle with equal angular spacing starting at 12
o'clock clockwise. Computes circle radius dynamically from maximum node
dimensions and angular chord distance to ensure neighbor boxes never collide.
Connects consecutive nodes with curved or straight bound arrows and centers
optional caption text in the hub of the circle.
"""

from __future__ import annotations

import math
from typing import Any

from app.compiler.layouts.diagram.rect import Rect
from app.compiler.palette import DEFAULT_STROKE, MUTED_TEXT, style_for_emphasis
from app.compiler.skeleton import SkeletonBuilder, fit_node
from app.compiler.text_metrics import measure, wrap
from app.ir.schemas import DiagramBlock


def layout_cycle(
    block: DiagramBlock,
    region: Rect,
    font_size: float = 28.0,
) -> tuple[list[dict[str, Any]], list[str], Rect]:
    """Position nodes along a clockwise circular path.

    Returns (elements, warnings, bounding_box).
    """
    builder = SkeletonBuilder(width=1920, height=1080)
    warnings: list[str] = []

    n = len(block.nodes)
    if n == 0:
        return [], warnings, region

    # 1. Size all nodes
    node_sizes: dict[str, tuple[float, float]] = {}
    max_w = 0.0
    max_h = 0.0
    for node in block.nodes:
        w, h = fit_node(node.label, node.sublabel, node.shape, font_size=font_size)
        node_sizes[node.id] = (w, h)
        max_w = max(max_w, w)
        max_h = max(max_h, h)

    # 2. Compute minimum safe radius
    diag = math.hypot(max_w, max_h)
    half_angle = math.pi / n
    min_radius = (diag + 40.0) / (2.0 * math.sin(half_angle))

    max_possible_r = min(region.w - max_w, region.h - max_h) / 2.0 - 20.0
    radius = min(max_possible_r, max(min_radius, 220.0))

    cx = region.cx
    cy = region.cy

    node_rects: dict[str, Rect] = {}

    # 3. Position nodes clockwise starting from 12 o'clock (-pi/2)
    for idx, node in enumerate(block.nodes):
        theta = -math.pi / 2.0 + idx * (2.0 * math.pi / n)
        nw, nh = node_sizes[node.id]
        nx = cx + radius * math.cos(theta) - nw / 2.0
        ny = cy + radius * math.sin(theta) - nh / 2.0
        node_rects[node.id] = Rect(nx, ny, nw, nh)

        colors = style_for_emphasis(node.emphasis)
        wrapped_label = "\n".join(wrap(node.label, font_size=font_size, max_width=nw - 56.0))
        label_text = wrapped_label
        if node.sublabel:
            wrapped_sub = "\n".join(wrap(node.sublabel, font_size=24.0, max_width=nw - 56.0))
            label_text = f"{wrapped_label}\n{wrapped_sub}"

        builder.shape(
            id=f"n_{node.id}",
            shape_type=node.shape,
            x=nx,
            y=ny,
            width=nw,
            height=nh,
            stroke_color=colors.stroke,
            background_color=colors.fill,
            fill_style=colors.fill_style,
            label=label_text,
            font_size=font_size,
            label_color=colors.text,
            group_ids=[f"g_{node.id}"] if node.sublabel else None,
        )

    # 4. Connect consecutive nodes plus closing loop
    nodes = block.nodes
    for idx in range(n):
        src = nodes[idx]
        dst = nodes[(idx + 1) % n]
        r_src = node_rects[src.id]
        r_dst = node_rects[dst.id]

        builder.arrow(
            id=f"e_{src.id}_{dst.id}",
            x=r_src.cx,
            y=r_src.cy,
            width=r_dst.cx - r_src.cx,
            height=r_dst.cy - r_src.cy,
            start_id=f"n_{src.id}",
            end_id=f"n_{dst.id}",
            stroke_color=DEFAULT_STROKE,
        )

    # 5. Optional centered caption
    if block.caption:
        wrapped_cap = "\n".join(wrap(block.caption, font_size=24.0, max_width=radius * 1.2))
        cw, ch = measure(wrapped_cap, 24.0)
        builder.text(
            id="cycle_caption",
            text=wrapped_cap,
            x=cx - cw / 2.0,
            y=cy - ch / 2.0,
            width=cw,
            height=ch,
            font_size=24.0,
            stroke_color=MUTED_TEXT,
            text_align="center",
            vertical_align="middle",
        )

    total_r = radius + max(max_w, max_h) / 2.0
    content_bb = Rect(cx - total_r, cy - total_r, total_r * 2.0, total_r * 2.0)
    return builder.elements, warnings, content_bb
