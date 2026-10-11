"""Cross-field validation for SlideIR yielding repair-ready actionable issues."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

from app.compiler.text_metrics import wrap
from app.ir.budgets import Budgets
from app.ir.schemas import (
    DiagramBlock,
    ImageBlock,
    SlideIR,
    TextBlock,
)

NODE_ID_REGEX = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


class IRIssue(BaseModel):
    code: str
    path: str
    message: str
    severity: Literal["error", "warning"] = "error"


def validate_ir(ir: SlideIR, budgets: Budgets | None = None) -> list[IRIssue]:
    """Validate SlideIR against layout, block, and diagram constraints.

    Returns a list of IRIssue items suitable for LLM prompt repair loops.
    """
    issues: list[IRIssue] = []

    # 1. Title and Subtitle checks per layout
    if ir.title:
        if len(ir.title) > 70:
            issues.append(
                IRIssue(
                    code="title_too_long",
                    path="title",
                    message=f"title exceeds maximum 70 characters (got {len(ir.title)})",
                )
            )

    if ir.layout in ("cover", "closing"):
        if not ir.title:
            issues.append(
                IRIssue(
                    code="missing_title",
                    path="title",
                    message=f"{ir.layout} layout requires a non-empty title",
                )
            )
        if not ir.subtitle:
            issues.append(
                IRIssue(
                    code="missing_subtitle",
                    path="subtitle",
                    message=f"{ir.layout} layout requires a non-empty subtitle",
                )
            )
    elif ir.layout == "statement":
        # Statement: title is optional
        pass
    else:
        # section, text, diagram, split, two_column, image_text: title required
        if not ir.title:
            issues.append(
                IRIssue(
                    code="missing_title",
                    path="title",
                    message=f"{ir.layout} layout requires a non-empty title",
                )
            )

    # 2. Block layout rules
    text_blocks = [b for b in ir.blocks if isinstance(b, TextBlock)]
    diagram_blocks = [b for b in ir.blocks if isinstance(b, DiagramBlock)]
    image_blocks = [b for b in ir.blocks if isinstance(b, ImageBlock)]
    total_blocks = len(ir.blocks)

    if ir.layout == "cover":
        if total_blocks > 0:
            issues.append(
                IRIssue(
                    code="invalid_blocks",
                    path="blocks",
                    message=f"cover layout must not contain blocks, got {total_blocks}",
                )
            )
    elif ir.layout == "closing":
        if total_blocks > 1 or (total_blocks == 1 and not text_blocks):
            issues.append(
                IRIssue(
                    code="invalid_blocks",
                    path="blocks",
                    message="closing layout allows at most 1 optional text block",
                )
            )
        elif len(text_blocks) == 1:
            tb = text_blocks[0]
            if len(tb.items) > 3:
                issues.append(
                    IRIssue(
                        code="too_many_bullets",
                        path="blocks[0].items",
                        message=f"closing layout allows at most 3 bullets, got {len(tb.items)}",
                    )
                )
    elif ir.layout == "section":
        if total_blocks > 0:
            issues.append(
                IRIssue(
                    code="invalid_blocks",
                    path="blocks",
                    message=f"section layout must not contain blocks, got {total_blocks}",
                )
            )
    elif ir.layout == "statement":
        if total_blocks != 1 or len(text_blocks) != 1:
            issues.append(
                IRIssue(
                    code="invalid_blocks",
                    path="blocks",
                    message=f"statement layout requires exactly 1 text block, got {total_blocks}",
                )
            )
        else:
            tb = text_blocks[0]
            if tb.style not in ("paragraph", "quote"):
                issues.append(
                    IRIssue(
                        code="invalid_text_style",
                        path="blocks[0].style",
                        message=f"statement layout text block style must be 'paragraph' or 'quote', got '{tb.style}'",
                    )
                )
            if len(tb.items) != 1:
                issues.append(
                    IRIssue(
                        code="statement_item_count",
                        path="blocks[0].items",
                        message=f"statement layout text block must have exactly 1 item, got {len(tb.items)}",
                    )
                )
    elif ir.layout == "text":
        if len(text_blocks) < 1 or total_blocks != len(text_blocks):
            issues.append(
                IRIssue(
                    code="invalid_blocks",
                    path="blocks",
                    message=f"text layout requires at least 1 text block and no other block types, got {total_blocks} blocks",
                )
            )
    elif ir.layout == "diagram":
        if total_blocks != 1 or len(diagram_blocks) != 1:
            issues.append(
                IRIssue(
                    code="invalid_blocks",
                    path="blocks",
                    message=f"diagram layout requires exactly 1 diagram block, got {total_blocks}",
                )
            )
    elif ir.layout == "split":
        if total_blocks != 2 or len(text_blocks) != 1 or len(diagram_blocks) != 1:
            issues.append(
                IRIssue(
                    code="invalid_blocks",
                    path="blocks",
                    message="split layout requires exactly 1 text block and 1 diagram block",
                )
            )
        if ir.text_side not in ("left", "right"):
            issues.append(
                IRIssue(
                    code="missing_side_config",
                    path="text_side",
                    message="split layout requires text_side to be 'left' or 'right'",
                )
            )
    elif ir.layout == "two_column":
        if total_blocks != 2 or len(text_blocks) != 2:
            issues.append(
                IRIssue(
                    code="invalid_blocks",
                    path="blocks",
                    message=f"two_column layout requires exactly 2 text blocks, got {total_blocks}",
                )
            )
        else:
            for idx, tb in enumerate(text_blocks):
                if not tb.heading:
                    issues.append(
                        IRIssue(
                            code="missing_column_heading",
                            path=f"blocks[{idx}].heading",
                            message=f"two_column layout text block {idx} requires a heading",
                        )
                    )
    elif ir.layout == "image_text":
        if total_blocks != 2 or len(image_blocks) != 1 or len(text_blocks) != 1:
            issues.append(
                IRIssue(
                    code="invalid_blocks",
                    path="blocks",
                    message="image_text layout requires exactly 1 image block and 1 text block",
                )
            )
        if ir.image_side not in ("left", "right"):
            issues.append(
                IRIssue(
                    code="missing_side_config",
                    path="image_side",
                    message="image_text layout requires image_side to be 'left' or 'right'",
                )
            )

    # 3. Text block validation & Budgets
    for b_idx, block in enumerate(ir.blocks):
        if isinstance(block, TextBlock):
            if block.style in ("bullets", "numbered"):
                if len(block.items) > 6:
                    issues.append(
                        IRIssue(
                            code="bullets_hard_cap",
                            path=f"blocks[{b_idx}].items",
                            message=f"bullets exceeds hard cap of 6 (got {len(block.items)})",
                        )
                    )
                elif budgets and len(block.items) > budgets.bullets:
                    issues.append(
                        IRIssue(
                            code="budget_bullets_exceeded",
                            path=f"blocks[{b_idx}].items",
                            message=f"bullets count {len(block.items)} exceeds budget of {budgets.bullets}",
                            severity="warning",
                        )
                    )

            for i_idx, item in enumerate(block.items):
                if len(item) > 140:
                    issues.append(
                        IRIssue(
                            code="bullet_too_long",
                            path=f"blocks[{b_idx}].items[{i_idx}]",
                            message=f"bullet exceeds maximum 140 characters (got {len(item)})",
                        )
                    )
                if budgets:
                    words = len(item.split())
                    if words > budgets.words_per_bullet:
                        issues.append(
                            IRIssue(
                                code="budget_words_exceeded",
                                path=f"blocks[{b_idx}].items[{i_idx}]",
                                message=f"bullet word count {words} exceeds budget of {budgets.words_per_bullet}",
                                severity="warning",
                            )
                        )

    # 4. Diagram block validation
    for b_idx, block in enumerate(ir.blocks):
        if isinstance(block, DiagramBlock):
            b_path = f"blocks[{b_idx}]"
            node_ids = set()
            nodes_by_id = {}

            # Hard cap on nodes
            if len(block.nodes) > 16:
                issues.append(
                    IRIssue(
                        code="nodes_hard_cap",
                        path=f"{b_path}.nodes",
                        message=f"nodes count {len(block.nodes)} exceeds hard cap of 16",
                    )
                )
            elif budgets and len(block.nodes) > budgets.max_nodes:
                issues.append(
                    IRIssue(
                        code="budget_nodes_exceeded",
                        path=f"{b_path}.nodes",
                        message=f"node count {len(block.nodes)} exceeds budget of {budgets.max_nodes}",
                        severity="warning",
                    )
                )

            # Node ID uniqueness & format & labels
            for n_idx, node in enumerate(block.nodes):
                n_path = f"{b_path}.nodes[{n_idx}]"
                if not NODE_ID_REGEX.match(node.id):
                    issues.append(
                        IRIssue(
                            code="invalid_node_id_format",
                            path=f"{n_path}.id",
                            message=f"node id '{node.id}' must match regex ^[a-z][a-z0-9_]{{0,31}}$",
                        )
                    )
                if node.id in node_ids:
                    issues.append(
                        IRIssue(
                            code="duplicate_node_id",
                            path=f"{n_path}.id",
                            message=f"duplicate node id '{node.id}' found",
                        )
                    )
                node_ids.add(node.id)
                nodes_by_id[node.id] = node

                if len(node.label) > 60:
                    issues.append(
                        IRIssue(
                            code="node_label_too_long",
                            path=f"{n_path}.label",
                            message=f"node '{node.id}' label exceeds 60 characters (got {len(node.label)})",
                        )
                    )
                # Check wrapped lines (label wrapped at ~260px at font 28)
                wrapped_label = wrap(node.label, font_size=28, max_width=260)
                if len(wrapped_label) > 3:
                    issues.append(
                        IRIssue(
                            code="node_label_too_many_lines",
                            path=f"{n_path}.label",
                            message=f"node '{node.id}' label wraps to {len(wrapped_label)} lines, max allowed is 3",
                        )
                    )

                if node.sublabel and len(node.sublabel) > 40:
                    issues.append(
                        IRIssue(
                            code="node_sublabel_too_long",
                            path=f"{n_path}.sublabel",
                            message=f"node '{node.id}' sublabel exceeds 40 characters (got {len(node.sublabel)})",
                        )
                    )

            # Edges validation
            for e_idx, edge in enumerate(block.edges):
                e_path = f"{b_path}.edges[{e_idx}]"
                if edge.source not in node_ids:
                    issues.append(
                        IRIssue(
                            code="edge_invalid_source",
                            path=f"{e_path}.source",
                            message=f"edge source '{edge.source}' does not exist in nodes",
                        )
                    )
                if edge.target not in node_ids:
                    issues.append(
                        IRIssue(
                            code="edge_invalid_target",
                            path=f"{e_path}.target",
                            message=f"edge target '{edge.target}' does not exist in nodes",
                        )
                    )
                if edge.source == edge.target:
                    issues.append(
                        IRIssue(
                            code="self_loop_forbidden",
                            path=e_path,
                            message=f"self-loop on node '{edge.source}' is forbidden",
                        )
                    )
                if edge.label and len(edge.label) > 30:
                    issues.append(
                        IRIssue(
                            code="edge_label_too_long",
                            path=f"{e_path}.label",
                            message=f"edge label exceeds 30 characters (got {len(edge.label)})",
                        )
                    )

            # Per-kind rules
            node_count = len(block.nodes)
            kind = block.kind

            if kind == "cycle":
                if not (3 <= node_count <= 8):
                    issues.append(
                        IRIssue(
                            code="invalid_node_count_cycle",
                            path=f"{b_path}.nodes",
                            message=f"cycle diagrams need 3-8 nodes, got {node_count}",
                        )
                    )
            elif kind == "timeline":
                if not (3 <= node_count <= 7):
                    issues.append(
                        IRIssue(
                            code="invalid_node_count_timeline",
                            path=f"{b_path}.nodes",
                            message=f"timeline diagrams need 3-7 nodes, got {node_count}",
                        )
                    )
            elif kind == "comparison":
                if not (2 <= len(block.groups) <= 3):
                    issues.append(
                        IRIssue(
                            code="invalid_group_count_comparison",
                            path=f"{b_path}.groups",
                            message=f"comparison diagrams need 2-3 groups, got {len(block.groups)}",
                        )
                    )
                group_ids = {g.id for g in block.groups}
                # Check that all nodes belong to a valid group
                nodes_in_groups = {g.id: 0 for g in block.groups}
                for n_idx, node in enumerate(block.nodes):
                    if not node.group_id or node.group_id not in group_ids:
                        issues.append(
                            IRIssue(
                                code="node_missing_group",
                                path=f"{b_path}.nodes[{n_idx}].group_id",
                                message=f"comparison node '{node.id}' must have a valid group_id",
                            )
                        )
                    else:
                        nodes_in_groups[node.group_id] += 1
                for gid, count in nodes_in_groups.items():
                    if count < 1:
                        issues.append(
                            IRIssue(
                                code="empty_group_comparison",
                                path=f"{b_path}.groups",
                                message=f"comparison group '{gid}' must contain at least 1 node",
                            )
                        )
            elif kind == "flow":
                if not (1 <= node_count <= 16):
                    issues.append(
                        IRIssue(
                            code="invalid_node_count_flow",
                            path=f"{b_path}.nodes",
                            message=f"flow diagrams need 1-16 nodes, got {node_count}",
                        )
                    )
            elif kind in ("hierarchy", "mindmap"):
                # Hierarchy & mindmap must be trees with exactly 1 root
                if node_count < 2:
                    issues.append(
                        IRIssue(
                            code="invalid_tree_size",
                            path=f"{b_path}.nodes",
                            message=f"{kind} diagrams need at least 2 nodes, got {node_count}",
                        )
                    )
                else:
                    # In-degrees check
                    in_degree: dict[str, int] = dict.fromkeys(node_ids, 0)
                    children_map: dict[str, list[str]] = {nid: [] for nid in node_ids}
                    for edge in block.edges:
                        if edge.target in in_degree:
                            in_degree[edge.target] += 1
                        if edge.source in children_map:
                            children_map[edge.source].append(edge.target)

                    roots = [nid for nid, deg in in_degree.items() if deg == 0]
                    if len(roots) != 1:
                        issues.append(
                            IRIssue(
                                code="tree_single_root_violation",
                                path=f"{b_path}.edges",
                                message=f"{kind} diagrams must be a tree with exactly one root, found {len(roots)} roots: {roots}",
                            )
                        )
                    elif any(deg > 1 for deg in in_degree.values()):
                        multi_parents = [nid for nid, deg in in_degree.items() if deg > 1]
                        issues.append(
                            IRIssue(
                                code="tree_multiple_parents",
                                path=f"{b_path}.edges",
                                message=f"{kind} tree nodes cannot have multiple parents, found: {multi_parents}",
                            )
                        )
                    else:
                        root = roots[0]
                        # Check reachability and cycles via BFS/DFS
                        visited = set()
                        queue = [(root, 0)]
                        max_depth = 0
                        has_cycle = False

                        while queue:
                            curr, depth = queue.pop(0)
                            if curr in visited:
                                has_cycle = True
                                break
                            visited.add(curr)
                            if depth > max_depth:
                                max_depth = depth
                            for child in children_map.get(curr, []):
                                queue.append((child, depth + 1))

                        if has_cycle or len(visited) != len(node_ids):
                            issues.append(
                                IRIssue(
                                    code="tree_cycle_or_disconnected",
                                    path=f"{b_path}.edges",
                                    message=f"{kind} diagram must be a fully connected acyclic tree",
                                )
                            )
                        elif kind == "mindmap" and max_depth > 2:
                            issues.append(
                                IRIssue(
                                    code="mindmap_depth_exceeded",
                                    path=f"{b_path}.nodes",
                                    message=f"mindmap diagrams cap depth at 2 (root + 2 levels), got depth {max_depth}",
                                )
                            )

    return issues
