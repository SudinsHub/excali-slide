"""Budget definitions and helpers per SPEC §6.1."""

from __future__ import annotations

from typing import NamedTuple

from app.schemas.deck import DeckSettings


class Budgets(NamedTuple):
    max_nodes: int
    bullets: int
    words_per_bullet: int
    diagram_share: float


# Constants for density levels
BUDGET_LIGHT = Budgets(max_nodes=8, bullets=3, words_per_bullet=8, diagram_share=0.25)
BUDGET_STANDARD = Budgets(max_nodes=12, bullets=4, words_per_bullet=12, diagram_share=0.50)
BUDGET_DENSE = Budgets(max_nodes=16, bullets=6, words_per_bullet=16, diagram_share=0.75)

DIAGRAM_SHARE_MAP = {
    "low": 0.25,
    "medium": 0.50,
    "high": 0.75,
}

DENSITY_MAP = {
    "light": (8, 3, 8),
    "standard": (12, 4, 12),
    "dense": (16, 6, 16),
}


def budgets_for(settings: DeckSettings | None = None) -> Budgets:
    """Compute budgets based on deck settings density and diagram_intensity."""
    if settings is None:
        return BUDGET_STANDARD

    density = settings.density
    intensity = settings.diagram_intensity

    max_nodes, bullets, words_per_bullet = DENSITY_MAP.get(
        density, (12, 4, 12)
    )
    diagram_share = DIAGRAM_SHARE_MAP.get(intensity, 0.50)

    return Budgets(
        max_nodes=max_nodes,
        bullets=bullets,
        words_per_bullet=words_per_bullet,
        diagram_share=diagram_share,
    )
