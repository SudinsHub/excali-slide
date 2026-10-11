"""Page layout implementations for Excalidraw slide types."""

from __future__ import annotations

from typing import Any

from app.compiler.layouts.diagram import layout_diagram
from app.compiler.layouts.diagram.rect import Rect
from app.compiler.palette import DEFAULT_TEXT, MUTED_TEXT
from app.compiler.skeleton import SkeletonBuilder
from app.compiler.text_metrics import measure, wrap
from app.ir.schemas import DiagramBlock, ImageBlock, SlideIR, TextBlock


class CompileCtx:
    """Context holding asset dimensions and runtime configuration."""

    def __init__(self, asset_dims: dict[str, tuple[int, int]] | None = None) -> None:
        self.asset_dims = asset_dims or {}


def layout_page(ir: SlideIR, ctx: CompileCtx | None = None) -> tuple[dict[str, Any], list[str]]:
    """Assemble a complete Excalidraw element skeleton for the specified slide layout.

    Returns (skeleton_dict, warnings).
    """
    ctx = ctx or CompileCtx()
    builder = SkeletonBuilder(width=1920, height=1080)
    warnings: list[str] = []

    layout = ir.layout

    # Common Title for standard pages
    if layout not in ("cover", "section", "statement", "closing") and ir.title:
        wrapped_title = "\n".join(wrap(ir.title, font_size=64.0, max_width=1680.0))
        tw, th = measure(wrapped_title, 64.0)
        builder.text(
            id="title",
            text=wrapped_title,
            x=120.0,
            y=90.0,
            width=1680.0,
            height=th,
            font_size=64.0,
            stroke_color=DEFAULT_TEXT,
            text_align="left",
            vertical_align="top",
        )

    if layout == "cover":
        # Cover layout: title 88 centered around y=400, underline, subtitle 40
        assert ir.title and ir.subtitle
        wrapped_title = "\n".join(wrap(ir.title, font_size=88.0, max_width=1600.0))
        tw, th = measure(wrapped_title, 88.0)
        title_y = max(180.0, 400.0 - th / 2.0)
        builder.text(
            id="title",
            text=wrapped_title,
            x=160.0,
            y=title_y,
            width=1600.0,
            height=th,
            font_size=88.0,
            stroke_color=DEFAULT_TEXT,
            text_align="center",
            vertical_align="middle",
        )

        # Hand-drawn accent underline
        line_y = title_y + th + 18.0
        line_w = min(1600.0, max(300.0, tw * 0.95))
        line_x = (1920.0 - line_w) / 2.0
        builder.line(
            id="title_underline",
            x=line_x,
            y=line_y,
            width=line_w,
            height=5.0,
            points=[[0.0, 0.0], [line_w * 0.5, 4.0], [line_w, 1.0]],
            stroke_color="#f08c00",
            stroke_width=4,
        )

        # Subtitle
        wrapped_sub = "\n".join(wrap(ir.subtitle, font_size=40.0, max_width=1500.0))
        sw, sh = measure(wrapped_sub, 40.0)
        builder.text(
            id="subtitle",
            text=wrapped_sub,
            x=210.0,
            y=line_y + 36.0,
            width=1500.0,
            height=sh,
            font_size=40.0,
            stroke_color=MUTED_TEXT,
            text_align="center",
            vertical_align="top",
        )

    elif layout == "section":
        # Section layout: title 96 at vertical center with accent ellipse marker
        assert ir.title
        wrapped_title = "\n".join(wrap(ir.title, font_size=96.0, max_width=1480.0))
        tw, th = measure(wrapped_title, 96.0)
        title_y = max(200.0, 540.0 - th / 2.0)

        # Accent marker
        builder.shape(
            id="section_marker",
            shape_type="ellipse",
            x=140.0,
            y=title_y + 32.0,
            width=28.0,
            height=28.0,
            stroke_color="#f08c00",
            background_color="#ffec99",
            fill_style="solid",
            stroke_width=3,
        )

        builder.text(
            id="title",
            text=wrapped_title,
            x=200.0,
            y=title_y,
            width=1480.0,
            height=th,
            font_size=96.0,
            stroke_color=DEFAULT_TEXT,
            text_align="left",
            vertical_align="middle",
        )

    elif layout == "statement":
        # Statement layout: optional small title, big quote/paragraph at 64
        if ir.title:
            tw, th = measure(ir.title, 40.0)
            builder.text(
                id="title",
                text=ir.title,
                x=120.0,
                y=100.0,
                width=1680.0,
                height=th,
                font_size=40.0,
                stroke_color=MUTED_TEXT,
                text_align="left",
            )

        tb = next(b for b in ir.blocks if isinstance(b, TextBlock))
        text_content = tb.items[0]
        wrapped_stmt = "\n".join(wrap(text_content, font_size=64.0, max_width=1400.0))
        sw, sh = measure(wrapped_stmt, 64.0)

        stmt_x = 260.0
        stmt_y = max(240.0, 540.0 - sh / 2.0)

        if tb.style == "quote":
            # Oversized opening quote positioned above-left of text
            builder.text(
                id="quote_glyph",
                text="“",
                x=stmt_x - 90.0,
                y=stmt_y - 100.0,
                width=80.0,
                height=90.0,
                font_size=120.0,
                stroke_color="#adb5bd",
            )

        builder.text(
            id="statement_text",
            text=wrapped_stmt,
            x=stmt_x,
            y=stmt_y,
            width=1400.0,
            height=sh,
            font_size=64.0,
            stroke_color=DEFAULT_TEXT,
            text_align="center",
            vertical_align="middle",
        )

    elif layout == "text":
        # Text layout: bullets at font 40 -> 36 -> 32 -> 28
        tb_blocks = [b for b in ir.blocks if isinstance(b, TextBlock)]
        font_candidates = [40.0, 36.0, 32.0, 28.0]
        chosen_font = 28.0
        chosen_gap = 28.0

        for f in font_candidates:
            gap = 28.0 if f >= 36 else 20.0
            total_h = 0.0
            for b in tb_blocks:
                for item in b.items:
                    lines = wrap(item, font_size=f, max_width=1600.0)
                    _, ih = measure("\n".join(lines), f)
                    total_h += ih + gap
            if 250.0 + total_h <= 980.0:
                chosen_font = f
                chosen_gap = gap
                break
        else:
            # Check if exceeds 980 at font 28
            total_h = sum(
                measure("\n".join(wrap(it, 28.0, 1600.0)), 28.0)[1] + 20.0
                for b in tb_blocks
                for it in b.items
            )
            if 250.0 + total_h > 1020.0:
                raise ValueError("text_overflow: Text content exceeds available frame height even at font 28")

        curr_y = 250.0
        for b_idx, tb in enumerate(tb_blocks):
            for i_idx, item in enumerate(tb.items):
                prefix = f"{i_idx + 1}.  " if tb.style == "numbered" else "•  "
                lines = wrap(f"{prefix}{item}", font_size=chosen_font, max_width=1640.0)
                bullet_str = "\n".join(lines)
                bw, bh = measure(bullet_str, chosen_font)

                builder.text(
                    id=f"b{b_idx}_i{i_idx}",
                    text=bullet_str,
                    x=140.0,
                    y=curr_y,
                    width=bw,
                    height=bh,
                    font_size=chosen_font,
                    stroke_color=DEFAULT_TEXT,
                    text_align="left",
                )
                curr_y += bh + chosen_gap

    elif layout == "two_column":
        # Two equal columns (each 800 wide, 80 gap)
        tb_blocks = [b for b in ir.blocks if isinstance(b, TextBlock)]
        col_w = 800.0
        gap = 80.0

        for c_idx, tb in enumerate(tb_blocks[:2]):
            col_x = 120.0 + c_idx * (col_w + gap)
            curr_y = 240.0

            # Heading (font 44 accent color)
            if tb.heading:
                hw, hh = measure(tb.heading, 44.0)
                builder.text(
                    id=f"col_heading_{c_idx}",
                    text=tb.heading,
                    x=col_x,
                    y=curr_y,
                    width=col_w,
                    height=hh,
                    font_size=44.0,
                    stroke_color="#f08c00",
                    text_align="left",
                )
                curr_y += hh + 24.0

            # Column bullets
            for i_idx, item in enumerate(tb.items):
                prefix = f"{i_idx + 1}.  " if tb.style == "numbered" else "•  "
                lines = wrap(f"{prefix}{item}", font_size=34.0, max_width=col_w)
                bullet_str = "\n".join(lines)
                bw, bh = measure(bullet_str, 34.0)

                builder.text(
                    id=f"c{c_idx}_i{i_idx}",
                    text=bullet_str,
                    x=col_x,
                    y=curr_y,
                    width=col_w,
                    height=bh,
                    font_size=34.0,
                    stroke_color=DEFAULT_TEXT,
                    text_align="left",
                )
                curr_y += bh + 20.0

    elif layout == "split":
        # Split layout: text panel (640 wide) + diagram panel (980 wide)
        tb = next(b for b in ir.blocks if isinstance(b, TextBlock))
        db = next(b for b in ir.blocks if isinstance(b, DiagramBlock))
        text_side = ir.text_side or "left"

        text_w = 640.0
        diag_w = 980.0
        gap = 60.0

        if text_side == "left":
            text_x = 120.0
            diag_x = 120.0 + text_w + gap
        else:
            diag_x = 120.0
            text_x = 120.0 + diag_w + gap

        # Render text side
        curr_y = 250.0
        if tb.heading:
            hw, hh = measure(tb.heading, 38.0)
            builder.text(
                id="split_text_heading",
                text=tb.heading,
                x=text_x,
                y=curr_y,
                width=text_w,
                height=hh,
                font_size=38.0,
                stroke_color="#f08c00",
            )
            curr_y += hh + 20.0

        for i_idx, item in enumerate(tb.items):
            prefix = f"{i_idx + 1}.  " if tb.style == "numbered" else "•  "
            lines = wrap(f"{prefix}{item}", font_size=34.0, max_width=text_w)
            bullet_str = "\n".join(lines)
            bw, bh = measure(bullet_str, 34.0)

            builder.text(
                id=f"split_t_i{i_idx}",
                text=bullet_str,
                x=text_x,
                y=curr_y,
                width=text_w,
                height=bh,
                font_size=34.0,
                stroke_color=DEFAULT_TEXT,
            )
            curr_y += bh + 20.0

        # Render diagram side
        diag_region = Rect(diag_x, 240.0, diag_w, 750.0)
        diag_layout = layout_diagram(db, diag_region, ctx)
        for el in diag_layout.elements:
            builder._register_id(el["id"])
            builder.elements.append(el)
        warnings.extend(diag_layout.warnings)

    elif layout == "image_text":
        # Image + text: 780x640 box on image_side, text panel 840 wide
        ib = next(b for b in ir.blocks if isinstance(b, ImageBlock))
        tb = next(b for b in ir.blocks if isinstance(b, TextBlock))
        image_side = ir.image_side or "left"

        box_w = 780.0
        box_h = 640.0
        text_w = 840.0
        gap = 60.0

        if image_side == "left":
            img_box_x = 120.0
            text_x = 120.0 + box_w + gap
        else:
            text_x = 120.0
            img_box_x = 120.0 + text_w + gap

        # Image sizing based on natural dimensions from ctx
        nat_w, nat_h = ctx.asset_dims.get(ib.asset_id, (780, 640))
        scale = min(box_w / nat_w, box_h / nat_h, 1.0)
        img_w = round(nat_w * scale, 1)
        img_h = round(nat_h * scale, 1)

        img_x = img_box_x + (box_w - img_w) / 2.0
        img_y = 250.0 + (box_h - img_h) / 2.0

        builder.image(
            id="img_element",
            file_id=ib.asset_id,
            x=img_x,
            y=img_y,
            width=img_w,
            height=img_h,
        )

        if ib.caption:
            lines = wrap(ib.caption, font_size=24.0, max_width=box_w)
            cap_str = "\n".join(lines)
            cw, ch = measure(cap_str, 24.0)
            builder.text(
                id="img_caption",
                text=cap_str,
                x=img_box_x,
                y=img_y + img_h + 14.0,
                width=box_w,
                height=ch,
                font_size=24.0,
                stroke_color=MUTED_TEXT,
                text_align="center",
            )

        # Text panel
        curr_y = 250.0
        for i_idx, item in enumerate(tb.items):
            prefix = f"{i_idx + 1}.  " if tb.style == "numbered" else "•  "
            lines = wrap(f"{prefix}{item}", font_size=36.0, max_width=text_w)
            bullet_str = "\n".join(lines)
            bw, bh = measure(bullet_str, 36.0)

            builder.text(
                id=f"it_i{i_idx}",
                text=bullet_str,
                x=text_x,
                y=curr_y,
                width=text_w,
                height=bh,
                font_size=36.0,
                stroke_color=DEFAULT_TEXT,
            )
            curr_y += bh + 24.0

    elif layout == "closing":
        # Closing layout: like cover with optional bullets <= 3 at 36 below
        assert ir.title and ir.subtitle
        wrapped_title = "\n".join(wrap(ir.title, font_size=88.0, max_width=1600.0))
        tw, th = measure(wrapped_title, 88.0)
        title_y = 300.0
        builder.text(
            id="title",
            text=wrapped_title,
            x=160.0,
            y=title_y,
            width=1600.0,
            height=th,
            font_size=88.0,
            stroke_color=DEFAULT_TEXT,
            text_align="center",
            vertical_align="middle",
        )

        line_y = title_y + th + 18.0
        line_w = min(1600.0, max(300.0, tw * 0.95))
        line_x = (1920.0 - line_w) / 2.0
        builder.line(
            id="title_underline",
            x=line_x,
            y=line_y,
            width=line_w,
            height=5.0,
            points=[[0.0, 0.0], [line_w * 0.5, 4.0], [line_w, 1.0]],
            stroke_color="#f08c00",
            stroke_width=4,
        )

        wrapped_sub = "\n".join(wrap(ir.subtitle, font_size=40.0, max_width=1500.0))
        sw, sh = measure(wrapped_sub, 40.0)
        curr_y = line_y + 36.0
        builder.text(
            id="subtitle",
            text=wrapped_sub,
            x=210.0,
            y=curr_y,
            width=1500.0,
            height=sh,
            font_size=40.0,
            stroke_color=MUTED_TEXT,
            text_align="center",
            vertical_align="top",
        )
        curr_y += sh + 40.0

        # Optional bullets
        tb_blocks = [b for b in ir.blocks if isinstance(b, TextBlock)]
        if tb_blocks:
            tb = tb_blocks[0]
            for i_idx, item in enumerate(tb.items[:3]):
                lines = wrap(f"•  {item}", font_size=36.0, max_width=1200.0)
                bullet_str = "\n".join(lines)
                bw, bh = measure(bullet_str, 36.0)
                builder.text(
                    id=f"close_i{i_idx}",
                    text=bullet_str,
                    x=360.0,
                    y=curr_y,
                    width=1200.0,
                    height=bh,
                    font_size=36.0,
                    stroke_color=DEFAULT_TEXT,
                    text_align="center",
                )
                curr_y += bh + 20.0

    elif layout == "diagram":
        # Diagram layout: title + diagram engine over full region
        db = next(b for b in ir.blocks if isinstance(b, DiagramBlock))
        region = Rect(120.0, 240.0, 1680.0, 760.0)
        diag_layout = layout_diagram(db, region, ctx)
        for el in diag_layout.elements:
            builder._register_id(el["id"])
            builder.elements.append(el)
        warnings.extend(diag_layout.warnings)

    frame_name = ir.title or ir.slide_key
    skeleton = builder.build(frame_name=frame_name)
    return skeleton, warnings
