"""Geometry primitives for layout boxes and collision math."""

from __future__ import annotations

from typing import NamedTuple


class Rect(NamedTuple):
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0

    def intersects(self, other: Rect) -> bool:
        """Check if two rectangles overlap with strict interior intersection."""
        return not (
            self.right <= other.x
            or other.right <= self.x
            or self.bottom <= other.y
            or other.bottom <= self.y
        )

    def contains(self, other: Rect, margin: float = 0.0) -> bool:
        """Check if this rectangle completely encloses another with optional margin."""
        return (
            other.x >= self.x + margin
            and other.y >= self.y + margin
            and other.right <= self.right - margin
            and other.bottom <= self.bottom - margin
        )


def line_intersects_rect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    rect: Rect,
) -> bool:
    """Check if the line segment (p1, p2) intersects the interior of a rectangle.

    Uses Liang-Barsky parametric line clipping.
    """
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1

    p = [-dx, dx, -dy, dy]
    q = [x1 - rect.x, rect.right - x1, y1 - rect.y, rect.bottom - y1]

    u1 = 0.0
    u2 = 1.0

    for pi, qi in zip(p, q, strict=False):
        if pi == 0:
            if qi < 0:
                return False
        else:
            t = qi / pi
            if pi < 0:
                if t > u2:
                    return False
                if t > u1:
                    u1 = t
            else:
                if t < u1:
                    return False
                if t < u2:
                    u2 = t

    return u1 < u2
