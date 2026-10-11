"""Mindmap diagram layout: radial tree with proportional angle sectors.

Centers a prominent root ellipse in the region and partitions 360 degrees of
angular sectors proportionally among primary subtrees based on leaf counts.
Level 1 child nodes occupy sector midpoints at radius R1, while level 2
grandchildren distribute within their parent's sector at radius R2, connected
by bound lines without arrowheads.
"""

from __future__ import annotations

import math
from typing import Any

from app.compiler.layouts.diagram.rect import Rect
from app.compiler.palette import DEFAULT_STROKE, style_for_emphasis
from app.compiler.skeleton import SkeletonBuilder, fit_node
from app.compiler.text_metrics import wrap
from app.ir.schemas import DiagramBlock


def layout_mindmap(
    block: DiagramBlock,
    region: Rect,
    font_size: float = 28.0,
) -> tuple[list[dict[str, Any]], list[str], Rect]:
    """Render radial mindmap centered in region with proportional sector allocation.

    Returns (elements, warnings, bounding_box).
    """
    builder = SkeletonBuilder(width=1920, height=1080)
    warnings: list[str] = []

    if not block.nodes:
        return [], warnings, region

    # 1. Identify root and adjacency
    node_map = {n.id: n for n in block.nodes}
    in_degree: dict[str, int] = {n.id: 0 for n in block.nodes}
    children_map: dict[str, list[str]] = {n.id: [] for n in block.nodes}

    for edge in block.edges:
        if edge.target in in_degree:
            in_degree[edge.target] += 1
        if edge.source in children_map:
            children_map[edge.source].append(edge.target)

    roots = [nid for nid, deg in in_degree.items() if deg == 0]
    root_id = roots[0] if roots else block.nodes[0].id
    root_node = node_map[root_id]

    # Count leaves for proportional sector allocation
    def count_leaves(nid: str) -> int:
        ch = children_map.get(nid, [])
        return sum(count_leaves(c) for c in ch) if ch else 1

    level1_ids = children_map.get(root_id, [])
    l1_leaves = [count_leaves(c) for c in level1_ids]
    total_leaves = max(1, sum(l1_leaves))

    cx = region.cx
    cy = region.cy

    rx1 = min(360.0, region.w * 0.22)
    ry1 = min(180.0, region.h * 0.24)
    rx2 = min(660.0, region.w * 0.40)
    ry2 = min(310.0, region.h * 0.41)

    # 2. Place root node at center
    rw, rh = fit_node(root_node.label, root_node.sublabel, "ellipse", font_size=font_size)
    root_colors = style_for_emphasis(root_node.emphasis)
    builder.shape(
        id=f"n_{root_node.id}",
        shape_type="ellipse",
        x=cx - rw / 2.0,
        y=cy - rh / 2.0,
        width=rw,
        height=rh,
        stroke_color=root_colors.stroke,
        background_color=root_colors.fill if root_colors.fill != "transparent" else "#ffffff",
        fill_style="solid",
        label=root_node.label,
        font_size=font_size,
        label_color=root_colors.text,
        stroke_width=3,
    )

    # 3. Distribute level 1 and level 2 nodes into angular sectors
    current_angle = -math.pi
    for l1_id, leaves in zip(level1_ids, l1_leaves, strict=False):
        sector_span = (leaves / total_leaves) * 2.0 * math.pi
        l1_angle = current_angle + sector_span / 2.0

        # Position L1 node
        l1_node = node_map[l1_id]
        nw, nh = fit_node(l1_node.label, l1_node.sublabel, l1_node.shape, font_size=font_size)
        nx = cx + rx1 * math.cos(l1_angle) - nw / 2.0
        ny = cy + ry1 * math.sin(l1_angle) - nh / 2.0
        colors = style_for_emphasis(l1_node.emphasis)

        wrapped_l1 = "\n".join(wrap(l1_node.label, font_size=font_size, max_width=nw - 56.0))
        builder.shape(
            id=f"n_{l1_node.id}",
            shape_type=l1_node.shape,
            x=nx,
            y=ny,
            width=nw,
            height=nh,
            stroke_color=colors.stroke,
            background_color=colors.fill,
            fill_style=colors.fill_style,
            label=wrapped_l1,
            font_size=font_size,
            label_color=colors.text,
        )

        # Edge root -> L1
        builder.arrow(
            id=f"e_{root_id}_{l1_id}",
            x=cx,
            y=cy,
            width=nx + nw / 2.0 - cx,
            height=ny + nh / 2.0 - cy,
            start_id=f"n_{root_id}",
            end_id=f"n_{l1_id}",
            stroke_color=DEFAULT_STROKE,
            end_arrowhead=None,
        )

        # Position grandchildren (L2) within the sector
        l2_ids = children_map.get(l1_id, [])
        if l2_ids:
            l2_step = sector_span / len(l2_ids)
            for g_idx, l2_id in enumerate(l2_ids):
                l2_angle = current_angle + (g_idx + 0.5) * l2_step
                l2_node = node_map[l2_id]
                gw, gh = fit_node(l2_node.label, l2_node.sublabel, l2_node.shape, font_size=24.0)
                gx = cx + rx2 * math.cos(l2_angle) - gw / 2.0
                gy = cy + ry2 * math.sin(l2_angle) - gh / 2.0
                g_colors = style_for_emphasis(l2_node.emphasis)

                wrapped_l2 = "\n".join(wrap(l2_node.label, font_size=24.0, max_width=gw - 40.0))
                builder.shape(
                    id=f"n_{l2_node.id}",
                    shape_type=l2_node.shape,
                    x=gx,
                    y=gy,
                    width=gw,
                    height=gh,
                    stroke_color=g_colors.stroke,
                    background_color=g_colors.fill,
                    fill_style=g_colors.fill_style,
                    label=wrapped_l2,
                    font_size=24.0,
                    label_color=g_colors.text,
                )

                # Edge L1 -> L2
                builder.arrow(
                    id=f"e_{l1_id}_{l2_id}",
                    x=nx + nw / 2.0,
                    y=ny + nh / 2.0,
                    width=gx + gw / 2.0 - (nx + nw / 2.0),
                    height=gy + gh / 2.0 - (ny + nh / 2.0),
                    start_id=f"n_{l1_id}",
                    end_id=f"n_{l2_id}",
                    stroke_color=DEFAULT_STROKE,
                    end_arrowhead=None,
                )

        current_angle += sector_span

    if builder.elements:
        min_x = min(el["x"] for el in builder.elements)
        min_y = min(el["y"] for el in builder.elements)
        max_x = max(el["x"] + el["width"] for el in builder.elements)
        max_y = max(el["y"] + el["height"] for el in builder.elements)
        content_bb = Rect(min_x, min_y, max_x - min_x, max_y - min_y)
    else:
        content_bb = region
    return builder.elements, warnings, content_bb
