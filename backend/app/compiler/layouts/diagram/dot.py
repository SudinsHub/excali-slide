"""Graphviz dot engine for flow and hierarchy diagrams.

Translates semantic nodes, groups, and edges into DOT format, runs Graphviz
dot -Tjson, extracts bounding boxes and node positions, flips the Y-axis to
screen coordinates, and centers the diagram inside the target region rect.
Draws straight bound arrows with collision avoidance for intermediate nodes,
rounded group containers, and edge label overlays.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from typing import Any

from app.compiler.layouts.diagram.rect import Rect, line_intersects_rect
from app.compiler.palette import DEFAULT_STROKE, DEFAULT_TEXT, style_for_emphasis
from app.compiler.skeleton import SkeletonBuilder, fit_node
from app.compiler.text_metrics import measure, wrap
from app.ir.schemas import DiagramBlock

logger = logging.getLogger("app.compiler.diagram.dot")


def layout_dot(
    block: DiagramBlock,
    region: Rect,
    font_size: float = 28.0,
    nodesep_px: float = 40.0,
    ranksep_px: float = 60.0,
) -> tuple[list[dict[str, Any]], list[str], Rect]:
    """Execute Graphviz dot layout and convert output to Excalidraw skeleton elements.

    Returns (elements, warnings, bounding_box).
    """
    if not shutil.which("dot"):
        raise RuntimeError(
            "Graphviz 'dot' binary is not installed or not in PATH. Please install graphviz."
        )

    # 1. Size nodes
    node_sizes: dict[str, tuple[float, float]] = {}
    for node in block.nodes:
        w, h = fit_node(node.label, node.sublabel, node.shape, font_size=font_size)
        node_sizes[node.id] = (w, h)

    # 2. Build DOT source
    direction = "TB" if block.kind == "hierarchy" else block.direction
    nodesep_inch = max(0.2, nodesep_px / 72.0)
    ranksep_inch = max(0.3, ranksep_px / 72.0)

    lines: list[str] = [
        "digraph G {",
        f'  rankdir="{direction}";',
        f"  nodesep={nodesep_inch:.3f};",
        f"  ranksep={ranksep_inch:.3f};",
        "  margin=0;",
        "  node [fixedsize=true];",
    ]

    # Group clusters (for flow diagrams)
    grouped_node_ids = set()
    if block.kind == "flow" and block.groups:
        for group in block.groups:
            g_nodes = group.node_ids or [n.id for n in block.nodes if n.group_id == group.id]
            if g_nodes:
                lines.append(f"  subgraph cluster_{group.id} {{")
                clean_label = group.label.replace('"', '\\"')
                lines.append(f'    label="{clean_label}";')
                for nid in g_nodes:
                    grouped_node_ids.add(nid)
                    w, h = node_sizes.get(nid, (160.0, 72.0))
                    lines.append(f'    "{nid}" [width={w / 72.0:.3f}, height={h / 72.0:.3f}];')
                lines.append("  }")

    # Top-level nodes not in any cluster
    for node in block.nodes:
        if node.id not in grouped_node_ids:
            w, h = node_sizes[node.id]
            lines.append(f'  "{node.id}" [width={w / 72.0:.3f}, height={h / 72.0:.3f}];')

    # Edges
    for edge in block.edges:
        lines.append(f'  "{edge.source}" -> "{edge.target}";')

    lines.append("}")
    dot_src = "\n".join(lines)

    # 3. Run dot -Tjson
    try:
        proc = subprocess.run(
            ["dot", "-Tjson"],
            input=dot_src.encode("utf-8"),
            capture_output=True,
            timeout=10.0,
            check=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Graphviz dot layout timed out after 10 seconds") from exc
    except subprocess.CalledProcessError as exc:
        stderr_msg = exc.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"Graphviz dot failed: {stderr_msg}") from exc

    data = json.loads(proc.stdout.decode("utf-8"))

    # 4. Parse bounding boxes and positions
    bb_parts = [float(p) for p in data.get("bb", "0,0,100,100").split(",")]
    llx, lly, urx, ury = bb_parts
    dot_w = urx - llx
    dot_h = ury - lly

    # Offset to center in region
    offset_x = region.x + max(0.0, (region.w - dot_w) / 2.0)
    offset_y = region.y + max(0.0, (region.h - dot_h) / 2.0)

    # Collect node positions
    node_positions: dict[str, tuple[float, float, float, float]] = {}
    cluster_boxes: list[dict[str, Any]] = []

    for obj in data.get("objects", []):
        name = obj.get("name", "")
        if "pos" in obj:
            # Node object
            pos_x, pos_y = [float(p) for p in obj["pos"].split(",")]
            # Flip Y
            cx = pos_x - llx
            cy = ury - pos_y
            nw, nh = node_sizes.get(name, (160.0, 72.0))
            nx = offset_x + cx - nw / 2.0
            ny = offset_y + cy - nh / 2.0
            node_positions[name] = (nx, ny, nw, nh)
        elif name.startswith("cluster_") and "bb" in obj:
            # Cluster subgraph
            c_llx, c_lly, c_urx, c_ury = [float(p) for p in obj["bb"].split(",")]
            cx = offset_x + (c_llx - llx)
            cy = offset_y + (ury - c_ury)
            cw = c_urx - c_llx
            ch = c_ury - c_lly
            gid = name.replace("cluster_", "")
            group_label = next((g.label for g in block.groups if g.id == gid), "Group")
            cluster_boxes.append(
                {"id": gid, "label": group_label, "x": cx, "y": cy, "w": cw, "h": ch}
            )

    # 5. Build elements via builder
    builder = SkeletonBuilder(width=1920, height=1080)
    warnings: list[str] = []

    # Cluster background rects first
    for cl in cluster_boxes:
        builder.shape(
            id=f"grp_{cl['id']}",
            shape_type="rounded",
            x=cl["x"] - 12.0,
            y=cl["y"] - 12.0,
            width=cl["w"] + 24.0,
            height=cl["h"] + 24.0,
            stroke_color="#adb5bd",
            background_color="#f8f9fa",
            fill_style="solid",
            stroke_style="dashed",
            stroke_width=2,
        )
        builder.text(
            id=f"grp_label_{cl['id']}",
            text=cl["label"],
            x=cl["x"],
            y=cl["y"] - 6.0,
            width=cl["w"],
            height=30.0,
            font_size=24.0,
            stroke_color="#495057",
        )

    # Nodes
    node_rects: dict[str, Rect] = {}
    for node in block.nodes:
        if node.id not in node_positions:
            continue
        nx, ny, nw, nh = node_positions[node.id]
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

    # Edges
    for idx, edge in enumerate(block.edges):
        if edge.source not in node_rects or edge.target not in node_rects:
            continue
        r_src = node_rects[edge.source]
        r_dst = node_rects[edge.target]

        p_src = (r_src.cx, r_src.cy)
        p_dst = (r_dst.cx, r_dst.cy)

        # Collision detection with other nodes
        collision = False
        collided_rects: list[Rect] = []
        for other_id, other_r in node_rects.items():
            if other_id not in (edge.source, edge.target):
                if line_intersects_rect(p_src, p_dst, other_r):
                    collision = True
                    collided_rects.append(other_r)

        arrow_id = f"e_{edge.source}_{edge.target}_{idx}"
        end_arrowhead = "arrow" if (edge.directed and block.kind != "hierarchy") else None

        if collision and collided_rects:
            # Route 3-point elbow around the obstruction
            top_y = min(cr.y for cr in collided_rects) - 30.0
            pts = [
                [0.0, 0.0],
                [round((r_dst.cx - r_src.cx) / 2.0, 1), round(top_y - r_src.cy, 1)],
                [round(r_dst.cx - r_src.cx, 1), round(r_dst.cy - r_src.cy, 1)],
            ]
            builder.arrow(
                id=arrow_id,
                x=r_src.cx,
                y=r_src.cy,
                width=r_dst.cx - r_src.cx,
                height=r_dst.cy - r_src.cy,
                start_id=f"n_{edge.source}",
                end_id=f"n_{edge.target}",
                points=pts,
                stroke_color=DEFAULT_STROKE,
                dashed=edge.dashed,
                end_arrowhead=end_arrowhead,
            )
        else:
            builder.arrow(
                id=arrow_id,
                x=r_src.cx,
                y=r_src.cy,
                width=r_dst.cx - r_src.cx,
                height=r_dst.cy - r_src.cy,
                start_id=f"n_{edge.source}",
                end_id=f"n_{edge.target}",
                stroke_color=DEFAULT_STROKE,
                dashed=edge.dashed,
                end_arrowhead=end_arrowhead,
            )

        # Edge label overlay
        if edge.label:
            mid_x = (r_src.cx + r_dst.cx) / 2.0
            mid_y = (r_src.cy + r_dst.cy) / 2.0

            # Check if reverse edge exists
            is_bidirectional = any(
                e.source == edge.target and e.target == edge.source for e in block.edges
            )
            if is_bidirectional:
                dx = r_dst.cx - r_src.cx
                dy = r_dst.cy - r_src.cy
                dist = max(1.0, (dx * dx + dy * dy) ** 0.5)
                sign = 1.0 if edge.source < edge.target else -1.0
                mid_x += (-dy / dist) * (36.0 * sign)
                mid_y += (dx / dist) * (36.0 * sign)

            lbl_w, lbl_h = measure(edge.label, 24.0)
            builder.shape(
                id=f"el_bg_{arrow_id}",
                shape_type="rounded",
                x=mid_x - lbl_w / 2.0 - 8.0,
                y=mid_y - lbl_h / 2.0 - 4.0,
                width=lbl_w + 16.0,
                height=lbl_h + 8.0,
                stroke_color="transparent",
                background_color="#ffffff",
                fill_style="solid",
            )
            builder.text(
                id=f"el_txt_{arrow_id}",
                text=edge.label,
                x=mid_x - lbl_w / 2.0,
                y=mid_y - lbl_h / 2.0,
                width=lbl_w,
                height=lbl_h,
                font_size=24.0,
                stroke_color=DEFAULT_TEXT,
                text_align="center",
            )

    content_bb = Rect(offset_x, offset_y, max(dot_w, 100.0), max(dot_h, 100.0))
    return builder.elements, warnings, content_bb
