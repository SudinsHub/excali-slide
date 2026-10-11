"""Deterministic Excalidraw element skeleton builder and node sizing helpers."""

from __future__ import annotations

import math
from typing import Any

from app.compiler.text_metrics import measure, wrap


def fit_node(
    label: str,
    sublabel: str | None,
    shape: str = "rounded",
    font_size: float = 28.0,
) -> tuple[float, float]:
    """Calculate (width, height) bounding box for a node container.

    Horizontal padding: 28 px (56 px total).
    Vertical padding: 18 px (36 px total).
    Min size: 160x72 px.
    Diamonds multiply by 1.5, ellipses by 1.3.
    """
    wrapped_lines = wrap(label, font_size=font_size, max_width=240)
    label_text = "\n".join(wrapped_lines)
    lw, lh = measure(label_text, font_size)

    total_w = lw
    total_h = lh

    if sublabel:
        sub_lines = wrap(sublabel, font_size=24.0, max_width=240)
        sw, sh = measure("\n".join(sub_lines), 24.0)
        total_w = max(total_w, sw)
        total_h += sh + 8.0  # 8 px gap between label and sublabel

    w = max(160.0, total_w + 56.0)
    h = max(72.0, total_h + 36.0)

    if shape == "diamond":
        w *= 1.5
        h *= 1.5
    elif shape == "ellipse":
        w *= 1.3
        h *= 1.3

    return math.ceil(w), math.ceil(h)


class SkeletonBuilder:
    """Pure, deterministic builder for Excalidraw element skeletons.

    Guarantees deterministic element ordering, id collision detection,
    and frame child tracking. Never uses random IDs or seeds.
    """

    def __init__(self, width: int = 1920, height: int = 1080) -> None:
        self.width = width
        self.height = height
        self.elements: list[dict[str, Any]] = []
        self.top_level_ids: list[str] = []
        self.asset_ids: list[str] = []
        self._seen_ids: set[str] = set()

    def _register_id(self, el_id: str) -> None:
        if el_id in self._seen_ids:
            raise ValueError(f"Duplicate element id '{el_id}' in skeleton")
        self._seen_ids.add(el_id)
        self.top_level_ids.append(el_id)

    def text(
        self,
        id: str,
        text: str,
        x: float,
        y: float,
        width: float,
        height: float,
        font_size: float = 36,
        stroke_color: str = "#1e1e1e",
        text_align: str = "left",
        vertical_align: str = "top",
        group_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add a standalone text element."""
        self._register_id(id)
        el: dict[str, Any] = {
            "type": "text",
            "id": id,
            "x": round(x, 1),
            "y": round(y, 1),
            "width": round(width, 1),
            "height": round(height, 1),
            "fontSize": font_size,
            "fontFamily": 1,
            "text": text,
            "strokeColor": stroke_color,
            "textAlign": text_align,
            "verticalAlign": vertical_align,
        }
        if group_ids:
            el["groupIds"] = group_ids
        self.elements.append(el)
        return el

    def shape(
        self,
        id: str,
        shape_type: str,
        x: float,
        y: float,
        width: float,
        height: float,
        stroke_color: str = "#1e1e1e",
        background_color: str = "transparent",
        fill_style: str = "solid",
        label: str | None = None,
        font_size: float = 28,
        label_color: str = "#1e1e1e",
        stroke_style: str = "solid",
        stroke_width: int = 2,
        group_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add a geometric shape element (rectangle, ellipse, diamond)."""
        self._register_id(id)

        excali_type = "rectangle"
        roundness = None

        if shape_type == "rounded":
            excali_type = "rectangle"
            roundness = {"type": 3}
        elif shape_type == "rect":
            excali_type = "rectangle"
        elif shape_type == "ellipse":
            excali_type = "ellipse"
        elif shape_type == "diamond":
            excali_type = "diamond"
        elif shape_type == "text":
            # For 'text' shape with background
            excali_type = "rectangle"
            stroke_color = "transparent"

        el: dict[str, Any] = {
            "type": excali_type,
            "id": id,
            "x": round(x, 1),
            "y": round(y, 1),
            "width": round(width, 1),
            "height": round(height, 1),
            "strokeColor": stroke_color,
            "backgroundColor": background_color,
            "fillStyle": fill_style,
            "strokeStyle": stroke_style,
            "strokeWidth": stroke_width,
        }
        if roundness:
            el["roundness"] = roundness
        if group_ids:
            el["groupIds"] = group_ids

        if label:
            el["label"] = {
                "text": label,
                "fontSize": font_size,
                "strokeColor": label_color,
            }

        self.elements.append(el)
        return el

    def arrow(
        self,
        id: str,
        x: float,
        y: float,
        width: float,
        height: float,
        start_id: str | None = None,
        end_id: str | None = None,
        points: list[list[float]] | None = None,
        stroke_color: str = "#1e1e1e",
        dashed: bool = False,
        start_arrowhead: str | None = None,
        end_arrowhead: str | None = "arrow",
    ) -> dict[str, Any]:
        """Add a bound or multi-point arrow."""
        self._register_id(id)
        el: dict[str, Any] = {
            "type": "arrow",
            "id": id,
            "x": round(x, 1),
            "y": round(y, 1),
            "width": round(width, 1),
            "height": round(height, 1),
            "strokeColor": stroke_color,
            "strokeStyle": "dashed" if dashed else "solid",
        }
        if start_id:
            el["start"] = {"id": start_id}
        if end_id:
            el["end"] = {"id": end_id}
        if points:
            el["points"] = points
        else:
            el["points"] = [[0, 0], [round(width, 1), round(height, 1)]]
        if start_arrowhead:
            el["startArrowhead"] = start_arrowhead
        if end_arrowhead:
            el["endArrowhead"] = end_arrowhead

        self.elements.append(el)
        return el

    def line(
        self,
        id: str,
        x: float,
        y: float,
        width: float,
        height: float,
        points: list[list[float]],
        stroke_color: str = "#1e1e1e",
        stroke_width: int = 2,
    ) -> dict[str, Any]:
        """Add a decorative or connecting line."""
        self._register_id(id)
        el: dict[str, Any] = {
            "type": "line",
            "id": id,
            "x": round(x, 1),
            "y": round(y, 1),
            "width": round(width, 1),
            "height": round(height, 1),
            "strokeColor": stroke_color,
            "strokeWidth": stroke_width,
            "points": points,
        }
        self.elements.append(el)
        return el

    def image(
        self,
        id: str,
        file_id: str,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> dict[str, Any]:
        """Add an image element referencing an asset."""
        self._register_id(id)
        el: dict[str, Any] = {
            "type": "image",
            "id": id,
            "fileId": file_id,
            "x": round(x, 1),
            "y": round(y, 1),
            "width": round(width, 1),
            "height": round(height, 1),
        }
        if file_id not in self.asset_ids:
            self.asset_ids.append(file_id)
        self.elements.append(el)
        return el

    def build(self, frame_name: str = "") -> dict[str, Any]:
        """Assemble the complete skeleton JSON with frame element as first item."""
        frame_el = {
            "type": "frame",
            "id": "slide-frame",
            "name": frame_name,
            "x": 0,
            "y": 0,
            "width": self.width,
            "height": self.height,
            "children": list(self.top_level_ids),
        }

        return {
            "version": 1,
            "frame": {
                "width": self.width,
                "height": self.height,
            },
            "elements": [frame_el, *self.elements],
            "asset_ids": self.asset_ids,
        }
