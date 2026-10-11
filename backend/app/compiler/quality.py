"""Quality gate inspecting generated Excalidraw skeletons for presentation defects."""

from __future__ import annotations

from typing import Any, Literal, NamedTuple

from app.compiler.layouts.diagram.rect import Rect, line_intersects_rect
from app.compiler.text_metrics import measure
from app.ir.schemas import DiagramBlock, SlideIR


class QualityIssue(NamedTuple):
    code: str
    severity: Literal["error", "warning"]
    element_id: str | None
    message: str


def check_quality(
    skeleton: dict[str, Any],
    ir: SlideIR | None = None,
) -> list[QualityIssue]:
    """Perform rigorous automated visual quality and clearance checks on a skeleton."""
    issues: list[QualityIssue] = []
    elements = skeleton.get("elements", [])
    if not elements:
        return issues

    frame = elements[0]
    frame_w = frame.get("width", 1920.0)
    frame_h = frame.get("height", 1080.0)
    clearance = 40.0

    # Collect geometric entities
    rect_elements: list[dict[str, Any]] = []
    arrow_elements: list[dict[str, Any]] = []

    for el in elements[1:]:
        el_id = el.get("id", "")
        el_type = el.get("type", "")
        x = el.get("x", 0.0)
        y = el.get("y", 0.0)
        w = el.get("width", 0.0)
        h = el.get("height", 0.0)

        # (a) Clearance and frame boundary checks
        # Allow negative arrow coordinates if bound or starting from midpoint
        if el_type not in ("arrow", "line"):
            r_right = x + w
            r_bottom = y + h
            if x < 0.0 or y < 0.0 or r_right > frame_w or r_bottom > frame_h:
                issues.append(
                    QualityIssue(
                        code="element_outside_frame",
                        severity="error",
                        element_id=el_id,
                        message=f"Element '{el_id}' ({x:.0f},{y:.0f},{w:.0f},{h:.0f}) extends outside 1920x1080 frame",
                    )
                )
            elif x < clearance or y < clearance or r_right > frame_w - clearance or r_bottom > frame_h - clearance:
                issues.append(
                    QualityIssue(
                        code="clearance_violation",
                        severity="warning",
                        element_id=el_id,
                        message=f"Element '{el_id}' encroaches on {clearance:.0f}px frame clearance margin",
                    )
                )

        # (d) Minimum font size check
        font_size = el.get("fontSize")
        if font_size is not None and font_size < 24.0:
            issues.append(
                QualityIssue(
                    code="font_too_small",
                    severity="error",
                    element_id=el_id,
                    message=f"Element '{el_id}' font size {font_size} is below minimum allowed 24px",
                )
            )

        if "label" in el and isinstance(el["label"], dict):
            lbl_font = el["label"].get("fontSize")
            if lbl_font is not None and lbl_font < 24.0:
                issues.append(
                    QualityIssue(
                        code="font_too_small",
                        severity="error",
                        element_id=el_id,
                        message=f"Element '{el_id}' label font size {lbl_font} is below minimum allowed 24px",
                    )
                )

            # (e) Estimated container text overflow
            lbl_text = el["label"].get("text", "")
            if lbl_text:
                tw, th = measure(lbl_text, lbl_font or 28.0)
                if tw > w + 4.0 or th > h + 4.0:
                    issues.append(
                        QualityIssue(
                            code="container_text_overflow",
                            severity="error",
                            element_id=el_id,
                            message=f"Container '{el_id}' ({w:.0f}x{h:.0f}) overflows with text ({tw:.0f}x{th:.0f})",
                        )
                    )

        if el_type in ("rectangle", "ellipse", "diamond") and not el_id.startswith("grp_") and not el_id.startswith("el_bg_"):
            rect_elements.append(el)
        elif el_type == "text" and not el_id.startswith("grp_label_") and not el_id.startswith("el_txt_") and el_id != "quote_glyph":
            # Exclude labels inside shapes, headers, and decorative glyphs
            rect_elements.append(el)
        elif el_type == "arrow":
            arrow_elements.append(el)

    # (b) Overlap checks between nodes and standalone text blocks
    for i in range(len(rect_elements)):
        el1 = rect_elements[i]
        r1 = Rect(el1["x"], el1["y"], el1["width"], el1["height"])
        id1 = el1["id"]

        for j in range(i + 1, len(rect_elements)):
            el2 = rect_elements[j]
            id2 = el2["id"]
            # Ignore sublabels paired with their own node
            if id2 == f"sub_{id1.replace('n_', '')}" or id1 == f"sub_{id2.replace('n_', '')}":
                continue
            if id2 == f"lbl_{id1.replace('n_', '')}" or id1 == f"lbl_{id2.replace('n_', '')}":
                continue

            r2 = Rect(el2["x"], el2["y"], el2["width"], el2["height"])
            if r1.intersects(r2):
                issues.append(
                    QualityIssue(
                        code="elements_overlap",
                        severity="error",
                        element_id=f"{id1},{id2}",
                        message=f"Elements '{id1}' and '{id2}' overlap each other",
                    )
                )

    # (c) Arrow crossing through non-endpoint nodes
    node_rects = {
        el["id"]: Rect(el["x"], el["y"], el["width"], el["height"])
        for el in rect_elements
        if el.get("type") in ("rectangle", "ellipse", "diamond")
    }

    for arrow in arrow_elements:
        start_id = arrow.get("start", {}).get("id")
        end_id = arrow.get("end", {}).get("id")
        ax = arrow.get("x", 0.0)
        ay = arrow.get("y", 0.0)
        aw = arrow.get("width", 0.0)
        ah = arrow.get("height", 0.0)
        p1 = (ax, ay)
        p2 = (ax + aw, ay + ah)

        for nid, nr in node_rects.items():
            if nid not in (start_id, end_id):
                if line_intersects_rect(p1, p2, nr):
                    issues.append(
                        QualityIssue(
                            code="arrow_crosses_node",
                            severity="warning",
                            element_id=arrow["id"],
                            message=f"Arrow '{arrow['id']}' passes through non-endpoint node '{nid}'",
                        )
                    )

    # (f) Edge crossings count above 6
    crossings = 0
    for i in range(len(arrow_elements)):
        a1 = arrow_elements[i]
        p1_start = (a1["x"], a1["y"])
        p1_end = (a1["x"] + a1["width"], a1["y"] + a1["height"])

        for j in range(i + 1, len(arrow_elements)):
            a2 = arrow_elements[j]
            p2_start = (a2["x"], a2["y"])
            p2_end = (a2["x"] + a2["width"], a2["y"] + a2["height"])

            # Check if common endpoints
            if {a1.get("start", {}).get("id"), a1.get("end", {}).get("id")} & {
                a2.get("start", {}).get("id"),
                a2.get("end", {}).get("id"),
            }:
                continue

            # Standard 2D segment intersection check
            def ccw(A, B, C):
                return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

            def intersect(A, B, C, D):
                return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

            if intersect(p1_start, p1_end, p2_start, p2_end):
                crossings += 1

    if crossings > 6:
        issues.append(
            QualityIssue(
                code="excessive_edge_crossings",
                severity="warning",
                element_id=None,
                message=f"Diagram contains {crossings} edge crossings (warning threshold is 6)",
            )
        )

    # (g) Node label length > 40 chars
    if ir:
        for b in ir.blocks:
            if isinstance(b, DiagramBlock):
                for node in b.nodes:
                    if len(node.label) > 40:
                        issues.append(
                            QualityIssue(
                                code="label_length_warning",
                                severity="warning",
                                element_id=f"n_{node.id}",
                                message=f"Node '{node.id}' label length {len(node.label)} exceeds recommended 40 characters",
                            )
                        )

    return issues
