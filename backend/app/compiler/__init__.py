"""Compiler entrypoint transforming SlideIR into deterministic Excalidraw skeletons."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.compiler.layouts.page import CompileCtx, layout_page
from app.compiler.quality import check_quality
from app.ir.schemas import DiagramBlock, SlideIR
from app.ir.validators import validate_ir


class CompileStats(BaseModel):
    node_count: int = 0
    element_count: int = 0
    min_font_used: float = 0.0
    bounding_box: dict[str, float] = Field(default_factory=dict)


class CompileResult(BaseModel):
    skeleton: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    stats: CompileStats = Field(default_factory=CompileStats)


def compile(ir: SlideIR, ctx: CompileCtx | None = None) -> CompileResult:
    """Compile a semantic SlideIR into a production Excalidraw element skeleton.

    Pure, deterministic function with zero I/O.
    1. Validates IR (validation errors immediately short-circuit with skeleton=None).
    2. Executes page and diagram geometry layout.
    3. Runs automated quality gate.
    4. Gathers statistics.
    """
    ctx = ctx or CompileCtx()
    all_warnings: list[str] = []
    all_errors: list[str] = []

    # 1. Validate IR
    ir_issues = validate_ir(ir)
    validation_errors = [i for i in ir_issues if i.severity == "error"]
    validation_warnings = [i for i in ir_issues if i.severity == "warning"]

    for w in validation_warnings:
        all_warnings.append(f"{w.path}: {w.message}")

    if validation_errors:
        for err in validation_errors:
            all_errors.append(f"{err.path}: {err.message}")
        return CompileResult(
            skeleton=None,
            warnings=all_warnings,
            errors=all_errors,
            stats=CompileStats(),
        )

    # 2. Page & Diagram Layout
    try:
        skeleton, page_warnings = layout_page(ir, ctx)
        all_warnings.extend(page_warnings)
    except Exception as exc:
        all_errors.append(str(exc))
        return CompileResult(
            skeleton=None,
            warnings=all_warnings,
            errors=all_errors,
            stats=CompileStats(),
        )

    # 3. Quality Gate
    quality_issues = check_quality(skeleton, ir)
    for qi in quality_issues:
        msg = f"{qi.code}: {qi.message}"
        if qi.severity == "error":
            all_errors.append(msg)
        else:
            all_warnings.append(msg)

    # 4. Compute Statistics
    elements = skeleton.get("elements", [])
    node_count = sum(
        len(b.nodes) for b in ir.blocks if isinstance(b, DiagramBlock)
    )

    fonts = []
    min_x, min_y = 1920.0, 1080.0
    max_x, max_y = 0.0, 0.0

    for el in elements[1:]:
        f = el.get("fontSize")
        if f:
            fonts.append(float(f))
        lbl = el.get("label")
        if isinstance(lbl, dict) and lbl.get("fontSize"):
            fonts.append(float(lbl["fontSize"]))

        x = el.get("x", 0.0)
        y = el.get("y", 0.0)
        w = el.get("width", 0.0)
        h = el.get("height", 0.0)
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x + w)
        max_y = max(max_y, y + h)

    min_font = min(fonts) if fonts else 28.0
    bb_dict = {
        "x": round(min_x, 1) if min_x < 1920.0 else 0.0,
        "y": round(min_y, 1) if min_y < 1080.0 else 0.0,
        "w": round(max_x - min_x, 1) if max_x > min_x else 0.0,
        "h": round(max_y - min_y, 1) if max_y > min_y else 0.0,
    }

    stats = CompileStats(
        node_count=node_count,
        element_count=len(elements),
        min_font_used=min_font,
        bounding_box=bb_dict,
    )

    return CompileResult(
        skeleton=skeleton,
        warnings=all_warnings,
        errors=all_errors,
        stats=stats,
    )


__all__ = ["CompileCtx", "CompileResult", "CompileStats", "compile"]
