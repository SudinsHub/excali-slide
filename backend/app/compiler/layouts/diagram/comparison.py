"""Comparison diagram layout: multi-column group comparison cards.

Partitions the content region into 2 to 3 equal-width columns. Each column
features a prominent header rectangle rendered with thematic emphasis colors
(accent for group 1, primary for group 2, positive for group 3) and vertically
stacked rounded rectangles for each of its member nodes.
"""

from __future__ import annotations

from typing import Any

from app.compiler.layouts.diagram.rect import Rect
from app.compiler.palette import PALETTE, style_for_emphasis
from app.compiler.skeleton import SkeletonBuilder, fit_node
from app.compiler.text_metrics import wrap
from app.ir.schemas import DiagramBlock

GROUP_HEADER_THEMES = [
    PALETTE["accent"],
    PALETTE["primary"],
    PALETTE["positive"],
]


def layout_comparison(
    block: DiagramBlock,
    region: Rect,
    font_size: float = 28.0,
) -> tuple[list[dict[str, Any]], list[str], Rect]:
    """Render 2-3 column comparative cards with group headers and node stacks.

    Returns (elements, warnings, bounding_box).
    """
    builder = SkeletonBuilder(width=1920, height=1080)
    warnings: list[str] = []

    groups = block.groups
    num_cols = len(groups)
    if num_cols == 0:
        return [], warnings, region

    gap = 40.0
    col_w = (region.w - (num_cols - 1) * gap) / num_cols
    header_h = 64.0

    # Group nodes by group_id
    nodes_by_group: dict[str, list[Any]] = {g.id: [] for g in groups}
    for node in block.nodes:
        if node.group_id and node.group_id in nodes_by_group:
            nodes_by_group[node.group_id].append(node)

    # Calculate uniform node card height based on maximum content
    max_card_h = 76.0
    for node in block.nodes:
        _, nh = fit_node(node.label, node.sublabel, "rounded", font_size=font_size)
        max_card_h = max(max_card_h, nh)

    max_nodes_in_col = max((len(nodes) for nodes in nodes_by_group.values()), default=1)
    card_gap = 16.0
    total_col_h = (
        header_h + 20.0 + max_nodes_in_col * max_card_h + max(0, max_nodes_in_col - 1) * card_gap
    )

    start_y = region.y + max(0.0, (region.h - total_col_h) / 2.0)

    for g_idx, group in enumerate(groups):
        col_x = region.x + g_idx * (col_w + gap)
        theme = GROUP_HEADER_THEMES[g_idx % len(GROUP_HEADER_THEMES)]

        # 1. Header rect
        builder.shape(
            id=f"grp_hdr_{group.id}",
            shape_type="rounded",
            x=col_x,
            y=start_y,
            width=col_w,
            height=header_h,
            stroke_color=theme.stroke,
            background_color=theme.fill,
            fill_style="solid",
            label=group.label,
            font_size=28.0,
            label_color=theme.stroke,
            stroke_width=3,
        )

        # 2. Stacked node cards
        g_nodes = nodes_by_group[group.id]
        curr_y = start_y + header_h + 20.0
        for node in g_nodes:
            colors = style_for_emphasis(node.emphasis)
            wrapped_label = "\n".join(wrap(node.label, font_size=font_size, max_width=col_w - 56.0))
            label_text = wrapped_label
            if node.sublabel:
                wrapped_sub = "\n".join(wrap(node.sublabel, font_size=22.0, max_width=col_w - 56.0))
                label_text = f"{wrapped_label}\n{wrapped_sub}"

            builder.shape(
                id=f"n_{node.id}",
                shape_type=node.shape,
                x=col_x,
                y=curr_y,
                width=col_w,
                height=max_card_h,
                stroke_color=colors.stroke,
                background_color=colors.fill,
                fill_style=colors.fill_style,
                label=label_text,
                font_size=font_size,
                label_color=colors.text,
                group_ids=[f"g_{node.id}"] if node.sublabel else None,
            )
            curr_y += max_card_h + card_gap

    content_bb = Rect(region.x, start_y, region.w, total_col_h)
    return builder.elements, warnings, content_bb
