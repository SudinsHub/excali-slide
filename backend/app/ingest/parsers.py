import io
import logging

from PIL import Image

logger = logging.getLogger("ingest.parsers")


def process_image_bytes(raw_bytes: bytes, min_dim: int = 0) -> tuple[bytes, str, int, int] | None:
    """Open an image, verify dimensions >= min_dim, downscale to long side <= 1600 px.

    Returns (processed_bytes, mime, width, height) or None if below min_dim or corrupt.
    """
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            w, h = img.size
            if min_dim > 0 and (w < min_dim or h < min_dim):
                return None

            # Downscale if long side exceeds 1600 px
            if max(w, h) > 1600:
                scale = 1600.0 / max(w, h)
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                w, h = img.size

            # Ensure compatible color format
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA" if "A" in img.mode else "RGB")

            buf = io.BytesIO()
            if img.mode == "RGBA":
                img.save(buf, format="PNG")
                mime = "image/png"
            else:
                img.save(buf, format="JPEG", quality=90)
                mime = "image/jpeg"

            return buf.getvalue(), mime, w, h
    except Exception as e:
        logger.warning(f"Failed to process image: {e}")
        return None


def parse_md_txt(raw_bytes: bytes) -> tuple[str, list[tuple[bytes, str]]]:
    """Parse Markdown or plain text files."""
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = raw_bytes.decode("latin-1", errors="replace")
    return text, []


def parse_pdf(raw_bytes: bytes) -> tuple[str, list[tuple[bytes, str]]]:
    """Parse PDF document: page text with markers and embedded images >= 200x200 px."""
    import pypdf

    reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
    page_texts: list[str] = []
    extracted_images: list[tuple[bytes, str]] = []

    for i, page in enumerate(reader.pages, start=1):
        txt = (page.extract_text() or "").strip()
        page_texts.append(f"--- page {i} ---\n{txt}")

        try:
            for img_file in page.images:
                locator = f"page {i}"
                extracted_images.append((img_file.data, locator))
        except Exception as e:
            logger.warning(f"Error extracting images from PDF page {i}: {e}")

    return "\n\n".join(page_texts), extracted_images


def parse_docx(raw_bytes: bytes) -> tuple[str, list[tuple[bytes, str]]]:
    """Parse DOCX document: headings with # markers, tables as pipe rows, inline images."""
    import docx

    doc = docx.Document(io.BytesIO(raw_bytes))
    lines: list[str] = []

    for p in doc.paragraphs:
        txt = p.text.strip()
        if not txt:
            continue
        style_name = p.style.name.lower() if p.style and p.style.name else ""
        if "heading 1" in style_name:
            lines.append(f"# {txt}")
        elif "heading 2" in style_name:
            lines.append(f"## {txt}")
        elif "heading 3" in style_name:
            lines.append(f"### {txt}")
        elif "heading" in style_name:
            lines.append(f"#### {txt}")
        else:
            lines.append(txt)

    for table in doc.tables:
        for row in table.rows:
            cell_texts = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            lines.append("| " + " | ".join(cell_texts) + " |")

    extracted_images: list[tuple[bytes, str]] = []
    try:
        for rel in doc.part.related_parts.values():
            if rel.content_type.startswith("image/"):
                extracted_images.append((rel.blob, "inline"))
    except Exception as e:
        logger.warning(f"Error extracting images from DOCX: {e}")

    return "\n\n".join(lines), extracted_images


def parse_pptx(raw_bytes: bytes) -> tuple[str, list[tuple[bytes, str]]]:
    """Parse PPTX presentation: slide titles, text frames in reading order, tables, notes, shape pictures."""
    import pptx

    prs = pptx.Presentation(io.BytesIO(raw_bytes))
    slide_texts: list[str] = []
    extracted_images: list[tuple[bytes, str]] = []

    for i, slide in enumerate(prs.slides, start=1):
        lines: list[str] = [f"--- slide {i} ---"]

        # Sort shapes top-to-bottom, left-to-right for consistent reading order
        shapes = sorted(slide.shapes, key=lambda s: (getattr(s, "top", 0), getattr(s, "left", 0)))

        for shape in shapes:
            if shape.has_text_frame:
                txt = shape.text_frame.text.strip()
                if txt:
                    lines.append(txt)
            elif shape.has_table:
                for row in shape.table.rows:
                    cell_texts = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                    lines.append("| " + " | ".join(cell_texts) + " |")

            # Extract pictures
            try:
                if hasattr(shape, "image"):
                    extracted_images.append((shape.image.blob, f"slide {i}"))
            except Exception:
                pass

        # Slide notes
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                lines.append(f"Notes: {notes}")

        slide_texts.append("\n".join(lines))

    return "\n\n".join(slide_texts), extracted_images


def parse_image(raw_bytes: bytes) -> tuple[str, list[tuple[bytes, str]]]:
    """Parse uploaded image file itself as an image asset."""
    return "", [(raw_bytes, "file")]


PARSERS = {
    "md": parse_md_txt,
    "text": parse_md_txt,
    "pdf": parse_pdf,
    "docx": parse_docx,
    "pptx": parse_pptx,
    "image": parse_image,
}
