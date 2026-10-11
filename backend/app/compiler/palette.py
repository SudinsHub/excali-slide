"""Palette definitions mapping emphasis levels to Excalidraw colors per SPEC §7."""

from __future__ import annotations

from typing import NamedTuple

from app.ir.schemas import Emphasis


class ColorStyle(NamedTuple):
    stroke: str
    fill: str
    text: str
    fill_style: str = "solid"


PALETTE: dict[Emphasis, ColorStyle] = {
    "normal": ColorStyle(
        stroke="#1e1e1e",
        fill="transparent",
        text="#1e1e1e",
        fill_style="solid",
    ),
    "primary": ColorStyle(
        stroke="#1971c2",
        fill="#a5d8ff",
        text="#1971c2",
        fill_style="solid",
    ),
    "accent": ColorStyle(
        stroke="#f08c00",
        fill="#ffec99",
        text="#f08c00",
        fill_style="solid",
    ),
    "positive": ColorStyle(
        stroke="#2f9e44",
        fill="#b2f2bb",
        text="#2f9e44",
        fill_style="solid",
    ),
    "negative": ColorStyle(
        stroke="#e03131",
        fill="#ffc9c9",
        text="#e03131",
        fill_style="solid",
    ),
    "muted": ColorStyle(
        stroke="#868e96",
        fill="#f1f3f5",
        text="#495057",
        fill_style="solid",
    ),
}

DEFAULT_STROKE = "#1e1e1e"
DEFAULT_TEXT = "#1e1e1e"
MUTED_TEXT = "#868e96"


def style_for_emphasis(emphasis: Emphasis) -> ColorStyle:
    """Return stroke, fill, text colors and fillStyle for an emphasis level."""
    return PALETTE.get(emphasis, PALETTE["normal"])
